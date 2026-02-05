# News Sources

Guide for using and adding news sources.

> Notes:
> - Examples assume you run commands from the `tech-news` directory.
> - Replace `/path/to/tech-news` with your local path when needed.

## Table of contents

- [Built-in Sources](#built-in-sources)
  - [Hacker News (hackernews)](#hacker-news-hackernews)
  - [Reddit r/programming (reddit-programming)](#reddit-rprogramming-reddit-programming)
  - [GitHub Trending (github-trending)](#github-trending-github-trending)
  - [Product Hunt (producthunt)](#product-hunt-producthunt)
- [Using Multiple Sources](#using-multiple-sources)
- [Adding Custom Sources](#adding-custom-sources)
  - [Method 1: Modify fetch_news.py](#method-1-modify-fetch_newspy)
  - [Method 2: Runtime registration](#method-2-runtime-registration)
  - [Method 3: Plugin system](#method-3-plugin-system)
- [Source Requirements](#source-requirements)
- [RSS/Atom Sources](#rssatom-sources)
- [API Sources](#api-sources)
- [Web Scraping Sources](#web-scraping-sources)
- [Popular Sources to Add](#popular-sources-to-add)
- [Rate Limiting](#rate-limiting)
- [Caching](#caching)

## Built-in Sources

### Hacker News (hackernews)

The default source. Fetches top stories from news.ycombinator.com via RSS.

```bash
# Fetch top 20 stories with at least 50 points
python3 scripts/fetch_news.py --source hackernews --count 20 --min-points 50
```

**Parameters:**
- `count`: Number of stories (max 30)
- `min_points`: Minimum vote threshold

**Fields:**
- title
- link
- comments (HN discussion URL)
- pub_date

### Reddit r/programming (reddit-programming)

Top posts from r/programming.

```bash
python3 scripts/fetch_news.py --source reddit-programming --count 15
```

**Note:** Reddit may rate-limit requests. If you get 429 errors, wait a few minutes.

**Fields:**
- title
- link
- comments (Reddit thread URL)
- score (upvotes)

### GitHub Trending (github-trending)

Trending repositories on GitHub.

```bash
# All languages
python3 scripts/fetch_news.py --source github-trending --count 10

# Specific language
python3 scripts/fetch_news.py --source github-trending --language python --count 10

# Available languages: python, javascript, rust, go, typescript, etc.
```

**Fields:**
- title (repo name)
- link (repo URL)
- description (combined with title)

### Product Hunt (producthunt)

New tech products and startups.

```bash
python3 scripts/fetch_news.py --source producthunt --count 10
```

**Note:** Product Hunt requires API authentication. Set up:
1. Get API token from https://www.producthunt.com/v2/oauth/applications
2. Add to `~/.config/tech-news/producthunt.json`:
   ```json
   {"api_token": "your_token_here"}
   ```

## Using Multiple Sources

Fetch from multiple sources and merge:

```bash
# Command line
python3 scripts/fetch_news.py --sources hackernews reddit-programming --count 10

# In Python
import sys
sys.path.insert(0, "scripts")
from fetch_news import fetch_multi_source

articles = fetch_multi_source(
    sources=["hackernews", "reddit-programming", "github-trending"],
    count_per_source=10
)
```

## Adding Custom Sources

### Method 1: Modify fetch_news.py

Add your fetcher function:

```python
def fetch_my_custom_source(count=20):
    """Fetch from custom API"""
    url = "https://api.example.com/news"
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "MyBot/1.0",
        "Authorization": "Bearer YOUR_TOKEN"  # if needed
    })
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    items = []
    for item in data.get("articles", [])[:count]:
        items.append({
            "title": item["title"],
            "link": item["url"],
            "comments": item.get("discussion_url"),
            "pub_date": item.get("published_at"),
            "source": "my-custom-source"
        })
    
    return items
```

Register in `fetch_news()`:

```python
fetchers = {
    # ... existing sources ...
    "my-custom-source": lambda: fetch_my_custom_source(count),
}
```

### Method 2: Runtime registration

```python
import sys
sys.path.insert(0, "scripts")
from fetch_news import add_custom_source, fetch_news

def fetch_techcrunch(count=20):
    """Custom TechCrunch fetcher"""
    # Your implementation
    return articles

# Register
add_custom_source(
    name="techcrunch",
    url="https://techcrunch.com",
    fetch_function=fetch_techcrunch
)

# Use
articles = fetch_news("techcrunch", count=10)
```

### Method 3: Plugin system

Create a separate plugin file:

```python
# /path/to/tech-news/sources/techcrunch.py

def fetch(count=20):
    # Implementation
    return articles

# In generate.py
import importlib.util

def load_custom_sources():
    sources_dir = Path(__file__).parent / "sources"
    for file in sources_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'fetch'):
            add_custom_source(file.stem, "", module.fetch)
```

## Source Requirements

A valid source fetcher must:

1. Accept `count` parameter
2. Return list of dicts with at minimum:
   - `title`: Article title (str)
   - `link`: Article URL (str)
   - `source`: Source identifier (str)
3. Handle errors gracefully
4. Respect rate limits

Optional fields:
- `comments`: Discussion URL
- `pub_date`: Publication date
- `description`: Article summary

## RSS/Atom Sources

Many sites offer RSS feeds. Parse them easily:

```python
def fetch_from_rss(url, count=20):
    """Generic RSS fetcher"""
    import xml.etree.ElementTree as ET
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    
    root = ET.fromstring(xml)
    
    # Handle RSS 2.0 and Atom
    items = []
    channel = root.find('channel') if root.tag == 'rss' else root
    
    for item in channel.findall('.//item')[:count]:
        title = item.find('title')
        link = item.find('link')
        
        if title is not None and link is not None:
            items.append({
                "title": title.text or "",
                "link": link.text or "",
                "source": "rss"
            })
    
    return items

# Use for any RSS feed
articles = fetch_from_rss("https://example.com/feed.xml", count=10)
```

## API Sources

For JSON APIs:

```python
def fetch_from_api(url, count=20, api_key=None):
    """Generic API fetcher"""
    headers = {"User-Agent": "Mozilla/5.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    # Adapt to API response structure
    items = []
    for item in data.get("results", [])[:count]:
        items.append({
            "title": item["headline"],
            "link": item["web_url"],
            "pub_date": item["pub_date"],
            "source": "api"
        })
    
    return items
```

## Web Scraping Sources

For sites without APIs:

```python
def fetch_by_scraping(url, count=20):
    """Fetch by scraping HTML"""
    from html.parser import HTMLParser
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    
    # Use regex or BeautifulSoup if available
    items = []
    
    # Example: extract article links
    article_pattern = re.compile(r'<article[^>]*>.*?<h[1-6][^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?</article>', re.DOTALL)
    
    for match in article_pattern.findall(html)[:count]:
        link, title = match
        items.append({
            "title": re.sub(r'<[^>]+>', '', title).strip(),
            "link": urljoin(url, link),
            "source": "scraping"
        })
    
    return items
```

## Popular Sources to Add

Consider adding these sources:

| Source | URL | Notes |
|--------|-----|-------|
| Lobsters | lobste.rs | Programmer community |
| Dev.to | dev.to | Developer blog platform |
| InfoQ | infoq.com | Enterprise development |
| ACM TechNews | technews.acm.org | Computing news |
| IEEE Spectrum | spectrum.ieee.org | Engineering news |
| The Verge | theverge.com | Tech news |
| Ars Technica | arstechnica.com | Tech news |
| TechCrunch | techcrunch.com | Startup news |
| Wired | wired.com | Tech culture |
| Slashdot | slashdot.org | News for nerds |

## Rate Limiting

Be respectful to source servers:

```python
import time

def fetch_with_rate_limit(url, delay=1):
    """Fetch with rate limiting"""
    time.sleep(delay)  # Wait between requests
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req)
```

## Caching

Cache results to avoid repeated requests:

```python
import json
import os
from datetime import datetime, timedelta

def fetch_with_cache(source, cache_duration_minutes=5):
    """Fetch with local caching"""
    cache_dir = Path.home() / ".cache/tech-news"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / f"{source}.json"
    
    # Check cache
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(minutes=cache_duration_minutes):
            return json.loads(cache_file.read_text())
    
    # Fetch fresh
    articles = fetch_news(source)
    
    # Save cache
    cache_file.write_text(json.dumps(articles, ensure_ascii=False))
    
    return articles
```
