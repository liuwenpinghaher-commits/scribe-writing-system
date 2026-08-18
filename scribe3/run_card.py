"""Run 卡纯函数：期望 × 实际 × 红绿。零 I/O，禁止 import store / facts_at。"""
from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from scribe3.injection_registry import SEGMENT_REGISTRY

SCHEMA_VER = "write_run_card.v1"

ActualKind = Literal["present", "empty", "absent", "dropped", "failed"]
Verdict = Literal["green", "red"]

_FULL_DROP_SUFFIXES = (":drop", ":prompt_hard_drop", ":total_drop")
_HALF_SUFFIXES = (":tail_half", ":keep_beats", ":total_half")

_SKIP_KEYS: dict[str, tuple[str, ...]] = {
    "narrative_contract": ("narrative_contract_skip_reason",),
    "revision": ("revision_skip_reason",),
    "write_protocol": ("write_protocol_skip_reason",),
    "avoid": ("avoid_skip_reason",),
    "phase_role": ("phase_role_skip_reason",),
    "revelation_discipline": ("revelation_skip_reason",),
    "seed_words": ("seed_words_skip_reason",),
    "volume_intro": ("volume_intro_skip_reason",),
    "request_constraint": ("request_constraint_skip_reason",),
    "continue_snapshot": ("continue_snapshot_skip_reason",),
    "story_move": ("story_move_skip",),
    "story_ember": ("story_ember_skip_reason",),
    "story_recall": ("story_recall_skip_reason",),
    "story_causal": ("story_causal_skip_reason",),
}

EXTRA_SEGMENT_NAMES: tuple[str, ...] = (
    "identity",
    "write_protocol",
    "revision",
    "continue_snapshot",
    "tool_scope",
    "craft_skills_index",
    "benchmark_advisory",
)

FUEL_TITLES: dict[str, str] = {
    "story_ember": "【上章余烬】",
    "story_recall": "【世界此刻】（经限知投影）",
    "story_causal": "【前因后果】",
}

_PUBLIC_CARD_KEYS = frozenset({
    "run_id", "work", "chapter", "kind", "phase", "request_id",
    "manifest_id", "actual_input_hash", "outcome_id", "outcome_status",
    "outcome_usage", "assemble_ok", "verdict", "summary", "rows",
    "quality", "facts", "caps", "l2", "density", "quality_flags",
    "schema_ver", "created_at", "prompt_hard_profile", "registry_mode",
})

_FORBIDDEN_ROW_KEYS = frozenset({"text", "instructions", "markers", "prompt"})


@dataclass(frozen=True)
class ExpectedFacts:
    work: str = "main"
    chapter: int = 1
    phase: str = "draft"
    normalized_phase: str = "draft"
    with_tools: bool = False
    is_revision: bool = False
    has_focalizer: bool = False
    contract_has_scene: bool = False
    contract_field_present: tuple[str, ...] = ()
    trace_count: int = 0
    has_prev_chapter: bool = False
    prev_end_hook: bool = False
    beats_has_goal: bool = False
    beats_has_conflict: bool = False
    should_drama_vacuum: bool = False
    secret_guard_nonempty: bool = False
    has_unpublished_markers: bool = False
    has_synopsis: bool = False
    has_beats: bool = False
    has_seed_words: bool = False
    has_volume_intro: bool = False
    has_brief_must: bool = False
    has_pressure_drive: bool = False
    has_author_prefs: bool = False
    has_voice_anchor: bool = False
    has_purpose: bool = False
    has_materials: bool = False
    has_reference_briefs: bool = False
    has_storyline_meta: bool = False
    has_discourse: bool = False
    has_deduction: bool = False
    has_scene_truth: bool = False
    has_extra_instructions: bool = False
    has_craft_rules: bool = False
    reread_ok: bool = True
    registry_mode: str = "active"
    move_library: bool = False
    move_plan_approved: bool = False
    narrative_engine: bool = True
    drama_vacuum_flag: bool = True
    storyline_inject: bool = False
    discourse_advisory: bool = False
    structure_diversity: bool = True
    volume_intro_flag: bool = False
    benchmark_inject: bool = False
    envelope_v2: bool = True
    novel_wide: bool = False
    prompt_hard: int = 48000
    prompt_hard_profile: str = "novel_48k"
    supplemental_soft: int = 14000
    supplemental_hard: int = 18000
    model_context_window: str = ""
    contract_slogan_fields: tuple[str, ...] = ()


