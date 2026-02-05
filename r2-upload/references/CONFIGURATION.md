# Configuration Reference

Complete configuration examples for different S3-compatible storage providers.

## Cloudflare R2

```yaml
default: my-r2-bucket

buckets:
  my-r2-bucket:
    endpoint: https://<account_id>.r2.cloudflarestorage.com
    access_key_id: your_access_key_id
    secret_access_key: your_secret_access_key
    bucket_name: my-bucket
    public_url: https://cdn.example.com        # Optional: custom domain
    region: auto
```

### Getting R2 credentials

1. Go to Cloudflare Dashboard → R2
2. Create a bucket (or use existing one)
3. Go to R2 API Tokens: `https://dash.cloudflare.com/<account_id>/r2/api-tokens`
4. Create API Token:
   - **Permissions**: Object Read & Write
   - **Bucket**: Select your specific bucket (recommended for security)
5. Copy Access Key ID and Secret Access Key
6. Your Account ID is in the URL: `dash.cloudflare.com/<account_id>/`

### Custom domain (optional)

1. In R2 bucket settings, go to "Custom Domains"
2. Add your domain (e.g., `cdn.example.com`)
3. Add CNAME record pointing to your R2 bucket
4. Wait for SSL certificate provisioning
5. Use the custom domain as `public_url`

## AWS S3

```yaml
default: aws-production

buckets:
  aws-production:
    endpoint: https://s3.us-east-1.amazonaws.com
    access_key_id: AKIAIOSFODNN7EXAMPLE
    secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    bucket_name: my-company-assets
    public_url: https://my-company-assets.s3.amazonaws.com
    region: us-east-1

  aws-backup:
    endpoint: https://s3.eu-west-1.amazonaws.com
    access_key_id: AKIAIOSFODNN7EXAMPLE
    secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    bucket_name: my-company-backups
    region: eu-west-1
```

### S3 permissions required

Your IAM user needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

## MinIO (Self-hosted)

```yaml
default: minio-local

buckets:
  minio-local:
    endpoint: http://localhost:9000
    access_key_id: minioadmin
    secret_access_key: minioadmin
    bucket_name: my-bucket
    public_url: http://localhost:9000/my-bucket
    region: us-east-1

  minio-production:
    endpoint: https://minio.company.internal:9000
    access_key_id: service-account
    secret_access_key: super-secret-key
    bucket_name: production-assets
    public_url: https://assets.company.internal
    region: us-east-1
```

### MinIO setup

```bash
# Start MinIO locally
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Create bucket
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/my-bucket
```

## Backblaze B2

```yaml
default: b2-assets

buckets:
  b2-assets:
    endpoint: https://s3.us-west-002.backblazeb2.com
    access_key_id: your_key_id
    secret_access_key: your_application_key
    bucket_name: my-b2-bucket
    public_url: https://f002.backblazeb2.com/file/my-b2-bucket
    region: us-west-002
```

### B2 S3-compatible keys

1. In B2 console, go to "Application Keys"
2. Create new key with:
   - **Type**: Application Key
   - **Allow access to**: Single bucket or all buckets
   - **Permissions**: Read and Write
3. The "keyID" is your `access_key_id`
4. The "applicationKey" is your `secret_access_key`

## Wasabi

```yaml
default: wasabi-primary

buckets:
  wasabi-primary:
    endpoint: https://s3.us-east-1.wasabisys.com
    access_key_id: your-access-key
    secret_access_key: your-secret-key
    bucket_name: my-wasabi-bucket
    public_url: https://s3.us-east-1.wasabisys.com/my-wasabi-bucket
    region: us-east-1
```

## Multiple buckets

You can define multiple buckets and switch between them:

```yaml
default: production

buckets:
  production:
    endpoint: https://xxx.r2.cloudflarestorage.com
    access_key_id: prod-key
    secret_access_key: prod-secret
    bucket_name: prod-assets
    public_url: https://cdn.example.com
    region: auto

  staging:
    endpoint: https://yyy.r2.cloudflarestorage.com
    access_key_id: staging-key
    secret_access_key: staging-secret
    bucket_name: staging-assets
    public_url: https://staging-cdn.example.com
    region: auto

  backups:
    endpoint: https://s3.us-east-1.amazonaws.com
    access_key_id: AKIA...
    secret_access_key: ...
    bucket_name: company-backups
    region: us-east-1
```

Switch buckets with `--bucket`:

```bash
# Use default (production)
python3 scripts/r2-upload.py file.jpg --public

# Use staging bucket
python3 scripts/r2-upload.py file.jpg --bucket staging --public

# Use backups bucket
python3 scripts/r2-upload.py backup.zip --bucket backups --key "backups/2026/02/04/backup.zip"
```

## Security best practices

1. **File permissions**: Set config file to 600
   ```bash
   chmod 600 ~/.r2-upload.yml
   ```

2. **Separate credentials**: Use different keys for different environments

3. **Least privilege**: Grant only `PutObject`, `GetObject`, `DeleteObject` permissions

4. **Environment variables**: For CI/CD, use env vars instead of config file:
   ```bash
   export R2_UPLOAD_CONFIG=/run/secrets/r2-config
   ```

5. **Rotate keys**: Regularly rotate access keys, especially for production
