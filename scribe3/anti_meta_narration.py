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

# M7 导演提纲腔 / 机器提案尾（claim_blocking）
_M7_DIRECTOR = re.compile(r"开写前|正文如下|先理一条线|这一章实质")
_M7_HEADING = re.compile(r"^#{1,3}\s*第\s*\d+\s*章", re.M)
_M7_MACHINE = re.compile(
    r"""['\"]fallback['\"]\s*:\s*True|'fallback':\s*True|"fallback":\s*True"""
    r"""|\{\s*['\"]scope['\"]\s*:\s*['\"]chapter['\"]"""
    r"""|⟦提案""",
    re.I,
)


def _clip(s: str, n: int = 80) -> str:
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    """Full-line [start, end) containing pos (end exclusive, may include newline)."""
    if not text:
        return 0, 0
    pos = max(0, min(pos, len(text)))
    lo = text.rfind("\n", 0, pos)
    lo = 0 if lo < 0 else lo + 1
    hi = text.find("\n", pos)
    if hi < 0:
        hi = len(text)
    return lo, hi


def _sentence_bounds(text: str, pos: int) -> tuple[int, int]:
    """Coarse sentence [start, end) containing pos."""
    if not text:
        return 0, 0
    pos = max(0, min(pos, len(text)))
    lo = pos
    while lo > 0 and text[lo - 1] not in "。！？\n…":
        lo -= 1
    hi = pos
    while hi < len(text) and text[hi] not in "。！？\n…":
        hi += 1
    if hi < len(text) and text[hi] in "。！？…":
        hi += 1
    return lo, hi


def _hit_span(
    id_: str, start: int, end: int, text: str, sev: str, msg: str,
) -> AntiMetaHit:
    return AntiMetaHit(
        id=id_,
        start=start,
        end=end,
        quote=_clip(text[start:end]),
        severity=sev,
        message_zh=msg,
    )


def _hit(id_: str, m: re.Match, text: str, sev: str, msg: str, *, expand_line: bool) -> AntiMetaHit:
    """Build hit; claim_blocking M1/M2 expand to whole line so list tails are covered."""
    s, e = m.start(), m.end()
    if expand_line and sev == "claim_blocking":
        s, e = _line_bounds(text, m.start())
    return _hit_span(id_, s, e, text, sev, msg)


# 行级验收腔（用于 is_meta_span 扩展：清单词在「伏笔触碰：」后）
_ACCEPT_LINE = re.compile(
    r"伏笔触碰\s*[:：]|信息差维持到章末|信息差钉在|伏笔仍\s*open|"
    r"本章只\s*touch|只\s*touch|不\s*close|读者知道|读者已知|"
    r"一一落在读者可感|(?<![A-Za-z])(open|touch|close)(?![A-Za-z])",
    re.I,
)


def scan_anti_meta(prose: str) -> dict[str, Any]:
    """Scan prose for acceptance-speak / meta-narration."""
    text = prose or ""
    hits: list[AntiMetaHit] = []

    for rx, msg in _M2_PATTERNS:
        for m in rx.finditer(text):
            hits.append(_hit("M2", m, text, "claim_blocking", msg, expand_line=True))

    for rx, msg in _M1_ZH:
        for m in rx.finditer(text):
            hits.append(_hit("M1", m, text, "claim_blocking", msg, expand_line=True))

    for m in _M1_EN.finditer(text):
        lo = max(0, m.start() - 24)
        hi = min(len(text), m.end() + 24)
        window = text[lo:hi]
        if _M1_NEIGHBOR.search(window):
            hits.append(
                _hit("M1", m, text, "claim_blocking",
                     "协议词 open/touch/close 与伏笔邻域共现", expand_line=True)
            )

    for m in _M3.finditer(text):
        lo = max(0, m.start() - 40)
        hi = min(len(text), m.end() + 40)
        window = text[lo:hi]
        if _M3_CO.search(window):
            # expand sentence so co-located 钥匙/秘密 also covered
            s, e = _sentence_bounds(text, m.start())
            hits.append(_hit_span(
                "M3", s, e, text, "claim_blocking",
                "用「读者知道」讲解信息差，出戏",
            ))
        else:
            hits.append(_hit("M3", m, text, "soft", "出现「读者…」表述（软提示）", expand_line=False))

    for rx, msg in _M4:
        for m in rx.finditer(text):
            hits.append(_hit("M4", m, text, "soft", msg, expand_line=False))

    for m in _M5.finditer(text):
        hits.append(_hit("M5", m, text, "soft", "母题 SEO 腔（软提示）", expand_line=False))

    # M6: same line ≥2 markers → whole line claim_blocking
    offset = 0
    for line in text.split("\n"):
        marks = list(_M6_MARK.finditer(line))
        if len(marks) >= 2:
            hits.append(
                AntiMetaHit(
                    id="M6",
                    start=offset,
                    end=offset + len(line),
                    quote=_clip(line.strip()),
                    severity="claim_blocking",
                    message_zh="同段堆叠协议/验收词（信息差·伏笔·open/touch…）",
                )
            )
        offset += len(line) + 1  # + newline

    # M7: 导演备忘录（章首 240 字）+ 机器提案尾
    head = text[:240]
    for rx, msg in (
        (_M7_DIRECTOR, "导演提纲腔入文（开写前/正文如下），不可宣称可读"),
        (_M7_HEADING, "章首 Markdown 章题像写作备忘，不是正文"),
    ):
        for m in rx.finditer(head):
            hits.append(_hit("M7", m, text, "claim_blocking", msg, expand_line=True))
    for m in _M7_MACHINE.finditer(text):
        hits.append(_hit(
            "M7", m, text, "claim_blocking",
            "提案帧/fallback 机器尾入文，不可宣称可读",
            expand_line=True,
        ))

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
    """Whether [i,j) is inside acceptance-speak (expanded hits or accept line)."""
    text = prose or ""
    if hits is None:
        hits = scan_anti_meta(text).get("hits") or []
    for h in hits:
        if (h.get("severity") or "") != "claim_blocking":
            continue
        hs, he = int(h.get("start") or 0), int(h.get("end") or 0)
        if not (j <= hs or i >= he):
            return True
    # line-level fallback: keyword sits on an acceptance-speak line
    if 0 <= i < len(text):
        lo, hi = _line_bounds(text, i)
        line = text[lo:hi]
        if _ACCEPT_LINE.search(line):
            return True
        # SEO 清单：必须是顿号枚举 + 验收引导词。
        # 禁止把普通逗号长句（「袖子里抖出一卷册子，也不铺垫，平着摊…」）当验收清单，
        # 否则 scene_cover 会把已落地的场面词全部判死。
        if "、" in line and re.search(r"伏笔触碰|触碰\s*[:：]|主题|母题|验收", line):
            parts = [p for p in re.split(r"[、]", line) if p.strip()]
            if len(parts) >= 3:
                return True
    return False
