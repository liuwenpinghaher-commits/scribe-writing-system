"""素材导入流水线纯逻辑:解析(markitdown)→ AI 切分打标 + 手法摘要。

解析器/LLM 注入便于测试。全程 fail-soft:LLM 失败降级整篇一条,单条校验失败跳过——
导入不因个别条目坏而丢整批。手法摘要供召回时"借鉴非照搬"(spec §6.2)。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from urllib.parse import urlparse

from scribe3.store import MATERIAL_KINDS


def parse_to_markdown(src, converter=None) -> str:
    """用 markitdown 把文件/URL 转 markdown(converter 注入便于测试)。"""
    if converter is None:
        from markitdown import MarkItDown
        converter = MarkItDown()
    return converter.convert(src).text_content


def _is_private_host(host: str) -> bool:
    """基础 SSRF 防护:拦 loopback / 明显内网 host。"""
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in ("localhost", "metadata.google.internal"):
        return True
    if h.endswith(".local") or h.endswith(".internal"):
        return True
    if h == "::1" or h.startswith("[::1]"):
        return True
    # 裸 IP 粗判
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", h):
        parts = [int(x) for x in h.split(".")]
        a, b = parts[0], parts[1]
        if a == 10 or a == 127 or a == 0:
            return True
        if a == 192 and b == 168:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        if a == 169 and b == 254:
            return True
    return False


def _assert_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的 URL scheme: {parsed.scheme!r}")
    if _is_private_host(parsed.hostname or ""):
        raise ValueError("拒绝访问内网/本地地址")


def _default_public_fetcher(url: str, *, max_hops: int = 5):
    """httpx 抓取:不自动跟随跳转,每跳再检私网。"""
    import httpx
    from urllib.parse import urljoin

    current = url
    for _ in range(max_hops):
        _assert_public_http_url(current)
        r = httpx.get(current, timeout=30, follow_redirects=False)
        if 300 <= r.status_code < 400:
            loc = (r.headers.get("location") or "").strip()
            if not loc:
                r.raise_for_status()
                return r.content
            current = urljoin(current, loc)
            continue
        r.raise_for_status()
        return r.content
    raise ValueError("拒绝访问内网/本地地址")


def parse_url_to_markdown(url: str, fetcher=None, converter=None) -> str:
    """抓取 URL 正文并经 markitdown 转 markdown(避免 raw HTML 直接入切分)。

    fetcher(url)->bytes|str 可注入;默认 httpx。内网 host 与跳转后的内网一律拒绝。
    """
    _assert_public_http_url(url)
    if fetcher is None:
        fetcher = _default_public_fetcher
    raw = fetcher(url)
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="replace")
    # 根据 path 猜后缀;默认 .html 让 markitdown 走 HTML 路径
    path = urlparse(url).path or ""
    suffix = os.path.splitext(path)[1] or ".html"
    if suffix.lower() not in (".html", ".htm", ".md", ".markdown", ".txt", ".pdf", ".docx"):
        suffix = ".html"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(raw)
        tmp.close()
        return parse_to_markdown(tmp.name, converter=converter)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


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


def near_dup_warning_payload(dups: list[dict], index: int, title: str) -> dict | None:
    """把 find_near_duplicate 结果压成 commit warning 形状;无候选则 None。"""
    if not dups:
        return None
    top = dups[0]
    return {
        "index": index,
        "title": title,
        "stage": "near_duplicate",
        "reason": f"疑似与已有素材重复: {top.get('title') or top.get('id')} "
                  f"(sim={top.get('sim')}, {top.get('reason')})",
        "matches": dups,
    }
