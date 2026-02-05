#!/usr/bin/env node
/**
 * R2 Upload Script - Command line tool for uploading files to R2/S3
 * Usage: node r2-upload.js <file> [--key path] [--bucket name] [--public]
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { URL } = require('url');

function loadConfig() {
    const configPath = process.env.R2_UPLOAD_CONFIG || path.join(process.env.HOME, '.r2-upload.yml');
    const yaml = require('yaml');
    return yaml.parse(fs.readFileSync(configPath, 'utf8'));
}

function sign(key, msg) {
    return crypto.createHmac('sha256', key).update(msg).digest();
}

function getSignatureKey(secret, dateStamp, region, service) {
    const kDate = sign(Buffer.from('AWS4' + secret), dateStamp);
    const kRegion = sign(kDate, region);
    const kService = sign(kRegion, service);
    const kSigning = sign(kService, 'aws4_request');
    return kSigning;
}

function getContentType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.gif': 'image/gif', '.pdf': 'application/pdf',
        '.md': 'text/markdown', '.txt': 'text/plain',
        '.json': 'application/json'
    };
    return types[ext] || 'application/octet-stream';
}

async function uploadFile(localPath, key, bucketConfig, makePublic = false) {
    const data = fs.readFileSync(localPath);
    const contentType = getContentType(localPath);
    
    const endpoint = bucketConfig.endpoint.replace(/\/$/, '');
    const accessKey = bucketConfig.access_key_id;
    const secretKey = bucketConfig.secret_access_key;
    const bucketName = bucketConfig.bucket_name;
    const publicUrl = bucketConfig.public_url || endpoint;
    const region = bucketConfig.region || 'auto';
    
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
    
    const canonicalUri = `/${bucketName}/${key}`;
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

function parseArgs() {
    const args = process.argv.slice(2);
    const result = { file: null, key: null, bucket: null, public: false, expires: 300 };
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--key') result.key = args[++i];
        else if (args[i] === '--bucket') result.bucket = args[++i];
        else if (args[i] === '--public') result.public = true;
        else if (args[i] === '--expires') result.expires = parseInt(args[++i]);
        else if (!result.file && !args[i].startsWith('--')) result.file = args[i];
    }
    
    return result;
}

async function main() {
    const args = parseArgs();
    
    if (!args.file) {
        console.error('Usage: node r2-upload.js <file> [--key path] [--bucket name] [--public]');
        process.exit(1);
    }
    
    const config = loadConfig();
    const bucketName = args.bucket || config.default;
    
    if (!bucketName) {
        console.error('Error: No bucket specified');
        process.exit(1);
    }
    
    const bucketConfig = config.buckets[bucketName];
    if (!bucketConfig) {
        console.error(`Error: Bucket "${bucketName}" not found in config`);
        process.exit(1);
    }
    
    let key = args.key;
    if (!key) {
        const filename = path.basename(args.file);
        const uuid = crypto.randomUUID().slice(0, 8);
        key = `${uuid}/${filename}`;
    }
    
    try {
        const url = await uploadFile(args.file, key, bucketConfig, args.public);
        console.log(url);
    } catch (err) {
        console.error(`Error: ${err.message}`);
        process.exit(1);
    }
}

main();
