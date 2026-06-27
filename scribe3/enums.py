"""scribe3 受控枚举 · 单一事实源(替换全库裸字符串 + 注释式枚举域)。

设计:全部 (str, Enum) 以便 JSON 序列化与 == 字符串比较直接可用。
DB 侧对应 ASSERT $value IN [...](migrations/010_enums.surql);两层防护——Python 进程内 + DB 落库层。
"""
from __future__ import annotations

from enum import Enum


class EntityKind(str, Enum):
    character = "character"
    item = "item"
    place = "place"
    faction = "faction"


class AcquiredVia(str, Enum):
    saw = "saw"
    told = "told"
    inferred = "inferred"
    given = "given"
    learned = "learned"
    narrated = "narrated"   # ingest reader_knows 写的值(叙述揭示即读者已知)


class PromiseKind(str, Enum):
    promise = "promise"
    red_herring = "red_herring"


class PromiseStatus(str, Enum):
    open = "open"
    closed = "closed"


class VoiceKind(str, Enum):
    free = "free"
    pressure = "pressure"
    relation = "relation"
    narration = "narration"


class FlagStatus(str, Enum):
    open = "open"
    done = "done"


class CraftRuleKind(str, Enum):
    purple_regex = "purple_regex"
    artifact_craft = "artifact_craft"
    cover_action = "cover_action"
