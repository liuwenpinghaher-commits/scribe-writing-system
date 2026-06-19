"""品味与偏好模型(内核2)· 跨书共享(00 §2.7)。

owner 级信号(work_id=NULL)跨所有书共享(=你的文风品味底色);
book 级信号(work_id=具体书)只作用于该书。
get_effective_signals(owner, work_id) = owner 级 + 该书级(防串味:不含其它书的信号)。
纯 stdlib,可离线单测。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TasteStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record_signal(self, owner_id: str, source: str, polarity: str = "+",
                      weight: float = 1.0, signal: dict | None = None,
                      work_id: str | None = None) -> str:
        """记录偏好信号。work_id=None → owner 级跨书;否则按书。"""
        sid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO preference_signals(id,owner_id,work_id,source,signal,polarity,weight,"
            "created_at) VALUES(?,?,?,?,?,?,?,?)",
            (sid, owner_id, work_id, source,
             json.dumps(signal or {}, ensure_ascii=False), polarity, weight, _now()),
        )
        self.conn.commit()
        return sid

    def get_effective_signals(self, owner_id: str, work_id: str) -> list[dict]:
        """该书生成时生效的偏好 = owner 级(跨书) + 本书级。绝不含其它书的信号(防串味)。"""
        rows = self.conn.execute(
            "SELECT * FROM preference_signals WHERE owner_id=? AND (work_id IS NULL OR work_id=?) "
            "ORDER BY created_at",
            (owner_id, work_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def aggregate(self, owner_id: str, work_id: str) -> dict:
        """把生效信号聚合成一个简易品味画像:净倾向分(按来源汇总加权 polarity)。"""
        score: dict[str, float] = {}
        for s in self.get_effective_signals(owner_id, work_id):
            sign = 1.0 if s["polarity"] == "+" else -1.0
            score[s["source"]] = score.get(s["source"], 0.0) + sign * (s["weight"] or 1.0)
        return score

    # ---- C1-1 TasteModel 真学习:从信号提取结构化偏好(时间衰减),落 taste_models ----
    @staticmethod
    def _keywords(text: str) -> list[str]:
        """从一句中文意见/方案里抽取偏好短语(粗分词:按标点切,留 2–12 字片段)。"""
        import re
        parts = re.split(r"[，,。；;、\s]+", text or "")
        return [p.strip() for p in parts if 2 <= len(p.strip()) <= 12]

    def build_taste_model(self, owner_id: str, work_id: str | None) -> dict:
        """聚合生效信号 → learned_preferences(正向偏好分布)+ negative_list(负向),
        近期信号权重更高(指数衰减)。写入/更新 taste_models。返回该模型。"""
        sigs = self.get_effective_signals(owner_id, work_id or "")
        prefs: dict[str, float] = {}
        negs: dict[str, float] = {}
        n = len(sigs)
        for i, s in enumerate(sigs):  # 越靠后(新)权重越高
            decay = 0.92 ** (n - 1 - i)
            w = (s["weight"] or 1.0) * decay
            pos = s["polarity"] != "-"
            try:
                payload = json.loads(s["signal"] or "{}")
            except Exception:
                payload = {}
            text = payload.get("text") or payload.get("instruction") or payload.get("approach") or ""
            bucket = prefs if pos else negs
            for kw in self._keywords(text):
                bucket[kw] = bucket.get(kw, 0.0) + w
            # 来源本身也是弱信号(如 intentional=对"看似偏离"宽容)
            if s["source"] == "intentional" and pos:
                prefs["容忍看似偏离的写法"] = prefs.get("容忍看似偏离的写法", 0.0) + w * 0.5
        top = lambda d: [k for k, _ in sorted(d.items(), key=lambda x: -x[1])[:12]]  # noqa: E731
        learned = {"prefers": top(prefs), "avoids": top(negs)}
        confidence = round(min(1.0, n / 20.0), 2)
        mid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO taste_models(id,owner_id,work_id,positive_exemplars,negative_list,"
            "learned_preferences,version,updated_at) VALUES(?,?,?,?,?,?,1,?)"
            " ON CONFLICT(owner_id,work_id) DO UPDATE SET learned_preferences=excluded.learned_preferences,"
            " negative_list=excluded.negative_list, version=taste_models.version+1, updated_at=excluded.updated_at",
            (mid, owner_id, work_id, json.dumps([]),
             json.dumps(learned["avoids"], ensure_ascii=False),
             json.dumps(learned, ensure_ascii=False), _now()),
        )
        self.conn.commit()
        return {"learned_preferences": learned, "confidence": confidence, "signal_count": n}

    def get_taste_model(self, owner_id: str, work_id: str | None) -> dict:
        """取该书生效品味:owner 级底色 + 本书级(本书覆盖)。无则实时构建。"""
        # 先确保最新(廉价:每次读时重建,信号量不大)
        self.build_taste_model(owner_id, None)
        if work_id:
            self.build_taste_model(owner_id, work_id)
        rows = self.conn.execute(
            "SELECT * FROM taste_models WHERE owner_id=? AND (work_id IS NULL OR work_id=?)",
            (owner_id, work_id or ""),
        ).fetchall()
        prefers: list[str] = []
        avoids: list[str] = []
        for r in rows:
            try:
                lp = json.loads(r["learned_preferences"] or "{}")
                prefers += lp.get("prefers", [])
                avoids += lp.get("avoids", [])
            except Exception:
                pass
        # 去重保序
        prefers = list(dict.fromkeys(prefers))[:12]
        avoids = list(dict.fromkeys(avoids))[:12]
        return {"prefers": prefers, "avoids": avoids}
