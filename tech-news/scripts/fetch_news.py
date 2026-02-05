#!/usr/bin/env python3
"""
News fetching module - Fetch articles from various sources
Supported sources: hackernews, reddit-programming, github-trending, 
                   devto, paperswithcode, huggingface, lobsters, 
                   infoq, hackernoon, towardsdatascience, arxiv

Usage: 
  python3 fetch_news.py --source hackernews --count 20
  python3 fetch_news.py --source paperswithcode --count 10
  python3 fetch_news.py --list-sources
"""

import argparse
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, quote
from datetime import datetime

# Source registry - 扩展更多源
SOURCES = {
    # 通用科技
    "hackernews": {
        "name": "Hacker News",
        "description": "Top stories from news.ycombinator.com",
        "url": "https://news.ycombinator.com",
        "category": "general",
    },
    "lobsters": {
        "name": "Lobsters",
        "description": "Computing-focused community",
        "url": "https://lobste.rs",
        "category": "general",
    },
    "infoq": {
        "name": "InfoQ",
        "description": "Enterprise development news and articles",
        "url": "https://www.infoq.com",
        "category": "general",
    },
    "hackernoon": {
        "name": "HackerNoon",
        "description": "Tech stories by developers",
        "url": "https://hackernoon.com",
        "category": "general",
    },
    "devto": {
        "name": "Dev.to",
        "description": "Developer blog platform",
        "url": "https://dev.to",
        "category": "programming",
    },
    
    # AI/ML 专用
    "paperswithcode": {
        "name": "Papers with Code",
        "description": "Latest AI/ML papers with implementations",
        "url": "https://paperswithcode.com",
        "category": "ai",
    },
    "huggingface": {
        "name": "Hugging Face",
        "description": "AI models, datasets and spaces trending",
        "url": "https://huggingface.co",
        "category": "ai",
    },
    "towardsdatascience": {
        "name": "Towards Data Science",
        "description": "Data science and ML articles from Medium",
        "url": "https://towardsdatascience.com",
        "category": "ai",
    },
    "arxiv-ai": {
        "name": "arXiv AI",
        "description": "Latest AI papers from arXiv",
        "url": "https://arxiv.org/list/cs.AI/recent",
        "category": "ai",
    },
    "reddit-machinelearning": {
        "name": "Reddit r/MachineLearning",
        "description": "Machine Learning discussions",
        "url": "https://www.reddit.com/r/MachineLearning",
        "category": "ai",
    },
    
    # 程序开发
    "github-trending": {
        "name": "GitHub Trending",
        "description": "Trending repositories on GitHub",
        "url": "https://github.com/trending",
        "category": "programming",
    },
    "reddit-programming": {
        "name": "Reddit r/programming",
        "description": "Programming discussions",
        "url": "https://www.reddit.com/r/programming",
        "category": "programming",
    },
    "reddit-rust": {
        "name": "Reddit r/rust",
        "description": "Rust programming community",
        "url": "https://www.reddit.com/r/rust",
        "category": "programming",
    },
    "reddit-golang": {
        "name": "Reddit r/golang",
        "description": "Go programming community",
        "url": "https://www.reddit.com/r/golang",
        "category": "programming",
    },
    "reddit-python": {
        "name": "Reddit r/Python",
        "description": "Python programming community",
        "url": "https://www.reddit.com/r/Python",
        "category": "programming",
    },
    "producthunt": {
        "name": "Product Hunt",
        "description": "New tech products and startups",
        "url": "https://www.producthunt.com",
        "category": "product",
    },
}

def list_sources():
    """List all available news sources by category"""
    print("Available news sources:")
    print()
    
    categories = {
        "general": "📰 综合科技",
        "ai": "🤖 AI / 机器学习", 
        "programming": "💻 程序开发",
        "product": "🚀 产品 / 创业",
    }
    
    for cat_key, cat_name in categories.items():
        cat_sources = {k: v for k, v in SOURCES.items() if v.get("category") == cat_key}
        if cat_sources:
            print(f"\n{cat_name}")
            print("-" * 40)
            for key, info in cat_sources.items():
                print(f"  {key:25} - {info['name']}")
                print(f"  {'':25}   {info['description']}")
    
    print("\n" + "=" * 50)
    print("Usage: python3 fetch_news.py --source <name> --count 10")
    print("       python3 fetch_news.py --sources hackernews paperswithcode --count 10")

