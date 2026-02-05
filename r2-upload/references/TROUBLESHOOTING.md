# Troubleshooting

Common issues and their solutions.

## Table of contents

- [HTTP 403 Forbidden](#http-403-forbidden)
- [HTTP 400 Bad Request](#http-400-bad-request)
- [HTTP 404 Not Found](#http-404-not-found)
- [Connection timeout](#connection-timeout)
- [Config file not found](#config-file-not-found)
- [PyYAML missing](#pyyaml-missing)
- [Invalid YAML syntax](#invalid-yaml-syntax)
- [Upload succeeds but file not accessible](#upload-succeeds-but-file-not-accessible)
- [Presigned URL expired](#presigned-url-expired)
- [Large file uploads fail](#large-file-uploads-fail)
- [SSL/TLS errors](#ssltls-errors)
- [Debugging tips](#debugging-tips)
- [Getting help](#getting-help)

## HTTP 403 Forbidden

### Symptoms
```
Error: HTTP 403: <?xml version="1.0" ?>
<Error><Code>AccessDenied</Code>...</Error>
```

### Causes and solutions

**1. Invalid credentials**
- Check `access_key_id` and `secret_access_key` in config
- For R2: regenerate API token in Cloudflare dashboard
- For AWS: verify IAM user has correct permissions

**2. Bucket doesn't exist**
- Verify `bucket_name` matches actual bucket name (case-sensitive)
- Create bucket if it doesn't exist

**3. Insufficient permissions**
R2: Ensure API token has "Object Read & Write" permission for the specific bucket

AWS: IAM policy needs these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/*"
    }
  ]
}
```

**4. Wrong endpoint**
- R2: Should be `https://<account_id>.r2.cloudflarestorage.com`
- AWS: Should be `https://s3.<region>.amazonaws.com`

## HTTP 400 Bad Request

### Symptoms
```
Error: HTTP 400: <Error><Code>InvalidRequest</Code>...</Error>
```

### Causes and solutions

**1. Wrong endpoint format**
```yaml
# Wrong
endpoint: https://xxx.r2.cloudflarestorage.com/my-bucket

# Correct
endpoint: https://xxx.r2.cloudflarestorage.com
bucket_name: my-bucket
```

**2. Wrong region**
- R2: Use `region: auto`
- AWS: Use actual region like `us-east-1`, `eu-west-1`

**3. Missing required headers**
- Usually internal error, check script version

## HTTP 404 Not Found

### Symptoms
```
Error: HTTP 404: <Error><Code>NoSuchBucket</Code>...</Error>
```

### Solution
Bucket doesn't exist. Create it first:

**R2:**
```bash
# Via Cloudflare dashboard
# Or using wrangler:
npx wrangler r2 bucket create my-bucket
```

**AWS:**
```bash
aws s3 mb s3://my-bucket --region us-east-1
```

**MinIO:**
```bash
mc mb local/my-bucket
```

## Connection timeout

### Symptoms
```
urllib.error.URLError: <urlopen error [Errno 110] Connection timed out>
```

### Causes and solutions

**1. Network issue**
```bash
# Test connectivity
curl -I https://xxx.r2.cloudflarestorage.com

# Test with longer timeout
python3 scripts/r2-upload.py file.jpg --timeout 60
```

**2. Firewall blocking**
- Ensure outbound HTTPS (port 443) is allowed
- For corporate networks, check proxy settings

**3. DNS resolution failure**
```bash
# Check DNS
nslookup xxx.r2.cloudflarestorage.com

# Use IP if needed (not recommended for production)
```

**4. Local MinIO not running**
```bash
# Check if MinIO is up
docker ps | grep minio

# Start if needed
docker start minio
```

## Config file not found

### Symptoms
```
FileNotFoundError: Config file not found: ~/.r2-upload.yml
```

### Solutions

**1. Create config file**
```bash
cat > ~/.r2-upload.yml << 'EOF'
default: my-bucket

buckets:
  my-bucket:
    endpoint: https://xxx.r2.cloudflarestorage.com
    access_key_id: your_key
    secret_access_key: your_secret
    bucket_name: my-bucket
    region: auto
EOF

chmod 600 ~/.r2-upload.yml
```

**2. Use custom path**
```bash
export R2_UPLOAD_CONFIG=/path/to/custom-config.yml
python3 scripts/r2-upload.py file.jpg
```

**3. Check file permissions**
```bash
# Should be readable by current user
ls -la ~/.r2-upload.yml

# Fix if needed
chmod 600 ~/.r2-upload.yml
```

## PyYAML missing

### Symptoms
```
Error: PyYAML is required. Install with: python3 -m pip install pyyaml
```

### Solution
```bash
python3 -m pip install pyyaml
```

## Invalid YAML syntax

### Symptoms
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

### Solutions

**1. Validate YAML**
```bash
# Using Python
python3 -c "import os,yaml; yaml.safe_load(open(os.path.expanduser('~/.r2-upload.yml')))"

# Using yamllint
yamllint ~/.r2-upload.yml
```

**2. Common mistakes**
```yaml
# Wrong - tabs not allowed
buckets:
	my-bucket:

# Correct - use spaces
buckets:
  my-bucket:

# Wrong - missing space after colon
endpoint:https://...

# Correct
endpoint: https://...
```

## Upload succeeds but file not accessible

### Symptoms
Upload returns URL, but accessing it gives 403/404

### Causes

**1. Public URL misconfigured**
```yaml
# Wrong - missing custom domain
public_url: https://xxx.r2.cloudflarestorage.com

# Correct - if using custom domain
public_url: https://cdn.example.com

# Or if accessing directly
public_url: https://xxx.r2.cloudflarestorage.com
```

**2. Public vs presigned URL mismatch**
The CLI returns a **presigned URL by default**. If you need a CDN/public URL, pass `--public`.

If your bucket is private, presigned URLs are the correct approach. Public URLs will 403 unless the bucket is public or behind a CDN that serves it.

**3. Wrong bucket in URL**
Check that `public_url` includes the bucket name if needed:
```yaml
# For R2 with custom domain
public_url: https://cdn.example.com
# Final URL: https://cdn.example.com/images/file.jpg

# For R2 without custom domain
public_url: https://xxx.r2.cloudflarestorage.com/my-bucket
# Final URL: https://xxx.r2.cloudflarestorage.com/my-bucket/images/file.jpg
```

## Large file uploads fail

### Symptoms
```
MemoryError
# or
Error: Request Entity Too Large
```

### Solutions

**1. Script reads files into memory**
This tool loads the entire file into memory. For very large files, use a provider SDK or CLI with multipart upload.

**2. Stream upload for large files (advanced)**
Modify script to use streaming:
```python
# Instead of reading entire file
data = f.read()

# Use streaming upload
req = urllib.request.Request(..., data=f, method='PUT')
```

**2. Multipart upload for very large files**
For files > 100MB, use S3 multipart upload API

**3. Increase memory (if applicable)**
```bash
ulimit -m 1048576  # 1GB
```

## SSL/TLS errors

### Symptoms
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

### Solutions

**1. Update CA certificates**
```bash
# macOS
brew install ca-certificates

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ca-certificates

# RHEL/CentOS
sudo yum install ca-certificates
```

**2. Self-signed certificates (MinIO)**
```python
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Pass context to urlopen
urllib.request.urlopen(req, context=ctx)
```

## Presigned URL expired

### Symptoms
```
AccessDenied: Request has expired
```

### Solutions

- Increase expiration time (max 7 days):
  ```bash
  python3 scripts/r2-upload.py file.jpg --expires 3600
  ```
- Generate a fresh presigned URL

## Debugging tips

### Enable verbose logging

```python
import http.client
http.client.HTTPConnection.debuglevel = 1
```

### Prefer provider CLIs for validation

```bash
# AWS CLI (works for AWS S3 and many S3-compatible providers)
aws s3 cp test.jpg s3://my-bucket/
```

### Check request signature manually

```python
import hashlib
import hmac
import datetime

# Print canonical request and string to sign
# (Add print statements in upload.py)
print("Canonical Request:", canonical_request)
print("String to Sign:", string_to_sign)
print("Signature:", signature)
```

## Getting help

If issues persist:

1. **Check provider status**
   - R2: https://www.cloudflarestatus.com/
   - AWS: https://status.aws.amazon.com/

2. **Verify with official CLI**
   ```bash
   # Install AWS CLI
   pip install awscli
   
   # Configure and test
   aws configure
   aws s3 cp test.jpg s3://my-bucket/
   ```

3. **Enable request logging in script**
   Add temporary print statements for canonical request and string-to-sign
