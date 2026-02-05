# Tech News Blog Examples

Common use cases and code snippets.

> Notes:
> - Examples assume you run commands from the `tech-news` directory.
> - Replace `/path/to/tech-news` and `/path/to/r2-upload` with your local paths when needed.

## Table of contents

- [Basic Examples](#basic-examples)
- [Advanced Examples](#advanced-examples)
- [Integration Examples](#integration-examples)
- [Translation Examples](#translation-examples)
- [Deployment Examples](#deployment-examples)
- [Docker Usage](#docker-usage)
- [Error Handling Examples](#error-handling-examples)

## Basic Examples

### Generate today's post

```bash
python3 scripts/generate.py --date $(date +%F)
```

### Generate with images

Images are processed by default. To disable:

```bash
python3 scripts/generate.py --date $(date +%F) --no-images
```

### Generate and save

```bash
python3 scripts/generate.py --date $(date +%F) --save ./news.md
```

## Advanced Examples

### Custom article count per source

```bash
python3 scripts/generate.py --date YYYY-MM-DD --count 25
```

### Limit final selection

```bash
python3 scripts/generate.py --date YYYY-MM-DD --limit 8
```

### Limit max images

```bash
python3 scripts/generate.py --date YYYY-MM-DD --max-images 5
```

## Integration Examples

### Custom blog generator

```python
#!/usr/bin/env python3
"""Custom generator with specific filters"""

import sys
sys.path.insert(0, "/path/to/tech-news/scripts")

from fetch_news import fetch_hackernews, categorize_article
from generate import translate_with_llm

def generate_ai_only_post():
    """Generate post with only AI-related articles"""

    # Fetch articles
    articles = fetch_hackernews(count=50)

    # Filter AI articles
    ai_articles = [
        a for a in articles
        if categorize_article(a.get("title", ""), a.get("description", "")) == "AI 与机器学习"
    ][:10]  # Take top 10

    # Generate markdown
    lines = ["# AI News Roundup", ""]
    for article in ai_articles:
        zh_title, _ = translate_with_llm(
            article.get("title", ""),
            article.get("description"),
            article.get("source")
        )
        lines.append(f"## {zh_title}")
        lines.append("")
        lines.append(f"[Read more]({article['link']})")
        lines.append("")

    return "\n".join(lines)

# Save
content = generate_ai_only_post()
with open("/tmp/ai-news.md", "w") as f:
    f.write(content)

print("Generated AI-focused post")
```

### Batch process historical posts

```python
#!/usr/bin/env python3
"""Add images to all posts from last week"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, "/path/to/tech-news/scripts")
from process_images import process_post_images

sys.path.insert(0, "/path/to/r2-upload/scripts")
from upload import upload_file

blog_dir = Path.home() / "projects/blog/source/_posts"

# Process last 7 days
for i in range(7):
    date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
    post = blog_dir / f"{date}-科技圈新闻汇总.md"

    if post.exists():
        print(f"Processing {post}")
        process_post_images(post, upload_file)
```

### Fetch and upload a single image

```python
import sys
sys.path.insert(0, "/path/to/r2-upload/scripts")
from upload import fetch_and_upload

# Download from URL and upload
url = fetch_and_upload(
    image_url="https://example.com/image.jpg",
    key="images/YYYY/MM/DD/custom.jpg",
    make_public=True
)
print(f"Image uploaded: {url}")
```

## Translation Examples

### Translate single title

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from llm_translate import translate_title_and_summary

zh_title, zh_summary = translate_title_and_summary("Show HN: My Rust Project")
print(zh_title)
PY
```

### Batch translate from file

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from llm_translate import translate_title_and_summary

with open("titles.txt", "r", encoding="utf-8") as f:
    for line in f:
        title = line.strip()
        if not title:
            continue
        zh_title, _ = translate_title_and_summary(title)
        print(f"{title}\n-> {zh_title}\n")
PY
```

## Deployment Examples

### GitHub Actions workflow

```yaml
# .github/workflows/tech-news.yml
name: Daily Tech News

on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM daily
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install pyyaml

      - name: Generate post
        run: |
          python3 ./tech-news/scripts/generate.py \
            --date $(date +%F) \
            --save ./news.md
        env:
          R2_UPLOAD_CONFIG: ${{ secrets.R2_CONFIG }}
```

## Docker Usage

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy skills
COPY tech-news/ /skills/tech-news/
COPY r2-upload/ /skills/r2-upload/

# Install dependencies
RUN pip install pyyaml

# Set entrypoint
ENTRYPOINT ["python3", "/skills/tech-news/scripts/generate.py"]
```

```bash
# Build and run
docker build -t tech-news .
docker run -v ~/.r2-upload.yml:/root/.r2-upload.yml tech-news --date $(date +%F)
```

## Error Handling Examples

### Graceful fallback (disable images)

```python
#!/usr/bin/env python3
import subprocess

cmd = ["python3", "scripts/generate.py", "--date", "YYYY-MM-DD", "--save", "/tmp/news.md"]

try:
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError:
    subprocess.run(cmd + ["--no-images"], check=True)
```

### Retry logic

```python
import sys
import time
sys.path.insert(0, "scripts")
from fetch_news import fetch_hackernews

# Retry up to 3 times
for attempt in range(3):
    try:
        articles = fetch_hackernews(count=20)
        break
    except Exception:
        if attempt == 2:
            raise
        print(f"Attempt {attempt + 1} failed, retrying...")
        time.sleep(5)
```