def fetch_hackernews(count=20, min_points=50):
    """Fetch top stories from Hacker News via RSS"""
    url = f"https://hnrss.org/frontpage?points={min_points}&count={count}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    
    items = []
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    
    for item_match in item_pattern.findall(xml):
        title = re.search(r'<title>(.*?)</title>', item_match)
        link = re.search(r'<link>(.*?)</link>', item_match)
        comments = re.search(r'<comments>(.*?)</comments>', item_match)
        pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item_match)
        
        if title and link:
            title_text = title.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
            items.append({
                "title": title_text,
                "link": link.group(1).strip(),
                "comments": comments.group(1).strip() if comments else None,
                "pub_date": pub_date.group(1).strip() if pub_date else None,
                "source": "hackernews",
                "source_name": "Hacker News"
            })
    
    return items

def fetch_lobsters(count=20):
    """Fetch top stories from Lobsters"""
    url = f"https://lobste.rs/top/rss"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    
    items = []
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    
    for item_match in item_pattern.findall(xml)[:count]:
        title = re.search(r'<title>(.*?)</title>', item_match)
        link = re.search(r'<link>(.*?)</link>', item_match)
        
        if title and link:
            title_text = title.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
            items.append({
                "title": title_text,
                "link": link.group(1).strip(),
                "source": "lobsters",
                "source_name": "Lobsters"
            })
    
    return items

def fetch_devto(count=20, tag=""):
    """Fetch top posts from Dev.to"""
    if tag:
        url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page={count}"
    else:
        url = f"https://dev.to/api/articles?top=7&per_page={count}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("⚠️ Dev.to rate limit hit, try again later")
            return []
        raise
    
    items = []
    for article in data[:count]:
        items.append({
            "title": article.get("title", ""),
            "link": article.get("url", ""),
            "description": article.get("description", ""),
            "tags": article.get("tag_list", []),
            "source": "devto",
            "source_name": "Dev.to"
        })
    
    return items

def fetch_paperswithcode(count=20):
    """Fetch trending papers from Papers with Code (HTML scraping as API requires auth)"""
    url = "https://paperswithcode.com/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"⚠️ Papers with Code unavailable: {e}")
        return []
    
    items = []
    # Try to extract trending papers from HTML
    paper_pattern = re.compile(r'<div[^>]*class="[^"]*paper-card[^"]*"[^>]*>.*?<a[^>]*href="(/paper/[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
    
    for match in paper_pattern.findall(html)[:count]:
        link_path, title_html = match
        # Clean title
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        
        if title:
            items.append({
                "title": f"[Paper] {title}",
                "link": f"https://paperswithcode.com{link_path}",
                "source": "paperswithcode",
                "source_name": "Papers with Code"
            })
    
    return items

def fetch_huggingface(count=20):
    """Fetch trending models from Hugging Face"""
    url = f"https://huggingface.co/api/models?sort=downloads&direction=-1&limit={count}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    items = []
    for model in data[:count]:
        model_id = model.get("modelId", "")
        if not model_id:
            continue
            
        items.append({
            "title": f"[Model] {model_id}",
            "link": f"https://huggingface.co/{model_id}",
            "downloads": model.get("downloads"),
            "tags": model.get("tags", []),
            "source": "huggingface",
            "source_name": "Hugging Face"
        })
    
    return items

def fetch_towardsdatascience(count=20):
    """Fetch latest from Towards Data Science RSS"""
    url = "https://towardsdatascience.com/feed"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml = resp.read().decode("utf-8")
    except urllib.error.HTTPError:
        # Medium RSS often blocks
        print("⚠️ Towards Data Science RSS unavailable")
        return []
    
    items = []
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    
    for item_match in item_pattern.findall(xml)[:count]:
        title = re.search(r'<title>(.*?)</title>', item_match)
        link = re.search(r'<link>(.*?)</link>', item_match)
        
        if title and link:
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title.group(1))
            items.append({
                "title": title_text,
                "link": link.group(1).strip(),
                "source": "towardsdatascience",
                "source_name": "Towards Data Science"
            })
    
    return items

def fetch_arxiv_ai(count=20):
    """Fetch recent AI papers from arXiv"""
    # arXiv cs.AI (Artificial Intelligence)
    url = f"http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results={count}&sortBy=submittedDate&sortOrder=descending"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    
    items = []
    entry_pattern = re.compile(r'<entry>(.*?)</entry>', re.DOTALL)
    
    for entry in entry_pattern.findall(xml):
        title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
        link = re.search(r'<id>(.*?)</id>', entry)
        summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
        published = re.search(r'<published>(.*?)</published>', entry)
        
        if title and link:
            title_text = title.group(1).replace('\n', ' ').strip()
            summary_text = summary.group(1).replace('\n', ' ').strip() if summary else ""
            
            # Truncate summary
            if len(summary_text) > 300:
                summary_text = summary_text[:297] + "..."
            
            items.append({
                "title": f"[arXiv] {title_text}",
                "link": link.group(1).strip(),
                "description": summary_text,
                "pub_date": published.group(1).strip() if published else None,
                "source": "arxiv-ai",
                "source_name": "arXiv AI"
            })
    
    return items

