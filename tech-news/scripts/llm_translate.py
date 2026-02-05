#!/usr/bin/env python3
"""LLM translation client supporting Minimax and OpenAI.

Env:
  # Option 1: Minimax
  MINIMAX_API_KEY (required)
  MINIMAX_BASE_URL (optional, default: https://api.minimaxi.com/anthropic)
  MINIMAX_MODEL (optional, default: MiniMax-M2.1-lightning)

  # Option 2: OpenAI
  OPENAI_API_KEY (required)
  OPENAI_BASE_URL (optional, default: https://api.openai.com)
  OPENAI_MODEL (optional, default: gpt-4o-mini)

Priority: Minimax > OpenAI
"""

from __future__ import annotations

import json
import os
import urllib.request


class TranslationError(Exception):
    """Translation API error with safe error message (no API key)."""
    pass


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sanitize_error(error: Exception) -> str:
    """Remove sensitive info from error message."""
    msg = str(error)
    # Remove potential API keys (patterns like sk-...)
    import re
    msg = re.sub(r'sk-[a-zA-Z0-9_-]{20,}', '***API_KEY***', msg)
    return msg


def translate_title_and_summary(
    title: str,
    description: str | None = None,
    source: str | None = None,
) -> tuple[str, str]:
    """Translate title + description to Chinese (title + summary + bullets)."""

    src = source or ""
    desc = (description or "").strip()

    system = """Output ONLY:
标题：<Chinese title>
摘要：<2-3 Chinese sentences>
要点：
- <bullet 1>
- <bullet 2>
- <bullet 3>"""

    user_text = f"来源：{src}\n标题：{title}\n描述：{desc}"

    # Try Minimax first
    minimax_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if minimax_key:
        base_url = os.environ.get(
            "MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"
        ).rstrip("/")
        model = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.1-lightning")

        payload = {
            "model": model,
            "max_tokens": 1500,
            "system": system,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_text}]}
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {minimax_key}",
        }
        try:
            out = _post_json(f"{base_url}/v1/messages", payload, headers, timeout=90)
            content = out.get("content", [])
            text_block = ""
            for block in content:
                if block.get("type") == "text":
                    text_block = block.get("text", "")
                    break

            if not text_block:
                raise TranslationError("No text block in response")

            return _parse_response(text_block)
        except Exception as e:
            safe_msg = _sanitize_error(e)
            raise TranslationError(f"Minimax translation failed: {safe_msg}")

    # Fallback to OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_key:
        raise TranslationError(
            "No translation API configured. Set MINIMAX_API_KEY or OPENAI_API_KEY."
        )

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_key}",
    }

    try:
        out = _post_json(f"{base_url}/v1/chat/completions", payload, headers, timeout=60)
        text = out["choices"][0]["message"]["content"].strip()
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        zh_title = parts[0].splitlines()[0].strip()
        zh_summary = "\n\n".join(parts[1:]).strip() if len(parts) > 1 else ""
        return zh_title, zh_summary
    except Exception as e:
        safe_msg = _sanitize_error(e)
        raise TranslationError(f"OpenAI translation failed: {safe_msg}")


def _parse_response(text: str) -> tuple[str, str]:
    """Parse Minimax response format."""
    lines = text.split("\n")
    zh_title = ""
    summary_parts = []
    bullet_parts = []
    current_section = ""

    for line in lines:
        line = line.strip()
        if line.startswith("标题："):
            zh_title = line[3:].strip()
        elif line.startswith("摘要："):
            current_section = "summary"
            summary_parts = [line[3:].strip()]
        elif line.startswith("要点："):
            current_section = "bullets"
        elif line.startswith("- "):
            if current_section == "bullets":
                bullet_parts.append(line[2:].strip())
            elif current_section == "summary":
                summary_parts.append(line[2:].strip())
        elif line and current_section == "summary":
            summary_parts.append(line)

    while len(bullet_parts) < 3:
        bullet_parts.append("细节待补充")

    zh_summary = "\n\n".join(summary_parts) if summary_parts else ""
    if bullet_parts:
        zh_summary = zh_summary + "\n\n要点：\n" + "\n".join(f"- {b}" for b in bullet_parts)

    return zh_title, zh_summary
