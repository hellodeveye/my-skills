#!/usr/bin/env python3
"""
Tech News Generator - 每日科技新闻聚合器

功能：
- 从多源抓取科技新闻
- AI翻译为中文
- 精选10条，均衡各来源
- 下载配图上传到R2
- 生成Markdown汇总

用法：
  python3 generate.py                          # 默认生成
  python3 generate.py --output-only            # 仅输出生成的Markdown
  python3 generate.py --save ~/news.md         # 保存到指定文件
  python3 generate.py --no-images              # 不处理图片
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

# 配置
SCRIPT_DIR = Path(__file__).parent.resolve()
CACHE_DIR = SCRIPT_DIR.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

FETCH_NEWS = SCRIPT_DIR / "fetch_news.py"

# 分类配置
CATEGORIES = {
    "AI 与机器学习": ["ai", "llm", "model", "agent", "gpt", "claude", "grok", "ml ", "neural", "deep learning", "machine learning", "huggingface", "transformer"],
    "开发工具与开源": ["rust", "python", "javascript", "typescript", "github", "open source", "framework", "library", "tool", "compiler", "database", "sql", "redis"],
    "基础设施与云原生": ["cloud", "aws", "gcp", "azure", "server", "datacenter", "infrastructure", "kubernetes", "docker", "devops", "security", "privacy", "encryption", "observability"],
    "产品与设计": ["product", "design", "ui", "ux", "figma", "startup", "launch", "feature", "update", "release"],
    "趣闻与观点": [],  # 默认分类
}

DEFAULT_SOURCES = ["hackernews", "github-trending", "lobsters", "devto"]


def fetch_multi_sources(sources, count=15):
    """从多个源抓取新闻。"""
    tmp = CACHE_DIR / "fetched_news.json"
    cmd = [sys.executable, str(FETCH_NEWS), "--sources", *sources, "--count", str(count), "--output", str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True)
    return json.loads(tmp.read_text(encoding="utf-8"))


def categorize(title):
    """根据标题关键词分类。"""
    t = title.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in t for k in keywords):
            return category
    return "趣闻与观点"


def translate_with_llm(title, description, source_name=None):
    """使用LLM翻译标题和生成摘要。"""
    import os

    try:
        minimax_key = os.environ.get('MINIMAX_API_KEY', '').strip()
        openai_key = os.environ.get('OPENAI_API_KEY', '').strip()
        has_api_key = bool(minimax_key or openai_key)

        if has_api_key:
            sys.path.insert(0, str(SCRIPT_DIR))
            from llm_translate import translate_title_and_summary, TranslationError
            return translate_title_and_summary(title, description=description or "", source=source_name)
    except TranslationError as e:
        print(f"[翻译警告] {e}", file=sys.stderr)
    except Exception as e:
        print(f"[翻译错误] {type(e).__name__}", file=sys.stderr)

    # 回退：简单处理
    return title, f"来自 {source_name or '科技社区'} 的热门内容。\n\n要点：\n- 详情见原文\n- 值得关注"


def load_translation_cache():
    """加载翻译缓存。"""
    cache_path = CACHE_DIR / "translations.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def save_translation_cache(cache):
    """保存翻译缓存。"""
    cache_path = CACHE_DIR / "translations.json"
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_articles(articles, days=3):
    """基于缓存去重最近N天的文章。"""
    cache_path = CACHE_DIR / "selected_articles.json"
    seen_links = set()

    if cache_path.exists():
        history = json.loads(cache_path.read_text(encoding="utf-8"))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        for entry in history:
            if entry.get("date", "") > cutoff:
                seen_links.add(entry.get("link"))

    return [a for a in articles if a.get("link") not in seen_links]


def pick_articles_balanced(articles, limit=10, per_source=2):
    """均衡选择文章，确保来源多样性。"""
    buckets = {}
    for a in articles:
        buckets.setdefault(a.get('source', 'unknown'), []).append(a)

    source_order = list(buckets.keys())
    picked = []

    # 第一轮：每源最多2条
    for src in source_order:
        if src in buckets:
            picked.extend(buckets[src][:per_source])
        if len(picked) >= limit:
            return picked[:limit]

    # 第二轮：轮询补充
    i = per_source
    while len(picked) < limit:
        progressed = False
        for src in source_order:
            if src in buckets and i < len(buckets[src]):
                picked.append(buckets[src][i])
                progressed = True
                if len(picked) >= limit:
                    return picked[:limit]
        if not progressed:
            break
        i += 1

    return picked[:limit]


def fetch_og_image(url, timeout=5):
    """抓取文章的og:image。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 尝试多种og:image格式
        patterns = [
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
            r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.I)
            if match:
                return urljoin(url, match.group(1))
    except Exception:
        pass
    return None


