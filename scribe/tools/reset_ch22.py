"""复位 ch22:删旧快照+章记忆,写正确的全局摘要(不含'苏清湄之子'时间线错误),
从 done_seqs 移除22。之后重启驱动会用修正后的 ch22 节拍重生成,
自然 ingest 重建全局,卷三据正确身世(孙辈)续写。
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database

WID = "eac58155-1ef2-4cc0-9aea-ac65a1f87c94"
STATE = Path(__file__).resolve().parent / ".novel_state.json"

# 正确的全书主线(至 ch21,~200字,不预设母子,留身世给 ch22 正确揭示为孙辈)
CORRECT_GLOBAL = (
    "乱世末年,裱画学徒少年阿砚(本名苏砚)师傅陈墨亭死于兵祸,携半幅《船渡图》逃到浊河北岸"
    "九原渡,被独眼老摆渡人渡叔收留为徒。渡叔守渡四十年,以原字号船渡活人也渡枉死亡魂,立"
    "'负心/欠债/自寻短见者不渡'的三不渡,夜夜在渡名册上为无名死者记名;阿砚天生能接声,渐通"
    "渡亡之业,与卖唱青衣柳娘、能见亡魂的哑女小满相依。溃军秦把总占渡口设卡勒索、草菅人命,"
    "渡叔以河伯旧例与河汛周旋。四十年前渡叔曾破例渡起诈死避祸的梅班头牌苏清湄,引乱兵屠渡、"
    "瞎其左眼、害死老师父,苏清湄终自沉,渡叔守灯赎罪至今。阿砚贴身布衫的苏字与苏清湄旧物"
    "同源,身世渐明。战事逼近,众亡魂相助渡尽难民,渡叔力竭重伤垂危,把渡口托付阿砚。"
)


def main():
    db = Database("scribe.db")
    ch22 = db.get_chapter(WID, 22)
    assert ch22, "ch22 不存在"
    cid = ch22["id"]
    # 1. 删 ch22 旧快照(重生成会写新的;latest-wins,旧的清掉更干净)
    n_snap = db.conn.execute("DELETE FROM snapshots WHERE chapter_id=?", (cid,)).rowcount
    db.conn.execute("DELETE FROM segments WHERE chapter_id=?", (cid,))
    # 2. 删 ch22 章记忆(含错误'苏清湄之子')
    n_mem = db.conn.execute(
        "DELETE FROM memory_entries WHERE work_id=? AND scope='chapter:22'", (WID,)).rowcount
    # 3. 写正确全局(供 ch22 重生成时注入,不含时间线错误)
    db.upsert_memory(WID, "global", CORRECT_GLOBAL, source_chapter_range="1-21")
    db.conn.commit()
    # 4. 从 done_seqs 移除 22
    st = json.loads(STATE.read_text(encoding="utf-8"))
    st["done_seqs"] = [s for s in st["done_seqs"] if s != 22]
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"删ch22快照 {n_snap} 条、章记忆 {n_mem} 条;全局已改正;done_seqs去22 -> {sorted(st['done_seqs'])[-5:]}")


if __name__ == "__main__":
    main()
