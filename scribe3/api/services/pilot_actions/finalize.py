"""Pilot action stage module (P1-16 phase split)."""
from __future__ import annotations


def build_actions(work: str) -> dict:
    """Bind pilot_runtime free vars and return this stage's action callables."""
    from scribe3.api.services import pilot_runtime as pr
    g = globals()
    for name in dir(pr):
        if name.startswith("__"):
            continue
        g[name] = getattr(pr, name)
    import json, os, logging  # noqa: F401 — used by stage bodies

    def finalize(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        # rev.1.2：写 kind=final 前强制 craft hard + 质控；stamp 单源 try_stamp_kind_final
        try:
            from scribe3.finalize_gate import check_persist_gates, try_stamp_kind_final
            foc = (ch.get("focalizer") or ch.get("pov") or "") or None
            _pg = check_persist_gates(
                st, int(seq), prose or "",
                focalizer=foc, danger_draft=False,
            )
            if not _pg.get("allowed"):
                return {
                    "finalized": False,
                    "error": _pg.get("code") or "persist_gate",
                    "detail": _pg.get("detail") or "",
                    "blocking": list(_pg.get("blocking") or []),
                    "gate": _pg,
                }
            _stamp = try_stamp_kind_final(
                st, int(seq), prose or "",
                label="pilot终选", stage="final", stats=_prose_stats(prose),
            )
            if not _stamp.get("allowed") or (
                not _stamp.get("stamped") and _stamp.get("code") == "craft_finalize"
            ):
                return {
                    "finalized": False,
                    "error": _stamp.get("code") or "craft_finalize",
                    "detail": _stamp.get("detail") or "",
                    "blocking": list(_stamp.get("blocking") or []),
                    "final_stamp": _stamp,
                }
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "pilot finalize persist gates 失败(阻断) seq=%s: %s", seq, e,
            )
            return {
                "finalized": False,
                "error": "persist_gate_error",
                "detail": str(e)[:200],
                "blocking": [],
            }
        # v6.1 §5.2：定稿后强制全类型 PostFinalize（持久化候选；不自动 apply L1）
        post_finalize = None
        try:
            from scribe3.api.services.canon_hooks import body_confirmed_report
            complete_fn = None
            try:
                from scribe3.llm import hermes_complete
                complete_fn = lambda p: hermes_complete(
                    p, timeout=90.0, max_tokens=2000, retries_override=0)
            except Exception:
                complete_fn = None
            post_finalize = body_confirmed_report(
                work=work, seq=seq, prose=prose, st=st,
                complete_fn=complete_fn, persist=True,
            )
        except Exception as e:
            logging.getLogger("scribe3").warning(
                "post_finalize_report failed work=%s seq=%s: %s", work, seq, e)
            post_finalize = {
                "seq": seq,
                "error": str(e)[:200],
                "silent_l1_write": False,
                "sections": {
                    "l2_objective": {"items": [], "modules": [], "auto_applied": False},
                    "l1_requires_approval": {"items": [], "modules": [], "auto_applied": False},
                },
            }
        return {
            "finalized": True,
            "post_finalize_report": post_finalize,
            "canon_loop": {
                "path": "body_confirmed",
                "silent_l1_write": False,
                "next": "POST /canon/change-pack/apply with approved_item_ids for L1 items",
            },
        }


    return {"finalize": finalize}
