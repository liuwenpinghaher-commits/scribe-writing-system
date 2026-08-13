"""定稿散文围栏：剥提案帧 / fallback JSON / 整章复读尾 / 导演提纲腔。

纯函数 · 零 I/O。存章与可见字共用，禁止把机器帧当正文留下。
"""
from __future__ import annotations

import ast
import re
from typing import Any

_FALLBACK_MARK = re.compile(
    r"""['\"]fallback['\"]\s*:\s*True"""
    r"""|fallback['\"]\s*:\s*True"""
    r"""|'fallback':\s*True"""
    r"""|"fallback":\s*True""",
    re.I,
)
_SCOPE_PROSE = re.compile(
    r"""\{\s*['\"]scope['\"]\s*:\s*['\"]chapter['\"]"""
    r"""|\{\s*'scope'\s*:\s*'chapter'"""
)
_PROPOSAL_FENCE = re.compile(r"⟦提案|⟦PROPOSAL⟧|scope=chapter")
_DIRECTOR_HEAD = re.compile(
    r"开写前|正文如下|先理一条线|这一章实质",
)
_CHAPTER_H1 = re.compile(r"^#{1,3}\s*第\s*\d+\s*章", re.M)
_PLACEHOLDER_TITLE = re.compile(r"^第\s*(\d+)\s*章$")
_PUNCT = re.compile(r"[\s，。、「」『』：:；;！？!?（）()【】\[\]…—\-·,.\"]+")


def find_machine_tail_start(prose: str) -> int | None:
    """机器尾起始下标。无则 None。"""
    text = prose or ""
    if not text:
        return None
    candidates: list[int] = []
    m = _SCOPE_PROSE.search(text)
    if m:
        candidates.append(m.start())
    m = _FALLBACK_MARK.search(text)
    if m:
        brace = text.rfind("{", 0, m.start())
        candidates.append(brace if brace >= 0 else m.start())
    m = _PROPOSAL_FENCE.search(text)
    if m:
        candidates.append(m.start())
    if not candidates:
        return None
    return min(candidates)


def strip_machine_tail(prose: str) -> str:
    """只剥提案帧 / fallback dict / 提案围栏，不改章首导演腔。"""
    text = prose or ""
    cut = find_machine_tail_start(text)
    if cut is None:
        return text
    return text[:cut].rstrip()


def _split_dup_suffix(text: str) -> str:
    """若后半几乎是前半拷贝（整章双份），只留前半。"""
    body = (text or "").strip()
    if len(body) < 400:
        return text
    mid = len(body) // 2
    # 在中点附近找段落边界
    window = body[mid - 80 : mid + 80]
    nl = window.find("\n")
    split = mid if nl < 0 else mid - 80 + nl
    a, b = body[:split].strip(), body[split:].strip()
    if len(a) < 200 or len(b) < 200:
        return text
    # 后半以「前半开头」起 → 整章复读
    head = a[:80]
    if b.startswith(head[:40]) or head[:40] in b[:120]:
        return a
    return text


_DIRECTOR_LINE = re.compile(
    r"^(开写前|正文如下|先理一条线|这一章实质).*$",
    re.M,
)


def strip_director_preamble(prose: str) -> str:
    """去掉章首导演备忘录与「## 第X章」标题行。"""
    text = prose or ""
    if not text:
        return text
    head = text[:240]
    if not (_DIRECTOR_HEAD.search(head) or _CHAPTER_H1.search(head)):
        return text
    lines = text.splitlines()
    out: list[str] = []
    skipping = True
    for i, line in enumerate(lines):
        s = line.strip()
        if skipping:
            if not s:
                continue
            if _DIRECTOR_LINE.match(s) or _CHAPTER_H1.match(s) or s == "正文如下：" or s == "正文如下:":
                continue
            if i < 8 and ("限知" in s and "正文如下" in text[:400]):
                # 提纲段内的限知说明
                continue
            skipping = False
        out.append(line)
    return "\n".join(out).lstrip("\n")


def strip_pollution(prose: str) -> str:
    """存章 / 可见字：剥机器尾 + 整章复读 + 导演提纲腔。"""
    text = strip_machine_tail(prose or "")
    text = _split_dup_suffix(text)
    text = strip_director_preamble(text)
    return text.rstrip()


def visible_length(prose: str) -> int:
    """先剥污染再计可见字（去空白）。"""
    clean = strip_pollution(prose)
    return len("".join(clean.split()))


def is_polluted(prose: str) -> bool:
    return find_machine_tail_start(prose or "") is not None


def fill_placeholder_title(title: str, synopsis: str = "", seq: int | None = None) -> str:
    """`第N章` 占位且有 synopsis 时补成「第N章·前八字」。"""
    raw = (title or "").strip()
    m = _PLACEHOLDER_TITLE.match(raw)
    if not m:
        return title or ""
    n = int(m.group(1))
    if seq is not None:
        n = int(seq)
    syn = _PUNCT.sub("", (synopsis or "").strip())
    if len(syn) < 2:
        return raw
    short = syn[:8]
    return f"第{n}章·{short}"


def try_extract_embedded_prose(blob: str) -> str | None:
    """若整段是 `{'scope':'chapter','prose': ...}` 则取出 prose。"""
    text = (blob or "").strip()
    if not text.startswith("{") or "prose" not in text[:80]:
        return None
    try:
        obj = ast.literal_eval(text)
    except Exception:
        return None
    if isinstance(obj, dict) and isinstance(obj.get("prose"), str):
        return obj["prose"]
    return None


_SCENE_MARKERS = (
    "封炉", "灯册", "清册", "核册", "刀鞘", "入芯", "揭册", "假账", "木匣",
)


def strip_replacement_chars(prose: str) -> str:
    """去掉 U+FFFD。SSE/续写拼接坏字节不得进读者正文。"""
    return (prose or "").replace("\ufffd", "")


def find_restaged_scene(prose: str) -> dict[str, Any] | None:
    """续写拼接把同一场面再演一遍：前半与后半共享 ≥3 个场面核。"""
    text = prose or ""
    if len(text) < 1600:
        return None
    mid = len(text) // 2
    a, b = text[:mid], text[mid:]
    shared = [m for m in _SCENE_MARKERS if m in a and m in b]
    if len(shared) >= 3:
        return {"shared": shared, "mid": mid}
    return None


def sanitize_for_persist(prose: str) -> dict[str, Any]:
    """存章入口。返回 {prose, stripped, reasons}。"""
    original = prose or ""
    reasons: list[str] = []
    embedded = try_extract_embedded_prose(original.strip())
    text = embedded if embedded is not None else original
    if embedded is not None:
        reasons.append("embedded_proposal")
    if "\ufffd" in text:
        reasons.append("replacement_char")
        text = strip_replacement_chars(text)
    if find_machine_tail_start(text) is not None:
        reasons.append("machine_tail")
        text = strip_machine_tail(text)
    peeled = _split_dup_suffix(text)
    if peeled != text:
        reasons.append("dup_suffix")
        text = peeled
    directed = strip_director_preamble(text)
    if directed != text:
        reasons.append("director_preamble")
        text = directed
    restage = find_restaged_scene(text)
    if restage:
        reasons.append("restaged_scene")
    return {
        "prose": text.rstrip(),
        "stripped": bool(reasons),
        "reasons": reasons,
        "restage": restage,
    }
