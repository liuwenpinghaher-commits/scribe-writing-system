"""参考标尺文本分段：纯函数，供导入后指纹 map-reduce 使用。

原则：
- 优先按 Markdown 标题 / 中文章卷标题切分；
- 超长段再按 target_chars 切片；
- 绝不在这里截断全书到固定 12k——分析器必须能拿到全部 segment。
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Iterable

# 单段目标字符数；十余兆作品会得到多段，迫使 map 覆盖全书而非首窗。
SEGMENT_TARGET_CHARS = 4_000
# 粘贴路径软上限：非整书主路径，避免浏览器 JSON 巨包。
PASTE_MAX_CHARS = 100_000

_MD_HEADING = re.compile(r"(?m)(?=^#{1,3}\s+\S)")
_CN_CHAPTER = re.compile(
    r"(?m)(?=^第[零〇一二三四五六七八九十百千万0-9]+[章节回部卷]\s*)"
)


@dataclass(frozen=True)
class ReferenceSegment:
    index: int
    text: str
    digest: str
    char_count: int

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "digest": self.digest,
            "char_count": self.char_count,
        }


def _digest_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_by_patterns(text: str) -> list[str]:
    for pattern in (_MD_HEADING, _CN_CHAPTER):
        parts = [p.strip() for p in pattern.split(text) if p and p.strip()]
        if len(parts) > 1:
            return parts
    return [text.strip()] if text.strip() else []


def _window_split(text: str, target_chars: int) -> list[str]:
    if len(text) <= int(target_chars * 1.5):
        return [text]
    out: list[str] = []
    step = max(1, target_chars)
    for start in range(0, len(text), step):
        chunk = text[start : start + step].strip()
        if chunk:
            out.append(chunk)
    return out or [text]


def segment_reference_text(
    text: str,
    *,
    target_chars: int = SEGMENT_TARGET_CHARS,
) -> tuple[ReferenceSegment, ...]:
    """把参考正文切成有序 segment；空文本返回空元组。"""
    raw = (text or "").strip()
    if not raw:
        return ()
    pieces: list[str] = []
    for part in _split_by_patterns(raw):
        pieces.extend(_window_split(part, target_chars))
    if not pieces:
        pieces = [raw]
    segments: list[ReferenceSegment] = []
    for index, piece in enumerate(pieces):
        segments.append(
            ReferenceSegment(
                index=index,
                text=piece,
                digest=_digest_text(piece),
                char_count=len(piece),
            )
        )
    return tuple(segments)


def total_chars(segments: Iterable[ReferenceSegment]) -> int:
    return sum(s.char_count for s in segments)
