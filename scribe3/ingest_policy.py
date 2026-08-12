"""IngestPolicy 单入口（设计 C-P1 · PR-2）。

纯函数 decide_ingest / allow_distill 可单测；run_or_enqueue 含 I/O。
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Literal

_log = logging.getLogger("scribe3.ingest_policy")

Action = Literal["auto", "hold", "skip"]


@dataclass
class GateSnapshot:
    path: str = "save"
    craft_allowed: bool | None = True
    finalize_verdict: str | None = "pass"  # pass|advisory|blocking|None
    danger_draft: bool = False
    soft_qc: dict | None = None
    ai_grade: str | None = None
    degraded_stages: list = field(default_factory=list)
    create_mode: str | None = None  # standard|explore


@dataclass
class DecideResult:
    action: Action
    reason: str = ""
    hold_reason: str = ""
    confirm_token: str = ""
    prose_fp: str = ""
    skip_reason: str = ""
    allow_distill: bool = False


def prose_fingerprint(prose: str) -> str:
    raw = (prose or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def policy_mode() -> str:
    """auto_if_pass | confirm_all | off"""
    try:
        from scribe3.settings import get_setting
        v = str(get_setting("SCRIBE3_INGEST_POLICY") or "auto_if_pass")
    except Exception:
        v = os.environ.get("SCRIBE3_INGEST_POLICY") or "auto_if_pass"
    v = (v or "auto_if_pass").strip().lower()
    if v in {"off", "0", "false", "disable"}:
        return "off"
    if v in {"confirm", "confirm_all", "always_confirm"}:
        return "confirm_all"
    return "auto_if_pass"


def _hold_state(st, seq: int) -> dict[str, Any]:
    """读 chapter hold 字段。"""
    if st is None:
        return {}
    try:
        ch = st.get_chapter(int(seq)) or {}
        return {
            "reason": (ch.get("ingest_hold_reason") or "").strip(),
            "token": (ch.get("ingest_confirm_token") or "").strip(),
            "fp": (ch.get("ingest_hold_prose_fp") or ch.get("ingest_prose_fp") or "").strip(),
            "until": float(ch.get("ingest_hold_until") or 0),
            "ok_fp": (ch.get("ingest_prose_fp") or "").strip(),
            "status": (ch.get("ingest_status") or "").strip(),
        }
    except Exception:
        return {}


def write_hold(
    st, seq: int, *, reason: str, token: str, prose_fp: str, ttl: float = 86400.0,
) -> None:
    if st is None:
        return
    until = time.time() + ttl
    try:
        st._raw_query(
            "DEFINE FIELD IF NOT EXISTS ingest_hold_reason ON chapter TYPE option<string>;"
        )
        st._raw_query(
            "DEFINE FIELD IF NOT EXISTS ingest_confirm_token ON chapter TYPE option<string>;"
        )
        st._raw_query(
            "DEFINE FIELD IF NOT EXISTS ingest_hold_prose_fp ON chapter TYPE option<string>;"
        )
        st._raw_query(
            "DEFINE FIELD IF NOT EXISTS ingest_hold_until ON chapter TYPE option<float>;"
        )
    except Exception:
        pass
    try:
        st._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_hold_reason=$r, ingest_confirm_token=$t, "
            "ingest_hold_prose_fp=$fp, ingest_hold_until=$u, ingest_status=$st",
            {
                "seq": int(seq), "r": reason[:120], "t": token[:64],
                "fp": prose_fp[:32], "u": until, "st": "held",
            },
        )
    except Exception as e:
        _log.warning("write_hold failed seq=%s: %s", seq, e)


def clear_hold(st, seq: int) -> None:
    if st is None:
        return
    try:
        st._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_hold_reason=NONE, ingest_confirm_token=NONE, "
            "ingest_hold_until=NONE",
            {"seq": int(seq)},
        )
    except Exception:
        pass


def explore_ingest_hold_enabled() -> bool:
    try:
        from scribe3.quality_enablement_flags import explore_ingest_hold_enabled as _f
        return bool(_f())
    except Exception:
        v = (os.environ.get("SCRIBE3_EXPLORE_INGEST_HOLD") or "1").strip().lower()
        return v not in ("0", "false", "no", "off", "")


def decide_ingest(
    st,
    work: str,
    seq: int,
    *,
    gate: GateSnapshot | None,
    prose: str,
    force: bool = False,
    source: str = "save",
    confirm_token: str | None = None,
) -> DecideResult:
    """策略决策（纯 + 读 hold 状态）。"""
    fp = prose_fingerprint(prose)
    mode = policy_mode()
    if mode == "off" and not force:
        return DecideResult(action="skip", skip_reason="policy_off", prose_fp=fp)

    hs = _hold_state(st, seq)
    now = time.time()

    # confirm path
    if source in ("confirm", "ingest_confirm") and confirm_token:
        if hs.get("token") and secrets.compare_digest(
            str(hs.get("token")), str(confirm_token)
        ):
            return DecideResult(
                action="auto", reason="confirm_token_ok", prose_fp=fp,
                allow_distill=True,
            )
        if not force:
            return DecideResult(
                action="hold", reason="bad_confirm_token",
                hold_reason=hs.get("reason") or "held",
                confirm_token=hs.get("token") or "",
                prose_fp=fp,
            )

    # Active hold supersedes (KD18)
    if not force and source not in ("confirm", "ingest_confirm"):
        reason = hs.get("reason") or ""
        until = float(hs.get("until") or 0)
        hold_fp = hs.get("fp") or ""
        active = bool(reason) and (until <= 0 or until > now) and (
            not hold_fp or hold_fp == fp
        )
        if active:
            return DecideResult(
                action="hold",
                reason="active_hold_supersedes",
                hold_reason=reason,
                confirm_token=hs.get("token") or "",
                prose_fp=fp,
                allow_distill=False,
            )

    # same prose already ok
    if not force and hs.get("status") == "ok" and hs.get("ok_fp") == fp:
        return DecideResult(
            action="skip", skip_reason="same_prose_fp", prose_fp=fp,
        )

    g = gate or GateSnapshot(path=source or "save")
    verdict = (g.finalize_verdict or "").strip().lower() or None

    # missing snapshot safety
    if verdict is None and not force:
        if (g.path or source) in (
            "checkpoint", "restore", "dedup", "polish", "semantic_repair",
        ):
            tok = secrets.token_hex(12)
            return DecideResult(
                action="hold",
                reason="missing_gate_snapshot",
                hold_reason="missing_gate_snapshot",
                confirm_token=tok,
                prose_fp=fp,
            )

    if mode == "confirm_all" and not force:
        tok = secrets.token_hex(12)
        return DecideResult(
            action="hold", reason="confirm_all",
            hold_reason="policy_confirm", confirm_token=tok, prose_fp=fp,
        )

    # auto_if_pass
    if g.danger_draft and not force:
        tok = secrets.token_hex(12)
        return DecideResult(
            action="hold", reason="danger_draft",
            hold_reason="danger_draft", confirm_token=tok, prose_fp=fp,
        )
    # WS-3：explore 实质稿默认 hold，防 dual-truth 自动进正典
    _cm = getattr(g, "create_mode", None)
    if not _cm:
        try:
            from scribe3.quality_enablement_flags import create_mode as _cm_fn
            _cm = _cm_fn()
        except Exception:
            _cm = os.environ.get("SCRIBE3_CREATE_MODE") or "standard"
    if (
        not force
        and explore_ingest_hold_enabled()
        and str(_cm).strip().lower() == "explore"
        and len((prose or "").strip()) >= 80
    ):
        tok = secrets.token_hex(12)
        return DecideResult(
            action="hold",
            reason="explore_draft",
            hold_reason="explore_draft",
            confirm_token=tok,
            prose_fp=fp,
            allow_distill=False,
        )
    if (g.ai_grade or "").lower() == "heavy" and not force:
        # save path: if blocking already rejected, we wouldn't be here
        # advisory soft: hold
        tok = secrets.token_hex(12)
        return DecideResult(
            action="hold", reason="ai_heavy",
            hold_reason="ai_heavy", confirm_token=tok, prose_fp=fp,
        )
    if verdict in ("blocking", "block", "fail") and not force:
        return DecideResult(
            action="skip", skip_reason="blocking_verdict", prose_fp=fp,
        )
    if verdict == "advisory" and not force:
        tok = secrets.token_hex(12)
        return DecideResult(
            action="hold", reason="advisory_gate",
            hold_reason="advisory_gate", confirm_token=tok, prose_fp=fp,
        )
    # pass or empty treated as pass for save after gate allowed
    return DecideResult(
        action="auto", reason="auto_if_pass", prose_fp=fp, allow_distill=True,
    )


def allow_distill(decision: DecideResult, *, apply_ok: bool, source: str = "") -> bool:
    """pure hold 禁止 distill；auto/confirm/force 成功 apply → 允许。"""
    if not apply_ok:
        return False
    if decision.action == "hold":
        return False
    if decision.action == "skip":
        return False
    return bool(decision.allow_distill or source in ("confirm", "force", "ingest_confirm"))


def run_or_enqueue(
    st,
    work: str,
    seq: int,
    *,
    mode: Literal["sync", "bg"] = "bg",
    background=None,
    gate: GateSnapshot | None = None,
    prose: str = "",
    force: bool = False,
    source: str = "save",
    confirm_token: str | None = None,
    complete_fn=None,
    max_attempts: int = 3,
    distill: bool = True,
) -> dict[str, Any]:
    """单入口编排：decide → lease → ingest → distill → release。"""
    from scribe3.ingest_lease import (
        combined_backend, new_owner, try_acquire_ingest_lease, release_ingest_lease,
    )

    if not prose and st is not None:
        try:
            ch = st.get_chapter(int(seq)) or {}
            prose = ch.get("prose") or ""
        except Exception:
            prose = ""

    decision = decide_ingest(
        st, work, int(seq),
        gate=gate, prose=prose, force=force, source=source,
        confirm_token=confirm_token,
    )
    out: dict[str, Any] = {
        "action": decision.action,
        "reason": decision.reason or decision.skip_reason or decision.hold_reason,
        "prose_fp": decision.prose_fp,
        "enqueued": False,
        "held": decision.action == "hold",
        "confirm_token": decision.confirm_token or None,
        "hold_reason": decision.hold_reason or None,
    }

    if decision.action == "hold":
        # active supersede: 已 held，勿用空 token 覆盖已有 confirm 字段
        if decision.reason != "active_hold_supersedes":
            write_hold(
                st, int(seq),
                reason=decision.hold_reason or decision.reason,
                token=decision.confirm_token or secrets.token_hex(12),
                prose_fp=decision.prose_fp,
            )
        return out

    if decision.action == "skip":
        return out

    # auto
    if mode == "bg":
        if background is None:
            out["action"] = "skip"
            out["reason"] = "no_background"
            return out
        # 清 hold 后排队
        clear_hold(st, int(seq))
        from scribe3.api.services.ingest_bg import _enqueue_ingest_raw
        enq = _enqueue_ingest_raw(background, work, int(seq))
        out["enqueued"] = bool(enq)
        out["reason"] = decision.reason if enq else "already_pending"
        return out

    # sync：A5 chapter_lock(ingest) + lease CAS
    ch_lock_held = False
    try:
        from scribe3.chapter_lock import acquire_chapter_lock
        clr = acquire_chapter_lock("ingest", work, int(seq), store=st, ttl_seconds=600)
        if not clr.ok:
            out["action"] = "skip"
            out["reason"] = "chapter_lock_busy"
            return out
        ch_lock_held = True
    except Exception as e:
        _log.debug("sync ingest chapter_lock: %s", e)
    backend = combined_backend(st)
    owner = new_owner()
    acq = try_acquire_ingest_lease(backend, work, int(seq), owner, ttl=600.0)
    if not acq.ok:
        if ch_lock_held:
            try:
                from scribe3.chapter_lock import release_chapter_lock
                release_chapter_lock("ingest", work, int(seq), store=st)
            except Exception:
                pass
        out["action"] = "skip"
        out["reason"] = "lease_busy"
        out["lease_owner"] = acq.owner
        return out
    try:
        from scribe3.ingest import ingest_chapter
        from scribe3.llm import hermes_complete
        fn = complete_fn or hermes_complete
        clear_hold(st, int(seq))
        r = ingest_chapter(
            st, int(seq), fn, work=work, force=bool(force),
            max_attempts=int(max_attempts),
            lease_owner=owner, lease_backend=backend,
        )
        apply_ok = not r.get("parse_failed") and not r.get("error")
        if r.get("skipped"):
            out["ingest"] = r
            out["reason"] = "same_prose_fp_ingest"
            return out
        out["ingest"] = r if isinstance(r, dict) else {}
        out["ingest_summary"] = {k: r.get(k) for k in (
            "parse_failed", "prose_fp", "skipped", "error",
        ) if isinstance(r, dict) and k in r}
        if (
            distill
            and apply_ok
            and allow_distill(decision, apply_ok=True, source=source)
        ):
            try:
                from scribe3.lesson import distill_chapter
                distill_chapter(st, int(seq), fn)
                out["distilled"] = True
            except Exception as e:
                _log.warning("distill after ingest failed: %s", e)
                out["distilled"] = False
        try:
            from scribe3.api.services.ingest_bg import mark_chapter_ingest_status
            if r.get("parse_failed"):
                mark_chapter_ingest_status(st, int(seq), "parse_failed", "parse_failed")
            else:
                mark_chapter_ingest_status(
                    st, int(seq), "ok", prose_fp=r.get("prose_fp") or decision.prose_fp,
                )
        except Exception:
            pass
        return out
    finally:
        release_ingest_lease(backend, work, int(seq), owner)
        if ch_lock_held:
            try:
                from scribe3.chapter_lock import release_chapter_lock
                release_chapter_lock("ingest", work, int(seq), store=st)
            except Exception:
                pass