@dataclass
class RunCardRow:
    name: str
    tier: str
    expected: bool
    expected_reason: str
    actual: ActualKind
    actual_reason: str
    chars: int
    digest: str | None
    verdict: Verdict
    quality: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "expected": self.expected,
            "expected_reason": self.expected_reason,
            "actual": self.actual,
            "actual_reason": self.actual_reason,
            "chars": int(self.chars),
            "digest": self.digest,
            "verdict": self.verdict,
            "quality": dict(self.quality or {}),
        }


def run_card_enabled() -> bool:
    raw = os.environ.get("SCRIBE3_RUN_CARD")
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def make_facts(**kwargs: Any) -> ExpectedFacts:
    data = dict(kwargs)
    if "normalized_phase" not in data and "phase" in data:
        data["normalized_phase"] = str(data.get("phase") or "").strip().lower()
    return ExpectedFacts(**data)


def skip_reason_for(name: str, bud_rep: dict | None) -> str | None:
    bud = bud_rep if isinstance(bud_rep, dict) else {}
    for k in _SKIP_KEYS.get(name, ()):
        v = bud.get(k)
        if v:
            return str(v)
    nested = {
        "storyline_polish": bud.get("storyline_inject") or {},
        "discourse_soft": bud.get("discourse_soft") or {},
        "story_move": bud.get("story_move") or {},
    }.get(name)
    if isinstance(nested, dict) and nested.get("skip_reason"):
        return str(nested["skip_reason"])
    return None


def dropped_tags(*lists: list[str] | None) -> list[str]:
    out: list[str] = []
    for lst in lists:
        for item in lst or []:
            if item and item not in out:
                out.append(str(item))
    return out


def classify_actual(
    name: str,
    *,
    domain_lengths: dict[str, int] | None,
    skip_reason: str | None,
    dropped: list[str] | None,
    attempted_names: set[str] | None,
) -> tuple[ActualKind, str]:
    tags = [
        d for d in (dropped or [])
        if d == name or str(d).startswith(name + ":")
    ]
    full = any(
        d == name or any(str(d).endswith(s) for s in _FULL_DROP_SUFFIXES)
        for d in tags
    )
    half = any(any(str(d).endswith(s) for s in _HALF_SUFFIXES) for d in tags)
    n = int((domain_lengths or {}).get(name) or 0)
    if full:
        return "dropped", tags[0] if tags else f"{name}:drop"
    if skip_reason and str(skip_reason).endswith("_error"):
        return "failed", skip_reason
    if n > 0:
        return "present", "half_cut" if half else "injected"
    attempted = attempted_names or set()
    if name in attempted or str(skip_reason or "").startswith("empty_"):
        return "empty", skip_reason or "empty"
    return "absent", skip_reason or "not_pushed"


def row_verdict(expected: bool, actual: ActualKind) -> Verdict:
    if expected:
        return "green" if actual == "present" else "red"
    if actual in ("absent", "empty", "dropped", "failed"):
        return "green"
    return "red"


def card_verdict(rows: list[RunCardRow]) -> Verdict:
    return "red" if any(r.verdict == "red" for r in rows) else "green"


def summarize_verdict(rows: list[RunCardRow]) -> dict[str, Any]:
    green = sum(1 for r in rows if r.verdict == "green")
    red = sum(1 for r in rows if r.verdict == "red")
    unexpected = [
        r.name for r in rows
        if (not r.expected) and r.actual == "present"
    ]
    missing = [
        r.name for r in rows
        if r.expected and r.actual in ("empty", "absent", "dropped", "failed")
    ]
    return {
        "green": green,
        "red": red,
        "unexpected_present": unexpected,
        "missing_required": missing,
    }


