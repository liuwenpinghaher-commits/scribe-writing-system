"""飞行记录仪：真实工件 + 完整事件。零 I/O。"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from scribe3.pipeline_trace import current_trace_buffer
from scribe3.pipeline_trace_catalog import lookup

SCHEMA_VER = "pipeline_recorder.v1"

RECORDER_FORBIDDEN_KEYS = frozenset({
    "instructions", "markers", "prompt", "arguments",
    "secret", "leak_markers", "input_text",
})

EVENT_KINDS = frozenset({
    "read", "pred", "branch", "emit", "keep", "drop", "skip", "produce", "consume",
    "budget", "usage", "error", "flag", "join", "gate", "obs_incomplete",
})

ARTIFACT_KINDS = frozenset({
    "story_inputs", "segment", "drop_before", "drop_after",
    "envelope_block", "fuel_block", "joined_meta",
    "gate_input", "outcome_meta",
    "spine_card", "must_land", "fate_delta", "ore_atoms", "choice_span", "seed_census",
    "gesture_print",
    "prompt", "output", "dropped", "gate_detail",
})


def put_fate_artifact(kind: str, name: str, body: str, *, redact: str = "secrets") -> None:
    rec = current_recorder()
    if rec is None or not getattr(rec, "enabled", True):
        return
    if kind not in ARTIFACT_KINDS:
        return
    try:
        rec.put_artifact(kind=kind, name=name, body=body or "", redact=redact)
    except Exception:
        return

REAL_KINDS = frozenset({
    "story_inputs", "fuel_block", "drop_before", "segment", "joined_meta",
})

PAYLOAD_TOP = frozenset({
    "source", "text", "preview_80", "chars", "chars_in", "chars_before", "chars_after",
    "chars_total", "tokens_est", "tokens_before", "tokens_after", "digest", "empty", "got",
    "artifact_id", "artifact_ids", "from_artifact_id", "from_span_id", "from_step_key",
    "name", "names", "keys", "shapes", "json_type", "length",
    "pred", "pred_value", "reason", "inputs", "fn", "branch", "op", "tag", "priority",
    "flag", "cap", "used", "remaining", "l0_est", "l1_est", "l2_est", "prompt_hard",
    "soft_exceeded", "shape", "status", "duration_ms", "hit_count", "kinds", "chunk_count",
    "provider", "model", "input_tokens", "output_tokens",
    "outcome_id", "manifest_id", "joined_digest", "pre_guard_digest", "post_guard_digest",
    "order", "raw_chars", "clipped_chars", "marker_count", "marker_lens",
    "class", "summary", "missing", "truncated", "role", "blocks", "omitted",
    "selected_n", "rejected_n", "total_token_estimate", "envelope_hash",
    "segment_names", "segment_artifact_ids",
    "guard_hits", "guard_scrubbed", "output_hash", "output_chars", "scrubbed",
})

_SECRET_RE = re.compile(r"(?i)(sk-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._\-]{12,})")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")


def pipeline_recorder_enabled() -> bool:
    raw = ""
    try:
        from scribe3.settings import get_setting
        val = get_setting("SCRIBE3_PIPELINE_RECORDER")
        if val is not None and str(val).strip() != "":
            raw = str(val).strip().lower()
    except Exception:
        raw = ""
    if not raw:
        raw = str(get_flag("SCRIBE3_PIPELINE_RECORDER") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def artifact_cap() -> int:
    raw = (get_flag("SCRIBE3_PIPELINE_ARTIFACT_CAP") or "16384").strip()
    try:
        return max(512, int(raw))
    except ValueError:
        return 16384


def current_recorder() -> "FlightRecorder | None":
    buf = current_trace_buffer()
    rec = getattr(buf, "recorder", None) if buf is not None else None
    return rec if isinstance(rec, FlightRecorder) else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _hex(n: int) -> str:
    return os.urandom(n).hex()


def digest_text(text: str | None) -> str | None:
    raw = (text or "").encode("utf-8")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def redact_secrets_inplace(s: str) -> str:
    return _SECRET_RE.sub("〔密〕", s or "")


def strip_recorder_forbidden(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in RECORDER_FORBIDDEN_KEYS:
                continue
            out[k] = strip_recorder_forbidden(v)
        return out
    if isinstance(obj, list):
        return [strip_recorder_forbidden(x) for x in obj]
    if isinstance(obj, str):
        return redact_secrets_inplace(obj)
    return obj


def _filter_payload(payload: dict | None) -> dict[str, Any]:
    src = strip_recorder_forbidden(dict(payload or {}))
    return {k: v for k, v in src.items() if k in PAYLOAD_TOP}


def dump_story_inputs(data: dict[str, Any] | None) -> dict[str, Any]:
    src = dict(data or {})
    contract = src.get("contract") if isinstance(src.get("contract"), dict) else {}
    voice = src.get("voice") if isinstance(src.get("voice"), dict) else {}
    ev = src.get("evidence_must_show")
    if not isinstance(ev, list):
        ev = []
    dump = {
        "chapter": int(src.get("chapter") or 0),
        "prev_chapter": int(src.get("prev_chapter") or max(0, int(src.get("chapter") or 1) - 1)),
        "contract": {
            "desire": str(contract.get("desire") or ""),
            "obstacle": str(contract.get("obstacle") or ""),
            "turn": str(contract.get("turn") or ""),
            "cost": str(contract.get("cost") or ""),
            "other_keys": list(contract.get("other_keys") or []),
            "bindings_keys": list(contract.get("bindings_keys") or []),
        },
        "evidence_must_show": [str(x) for x in ev],
        "voice": {
            "register": str(voice.get("register") or voice.get("label") or ""),
            "label": str(voice.get("label") or voice.get("register") or ""),
        },
        "prior_consequences": str(src.get("prior_consequences") or ""),
        "recall_context": str(src.get("recall_context") or ""),
        "causal_graph": str(src.get("causal_graph") or ""),
    }
    dump["presence"] = {
        "contract": any(dump["contract"][k] for k in ("desire", "obstacle", "turn", "cost")),
        "desire": bool(dump["contract"]["desire"]),
        "obstacle": bool(dump["contract"]["obstacle"]),
        "turn": bool(dump["contract"]["turn"]),
        "cost": bool(dump["contract"]["cost"]),
        "evidence_must_show": bool(dump["evidence_must_show"]),
        "voice": bool(dump["voice"]["register"] or dump["voice"]["label"]),
        "prior_consequences": bool(str(src.get("prior_consequences") or "").strip())
        if "prior_consequences" in src else False,
        "recall_context": bool(dump["recall_context"].strip()),
        "causal_graph": bool(dump["causal_graph"].strip()),
    }
    dump["chars"] = {
        "desire": len(dump["contract"]["desire"]),
        "obstacle": len(dump["contract"]["obstacle"]),
        "turn": len(dump["contract"]["turn"]),
        "cost": len(dump["contract"]["cost"]),
        "evidence_must_show": sum(len(str(x)) for x in dump["evidence_must_show"]),
        "prior_consequences": len(dump["prior_consequences"]),
        "recall_context": len(dump["recall_context"]),
        "causal_graph": len(dump["causal_graph"]),
    }
    return dump


def completeness_check(
    step_key: str,
    events: list[dict],
    artifacts: list[dict],
    *,
    ctx: dict | None = None,
) -> list[str]:
    """缺合同事件/工件 → 字符串列表。未开步不查。"""
    ctx = ctx or {}
    started = bool(ctx.get("started"))
    if not started:
        return []
    kinds = {str(e.get("kind") or "") for e in events}
    if "skip" in kinds:
        return []
    art_kinds = {str(a.get("kind") or "") for a in artifacts}
    missing: list[str] = []
    key = str(step_key or "")
    if key == "assemble.load_story_inputs":
        if "story_inputs" not in art_kinds:
            missing.append("story_inputs")
        if "read" not in kinds:
            missing.append("read")
        if "produce" not in kinds:
            missing.append("produce")
    elif key == "assemble.seg.story_ember":
        if "read" not in kinds:
            missing.append("read")
        if "pred" not in kinds:
            missing.append("pred")
    elif key == "budget.l2":
        expect_drops = int(ctx.get("drop_n") or 0)
        drop_arts = [a for a in artifacts if a.get("kind") == "drop_before"]
        if expect_drops and len(drop_arts) < expect_drops:
            missing.append("drop_before")
    elif key in ("assemble.compile", "compile.joined"):
        if "joined_meta" not in art_kinds and "join" not in kinds:
            missing.append("join")
    return missing


class FlightRecorder:
    """挂在 TraceBuffer 上。零 I/O。"""

    def __init__(self, *, work: str = "main", chapter: int = 0, kind: str = "write",
                 trace_id: str = "", enabled: bool | None = None) -> None:
        self.work = str(work or "main")
        self.chapter = int(chapter or 0)
        self.chain_kind = str(kind or "write")
        self.trace_id = str(trace_id or "")
        self.enabled = pipeline_recorder_enabled() if enabled is None else bool(enabled)
        self.artifacts: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._seq = 0
        self._produced_by_key: dict[str, list[str]] = {}
        self._produced_by_name: dict[str, str] = {}
        self._artifact_index: dict[str, dict[str, Any]] = {}
        self._span_key: dict[str, str] = {}
        self.n_events_flushed = 0
        self.n_artifacts_flushed = 0

    def remember_span(self, span_id: str, step_key: str) -> None:
        if span_id and step_key:
            self._span_key[span_id] = step_key

    def has_real_artifact(self) -> bool:
        return any(a.get("kind") in REAL_KINDS for a in self.artifacts)

    def put_artifact(
        self,
        *,
        kind: str,
        name: str,
        body: str,
        media: str = "text",
        span_id: str = "",
        tokens_est: int | None = None,
        redact: str | None = None,
    ) -> str:
        if not self.enabled:
            return ""
        if not isinstance(body, str):
            return ""
        nm = str(name or "")
        if nm == "secret_guard" and redact != "secret_guard":
            return ""
        text = body
        redacted = False
        if redact == "secret_guard":
            text = re.sub(
                r"严禁在正文出现以下破绽词[^。]*。|破绽词含：[^。]*。",
                "破绽词：〔已打码〕",
                text,
                flags=re.S,
            )
            redacted = True
        elif redact == "secrets":
            text = redact_secrets_inplace(text)
            redacted = text != body
        text = redact_secrets_inplace(text)
        full = len(text)
        cap = artifact_cap()
        trunc = full > cap
        stored = text[:cap] if trunc else text
        pre_digest = digest_text(text)
        aid = _hex(8)
        row = {
            "id": aid,
            "artifact_id": aid,
            "trace_id": self.trace_id,
            "span_id": span_id or None,
            "kind": str(kind or "segment"),
            "name": nm or None,
            "media": "json" if media == "json" else "text",
            "body": stored,
            "digest": pre_digest,
            "chars": len(stored),
            "chars_full": full,
            "tokens_est": tokens_est,
            "truncated": trunc,
            "redacted": redacted,
            "work": self.work,
            "chapter": self.chapter,
            "schema_ver": SCHEMA_VER,
        }
        self.artifacts.append(row)
        self._artifact_index[aid] = {
            "id": aid,
            "kind": row["kind"],
            "name": row["name"],
            "chars": int(row["chars"] or 0),
            "chars_full": int(row["chars_full"] or 0),
        }
        return aid

    def produced_segments(self) -> list[dict[str, Any]]:
        """drain 后仍可用：按 produce 名取 kind=segment 的字数与 id。"""
        out: list[dict[str, Any]] = []
        for name, aid in self._produced_by_name.items():
            meta = self._artifact_index.get(str(aid) or "") or {}
            if meta.get("kind") != "segment":
                continue
            full = int(meta.get("chars_full") or 0)
            stored = int(meta.get("chars") or 0)
            out.append({
                "id": str(aid),
                "name": str(name),
                "chars": full or stored,
            })
        return out

    def snapshot_join(self) -> dict[str, Any]:
        """compile_joined 合同：段序 + 真字数 + 可 consume 的 id。"""
        segs = self.produced_segments()
        return {
            "order": [s["name"] for s in segs],
            "chars_total": sum(int(s["chars"]) for s in segs),
            "segment_names": [s["name"] for s in segs],
            "segment_artifact_ids": [s["id"] for s in segs],
        }

    def emit(
        self,
        span_id: str,
        kind: str,
        *,
        summary: str = "",
        empty: bool | None = None,
        pred: str | None = None,
        pred_value: bool | None = None,
        artifact_ids: list[str] | None = None,
        from_span_id: str | None = None,
        from_step_key: str | None = None,
        from_artifact_id: str | None = None,
        payload: dict | None = None,
        level: str | None = None,
    ) -> str:
        if not self.enabled:
            return ""
        raw_kind = str(kind or "")
        missing = None
        if raw_kind not in EVENT_KINDS:
            missing = [raw_kind[:32] or "unknown"]
            raw_kind = "other"
        pay = _filter_payload(payload)
        if missing:
            pay["missing"] = missing
        self._seq += 1
        eid = _hex(8)
        meta = lookup(self._span_key.get(span_id) or "")
        step_key = self._span_key.get(span_id) or meta.step_key or ""
        summ = str(summary or "")[:240]
        row = {
            "id": eid,
            "event_id": eid,
            "trace_id": self.trace_id,
            "span_id": span_id or None,
            "seq": self._seq,
            "ts": _now_iso(),
            "level": level or ("warn" if raw_kind in ("drop", "obs_incomplete", "error") else "info"),
            "step_key": step_key,
            "step_title": meta.step_title or None,
            "layer": meta.layer or None,
            "kind": raw_kind,
            "summary": summ or None,
            "empty": empty,
            "pred": pred,
            "pred_value": pred_value,
            "artifact_ids": list(artifact_ids or []) or None,
            "from_span_id": from_span_id,
            "from_step_key": from_step_key,
            "from_artifact_id": from_artifact_id,
            "payload": pay or None,
            "work": self.work,
            "chapter": self.chapter,
            "chain_kind": self.chain_kind,
            "schema_ver": SCHEMA_VER,
        }
        self.events.append(row)
        return eid

    def produce(self, span_id: str, artifact_id: str, *, name: str = "") -> None:
        if not self.enabled or not artifact_id:
            return
        step_key = self._span_key.get(span_id) or ""
        self._produced_by_key.setdefault(step_key, []).append(artifact_id)
        if name:
            self._produced_by_name[name] = artifact_id
        self.emit(
            span_id, "produce",
            artifact_ids=[artifact_id],
            from_artifact_id=artifact_id,
            payload={"artifact_id": artifact_id, "name": name or None, "got": True},
        )

    def consume(
        self,
        dest_span_id: str,
        *,
        from_step_key: str | None = None,
        artifact_id: str | None = None,
        name: str | None = None,
        role: str = "input",
        got: bool = True,
    ) -> str | None:
        if not self.enabled:
            return None
        aid = str(artifact_id or "").strip()
        if not _HEX16.match(aid):
            if name and name in self._produced_by_name:
                aid = self._produced_by_name[name]
            elif from_step_key:
                ids = self._produced_by_key.get(from_step_key) or []
                if len(ids) == 1:
                    aid = ids[0]
                else:
                    return None
            else:
                aid = ""
        if got and not _HEX16.match(aid):
            return None
        return self.emit(
            dest_span_id, "consume",
            from_step_key=from_step_key,
            from_artifact_id=aid or None,
            artifact_ids=[aid] if aid else None,
            payload={"got": bool(got), "role": role, "from_artifact_id": aid or None},
        )

    def drain(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ev, ar = list(self.events), list(self.artifacts)
        self.n_events_flushed += len(ev)
        self.n_artifacts_flushed += len(ar)
        self.events.clear()
        self.artifacts.clear()
        return ev, ar

    def counts(self) -> tuple[int, int]:
        return (
            self.n_events_flushed + len(self.events),
            self.n_artifacts_flushed + len(self.artifacts),
        )