def fetch_reddit_subreddit(subreddit, count=20):
    """Generic Reddit fetcher for any subreddit"""
    url = f"https://www.reddit.com/r/{subreddit}/top.json?limit={count}&t=day"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TechNewsBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"⚠️ Reddit rate limit hit for r/{subreddit}")
            return []
        raise
    
    items = []
    for post in data.get("data", {}).get("children", []):
        p = post.get("data", {})
        
        if p.get("stickied"):
            continue
        
        items.append({
            "title": p.get("title", ""),
            "link": p.get("url", ""),
            "comments": f"https://www.reddit.com{p.get('permalink', '')}",
            "score": p.get("score", 0),
            "source": f"reddit-{subreddit}",
            "source_name": f"Reddit r/{subreddit}"
        })
    
    return items

def fetch_github_trending(count=20, language=""):
    """Fetch trending repositories from GitHub (via Search API)"""
    # Use GitHub search API as fallback when HTML scraping fails
    query = f"stars:>1000"
    if language:
        query += f" language:{language}"
    
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={count}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TechNewsBot/1.0)",
        "Accept": "application/vnd.github.v3+json"
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("⚠️ GitHub API rate limit, using cached/alternative method")
            # Fallback to manual curated list
            return [
                {
                    "title": "Use GitHub API with token for full access",
                    "link": "https://github.com/trending",
                    "source": "github-trending",
                    "source_name": "GitHub Trending",
                    "description": "Set GITHUB_TOKEN env var to avoid rate limits"
                }
            ]
        raise
    
    items = []
    for repo in data.get("items", [])[:count]:
        items.append({
            "title": f"{repo.get('full_name', '')}: {repo.get('description', '')}",
            "link": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language", ""),
            "source": "github-trending",
            "source_name": "GitHub Trending"
        })
    
    return items

def fetch_infoq(count=20):
    """Fetch latest articles from InfoQ"""
    url = "https://www.infoq.com/feed"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml = resp.read().decode("utf-8")
    except urllib.error.HTTPError:
        print("⚠️ InfoQ RSS unavailable")
        return []
    
    items = []
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    
    for item_match in item_pattern.findall(xml)[:count]:
        title = re.search(r'<title>(.*?)</title>', item_match)
        link = re.search(r'<link>(.*?)</link>', item_match)
        
        if title and link:
            items.append({
                "title": title.group(1).strip(),
                "link": link.group(1).strip(),
                "source": "infoq",
                "source_name": "InfoQ"
            })
    
    return items

def fetch_hackernoon(count=20):
    """Fetch latest stories from HackerNoon"""
    url = "https://hackernoon.com/feed"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml = resp.read().decode("utf-8")
    except urllib.error.HTTPError:
        print("⚠️ HackerNoon RSS unavailable")
        return []
    
    items = []
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL)
    
    for item_match in item_pattern.findall(xml)[:count]:
        title = re.search(r'<title>(.*?)</title>', item_match)
        link = re.search(r'<link>(.*?)</link>', item_match)
        
        if title and link:
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title.group(1))
            items.append({
                "title": title_text,
                "link": link.group(1).strip(),
                "source": "hackernoon",
                "source_name": "HackerNoon"
            })
    
    return items

def fetch_news(source, count=20, **kwargs):
    """Fetch news from specified source"""
    fetchers = {
        "hackernews": lambda: fetch_hackernews(count, kwargs.get("min_points", 50)),
        "lobsters": lambda: fetch_lobsters(count),
        "infoq": lambda: fetch_infoq(count),
        "hackernoon": lambda: fetch_hackernoon(count),
        "devto": lambda: fetch_devto(count, kwargs.get("tag", "")),
        "paperswithcode": lambda: fetch_paperswithcode(count),
        "huggingface": lambda: fetch_huggingface(count),
        "towardsdatascience": lambda: fetch_towardsdatascience(count),
        "arxiv-ai": lambda: fetch_arxiv_ai(count),
        "reddit-machinelearning": lambda: fetch_reddit_subreddit("MachineLearning", count),
        "reddit-programming": lambda: fetch_reddit_subreddit("programming", count),
        "reddit-rust": lambda: fetch_reddit_subreddit("rust", count),
        "reddit-golang": lambda: fetch_reddit_subreddit("golang", count),
        "reddit-python": lambda: fetch_reddit_subreddit("Python", count),
        "github-trending": lambda: fetch_github_trending(count, kwargs.get("language", "")),
    }
    
    if source not in fetchers:
        raise ValueError(f"Unknown source: {source}. Run --list-sources to see available sources.")
    
    return fetchers[source]()

