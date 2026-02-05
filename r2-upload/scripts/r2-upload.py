#!/usr/bin/env python3
"""
R2 Upload Script - Command line tool for uploading files to R2/S3
Usage: python3 r2-upload.py <file> [--key path] [--bucket name] [--public]
"""

import argparse
import hashlib
import hmac
import datetime
import os
import sys
import urllib.request
import yaml
from pathlib import Path
from urllib.parse import quote

def load_config():
    """Load configuration from ~/.r2-upload.yml"""
    config_path = os.environ.get('R2_UPLOAD_CONFIG', os.path.expanduser('~/.r2-upload.yml'))
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
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

def upload_file(local_path, key, bucket_config, make_public=False):
    """Upload a file to S3-compatible storage"""
    with open(local_path, 'rb') as f:
        data = f.read()
    
    # Determine content type
    content_type = 'application/octet-stream'
    if local_path.endswith(('.jpg', '.jpeg')):
        content_type = 'image/jpeg'
    elif local_path.endswith('.png'):
        content_type = 'image/png'
    elif local_path.endswith('.webp'):
        content_type = 'image/webp'
    elif local_path.endswith('.gif'):
        content_type = 'image/gif'
    elif local_path.endswith('.pdf'):
        content_type = 'application/pdf'
    elif local_path.endswith('.md'):
        content_type = 'text/markdown'
    
    endpoint = bucket_config['endpoint'].rstrip('/')
    access_key = bucket_config['access_key_id']
    secret_key = bucket_config['secret_access_key']
    bucket_name = bucket_config['bucket_name']
    public_url = bucket_config.get('public_url', endpoint)
    region = bucket_config.get('region', 'auto')
    
    # Generate timestamp
    t = datetime.datetime.now(datetime.timezone.utc)
    date_stamp = t.strftime('%Y%m%d')
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    
    # Create canonical request
    payload_hash = hashlib.sha256(data).hexdigest()
    
    headers = {
        'host': endpoint.replace('https://', '').replace('http://', ''),
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amz_date,
        'content-type': content_type,
    }
    
    canonical_uri = f'/{bucket_name}/{key}'
    canonical_querystring = ''
    canonical_headers = ''.join([f'{k}:{v}\n' for k, v in sorted(headers.items())])
    signed_headers = ';'.join(sorted(headers.keys()))
    
    canonical_request = f'PUT\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
    
    # Create string to sign
    credential_scope = f'{date_stamp}/{region}/s3/aws4_request'
    string_to_sign = f'AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}'
    
    # Calculate signature
    signing_key = get_signature_key(secret_key, date_stamp, region, 's3')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # Create authorization header
    auth_header = f'AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
    
    # Make request
    url = f'{endpoint}/{bucket_name}/{quote(key)}'
    req = urllib.request.Request(
        url,
        data=data,
        method='PUT',
        headers={**headers, 'Authorization': auth_header}
    )
    
    with urllib.request.urlopen(req) as resp:
        if resp.status == 200:
            if make_public:
                return f'{public_url}/{key}'
            else:
                # Generate presigned URL
                return generate_presigned_url(key, bucket_config)
        else:
            raise Exception(f'Upload failed: HTTP {resp.status}')

def generate_presigned_url(key, bucket_config, expires=300):
    """Generate a presigned URL for temporary access"""
    endpoint = bucket_config['endpoint'].rstrip('/')
    public_url = bucket_config.get('public_url', endpoint)
    return f'{public_url}/{key}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...'

def main():
    parser = argparse.ArgumentParser(description='Upload files to R2/S3 storage')
    parser.add_argument('file', help='File to upload')
    parser.add_argument('--key', help='Custom key/path for the file')
    parser.add_argument('--bucket', help='Bucket to use')
    parser.add_argument('--public', action='store_true', help='Generate public URL')
    parser.add_argument('--expires', type=int, default=300, help='Presigned URL expiration (seconds)')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Determine bucket
    bucket_name = args.bucket or config.get('default')
    if not bucket_name:
        print('Error: No bucket specified', file=sys.stderr)
        sys.exit(1)
    
    bucket_config = config['buckets'].get(bucket_name)
    if not bucket_config:
        print(f'Error: Bucket "{bucket_name}" not found in config', file=sys.stderr)
        sys.exit(1)
    
    # Generate key if not provided
    key = args.key
    if not key:
        filename = os.path.basename(args.file)
        import uuid
        key = f'{uuid.uuid4().hex[:8]}/{filename}'
    
    # Upload
    try:
        url = upload_file(args.file, key, bucket_config, args.public)
        print(url)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
