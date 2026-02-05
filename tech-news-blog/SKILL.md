---
name: tech-news-blog
description: |
  每日科技新闻聚合器。从 Hacker News、GitHub Trending 等源抓取热门文章，
  AI翻译成中文，自动下载配图上传到R2存储，精选10条生成汇总报告。
  Use when: 用户说"生成今日科技新闻"、"科技新闻"、"tech news"等。
triggers:
  - 生成今日科技新闻
  - 科技新闻
  - tech news
  - 抓取科技新闻
  - 获取今日新闻
inputs:
  - name: sources
    type: array
    description: 新闻源列表
    default: ["hackernews", "github-trending", "lobsters", "devto"]
  - name: limit
    type: integer
    description: 最终精选文章数量
    default: 10
  - name: with_images
    type: boolean
    description: 是否抓取配图上传R2
    default: true
outputs:
  - name: markdown_content
    type: string
    description: Markdown格式新闻汇总
---

# 科技新闻聚合

从多源抓取热门科技新闻，AI翻译为中文，下载配图上传R2，生成汇总报告。

## 快速使用

```bash
./run.sh
```

## 执行流程

1. **抓取新闻**: 从配置的源抓取文章（每源15条）
2. **智能精选**: 均衡选择10条，每源最多2条，自动去重
3. **AI翻译**: 标题翻译为中文，生成摘要和要点
4. **图片处理**: 下载og:image上传到R2，显示公开URL
5. **生成报告**: 按分类组织，输出Markdown

## 分类规则

- **AI与机器学习**: ai, llm, gpt, claude, model
- **开发工具与开源**: rust, python, github, framework
- **基础设施与云原生**: cloud, aws, kubernetes, docker
- **产品与设计**: product, design, ui, startup
- **趣闻与观点**: 其他

## 依赖配置

**翻译API（必需）:**
- `MINIMAX_API_KEY` 或 `OPENAI_API_KEY`

**R2存储（图片上传）:**
- `~/.r2-upload.yml` 配置文件

## 可用参数

```bash
python3 scripts/generate.py \
  --sources hackernews github-trending \
  --limit 10 \
  --max-images 10 \
  --no-images          # 禁用图片
  --save ~/news.md     # 保存到文件
```

## 输出格式

采用固定结构，确保一致性：

```markdown
# 📰 2026-02-05 科技早报

> 📊 **今日导读**
> 精选 10 条科技新闻
> 来源：Hacker News(4) | GitHub Trending(3) | Lobsters(3)

---

## 📋 文章速览

**AI与机器学习**：3 篇
1. 文章标题一
2. 文章标题二
...

---

## AI 与机器学习

### 1. 文章中文标题

📰 **Hacker News**

<img src="https://r2.example.com/image.jpg" width="100%">

**摘要**：中文摘要内容...

**核心要点**：
• 要点一
• 要点二
• 要点三

🔗 [阅读原文](https://example.com)

---
```
