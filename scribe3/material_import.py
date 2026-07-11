"""素材导入流水线纯逻辑:解析(markitdown)→ AI 切分打标 + 手法摘要。

解析器/LLM 注入便于测试。全程 fail-soft:LLM 失败降级整篇一条,单条校验失败跳过——
导入不因个别条目坏而丢整批。手法摘要供召回时"借鉴非照搬"(spec §6.2)。
"""
from __future__ import annotations

import json

from scribe3.store import MATERIAL_KINDS


def parse_to_markdown(src, converter=None) -> str:
    """用 markitdown 把文件/URL 转 markdown(converter 注入便于测试)。"""
    if converter is None:
        from markitdown import MarkItDown
        converter = MarkItDown()
    return converter.convert(src).text_content


def split_and_tag(markdown: str, llm, source: str | None = None) -> list[dict]:
    """长 markdown → 多条素材候选(AI 切分 + 每条 title/kind/ref_tags/body/summary)。
    llm(prompt)->str。单条校验失败 fail-soft 跳过;LLM 整体失败 → 整篇降级为一条(不丢数据)。"""
    if not (markdown or "").strip():
        return []
    prompt = (
        "把以下资料切分成若干条独立、可复用的写作素材。每条给:\n"
        "- title: 简短标题\n"
        f"- kind: 分类之一 {list(MATERIAL_KINDS)}\n"
        "- ref_tags: 参考维度数组(风格/剧情/手法/情绪/桥段/世界观 中若干)\n"
        "- body: 素材正文(保留可借鉴的原文要点)\n"
        "- summary: 一句话手法摘要(这条可借鉴之处,供写作时借鉴而非照搬)\n"
        '只返回 JSON 数组:[{"title":"","kind":"","ref_tags":[],"body":"","summary":""}]\n\n'
        f"资料:\n{markdown[:8000]}")
    try:
        raw = llm(prompt)
        items = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        if not isinstance(items, list):
            raise ValueError("非数组")
    except Exception:
        # LLM/解析失败降级:整篇作为一条素材,不丢数据
        return [{"title": (markdown[:20].strip() or "导入素材"), "body": markdown,
                 "kind": "note", "ref_tags": [], "summary": "", "source": source}]
    out = []
    for it in items:
        if not isinstance(it, dict) or not (it.get("title") or "").strip():
            continue   # fail-soft:无标题条跳过
        kind = it.get("kind") if it.get("kind") in MATERIAL_KINDS else "note"
        out.append({"title": it["title"].strip(), "body": it.get("body") or "",
                    "kind": kind, "ref_tags": it.get("ref_tags") or [],
                    "summary": it.get("summary") or "", "source": source})
    return out
