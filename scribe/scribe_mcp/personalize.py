"""个性化数据管道(内核2 → LoRA 第三档)。

把"作者已认可的稿件 + 偏好 + 文风范本"导出为指令微调训练集(SFT 格式)。
- export_training_data():纯读 SQLite,**无需 GPU,可离线运行与验证**。
- 实际 LoRA 训练执行需 GPU + 开源模型权重(见 tools/lora_finetune.py),火山闭源 API 无法做。
正例来源:human-locked / created_by='human' 的 snapshot(作者认可的正文)+ style_exemplars。
"""
from __future__ import annotations

import json

from .db import Database


def _ctx(db: Database, work_id: str, chapter_id: str) -> str:
    intent = db.get_author_intent(work_id) or {}
    parts = []
    if intent.get("reader_feeling"):
        parts.append(f"北极星(读者感受):{intent['reader_feeling']}")
    if intent.get("central_promise"):
        parts.append(f"核心承诺:{intent['central_promise']}")
    ch = db.conn.execute("SELECT outline,title FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if ch:
        if ch["title"]:
            parts.append(f"章节:{ch['title']}")
        try:
            o = json.loads(ch["outline"] or "{}")
            if o:
                parts.append("大纲:" + json.dumps(o, ensure_ascii=False))
        except Exception:
            pass
    return "\n".join(parts)


def export_training_data(db: Database, owner_id: str) -> list[dict]:
    """返回 SFT 样本列表 [{instruction, input, output, _source}]。"""
    samples: list[dict] = []
    for w in db.list_works(owner_id):
        wid = w["id"]
        # 正例:作者认可的正文(human-locked 或 human 写的)
        rows = db.conn.execute(
            "SELECT s.content, s.chapter_id FROM snapshots s "
            "WHERE s.work_id=? AND (s.is_human_locked=1 OR s.created_by='human') AND length(s.content)>40",
            (wid,),
        ).fetchall()
        for r in rows:
            samples.append({
                "instruction": f"你是作者本人的写作助手。严格贴合其文风,根据以下设定与大纲,写出这一章/这一段正文。",
                "input": _ctx(db, wid, r["chapter_id"]),
                "output": r["content"],
                "_source": "approved_snapshot",
            })
    # 文风范本:owner 级,跨书一次(不在 per-work 循环内,避免重复)
    for ex in db.conn.execute(
        "SELECT label, sample_text FROM style_exemplars WHERE owner_id=? AND length(sample_text)>40",
        (owner_id,),
    ).fetchall():
        samples.append({
            "instruction": "以下是作者偏爱的文风范本。请学习并以同样的语感、节奏、克制度写作。",
            "input": f"范本标签:{ex['label'] or ''}",
            "output": ex["sample_text"],
            "_source": "style_exemplar",
        })
    return samples


def export_jsonl(db: Database, owner_id: str, path: str) -> int:
    """导出为 JSONL(每行一个 SFT 样本),返回条数。"""
    data = export_training_data(db, owner_id)
    with open(path, "w", encoding="utf-8") as f:
        for s in data:
            f.write(json.dumps({k: v for k, v in s.items() if not k.startswith("_")},
                               ensure_ascii=False) + "\n")
    return len(data)
