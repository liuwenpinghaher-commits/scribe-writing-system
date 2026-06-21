"""前端兼容层:旧 web-app 用 ~50 端点,scribe2 已实现核心写作流(works/chapters/prose/
北极星/角色/伏笔/设定/生成/critique/check/memory/search)。这里给尚未在新底座落地的
外围面板端点(insights/option-sets/threads/materials/agent-* 等)加**优雅桩**,
使前端切到 scribe2(设 VITE_API)后不 404、核心写作可用、外围面板优雅留空。

注:这些是桩,非真实实现;外围功能的真正移植是后续工程(非"写作层移植"范畴)。
volumes 走真实 domain。
"""
from __future__ import annotations

from fastapi import Header
from pydantic import BaseModel


class VolumeIn(BaseModel):  # 模块级:否则 FastAPI 解析不到注解,会把 body 当 query 参数
    seq: int
    title: str = ""


def register(app, get_domain, owner, Depends, Domain):
    """把兼容桩端点注册到 app。核心端点已在 app.py 真实实现,这里只补外围。"""

    def _own(x):
        return owner(x)

    # ---- volumes(真实) ----
    @app.get("/works/{w}/volumes")
    def list_volumes(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
        _own(x_owner_id)
        return d.s.list("volume", "work = $w", {"w": f"work:{w}"})

    @app.post("/works/{w}/volumes")
    def create_volume(w: str, b: VolumeIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
        _own(x_owner_id)
        return {"volume_id": d.create_volume(w, b.seq, b.title)}

    # ---- 外围 GET 列表 → 空(优雅留空,前端面板不报错)----
    EMPTY_LIST = [
        "insights", "option-sets", "threads", "materials", "imaginations",
        "relations", "timeline", "agent-memory", "agent-skills", "pending-writes",
    ]
    for _name in EMPTY_LIST:
        def _mk(n):
            @app.get(f"/works/{{w}}/{n}")
            def _stub(w: str, x_owner_id: str | None = Header(None)):
                _own(x_owner_id)
                return []
            return _stub
        _mk(_name)

    # ---- 外围 GET 对象 → 合理默认 ----
    @app.get("/works/{w}/cost")
    def cost(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"calls": 0, "tokens": 0, "cost_usd": 0}

    @app.get("/works/{w}/quality")
    def quality(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {}

    @app.get("/works/{w}/quality/history")
    def quality_history(w: str, scope: str = "", x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return []

    @app.get("/works/{w}/chapters/{c}/branches")
    def branches(w: str, c: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return []

    @app.get("/works/{w}/chapters/{c}/segments")
    def segments(w: str, c: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return []

    @app.get("/works/{w}/chapters/{c}/task")
    def task(w: str, c: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {}

    # ---- 外围 POST → ok/合理默认(暂不落实际逻辑)----
    @app.post("/works/{w}/proactive-review")
    def proactive_review(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"new_insights": 0}

    @app.post("/works/{w}/analyze")
    def analyze(w: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"ok": True}

    @app.post("/works/{w}/chapters/{c}/deep-check")
    def deep_check(w: str, c: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"new_flags": 0}

    @app.post("/works/{w}/chapters/{c}/intent-check")
    def intent_check(w: str, c: str, x_owner_id: str | None = Header(None)):
        _own(x_owner_id)
        return {"verdict": "aligned", "deviations": []}
