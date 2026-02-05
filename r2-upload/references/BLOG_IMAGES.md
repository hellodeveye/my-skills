# Blog Images Workflow

Complete workflow for fetching article images and uploading to R2, as used in the tech-news skill.

> Notes:
> - Examples assume you run code from the r2-upload skill directory or add it to `PYTHONPATH`.
> - Replace `/path/to/r2-upload` with your local path if needed.

## Table of contents

- [Overview](#overview)
- [Complete example](#complete-example)
- [Helper functions](#helper-functions)
  - [Extract og:image from HTML](#extract-ogimage-from-html)
  - [Batch process multiple articles](#batch-process-multiple-articles)
- [Directory structure convention](#directory-structure-convention)
- [Image optimization tips](#image-optimization-tips)
  - [Before uploading](#before-uploading)
  - [Generating responsive images](#generating-responsive-images)
- [Integration with Hexo/Static sites](#integration-with-hexostatic-sites)
  - [Generate markdown image syntax](#generate-markdown-image-syntax)
  - [Hexo frontmatter with cover image](#hexo-frontmatter-with-cover-image)

## Overview

For a typical tech news blog post with multiple articles:

1. Extract article URLs from the blog post
2. Fetch each article's `og:image` or first image
3. Download images to temp directory
4. Upload to R2 with date-based paths
5. Insert image references into Markdown

## Complete example

```python
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

# Import upload functions from this skill
sys.path.insert(0, '/path/to/r2-upload/scripts')
from upload import fetch_and_upload

# Configuration
BLOG_DATE = "YYYY-MM-DD"
R2_PREFIX = f"images/{BLOG_DATE.replace('-', '/')}"

# Step 1: Define articles
articles = [
    {
        "title": "Xcode 26.3发布",
        "url": "https://www.apple.com/newsroom/...",
        "image_key": f"{R2_PREFIX}/xcode-26.3.jpg"
    },
    {
        "title": "Qwen3-Coder-Next",
        "url": "https://qwen.ai/blog?id=...",
        "image_key": f"{R2_PREFIX}/qwen3-coder.jpg"
    }
]

# Step 2: Fetch and upload images
uploaded = {}
for article in articles:
    try:
        # Extract og:image from article page
        req = urllib.request.Request(
            article["url"],
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        
        # Find og:image meta tag
        import re
        og_match = re.search(
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE
        )
        if not og_match:
            og_match = re.search(
                r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
                html,
                re.IGNORECASE
            )
        
        if og_match:
            image_url = urljoin(article["url"], og_match.group(1))
            
            # Upload to R2
            public_url = fetch_and_upload(
                image_url=image_url,
                key=article["image_key"],
                make_public=True
            )
            uploaded[article["url"]] = public_url
            print(f"✓ {article['title']}: {public_url}")
            
    except Exception as e:
        print(f"✗ {article['title']}: {e}")

# Step 3: Insert into Markdown
md_file = Path(f"~/projects/blog/source/_posts/{BLOG_DATE}-tech-news.md")
md_content = md_file.read_text(encoding="utf-8")

for article_url, image_url in uploaded.items():
    # Find article section and insert image
    pattern = rf"(### [^\n]+\n\n)(?=.*\[原文链接\]\({re.escape(article_url)}\))"
    replacement = rf"\1<img src=\"{image_url}\" alt=\"配图\" style=\"max-width:100%;height:auto;\">\n\n"
    md_content = re.sub(pattern, replacement, md_content, flags=re.DOTALL)

md_file.write_text(md_content, encoding="utf-8")
print(f"\nUpdated {md_file}")
```

## Helper functions

### Extract og:image from HTML

```python
def extract_og_image(html: str, base_url: str) -> str | None:
    """Extract og:image or twitter:image from HTML"""
    import re
    from urllib.parse import urljoin
    
    patterns = [
        r'<meta[^>]*property=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\'](?:og:image|twitter:image)["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1))
    
    return None
```

### Batch process multiple articles

```python
def process_blog_images(articles: list[dict], date: str) -> dict[str, str]:
    """
    Process images for multiple blog articles
    
    Args:
        articles: List of {"title": str, "url": str}
        date: Date string like "YYYY-MM-DD"
    
    Returns:
        Dict mapping article URL to uploaded image URL
    """
    from scripts.upload import fetch_and_upload
    import urllib.request
    
    prefix = f"images/{date.replace('-', '/')}"
    results = {}
    
    for i, article in enumerate(articles):
        try:
            # Fetch article HTML
            req = urllib.request.Request(
                article["url"],
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            
            # Extract image
            image_url = extract_og_image(html, article["url"])
            if not image_url:
                continue
            
            # Generate safe filename
            safe_title = re.sub(r'[^\w\-]', '-', article["title"])[:50]
            key = f"{prefix}/{i:02d}-{safe_title}.jpg"
            
            # Upload
            public_url = fetch_and_upload(image_url, key=key, make_public=True)
            results[article["url"]] = public_url
            
        except Exception as e:
            print(f"Failed to process {article['title']}: {e}")
    
    return results
```

## Directory structure convention

Recommended path structure for blog images:

```
images/
├── YYYY/
│   ├── MM/
│   │   ├── DD/
│   │   │   ├── 01-article-a.jpg
│   │   │   ├── 02-article-b.jpg
│   │   │   └── 03-article-c.jpg
│   │   └── DD/
│   │       ├── 01-topic-x.jpg
│   │       └── 02-topic-y.jpg
│   └── MM/
│       └── DD/
│           └── another-article.jpg
```

This structure:
- Keeps images organized by date
- Easy to browse in R2 console
- Simple to construct URLs programmatically
- Supports multiple images per day

## Image optimization tips

### Before uploading

```python
from PIL import Image
import io

def optimize_image(image_path: str, max_width: int = 1200) -> bytes:
    """Resize and compress image for web"""
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        return buffer.getvalue()
```

### Generating responsive images

```python
def generate_responsive_images(image_path: str, key_prefix: str) -> dict:
    """Generate multiple sizes for responsive images"""
    sizes = {
        'small': 400,
        'medium': 800,
        'large': 1200
    }
    
    urls = {}
    for name, width in sizes.items():
        data = optimize_image(image_path, max_width=width)
        key = f"{key_prefix}-{name}.jpg"
        
        # Save temp file and upload
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(data)
            temp_path = f.name
        
        try:
            url = upload_file(temp_path, key=key, make_public=True)
            urls[name] = url
        finally:
            os.unlink(temp_path)
    
    return urls
```

## Integration with Hexo/Static sites

### Generate markdown image syntax

```python
def generate_image_markdown(url: str, alt: str = "配图", caption: str = None) -> str:
    """Generate markdown/HTML for blog images"""
    
    if caption:
        return f'''<figure>
  <img src="{url}" alt="{alt}" style="max-width:100%;height:auto;">
  <figcaption>{caption}</figcaption>
</figure>'''
    else:
        return f'<img src="{url}" alt="{alt}" style="max-width:100%;height:auto;margin:10px 0;">'
```

### Hexo frontmatter with cover image

```python
def generate_hexo_frontmatter(title: str, date: str, image_url: str = None) -> str:
    """Generate Hexo blog post frontmatter"""
    fm = f"""---
title: {title}
date: {date}
tags: [tech, news]
categories: [技术新闻]
"""
    if image_url:
        fm += f"cover: {image_url}\n"
    
    fm += "---\n\n"
    return fm
```
