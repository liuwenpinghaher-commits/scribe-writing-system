"""反元叙事 / 验收腔检测（dual-lamp · 宣称可读硬门）。

纯函数 · 零 store IO。
hits 可 claim_blocking 或 soft；默认 **永不** 经 is_blocking_issue 挡存稿。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AntiMetaHit:
    id: str
    start: int
    end: int
    quote: str
    severity: str  # claim_blocking | soft
    message_zh: str


# M2 验收清单腔
_M2_PATTERNS = [
    (re.compile(r"伏笔触碰\s*[:：]"), "像检查清单一样罗列伏笔，读者会出戏"),
    (re.compile(r"信息差维持到章末"), "把「信息差」当验收项写进正文了"),
    (re.compile(r"信息差钉在"), "把「信息差」当验收项写进正文了"),
    (re.compile(r"一一落在读者可感"), "验收腔：在向检查表汇报，不是在讲故事"),
    (re.compile(r"可追踪钩子"), "验收腔：工艺术语入文"),
]

# M1 中文协议状态
_M1_ZH = [
    (re.compile(r"伏笔仍\s*open", re.I), "协议词 open 入文"),
    (re.compile(r"只\s*touch", re.I), "协议词 touch 入文"),
    (re.compile(r"不\s*close", re.I), "协议词 close 入文"),
    (re.compile(r"本章只\s*touch", re.I), "协议词「本章只 touch」入文"),
    (re.compile(r"touch\s*，?\s*不\s*close", re.I), "协议词 touch/close 入文"),
]

_M1_EN = re.compile(r"(?<![A-Za-z])(open|touch|close)(?![A-Za-z])", re.I)
_M1_NEIGHBOR = re.compile(r"伏笔|信息差|回收|本章")

# M3 读者元叙事
_M3 = re.compile(r"读者知道|读者已知|读者可感")
_M3_CO = re.compile(r"信息差|伏笔|钥匙|秘密|不知道")

# M4 soft
_M4 = [
    (re.compile(r"章末钩子悬着"), "结构报幕腔（软提示）"),
    (re.compile(r"本章不揭"), "结构报幕腔（软提示）"),
    (re.compile(r"回收尚未到来"), "结构报幕腔（软提示）"),
]

# M5 soft
_M5 = re.compile(r"主题在.{0,20}轻轻回响")

# M6 stack markers
_M6_MARK = re.compile(r"信息差|伏笔|(?<![A-Za-z])(open|touch|close)(?![A-Za-z])|回收", re.I)


def _clip(s: str, n: int = 80) -> str:
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _hit(id_: str, m: re.Match, sev: str, msg: str) -> AntiMetaHit:
    return AntiMetaHit(
        id=id_,
        start=m.start(),
        end=m.end(),
        quote=_clip(m.group(0)),
        severity=sev,
        message_zh=msg,
    )


def scan_anti_meta(prose: str) -> dict[str, Any]:
    """Scan prose for acceptance-speak / meta-narration."""
    text = prose or ""
    hits: list[AntiMetaHit] = []

    for rx, msg in _M2_PATTERNS:
        for m in rx.finditer(text):
            hits.append(_hit("M2", m, "claim_blocking", msg))

    for rx, msg in _M1_ZH:
        for m in rx.finditer(text):
            hits.append(_hit("M1", m, "claim_blocking", msg))

    for m in _M1_EN.finditer(text):
        # same sentence-ish window
        lo = max(0, m.start() - 24)
        hi = min(len(text), m.end() + 24)
        window = text[lo:hi]
        if _M1_NEIGHBOR.search(window):
            hits.append(_hit("M1", m, "claim_blocking", "协议词 open/touch/close 与伏笔邻域共现"))

    for m in _M3.finditer(text):
        lo = max(0, m.start() - 40)
        hi = min(len(text), m.end() + 40)
        window = text[lo:hi]
        if _M3_CO.search(window):
            hits.append(
                _hit("M3", m, "claim_blocking", "用「读者知道」讲解信息差，出戏")
            )
        else:
            hits.append(_hit("M3", m, "soft", "出现「读者…」表述（软提示）"))

    for rx, msg in _M4:
        for m in rx.finditer(text):
            hits.append(_hit("M4", m, "soft", msg))

    for m in _M5.finditer(text):
        hits.append(_hit("M5", m, "soft", "母题 SEO 腔（软提示）"))

    # M6: same paragraph ≥2 markers
    paras = re.split(r"\n\s*\n", text) if "\n\n" in text else text.split("\n")
    offset = 0
    for para in paras:
        if not para:
            offset += 1
            continue
        marks = list(_M6_MARK.finditer(para))
        if len(marks) >= 2:
            # report first two as one stack hit on first mark in full text
            m0 = marks[0]
            abs_start = offset + m0.start()
            abs_end = offset + marks[-1].end()
            hits.append(
                AntiMetaHit(
                    id="M6",
                    start=abs_start,
                    end=abs_end,
                    quote=_clip(para.strip()),
                    severity="claim_blocking",
                    message_zh="同段堆叠协议/验收词（信息差·伏笔·open/touch…）",
                )
            )
        # advance offset including separator
        offset += len(para)
        if offset < len(text):
            # account for split separators roughly
            while offset < len(text) and text[offset] in "\n":
                offset += 1

    # de-dupe by (id, start, end)
    seen: set[tuple] = set()
    uniq: list[AntiMetaHit] = []
    for h in hits:
        key = (h.id, h.start, h.end)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    uniq.sort(key=lambda h: (h.start, h.id))

    claim_ids = [h.id for h in uniq if h.severity == "claim_blocking"]
    return {
        "hits": [asdict(h) for h in uniq],
        "ok_for_claim": len(claim_ids) == 0,
        "claim_blocking_ids": claim_ids,
    }


def is_meta_span(
    prose: str,
    i: int,
    j: int,
    hits: list[dict[str, Any]] | None = None,
) -> bool:
    """Whether [i,j) intersects any claim_blocking anti_meta hit."""
    if hits is None:
        hits = scan_anti_meta(prose).get("hits") or []
    for h in hits:
        if (h.get("severity") or "") != "claim_blocking":
            continue
        hs, he = int(h.get("start") or 0), int(h.get("end") or 0)
        if not (j <= hs or i >= he):
            return True
    return False