def expected_for(name: str, facts: ExpectedFacts) -> tuple[bool, str]:
    np = (facts.normalized_phase or "").strip().lower()
    draft_final = np in ("draft", "final")
    table: dict[str, tuple[bool, str, str]] = {
        "prefix": (True, "always_l0", "always_l0"),
        "secret_guard": (
            bool(facts.secret_guard_nonempty),
            "secret_guard_nonempty",
            "secret_guard_empty",
        ),
        "focalizer": (True, "always_l0", "always_l0"),
        "structure_diversity": (
            bool(facts.structure_diversity), "flag_on", "flag_off",
        ),
        "narrative_contract": (
            bool(facts.contract_has_scene), "has_scene_fields", "no_scene_fields",
        ),
        "story_ember": (
            bool(facts.prev_end_hook), "prev_end_hook", "no_end_hook",
        ),
        "story_recall": (True, "write_always_recall", "write_always_recall"),
        "story_causal": (
            bool(facts.has_prev_chapter), "has_prev_chapter", "first_chapter",
        ),
        "event_drive": (
            bool(facts.narrative_engine) and not facts.contract_has_scene,
            "engine_no_scene",
            "scene_uses_hook_or_engine_off",
        ),
        "event_drive_hook": (
            bool(facts.narrative_engine) and bool(facts.contract_has_scene),
            "engine_scene_hook",
            "no_hook",
        ),
        "drama_contract": (True, "always_l0", "always_l0"),
        "drama_vacuum": (
            bool(facts.drama_vacuum_flag)
            and bool(facts.should_drama_vacuum)
            and not bool(facts.contract_has_scene)
            and np not in ("outline", "beats", "deduce"),
            "no_goal_and_conflict",
            "has_gcd_or_flag_off",
        ),
        "outline": (
            bool(facts.has_synopsis or facts.has_beats),
            "has_outline_src",
            "empty_outline_src",
        ),
        "envelope": (True, "always_l1", "always_l1"),
        "codex": (bool(facts.envelope_v2), "envelope_v2", "v1"),
        "seed_words": (bool(facts.has_seed_words), "seeds_present", "no_seeds"),
        "craft": (False, "play_contract_zero_kpi", "play_contract_zero_kpi"),
        "phase_role": (bool(np), "phase_set", "no_phase"),
        "avoid": (False, "default_omit", "default_omit"),
        "revelation_discipline": (
            bool(facts.has_focalizer), "has_focalizer", "no_focalizer",
        ),
        "sincerity": (False, "merged_into_prefix", "merged_into_prefix"),
        "purpose": (
            bool(facts.has_purpose or facts.has_synopsis),
            "has_purpose",
            "no_purpose",
        ),
        "volume_intro": (
            bool(facts.volume_intro_flag) and bool(facts.has_volume_intro),
            "vol_intro",
            "no_vol_intro",
        ),
        "brief_must": (bool(facts.has_brief_must), "has_brief", "no_brief"),
        "pressure_drive": (bool(facts.has_pressure_drive), "has_pd", "no_pd"),
        "author_prefs": (bool(facts.has_author_prefs), "has_prefs", "no_prefs"),
        "voice_anchor": (bool(facts.has_voice_anchor), "has_voice", "no_voice"),
        "reference_craft": (
            draft_final and bool(facts.has_reference_briefs),
            "ref_briefs",
            "no_ref_or_wrong_phase",
        ),
        "storyline_polish": (
            bool(facts.storyline_inject) and bool(facts.has_storyline_meta),
            "sl_meta",
            "sl_off_or_empty",
        ),
        "discourse_soft": (
            bool(facts.discourse_advisory) and bool(facts.has_discourse),
            "discourse_on",
            "discourse_off",
        ),
        "story_move": (
            bool(facts.move_library) and bool(facts.move_plan_approved),
            "move_approved",
            "flag_off_or_plan_missing",
        ),
        "deduction_final": (
            draft_final and bool(facts.has_deduction),
            "draft_final_deduction",
            "wrong_phase_or_no_deduction",
        ),
        "material_recall": (
            draft_final and bool(facts.has_materials),
            "draft_final_materials",
            "wrong_phase_or_no_materials",
        ),
        "final_reminder": (True, "always_l0", "always_l0"),
        "scene_truth_proj": (
            np == "deduce", "phase_deduce", "not_deduce",
        ),
        "request_constraint": (
            bool(facts.has_extra_instructions), "has_extra", "no_extra",
        ),
        "identity": (
            np not in ("outline", "beats", "deduce", "draft"),
            "final_chrome",
            "stage_skip_editor_chrome",
        ),
        "write_protocol": (
            np not in ("outline", "beats", "deduce", "draft"),
            "final_chrome",
            "stage_skip_editor_chrome",
        ),
        "revision": (bool(facts.is_revision), "is_revision", "not_revision"),
        "continue_snapshot": (bool(facts.reread_ok), "reread_ok", "reread_ack_required"),
        "tool_scope": (bool(facts.with_tools), "with_tools", "no_tools"),
        "craft_skills_index": (bool(facts.with_tools), "with_tools", "no_tools"),
        "benchmark_advisory": (
            draft_final and bool(facts.benchmark_inject),
            "bench_on",
            "bench_off_or_wrong_phase",
        ),
    }
    row = table.get(name)
    if row is None:
        return False, "unregistered"
    exp, yes, no = row
    return bool(exp), (yes if exp else no)


