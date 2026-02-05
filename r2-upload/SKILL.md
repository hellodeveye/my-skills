---
name: r2-upload
description: Upload files to Cloudflare R2, AWS S3, or any S3-compatible storage. Use when the user needs to upload files to cloud storage, generate public or presigned URLs, or integrate upload functionality into other skills.
compatibility: Requires Python 3.8+ or Node.js 16+. Needs AWS4-HMAC-SHA256 signature support (no external SDK required).
metadata:
  author: foundra
  version: "2.0"
---

# R2 Upload

Upload files to R2/S3-compatible storage with support for public URLs and presigned links.

## When to use

- Upload images, documents, or any files to cloud storage
- Generate permanent public URLs for blog assets, CDN content
- Create temporary presigned URLs for secure file sharing
- Integrate upload functionality into other skills (like tech-news-blog)

## Quick start

### 1. Configure credentials

Create `~/.r2-upload.yml`:

```yaml
default: my-bucket

buckets:
  my-bucket:
    endpoint: https://<account_id>.r2.cloudflarestorage.com
    access_key_id: your_key
    secret_access_key: your_secret
    bucket_name: my-bucket
    public_url: https://cdn.example.com
    region: auto
```

See [references/CONFIGURATION.md](references/CONFIGURATION.md) for AWS S3 and MinIO examples.

### 2. Upload a file

**Command line:**
```bash
python3 scripts/r2-upload.py ./photo.jpg --public
# Output: https://cdn.example.com/abc123/photo.jpg

# With custom path
python3 scripts/r2-upload.py ./photo.jpg --key images/2026/02/04/cover.jpg --public
```

**From other skills:**
```python
import sys
sys.path.insert(0, '/root/.clawdbot/skills/r2-upload/scripts')
from upload import upload_file

url = upload_file(
    local_path="./image.jpg",
    key="images/2026/02/04/image.jpg",
    make_public=True
)
```

## Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| [scripts/r2-upload.py](scripts/r2-upload.py) | CLI upload tool | `python3 scripts/r2-upload.py file.jpg --public` |
| [scripts/r2-upload.js](scripts/r2-upload.js) | Node.js CLI | `node scripts/r2-upload.js file.jpg --public` |
| [scripts/upload.py](scripts/upload.py) | Python module for import | `from scripts.upload import upload_file` |
| [scripts/upload.js](scripts/upload.js) | Node.js module for require | `require('./scripts/upload.js')` |

## Common patterns

### Upload blog post images

See [references/BLOG_IMAGES.md](references/BLOG_IMAGES.md) for the complete workflow used in tech-news-blog.

```python
from scripts.upload import fetch_and_upload

# Download og:image from article and upload to R2
url = fetch_and_upload(
    image_url="https://example.com/og-image.jpg",
    key="images/2026/02/04/article.jpg",
    make_public=True
)
```

### Batch upload

```python
from scripts.upload import batch_upload

urls = batch_upload(
    files=["1.jpg", "2.png", "3.webp"],
    key_prefix="images/2026/02/04/",
    make_public=True
)
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| HTTP 403 | Check credentials and bucket permissions |
| HTTP 400 | Verify endpoint format and region setting |
| Config not found | Ensure `~/.r2-upload.yml` exists |

See [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) for detailed solutions.
