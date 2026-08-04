"""SurrealStore facade — physical split of legacy store.py."""
from __future__ import annotations

from scribe3.store.connection import ConnectionMixin
from scribe3.store.characters import CharactersMixin
from scribe3.store.facts_knowledge import FactsKnowledgeMixin
from scribe3.store.events import EventsMixin
from scribe3.store.recall import RecallMixin
from scribe3.store.chapters import ChaptersMixin
from scribe3.store.promises import PromisesMixin
from scribe3.store.intent import IntentMixin
from scribe3.store.codex_ext import CodexExtMixin
from scribe3.store.voice_craft import VoiceCraftMixin
from scribe3.store.materials import MaterialsMixin
from scribe3.store.chat_ai import ChatAiMixin
from scribe3.store.structure import StructureMixin
from scribe3.store.works import WorksMixin
from scribe3.store.motifs import MotifsMixin
from scribe3.store.unverified_ingest import UnverifiedIngestMixin
from scribe3.store.progress_stats import ProgressStatsMixin
from scribe3.store.character_arc import CharacterArcMixin
from scribe3.store.misc import MiscMixin

class SurrealStore(ConnectionMixin, CharactersMixin, FactsKnowledgeMixin, EventsMixin, RecallMixin, ChaptersMixin, PromisesMixin, IntentMixin, CodexExtMixin, VoiceCraftMixin, MaterialsMixin, ChatAiMixin, StructureMixin, WorksMixin, MotifsMixin, UnverifiedIngestMixin, ProgressStatsMixin, CharacterArcMixin, MiscMixin):
    """组合各域 mixin;公开 API 与历史 store.SurrealStore 一致。"""
    pass