def upload_image_to_r2(image_url, key, timeout=10):
    """上传图片到R2并返回公开URL。"""
    # 通过环境变量或相对路径查找 r2-upload
    r2_path = os.environ.get("R2_UPLOAD_PATH")
    if r2_path:
        paths_to_try = [r2_path]
    else:
        # 默认尝试：同级目录下的 r2-upload
        paths_to_try = [
            str(SCRIPT_DIR.parent.parent / "r2-upload" / "scripts"),
        ]

    for path in paths_to_try:
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        from upload import fetch_and_upload
        return fetch_and_upload(image_url, key=key, make_public=True)
    except ImportError:
        print(f"[警告] r2-upload 不可用，跳过: {image_url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[上传失败] {image_url}: {e}", file=sys.stderr)
        return None


def process_articles_images(articles, date_str, max_images=10):
    """处理文章图片，上传R2并返回URL列表。"""
    uploaded_urls = []

    for i, article in enumerate(articles):
        if len(uploaded_urls) >= max_images:
            article.pop("image_url", None)
            continue

        # 抓取og:image
        image_url = fetch_og_image(article["link"])
        if not image_url:
            article.pop("image_url", None)
            continue

        # 生成R2 key
        key = f"images/{date_str.replace('-', '/')}/article-{i+1:02d}.jpg"

        # 上传到R2
        public_url = upload_image_to_r2(image_url, key)
        if public_url:
            article["image_url"] = public_url
            uploaded_urls.append({
                "article": article.get("zh_title", article["title"])[:30],
                "r2_url": public_url,
                "source_image": image_url
            })
            print(f"  [图片上传] {public_url}")
        else:
            article.pop("image_url", None)

    return uploaded_urls


