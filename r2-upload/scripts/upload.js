/**
 * R2 Upload Library - Node.js module for integration into other skills
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { URL } = require('url');

function loadConfig(configPath) {
    const yaml = require('yaml');
    if (!configPath) {
        configPath = process.env.R2_UPLOAD_CONFIG || path.join(process.env.HOME, '.r2-upload.yml');
    }
    return yaml.parse(fs.readFileSync(configPath, 'utf8'));
}

function sign(key, msg) {
    return crypto.createHmac('sha256', key).update(msg).digest();
}

function getSignatureKey(secret, dateStamp, region, service) {
    const kDate = sign(Buffer.from('AWS4' + secret), dateStamp);
    const kRegion = sign(kDate, region);
    const kService = sign(kRegion, service);
    return sign(kService, 'aws4_request');
}

function getContentType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.gif': 'image/gif', '.pdf': 'application/pdf',
        '.md': 'text/markdown'
    };
    return types[ext] || 'application/octet-stream';
}

async function uploadFile({ localPath, key, bucket, makePublic = false, config }) {
    if (!config) config = loadConfig();
    
    const bucketName = bucket || config.default;
    const bucketConfig = config.buckets[bucketName];
    
    const data = fs.readFileSync(localPath);
    const contentType = getContentType(localPath);
    
    const endpoint = bucketConfig.endpoint.replace(/\/$/, '');
    const accessKey = bucketConfig.access_key_id;
    const secretKey = bucketConfig.secret_access_key;
    const bucketNameActual = bucketConfig.bucket_name;
    const publicUrl = bucketConfig.public_url || endpoint;
    const region = bucketConfig.region || 'auto';
    
    if (!key) {
        const filename = path.basename(localPath);
        const uuid = crypto.randomUUID().slice(0, 8);
        key = `${uuid}/${filename}`;
    }
    
    const now = new Date();
    const dateStamp = now.toISOString().slice(0, 10).replace(/-/g, '');
    const amzDate = dateStamp + 'T' + now.toISOString().slice(11, 19).replace(/:/g, '') + 'Z';
    
    const payloadHash = crypto.createHash('sha256').update(data).digest('hex');
    
    const headers = {
        'host': endpoint.replace(/^https?:\/\//, ''),
        'x-amz-content-sha256': payloadHash,
        'x-amz-date': amzDate,
        'content-type': contentType,
    };
    
    const canonicalUri = `/${bucketNameActual}/${key}`;
    const canonicalHeaders = Object.entries(headers)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => `${k}:${v}\n`)
        .join('');
    const signedHeaders = Object.keys(headers).sort().join(';');
    
    const canonicalRequest = `PUT\n${canonicalUri}\n\n${canonicalHeaders}\n${signedHeaders}\n${payloadHash}`;
    
    const credentialScope = `${dateStamp}/${region}/s3/aws4_request`;
    const stringToSign = `AWS4-HMAC-SHA256\n${amzDate}\n${credentialScope}\n${crypto.createHash('sha256').update(canonicalRequest).digest('hex')}`;
    
    const signingKey = getSignatureKey(secretKey, dateStamp, region, 's3');
    const signature = crypto.createHmac('sha256', signingKey).update(stringToSign).digest('hex');
    
    const authHeader = `AWS4-HMAC-SHA256 Credential=${accessKey}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;
    
    return new Promise((resolve, reject) => {
        const url = new URL(`${endpoint}${canonicalUri}`);
        const options = {
            hostname: url.hostname,
            port: url.port || 443,
            path: url.pathname + url.search,
            method: 'PUT',
            headers: {
                ...headers,
                'Authorization': authHeader,
                'Content-Length': data.length
            }
        };
        
        const req = https.request(options, (res) => {
            if (res.statusCode === 200) {
                resolve(`${publicUrl}/${key}`);
            } else {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => reject(new Error(`HTTP ${res.statusCode}: ${body}`)));
            }
        });
        
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

async function batchUpload(files, { keyPrefix = '', bucket, makePublic = false }) {
    const config = loadConfig();
    const urls = [];
    for (const filePath of files) {
        const filename = path.basename(filePath);
        const key = keyPrefix ? `${keyPrefix}${filename}` : undefined;
        const url = await uploadFile({ localPath: filePath, key, bucket, makePublic, config });
        urls.push(url);
    }
    return urls;
}

async function fetchAndUpload(imageUrl, { key, bucket, makePublic = false }) {
    const https = require('https');
    const fs = require('fs');
    const os = require('os');
    
    const data = await new Promise((resolve, reject) => {
        const req = https.request(imageUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => resolve(Buffer.concat(chunks)));
        });
        req.on('error', reject);
        req.end();
    });
    
    const ext = path.extname(imageUrl.split('?')[0]) || '.jpg';
    const tempPath = path.join(os.tmpdir(), `r2-upload-${Date.now()}${ext}`);
    fs.writeFileSync(tempPath, data);
    
    try {
        const url = await uploadFile({ localPath: tempPath, key, bucket, makePublic });
        return url;
    } finally {
        fs.unlinkSync(tempPath);
    }
}

module.exports = {
    loadConfig,
    uploadFile,
    batchUpload,
    fetchAndUpload
};
