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
from scribe3.store.canon_candidates import CanonCandidatesMixin
from scribe3.store.progress_stats import ProgressStatsMixin
from scribe3.store.character_arc import CharacterArcMixin
from scribe3.store.misc import MiscMixin
from scribe3.store.storyline import StorylineStoreMixin
from scribe3.store.pilot_ops import PilotOpsMixin
from scribe3.store.infra_ops import InfraOpsMixin
from scribe3.store.context_ops import ContextOpsMixin
from scribe3.store.adapter_ops import AdapterOpsMixin
from scribe3.store.quality_ops import QualityOpsMixin
from scribe3.store.story_moves import StoryMovesMixin
from scribe3.store.run_card_ops import RunCardOpsMixin
from scribe3.store.pipeline_trace_ops import PipelineTraceOpsMixin

class SurrealStore(ConnectionMixin, CharactersMixin, FactsKnowledgeMixin, EventsMixin, RecallMixin, ChaptersMixin, PromisesMixin, IntentMixin, CodexExtMixin, VoiceCraftMixin, MaterialsMixin, ChatAiMixin, StructureMixin, WorksMixin, MotifsMixin, UnverifiedIngestMixin, CanonCandidatesMixin, ProgressStatsMixin, CharacterArcMixin, StorylineStoreMixin, PilotOpsMixin, InfraOpsMixin, ContextOpsMixin, AdapterOpsMixin, QualityOpsMixin, StoryMovesMixin, RunCardOpsMixin, PipelineTraceOpsMixin, MiscMixin):
    """组合各域 mixin;公开 API 与历史 store.SurrealStore 一致。"""
    pass