def generate_markdown(date_str, articles):
    """生成Markdown格式的新闻汇总，使用固定格式。"""
    lines = []

    # 1. 固定标题格式
    lines.append(f"# 📰 {date_str} 科技早报")
    lines.append("")

    # 2. 固定摘要格式 - 包含文章数量和来源分布
    source_counts = {}
    for a in articles:
        src = a.get("source_name", a.get("source", "未知"))
        source_counts[src] = source_counts.get(src, 0) + 1

    source_summary = " | ".join([f"{src}({count})" for src, count in sorted(source_counts.items())])

    lines.append("> 📊 **今日导读**")
    lines.append(f"> 精选 {len(articles)} 条科技新闻")
    lines.append(f"> 来源：{source_summary}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. 文章速览 - 固定格式的目录
    lines.append("## 📋 文章速览")
    lines.append("")

    # 按分类分组统计
    grouped = {cat: [] for cat in CATEGORIES.keys()}
    for article in articles:
        cat = article.get("category", categorize(article["title"]))
        if cat not in grouped:
            cat = "趣闻与观点"
        grouped[cat].append(article)

    # 生成分类概览
    for category in CATEGORIES.keys():
        items = grouped[category]
        if not items:
            continue
        lines.append(f"**{category}**：{len(items)} 篇")
        for i, item in enumerate(items, 1):
            zh_title = item.get("zh_title", item["title"])
            # 限制标题长度
            display_title = zh_title[:40] + "..." if len(zh_title) > 40 else zh_title
            lines.append(f"{i}. {display_title}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 4. 详细内容 - 固定结构
    for category in CATEGORIES.keys():
        items = grouped[category]
        if not items:
            continue

        lines.append(f"## {category}")
        lines.append("")

        for idx, item in enumerate(items, 1):
            zh_title = item.get("zh_title", item["title"])
            zh_summary = item.get("zh_summary", "")
            source_name = item.get("source_name", item.get("source", "来源"))

            # 固定文章编号格式
            lines.append(f"### {idx}. {zh_title}")
            lines.append("")

            # 元信息行 - 固定格式
            meta_info = f"📰 **{source_name}**"
            lines.append(meta_info)
            lines.append("")

            # 图片 - 固定位置
            if item.get("image_url"):
                lines.append(f'<img src="{item["image_url"]}" width="100%" alt="{zh_title[:20]}" style="border-radius:8px;margin:10px 0;">')
                lines.append("")

            # 摘要内容 - 固定格式处理
            if zh_summary:
                # 解析摘要和要点
                summary_parts = zh_summary.split("\n\n要点：")
                main_summary = summary_parts[0].strip()

                if main_summary:
                    lines.append("**摘要**：" + main_summary)
                    lines.append("")

                # 要点处理
                if len(summary_parts) > 1:
                    bullet_text = summary_parts[1].strip()
                    bullets = [b.strip() for b in bullet_text.split("\n") if b.strip().startswith("-")]

                    if bullets:
                        lines.append("**核心要点**：")
                        for bullet in bullets[:3]:  # 最多显示3个要点
                            # 移除开头的 "- "
                            bullet_content = bullet[2:].strip() if bullet.startswith("- ") else bullet
                            lines.append(f"• {bullet_content}")
                        lines.append("")

            # 原文链接 - 固定格式
            lines.append(f"🔗 [阅读原文]({item['link']})")
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.append(f"*本次汇总于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 生成*")
    lines.append("")

    return "\n".join(lines)


def save_selected_history(articles, date_str):
    """保存已选文章到历史记录（用于去重）。"""
    cache_path = CACHE_DIR / "selected_articles.json"
    history = []
    if cache_path.exists():
        history = json.loads(cache_path.read_text(encoding="utf-8"))

    for a in articles:
        history.append({
            "date": datetime.now().isoformat(),
            "link": a["link"],
            "title": a.get("zh_title", a["title"]),
        })

    # 只保留最近30天
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    history = [h for h in history if h.get("date", "") > cutoff]

    cache_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def print_summary(articles, uploaded_images, elapsed_time):
    """打印执行摘要。"""
    print("\n" + "="*60)
    print("执行摘要")
    print("="*60)

    # 统计
    source_count = {}
    for a in articles:
        src = a.get("source_name", a.get("source", "unknown"))
        source_count[src] = source_count.get(src, 0) + 1

    print(f"\n文章统计:")
    print(f"  - 精选文章: {len(articles)} 条")
    print(f"  - 上传图片: {len(uploaded_images)} 张")
    print(f"  - 耗时: {elapsed_time:.1f} 秒")

    print(f"\n来源分布:")
    for src, count in sorted(source_count.items(), key=lambda x: -x[1]):
        print(f"  - {src}: {count} 条")

    if uploaded_images:
        print(f"\n图片URL列表:")
        for img in uploaded_images:
            print(f"  - {img['article'][:25]}...")
            print(f"    {img['r2_url']}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="生成科技新闻汇总")
    parser.add_argument("--date", help="日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES, help="新闻源列表")
    parser.add_argument("--count", type=int, default=15, help="每源抓取数量")
    parser.add_argument("--limit", type=int, default=10, help="最终精选数量")
    parser.add_argument("--max-images", type=int, default=10, help="最大图片数")
    parser.add_argument("--no-images", action="store_true", help="不处理图片")
    parser.add_argument("--save", help="保存到指定文件路径")
    parser.add_argument("--output-only", action="store_true", help="仅输出生成的Markdown")

    args = parser.parse_args()

    import time
    start_time = time.time()

    # 日期
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    # 1. 抓取新闻
    print(f"[1/5] 从 {len(args.sources)} 个源抓取新闻...")
    articles = fetch_multi_sources(args.sources, args.count)
    print(f"      获取 {len(articles)} 篇文章")

    # 2. 去重
    print("[2/5] 去除近期重复文章...")
    articles = dedupe_articles(articles)
    print(f"      剩余 {len(articles)} 篇")

    # 3. 精选
    print(f"[3/5] 精选 {args.limit} 篇文章...")
    articles = pick_articles_balanced(articles, limit=args.limit)
    print(f"      已精选: {', '.join(a.get('source', 'unknown') for a in articles)}")

    # 4. 翻译
    print("[4/5] 翻译标题和生成摘要...")
    cache = load_translation_cache()
    for a in articles:
        key = a.get("link") or a.get("title")
        if key in cache:
            a["zh_title"] = cache[key].get("zh_title")
            a["zh_summary"] = cache[key].get("zh_summary")
        else:
            zh_title, zh_summary = translate_with_llm(
                a.get("title", ""),
                a.get("description"),
                source_name=a.get("source_name")
            )
            a["zh_title"] = zh_title
            a["zh_summary"] = zh_summary
            cache[key] = {"zh_title": zh_title, "zh_summary": zh_summary}
    save_translation_cache(cache)

    # 5. 图片处理
    uploaded_images = []
    if not args.no_images:
        print("[5/5] 抓取并上传文章配图...")
        uploaded_images = process_articles_images(articles, date_str, args.max_images)
        print(f"      已上传 {len(uploaded_images)} 张图片")
    else:
        print("[5/5] 跳过图片处理")

    # 6. 生成Markdown
    markdown = generate_markdown(date_str, articles)

    # 7. 保存历史（用于去重）
    save_selected_history(articles, date_str)

    # 8. 输出结果
    if args.output_only:
        print(markdown)
    elif args.save:
        Path(args.save).write_text(markdown, encoding="utf-8")
        print(f"\n已保存到: {args.save}")
    else:
        print("\n" + "="*60)
        print("生成的内容")
        print("="*60)
        print(markdown)

    # 9. 执行摘要
    elapsed = time.time() - start_time
    print_summary(articles, uploaded_images, elapsed)

    return {
        "markdown": markdown,
        "articles": articles,
        "images": uploaded_images,
    }


if __name__ == "__main__":
    result = main()