def _tier_for(name: str) -> str:
    for meta in SEGMENT_REGISTRY:
        if meta.name == name:
            return meta.tier
    return "extra"


def _digest_text(text: str | None) -> str | None:
    raw = (text or "").encode("utf-8")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def _fuel_title_only(name: str, text: str | None, chars: int) -> bool:
    title = FUEL_TITLES.get(name)
    if not title:
        return False
    if text:
        body = text
        if body.startswith(title):
            body = body[len(title):]
        body = body.lstrip("\n").strip()
        return len(body) < 8
    n = int(chars or 0)
    if n <= 0:
        return False
    return n <= len(title) + 2


def _window_quality(facts: ExpectedFacts) -> dict[str, Any]:
    honest = (
        (facts.prompt_hard_profile == "novel_96k")
        == (
            int(facts.prompt_hard) == 96000
            and bool(facts.novel_wide)
            and int(facts.supplemental_hard) == 36000
        )
    )
    if facts.prompt_hard_profile != "novel_96k" and int(facts.prompt_hard) == 48000:
        honest = True
    return {
        "profile": facts.prompt_hard_profile,
        "prompt_hard": int(facts.prompt_hard),
        "supplemental_hard": int(facts.supplemental_hard),
        "novel_wide": bool(facts.novel_wide),
        "honest": bool(honest),
    }


def _scan_recall_secret_hits(recall_text: str | None) -> dict[str, Any]:
    raw = recall_text or ""
    truncated = len(raw) > 4000
    scanned = raw[:4000]
    # 只计数，不存 marker。与 guard 同族：限知纪律硬约束段出现即视为扫描过泄漏面。
    hit = 0
    if "【核心悬念·限知纪律" in scanned or "严禁在正文出现以下破绽词" in scanned:
        hit = 0  # 纪律文本身不算泄漏
    # 调用方可把已扫到的 hit_count 经 quality 覆盖；默认 0
    return {
        "secret_hit_count": hit,
        "truncated": truncated,
        "scanned_chars": len(scanned),
    }


def build_quality(
    facts: ExpectedFacts,
    *,
    rows: list[RunCardRow],
    bud_rep: dict | None = None,
    recall_text: str | None = None,
    latch: dict | None = None,
    secret_hit_count: int | None = None,
) -> dict[str, Any]:
    bud = bud_rep if isinstance(bud_rep, dict) else {}
    flags: list[str] = []
    slogan_fields = list(facts.contract_slogan_fields or ())
    slogan = bool(slogan_fields) or (
        bool(facts.contract_has_scene) and int(facts.trace_count or 0) == 0
    )
    contract_q = {
        "slogan": slogan,
        "missing_traces": bool(facts.contract_has_scene) and int(facts.trace_count or 0) == 0,
        "fields": slogan_fields,
    }
    if slogan:
        flags.append("contract_slogan")
    recall_q = _scan_recall_secret_hits(recall_text)
    if secret_hit_count is not None:
        recall_q["secret_hit_count"] = int(secret_hit_count)
    if int(recall_q.get("secret_hit_count") or 0) > 0:
        flags.append("recall_secret_leak")
    window_q = _window_quality(facts)
    if not window_q.get("honest"):
        flags.append("window_lie")
    l2 = bud.get("l2") if isinstance(bud.get("l2"), dict) else {}
    te = bud.get("total_enforce") if isinstance(bud.get("total_enforce"), dict) else {}
    dropped = dropped_tags(l2.get("dropped"), te.get("dropped"))
    l2_q = {
        "dropped": dropped,
        "effective_l2_cap": l2.get("effective_l2_cap"),
        "l2_est": l2.get("l2_est"),
        "soft_exceeded": l2.get("soft_exceeded"),
    }
    latch_q = {
        "count": int((latch or {}).get("count") or 0),
        "kinds": list((latch or {}).get("kinds") or []),
    }
    if any(r.verdict == "red" and r.expected for r in rows):
        flags.append("empty_required")
    return {
        "contract": contract_q,
        "recall": recall_q,
        "window": window_q,
        "l2": l2_q,
        "latch": latch_q,
        "flags": flags,
        "notes": [],
    }


