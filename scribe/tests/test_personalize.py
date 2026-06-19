"""个性化训练集导出自检(LoRA 数据管道,无需 GPU)。"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.personalize import export_training_data, export_jsonl  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    w = db.create_work("u1", "书")
    db.set_author_intent(w, reader_feeling="结尾脊背发凉")
    cid = db.save_chapter(w, 1, "第一章", outline={"events": ["雨夜对峙"]})
    # 一个 AI 草稿(不应入训练集)+ 一个作者认可版(human-locked,应入)。两者均 >40 字,
    # 确保"排除 AI 稿"是因 created_by 而非长度。
    db.save_snapshot(w, cid, "AI的草稿正文," + "平淡而冗长的句子反复铺陈着雨夜的场景描写细节" * 2, created_by="ai")
    sid = db.save_snapshot(w, cid, "作者亲自定稿的正文:雨砸在窗上,他没有回头,只把领子竖起走进了那片浓得化不开的黑里去了。", created_by="human")
    db.lock_snapshot(sid)
    return db, w


def test_export_only_approved():
    db, w = _setup()
    data = export_training_data(db, "u1")
    outs = [s["output"] for s in data]
    assert any("作者亲自定稿" in o for o in outs), "作者认可正文应入训练集"
    assert all("AI 的草稿" not in o for o in outs), "AI 草稿不应进入训练集"
    # context 含北极星
    appr = [s for s in data if s["_source"] == "approved_snapshot"][0]
    assert "脊背发凉" in appr["input"]


def test_jsonl_and_style_exemplar():
    db, w = _setup()
    db.conn.execute(
        "INSERT INTO style_exemplars(id,owner_id,work_id,label,sample_text,scope) "
        "VALUES('e1','u1',?, '冷硬', '短句。克制。留白。他不解释,也不回头。雨把街灯泡成一团团昏黄,他走得很慢,像在数自己还剩多少步。','work')", (w,))
    db.conn.commit()
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False); tmp.close()
    n = export_jsonl(db, "u1", tmp.name)
    lines = [json.loads(l) for l in Path(tmp.name).read_text(encoding="utf-8").splitlines()]
    assert n == len(lines) and n >= 2
    assert all({"instruction", "input", "output"} <= set(x) for x in lines)
    assert any("文风范本" in x["instruction"] for x in lines)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
