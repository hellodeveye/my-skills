---
name: r2-upload
description: Uploads files to Cloudflare R2, AWS S3, or any S3-compatible storage and returns a public or temporary URL. Use when you need to publish assets, share files, or provide upload helpers to other skills.
compatibility: Requires Python 3.8+. Needs AWS4-HMAC-SHA256 signature support (no external SDK required).
metadata:
  author: foundra
  version: "2.0"
---

# R2 Upload

Upload files to R2/S3-compatible storage and return a URL.

## Use when

- Upload images, documents, or other assets to object storage
- Generate public URLs for web/CDN use
- Provide upload helpers to other skills (like tech-news)

## Prerequisites

- Python 3.8+ available as `python3`
- Config at `~/.r2-upload.yml` (or set `R2_UPLOAD_CONFIG`)
- Decide the bucket, object key/path, and visibility (public vs temporary)

## Recommended workflow

1. Confirm bucket/key and whether the URL should be public (avoid overwrites unless asked).
2. Verify config and bucket exist.
3. Upload with the CLI (recommended) or Python helper.
4. Return the URL and key; note whether it is public or temporary.

## Quick commands

```bash
python3 scripts/r2-upload.py ./photo.jpg --public
python3 scripts/r2-upload.py ./photo.jpg --key images/YYYY/MM/DD/cover.jpg --public
python3 scripts/r2-upload.py ./report.pdf --key reports/YYYY/MM/DD/report.pdf
```

## Key options

- `--bucket <name>`: override the default bucket in config
- `--key <path>`: set the object key/path
- `--public`: return a public URL instead of a temporary URL

## Programmatic usage

```python
import sys
from pathlib import Path

r2_dir = Path("/path/to/r2-upload")  # update to your local path
sys.path.insert(0, str(r2_dir / "scripts"))

from upload import upload_file, batch_upload, fetch_and_upload

url = upload_file(
    local_path="./image.jpg",
    key="images/YYYY/MM/DD/image.jpg",
    make_public=True
)
```

## Scripts

- `scripts/r2-upload.py`: CLI upload tool
- `scripts/upload.py`: Python helpers (`upload_file`, `batch_upload`, `fetch_and_upload`)

## References

- `references/CONFIGURATION.md` (provider config examples)
- `references/BLOG_IMAGES.md` (blog image workflow)
- `references/TROUBLESHOOTING.md` (common errors)