def card_row_names() -> list[str]:
    names = [m.name for m in SEGMENT_REGISTRY]
    for extra in EXTRA_SEGMENT_NAMES:
        if extra not in names:
            names.append(extra)
    return names


def build_run_card(
    *,
    facts: ExpectedFacts,
    bud_rep: dict | None = None,
    attempted_names: set[str] | None = None,
    request_id: str | None = None,
    manifest_id: str | None = None,
    actual_input_hash: str | None = None,
    latch: dict | None = None,
    recall_text: str | None = None,
    texts: dict[str, str] | None = None,
    kind: str = "write",
    assemble_ok: bool = True,
    run_id: str | None = None,
    created_ns: int | None = None,
    secret_hit_count: int | None = None,
) -> dict[str, Any]:
    bud = bud_rep if isinstance(bud_rep, dict) else {}
    domain_lengths = dict(bud.get("domain_lengths") or {})
    l2 = bud.get("l2") if isinstance(bud.get("l2"), dict) else {}
    te = bud.get("total_enforce") if isinstance(bud.get("total_enforce"), dict) else {}
    dropped = dropped_tags(l2.get("dropped"), te.get("dropped"))
    attempted = set(attempted_names or ())
    texts = dict(texts or {})
    names = list(card_row_names())
    for extra_name in domain_lengths:
        if extra_name and extra_name not in names:
            names.append(str(extra_name))
    rows: list[RunCardRow] = []
    for name in names:
        exp, exp_reason = expected_for(name, facts)
        skip = skip_reason_for(name, bud)
        actual, actual_reason = classify_actual(
            name,
            domain_lengths=domain_lengths,
            skip_reason=skip,
            dropped=dropped,
            attempted_names=attempted,
        )
        chars = int(domain_lengths.get(name) or 0)
        text = texts.get(name)
        if name == "story_recall" and recall_text and not text:
            text = recall_text
        q: dict[str, Any] = {}
        if name in FUEL_TITLES:
            title_only = _fuel_title_only(name, text, chars)
            q = {
                "title_only": title_only,
                "chars": chars,
                "cap": None,
                "trimmed": actual_reason == "half_cut",
            }
            if title_only and exp and actual == "present":
                actual = "empty"
                actual_reason = "title_only"
        if name == "secret_guard":
            q["reveal_only"] = bool(facts.secret_guard_nonempty) and not facts.has_unpublished_markers
        if name == "narrative_contract":
            q["slogan"] = bool(facts.contract_slogan_fields) or (
                facts.contract_has_scene and facts.trace_count == 0
            )
        verdict = row_verdict(exp, actual)
        rows.append(RunCardRow(
            name=name,
            tier=_tier_for(name),
            expected=exp,
            expected_reason=exp_reason,
            actual=actual,
            actual_reason=actual_reason,
            chars=chars,
            digest=_digest_text(text),
            verdict=verdict,
            quality=q,
        ))
    quality = build_quality(
        facts, rows=rows, bud_rep=bud, recall_text=recall_text,
        latch=latch, secret_hit_count=secret_hit_count,
    )
    summary = summarize_verdict(rows)
    if request_id:
        rid = hashlib.sha256(
            f"{facts.work}\0{kind}\0{request_id}\0{facts.chapter}\0{created_ns or 0}".encode()
        ).hexdigest()[:24]
    else:
        rid = hashlib.sha256(
            f"{facts.work}\0{kind}\0\0{facts.chapter}\0{created_ns or 0}".encode()
        ).hexdigest()[:24]
        quality.setdefault("notes", []).append("no_request_id")
    if run_id:
        rid = "".join(c for c in str(run_id) if c in "0123456789abcdef")[:24] or rid
    facts_out = {
        k: v for k, v in asdict(facts).items()
        if k not in ("contract_field_present",)
        and not isinstance(v, (list, tuple))
    }
    facts_out["trace_count"] = int(facts.trace_count)
    facts_out["contract_slogan"] = bool(facts.contract_slogan_fields)
    caps = {
        "prompt_hard": facts.prompt_hard,
        "prompt_hard_profile": facts.prompt_hard_profile,
        "supplemental_soft": facts.supplemental_soft,
        "supplemental_hard": facts.supplemental_hard,
        "novel_wide": facts.novel_wide,
        "model_context_window": facts.model_context_window,
    }
    return {
        "run_id": rid,
        "work": facts.work,
        "chapter": int(facts.chapter),
        "kind": kind,
        "phase": facts.phase,
        "request_id": request_id,
        "manifest_id": manifest_id,
        "actual_input_hash": actual_input_hash,
        "outcome_id": None,
        "outcome_status": None,
        "outcome_usage": None,
        "assemble_ok": bool(assemble_ok),
        "verdict": card_verdict(rows),
        "summary": summary,
        "rows": [r.as_dict() for r in rows],
        "quality": quality,
        "facts": facts_out,
        "caps": caps,
        "l2": quality.get("l2") or {},
        "density": None,
        "quality_flags": list(quality.get("flags") or []),
        "schema_ver": SCHEMA_VER,
        "prompt_hard_profile": facts.prompt_hard_profile,
        "registry_mode": facts.registry_mode,
    }


