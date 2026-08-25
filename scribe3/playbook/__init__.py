"""Play & Contract chapter pipeline (playbook.3.2.14)."""
from scribe3.playbook.quote import PLAYBOOK_VERSION, _norm, quote_in_play
from scribe3.playbook.errors import FrozenAssetError, StageGone, StructFail
from scribe3.playbook.envelope import artifact_sha, wrap
from scribe3.playbook.memory_store import (
    MemoryPlaybookStore,
    freeze_artifact,
    overwrite_play,
    supersede_downstream,
)
from scribe3.playbook.judge import VERSIONED_RUBRICS
from scribe3.playbook.pipeline import extract_chapter_state, run_stage
from scribe3.playbook.stages import (
    LIVE_STAGES,
    MIGRATE_HINT,
    normalize_stage,
    reject_gone_stage,
    stage_max_tokens,
)
from scribe3.playbook.structural import (
    check_contract_struct,
    check_deduce_struct,
    check_duty_struct,
    check_play_struct,
)
from scribe3.playbook.assemble import assemble_final_prompt

__all__ = [
    "PLAYBOOK_VERSION",
    "_norm",
    "quote_in_play",
    "FrozenAssetError",
    "StageGone",
    "StructFail",
    "artifact_sha",
    "wrap",
    "MemoryPlaybookStore",
    "freeze_artifact",
    "overwrite_play",
    "supersede_downstream",
    "run_stage",
    "extract_chapter_state",
    "VERSIONED_RUBRICS",
    "LIVE_STAGES",
    "MIGRATE_HINT",
    "normalize_stage",
    "reject_gone_stage",
    "stage_max_tokens",
    "check_contract_struct",
    "check_deduce_struct",
    "check_duty_struct",
    "check_play_struct",
    "assemble_final_prompt",
]
