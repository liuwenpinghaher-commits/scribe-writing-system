"""锚定核心人物身份血缘(角色档案=逐章verbatim注入,防全局压缩漂移)+ 设权威全局
+ 复位 ch29(删错误'阿荞'快照/章记忆,从done_seqs移除)。之后重启后端(载新rollup)+
驱动重生成 ch29-32。
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database

WID = "eac58155-1ef2-4cc0-9aea-ac65a1f87c94"
STATE = Path(__file__).resolve().parent / ".novel_state.json"

# 铁律人物锚(写进 motivation,_writing_context 每章原样注入,LLM 压缩动不了)
ANCHORS = {
    "渡叔": "守渡四十年的独眼老摆渡人。四十年前破三不渡、捞渡了诈死避祸的梅班头牌【苏清湄】,"
            "引乱兵屠渡、瞎其左眼、害死老摆渡师父,苏清湄终自沉浊河;他悔恨守长明灯赎罪,"
            "把苏清湄的魂扣在河上整整四十年。临终要亲自渡苏清湄归南、把渡业传给苏家骨血阿砚。"
            "他不是苏家人,是失了苏清湄的局外人。",
    "阿砚": "本名苏砚,梅班头牌【苏清湄】的孙辈——苏清湄四十年前投河前藏在船缝的婴儿是阿砚的父亲,"
            "经南岸裱画匠陈墨亭收养教养、长大成人后才生下阿砚;阿砚如今十五六岁。裱画学徒,师父陈墨亭"
            "死于兵祸,携半幅《船渡图》逃到九原渡被渡叔收徒,天生能接声,继承渡业。绝不是苏清湄的儿子。",
    "小满": "柳娘的哑女,七八岁,生来落地即溺、被救活的'半魂',能看见河里的亡魂。依恋柳娘;"
            "柳娘为救难民投河后,她第一次开口嘶哑喊出'娘'。她不是四十年前屠渡的亡女。",
    "柳娘": "梅班青衣,带哑女小满逃难,以唱戏换渡钱。为引开追杀难民的乱兵,纵身投河自尽,"
            "阿砚为她破了'自寻短见者不渡'的三不渡、渡她过南岸。",
    "陈墨亭": "阿砚的裱画师父(南岸裱画匠),收养教养了苏清湄之子(即阿砚之父),持有苏家半幅《船渡图》,"
              "死于兵祸前把半图交给阿砚、嘱其'送到南边姓渡的人手里'(即渡叔)。他不是梅班小幺。",
}

# 权威全局(至ch28,精确身份血缘,供 ch29 重生成注入)
CORRECT_GLOBAL = (
    "裱画学徒少年阿砚(本名苏砚)师父陈墨亭死于兵祸,携半幅《船渡图》与未托完的《寒江钓雪》逃到浊河北岸"
    "九原渡,被独眼老摆渡人渡叔收为徒。渡叔守渡四十年,以原字号船渡活人也渡枉死亡魂,立'负心/欠债/自寻短见者"
    "不渡'的三不渡,夜夜在渡名册为无名死者记名;阿砚天生能接声,与卖唱青衣柳娘、能见亡魂的半魂哑女小满相依。"
    "溃军秦把总占渡口设卡勒索、草菅人命。四十年前渡叔曾破三不渡渡起诈死避祸的梅班头牌【苏清湄】,引乱兵屠渡、"
    "瞎其左眼、害死老师父,苏清湄终自沉,渡叔守灯赎罪、把她的魂扣在河上至今。半图合璧,渡叔认下阿砚是【苏清湄"
    "的孙辈】(苏清湄藏的婴儿=阿砚之父,经陈墨亭收养教养才有阿砚),苏家仅存这一线血脉。战事逼近,渡叔屠渡中"
    "中箭垂危;柳娘为救难民投河,阿砚破三不渡渡她,小满悲恸中第一次喊'娘';渡叔弥留,将渡业、名册、渡牌、"
    "合璧船渡图托付阿砚。"
)


def main():
    db = Database("scribe.db")
    # 1. 角色锚
    for name, mot in ANCHORS.items():
        db.upsert_character(WID, name, motivation=mot)
    # 2. 权威全局
    db.upsert_memory(WID, "global", CORRECT_GLOBAL, source_chapter_range="1-28")
    # 3. 复位 ch29
    ch29 = db.get_chapter(WID, 29)
    if ch29:
        cid = ch29["id"]
        db.conn.execute("DELETE FROM snapshots WHERE chapter_id=?", (cid,))
        db.conn.execute("DELETE FROM segments WHERE chapter_id=?", (cid,))
        db.conn.execute("DELETE FROM memory_entries WHERE work_id=? AND scope='chapter:29'", (WID,))
    db.conn.commit()
    st = json.loads(STATE.read_text(encoding="utf-8"))
    st["done_seqs"] = [s for s in st["done_seqs"] if s != 29]
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"锚定角色 {len(ANCHORS)} 个;权威全局已写;ch29已复位;done_seqs尾 {sorted(st['done_seqs'])[-4:]}")


if __name__ == "__main__":
    main()
