"""
R2 Upload Library - Python module for integration into other skills
"""

import hashlib
import hmac
import datetime
import os
import urllib.request
import uuid
from urllib.parse import quote

def load_config(config_path=None):
    """Load R2/S3 configuration from YAML file"""
    import yaml
    
    if config_path is None:
        config_path = os.environ.get('R2_UPLOAD_CONFIG', os.path.expanduser('~/.r2-upload.yml'))
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(secret, date_stamp, region, service):
    k_date = sign(('AWS4' + secret).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, 'aws4_request')
    return k_signing

def upload_file(local_path, key=None, bucket=None, make_public=False, config=None):
    """
    Upload a file to R2/S3 storage
    
    Args:
        local_path: Path to local file
        key: Storage key/path (optional, auto-generated if not provided)
        bucket: Bucket name (optional, uses default from config)
        make_public: If True, returns public URL; otherwise returns presigned URL
        config: Configuration dict (optional, loaded from file if not provided)
    
    Returns:
        str: URL of uploaded file
    """
    if config is None:
        config = load_config()
    
    bucket_name = bucket or config.get('default')
    bucket_config = config['buckets'][bucket_name]
    
    with open(local_path, 'rb') as f:
        data = f.read()
    
    if key is None:
        filename = os.path.basename(local_path)
        key = f'{uuid.uuid4().hex[:8]}/{filename}'
    
    # Content type detection
    content_type = 'application/octet-stream'
    ext = os.path.splitext(local_path)[1].lower()
    type_map = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp',
        '.gif': 'image/gif', '.pdf': 'application/pdf',
        '.md': 'text/markdown', '.txt': 'text/plain',
        '.json': 'application/json', '.yaml': 'text/yaml',
        '.yml': 'text/yaml'
    }
    content_type = type_map.get(ext, content_type)
    
    endpoint = bucket_config['endpoint'].rstrip('/')
    access_key = bucket_config['access_key_id']
    secret_key = bucket_config['secret_access_key']
    bucket_name = bucket_config['bucket_name']
    public_url = bucket_config.get('public_url', endpoint)
    region = bucket_config.get('region', 'auto')
    
    t = datetime.datetime.now(datetime.timezone.utc)
    date_stamp = t.strftime('%Y%m%d')
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    
    payload_hash = hashlib.sha256(data).hexdigest()
    
    headers = {
        'host': endpoint.replace('https://', '').replace('http://', ''),
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amz_date,
        'content-type': content_type,
    }
    
    canonical_uri = f'/{bucket_name}/{key}'
    canonical_headers = ''.join([f'{k}:{v}\n' for k, v in sorted(headers.items())])
    signed_headers = ';'.join(sorted(headers.keys()))
    
    canonical_request = f'PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
    
    credential_scope = f'{date_stamp}/{region}/s3/aws4_request'
    string_to_sign = f'AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}'
    
    signing_key = get_signature_key(secret_key, date_stamp, region, 's3')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    auth_header = f'AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
    
    url = f'{endpoint}/{bucket_name}/{quote(key)}'
    req = urllib.request.Request(
        url,
        data=data,
        method='PUT',
        headers={**headers, 'Authorization': auth_header}
    )
    
    with urllib.request.urlopen(req) as resp:
        if resp.status == 200:
            return f'{public_url}/{key}'
        raise Exception(f'Upload failed: HTTP {resp.status}')

def batch_upload(files, key_prefix='', bucket=None, make_public=False):
    """
    Upload multiple files
    
    Args:
        files: List of local file paths
        key_prefix: Prefix for all keys
        bucket: Bucket name
        make_public: Generate public URLs
    
    Returns:
        List of URLs
    """
    config = load_config()
    urls = []
    for file_path in files:
        filename = os.path.basename(file_path)
        key = f'{key_prefix}{filename}' if key_prefix else None
        url = upload_file(file_path, key=key, bucket=bucket, make_public=make_public, config=config)
        urls.append(url)
    return urls

def fetch_and_upload(image_url, key, bucket=None, make_public=False):
    """
    Download image from URL and upload to R2/S3
    
    Args:
        image_url: URL to download
        key: Storage key
        bucket: Bucket name
        make_public: Generate public URL
    
    Returns:
        str: Public URL of uploaded file
    """
    import tempfile
    
    # Download to temp file
    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        ext = os.path.splitext(image_url.split('?')[0])[1] or '.jpg'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(data)
            temp_path = f.name
    
    try:
        url = upload_file(temp_path, key=key, bucket=bucket, make_public=make_public)
        return url
    finally:
        os.unlink(temp_path)