def fetch_multi_source(sources, count_per_source=10):
    """Fetch from multiple sources and merge results"""
    all_articles = []
    results = {}
    errors = {}

    try:
        max_workers = int(os.environ.get("FETCH_WORKERS", "4"))
    except ValueError:
        max_workers = 4
    max_workers = max(1, min(max_workers, len(sources)))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_news, source, count=count_per_source): source
            for source in sources
        }
        for future in as_completed(future_map):
            source = future_map[future]
            try:
                results[source] = future.result()
            except Exception as e:
                errors[source] = e

    for source in sources:
        if source in results:
            articles = results[source]
            all_articles.extend(articles)
            source_name = SOURCES.get(source, {}).get("name", source)
            print(f"✓ {source_name}: {len(articles)} articles")
        else:
            err = errors.get(source)
            print(f"✗ {source}: {err}")

    return all_articles

def categorize_article(title, description=""):
    """Categorize article by title/description keywords"""
    text = (title + " " + description).lower()
    
    categories = {
        "AI 与机器学习": ["ai", "llm", "model", "agent", "gpt", "claude", "grok", "ml ", "neural", "deep learning", "transformer", "embedding", "fine-tune", "pytorch", "tensorflow", "huggingface", "paper", "arxiv"],
        "游戏与怀旧科技": ["game", "gaming", "retro", "vintage", "nostalgia", "classic", "emulator", "amiga", "commodore", "atari", "sega", "nintendo"],
        "开发工具与开源": ["rust", "python", "javascript", "typescript", "github", "open source", "framework", "library", "tool", "compiler", "database", "sql", "docker", "kubernetes", "git", "vscode"],
        "基础设施与行业": ["cloud", "aws", "gcp", "azure", "server", "datacenter", "infrastructure", "devops", "security", "privacy", "encryption", "blockchain", "crypto"],
    }
    
    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return category
    
    return "趣闻"

def main():
    parser = argparse.ArgumentParser(description="Fetch tech news from various sources")
    parser.add_argument("--source", default="hackernews", help="News source")
    parser.add_argument("--sources", nargs="+", help="Multiple sources to fetch from")
    parser.add_argument("--count", type=int, default=20, help="Number of articles per source")
    parser.add_argument("--min-points", type=int, default=50, help="Min points for HN")
    parser.add_argument("--language", help="Language filter for GitHub trending")
    parser.add_argument("--tag", help="Tag filter for Dev.to")
    parser.add_argument("--output", help="Output file (JSON)")
    parser.add_argument("--list-sources", action="store_true", help="List available sources")
    
    args = parser.parse_args()
    
    if args.list_sources:
        list_sources()
        return
    
    # Fetch from multiple sources if specified
    if args.sources:
        articles = fetch_multi_source(args.sources, args.count)
    else:
        kwargs = {}
        if args.source == "hackernews":
            kwargs["min_points"] = args.min_points
        elif args.source == "github-trending":
            kwargs["language"] = args.language
        elif args.source == "devto":
            kwargs["tag"] = args.tag
        
        articles = fetch_news(args.source, args.count, **kwargs)
    
    # Print results (human-friendly). If --output is set, stay quiet for machine-friendly piping.
    if not args.output:
        current_source = ""
        for i, article in enumerate(articles, 1):
            # Print source header when it changes
            article_source = article.get("source_name", args.source)
            if article_source != current_source:
                current_source = article_source
                print(f"\n{'='*50}")
                print(f"📰 {current_source}")
                print('='*50)

            print(f"\n{i}. {article['title']}")
            print(f"   Link: {article['link']}")
            print(f"   Category: {categorize_article(article['title'], article.get('description', ''))}")
            if article.get('description'):
                desc = article['description'][:100] + "..." if len(article['description']) > 100 else article['description']
                print(f"   Summary: {desc}")
            if article.get('comments'):
                print(f"   Comments: {article['comments']}")

        print(f"\n\nTotal: {len(articles)} articles")

    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