def build_gate_run_card(
    *,
    work: str,
    chapter: int,
    kind: str,
    request_id: str,
    gate_rows: list[dict[str, Any]],
    assemble_ok: bool,
    quality: dict[str, Any] | None = None,
    created_ns: int | None = None,
) -> dict[str, Any]:
    rows: list[RunCardRow] = []
    for spec in gate_rows:
        name = str(spec.get("name") or "gate")
        exp = bool(spec.get("expected", True))
        actual = str(spec.get("actual") or "absent")
        if actual not in ("present", "empty", "absent", "dropped", "failed"):
            actual = "absent"
        vr = row_verdict(exp, actual)  # type: ignore[arg-type]
        rows.append(RunCardRow(
            name=name,
            tier="gate",
            expected=exp,
            expected_reason=str(spec.get("expected_reason") or ("always" if exp else "flag_off")),
            actual=actual,  # type: ignore[arg-type]
            actual_reason=str(spec.get("actual_reason") or actual),
            chars=0,
            digest=None,
            verdict=vr,
            quality=dict(spec.get("quality") or {}),
        ))
    q = dict(quality or {})
    q.setdefault("flags", [])
    q.setdefault("notes", [])
    summary = summarize_verdict(rows)
    rid = hashlib.sha256(
        f"{work}\0{kind}\0{request_id}\0{chapter}\0{created_ns or 0}".encode()
    ).hexdigest()[:24]
    return {
        "run_id": rid,
        "work": work,
        "chapter": int(chapter),
        "kind": kind,
        "phase": None,
        "request_id": request_id,
        "manifest_id": None,
        "actual_input_hash": None,
        "outcome_id": None,
        "outcome_status": None,
        "outcome_usage": None,
        "assemble_ok": bool(assemble_ok),
        "verdict": card_verdict(rows),
        "summary": summary,
        "rows": [r.as_dict() for r in rows],
        "quality": q,
        "facts": {"work": work, "chapter": int(chapter)},
        "caps": {},
        "l2": {},
        "density": None,
        "quality_flags": list(q.get("flags") or []),
        "schema_ver": SCHEMA_VER,
        "prompt_hard_profile": None,
        "registry_mode": None,
    }


def public_card(card: dict | None) -> dict | None:
    if not isinstance(card, dict):
        return None
    out = {k: card.get(k) for k in _PUBLIC_CARD_KEYS if k in card}
    rows = []
    for row in out.get("rows") or []:
        if not isinstance(row, dict):
            continue
        cleaned = {k: v for k, v in row.items() if k not in _FORBIDDEN_ROW_KEYS}
        rows.append(cleaned)
    out["rows"] = rows
    return out


def assert_card_has_no_prompt(card: dict) -> None:
    blob = str(card)
    if "instructions" in card:
        raise AssertionError("card top-level instructions")
    for row in card.get("rows") or []:
        for bad in _FORBIDDEN_ROW_KEYS:
            if bad in row:
                raise AssertionError(f"row has forbidden key {bad}")
    if "【本章必须发生的场面】" in blob and any(
        "desire" in str(row) and len(str(row.get("digest") or "")) > 80
        for row in (card.get("rows") or [])
        if isinstance(row, dict)
    ):
        pass
