# Tech News Blog Workflow

Complete workflow for generating tech news blog posts.

> Notes:
> - Examples assume you run commands from the `tech-news` directory.
> - Replace `/path/to/tech-news` and `/path/to/r2-upload` with your local paths when needed.

## Table of contents

- [Daily Workflow](#daily-workflow)
- [Custom Workflows](#custom-workflows)
- [Category Assignment](#category-assignment)
- [Image Handling](#image-handling)
- [Deduplication](#deduplication)
- [Integration with Other Skills](#integration-with-other-skills)
- [Cron/Automated Usage](#cronautomated-usage)
- [Troubleshooting](#troubleshooting)

## Daily Workflow

### 1. Generate Today's Post

```bash
cd /path/to/tech-news

# Basic generation (includes images by default)
python3 scripts/generate.py --date $(date +%F)

# Custom count + save to file
python3 scripts/generate.py --date $(date +%F) --count 20 --save ./news.md
```

### 2. Manual Review

```bash
# Open generated file
cat ~/projects/blog/source/_posts/$(date +%F)-科技圈新闻汇总.md

# Edit if needed
vim ~/projects/blog/source/_posts/$(date +%F)-科技圈新闻汇总.md
```

### 3. Deploy (optional)

```bash
cd ~/projects/blog
hexo clean && hexo g && hexo d
```

## Custom Workflows

### Fetch Specific Articles

```bash
# Get top 30 articles from HN
python3 scripts/fetch_news.py --count 30

# Save to file
python3 scripts/fetch_news.py --count 30 --output /tmp/articles.json
```

### Translate Titles (advanced)

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from llm_translate import translate_title_and_summary

zh_title, zh_summary = translate_title_and_summary("Show HN: My New Project")
print(zh_title)
PY
```

### Process Images Only

```bash
# Add images to existing post
python3 scripts/process_images.py --post ~/projects/blog/source/_posts/YYYY-MM-DD-科技圈新闻汇总.md
```

## Category Assignment

Articles are automatically categorized based on keywords:

| Category | Keywords |
|----------|----------|
| AI 与机器学习 | ai, llm, model, agent, gpt, claude, ml, neural |
| 游戏与怀旧科技 | game, retro, vintage, emulator, amiga |
| 开发工具与开源 | rust, python, github, open source, framework |
| 基础设施与行业 | cloud, aws, server, security, devops |
| 趣闻 | (fallback) |

### Override Category

Edit the generated markdown to move articles between sections.

## Image Handling

### Automatic (Recommended)

```bash
python3 scripts/generate.py --date YYYY-MM-DD
```

This will:
1. Generate post with image placeholders
2. Fetch og:image from each article
3. Upload to R2 at `images/YYYY/MM/DD/article-XX.jpg`
4. Insert `<img>` tags into markdown

### Manual

```bash
# 1. Generate without images
python3 scripts/generate.py --date YYYY-MM-DD --no-images

# 2. Download images manually
curl -o /tmp/image.jpg "https://example.com/og-image.jpg"

# 3. Upload via r2-upload
python3 /path/to/r2-upload/scripts/r2-upload.py \
  /tmp/image.jpg \
  --key images/YYYY/MM/DD/manual.jpg \
  --public

# 4. Insert into markdown
# Edit file to add: <img src="https://.../manual.jpg">
```

## Deduplication

By default, articles from the last 3 days are excluded to avoid repetition.

To change the window, edit `dedupe_articles(articles, days=3)` in `scripts/generate.py`.

## Integration with Other Skills

### Using r2-upload

```python
import sys
sys.path.insert(0, "/path/to/r2-upload/scripts")
from upload import upload_file, fetch_and_upload

# Upload local file
url = upload_file("/tmp/image.jpg", key="images/test.jpg", make_public=True)

# Fetch and upload
url = fetch_and_upload("https://example.com/image.jpg", key="images/test.jpg")
```

### Using tech-news from other skills

```python
import sys
sys.path.insert(0, "/path/to/tech-news/scripts")

from generate import fetch_multi_sources, pick_articles_balanced, generate_markdown, translate_with_llm
from fetch_news import fetch_hackernews, categorize_article

articles = fetch_multi_sources(["hackernews"], count=20)
articles = pick_articles_balanced(articles, limit=10)
markdown = generate_markdown("YYYY-MM-DD", articles)
```

## Cron/Automated Usage

```bash
#!/bin/bash
# /etc/cron.daily/tech-news

cd /path/to/tech-news

python3 scripts/generate.py \
  --date $(date +%F) \
  --count 15 \
  --save /var/tmp/tech-news.md \
  >> /var/log/tech-news.log 2>&1
```

## Troubleshooting

### No articles fetched

- Check HN RSS: `curl https://hnrss.org/frontpage`
- Verify network connectivity

### Images not uploading

- Verify r2-upload skill: `python3 /path/to/r2-upload/scripts/r2-upload.py --help`
- Check R2 credentials in `~/.r2-upload.yml`

### Hexo deploy fails

- Check hexo: `hexo --version`
- Verify blog config: `cat ~/projects/blog/_config.yml | grep deploy`
