"""前端兼容层:给尚未在 scribe2 真实实现的端点加优雅桩,使前端切到 scribe2 不 404。
随各 Wave 推进逐步移除。当前剩:质量/成本/任务态/待批写 + Wave C 的 LLM 端点
(proactive-review/analyze/deep-check/intent-check/option-gen/material process|distill)。
"""
from __future__ import annotations

from fastapi import Header


def register(app, get_domain, owner, Depends, Domain):
    def _own(x):
        return owner(x)

    # ---- 质量/成本/任务态(Wave C 真实化前的桩)----
    @app.get("/works/{w}/quality")
    def quality(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {}

    @app.get("/works/{w}/quality/history")
    def quality_history(w: str, scope: str = "", x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return []

    @app.get("/works/{w}/cost")
    def cost(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"calls": 0, "tokens": 0, "cost_usd": 0}

    @app.get("/works/{w}/chapters/{seq}/task")
    def task(w: str, seq: int, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {}

    @app.post("/works/{w}/chapters/{seq}/task/advance")
    def task_advance(w: str, seq: int, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {}

    # ---- 待批写(B3,Wave C 真实化)----
    @app.get("/works/{w}/pending-writes")
    def pending_writes(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return []

    @app.post("/works/{w}/pending-writes/{pid}/approve")
    def approve_pending(w: str, pid: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"status": "approved"}

    @app.post("/works/{w}/pending-writes/{pid}/reject")
    def reject_pending(w: str, pid: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"status": "rejected"}

    # ---- Wave C LLM 端点(真实化前桩)----
    @app.post("/works/{w}/proactive-review")
    def proactive_review(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"new_insights": 0}

    @app.post("/works/{w}/analyze")
    def analyze(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"analyzed": True, "relations": 0, "events": 0, "states": 0}

    @app.post("/works/{w}/chapters/{seq}/deep-check")
    def deep_check(w: str, seq: int, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"new_flags": 0}

    @app.post("/works/{w}/chapters/{seq}/intent-check")
    def intent_check(w: str, seq: int, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"status": "aligned", "reason": "", "red_lines": []}

    @app.post("/works/{w}/option-sets/generate")
    def gen_options(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"option_set_id": ""}

    @app.post("/works/{w}/materials/{mid}/process")
    def process_material(w: str, mid: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"summary": "", "tags": []}

    @app.post("/works/{w}/materials/{mid}/distill")
    def distill_material(w: str, mid: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"ok": True}
