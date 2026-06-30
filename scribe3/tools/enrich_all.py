#!/usr/bin/env python3
"""主编对话方式补全《纸命》所有设定字段。

用与 UI 素材讨论完全相同的主编(hermes_complete_stream + _editor_system 联书 codex)
逐条目生成全字段 JSON,再经 store.update_record 可靠落库。
内容 100% 主编生成(联全书+已写4章);因表单控件批量交互不稳,落库走稳的 store 路。
用法: python -m scribe3.tools.enrich_all [类名]  (不带参=全部)
"""
import json
import re
import sys

from scribe3.store import SurrealStore
from scribe3.app import _editor_system
from scribe3.llm import hermes_complete_stream

DB = "book_c256380e"


def ask_chief(st, prompt: str) -> dict | None:
    """调主编(联书 codex)拿一个 JSON 对象。"""
    sysmsg = _editor_system(st)
    reply = "".join(hermes_complete_stream(prompt, system=sysmsg))
    m = re.search(r"\{[\s\S]*\}", reply)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        # 容错:去掉可能的尾随逗号
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
        except Exception:
            return None


def s(v):
    return None if v is None else (str(v).strip() or None)


def arr(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r"[、,，;；]", str(v)) if x.strip()]


def num(v):
    try:
        return int(re.search(r"\d+", str(v)).group(0))
    except Exception:
        return None


def enrich_characters(st):
    IMP = {"主角": "protagonist", "重要": "major", "次要": "minor", "背景": "background",
           "protagonist": "protagonist", "major": "major", "minor": "minor", "background": "background"}
    for c in st.characters():
        name = c.name
        p = (f"基于《纸命》全书与已写4章正文,为角色「{name}」补全完整人物卡。只输出一个JSON对象,键:"
             "外貌,性格深描,性格标签(数组),前史,能力(数组,每项{名称,等级,描述}),弱点(数组),"
             "表面目标,深层需求,内在冲突,恐惧,重要度(主角/重要/次要/背景之一),首次出场(1-4章号数字)。"
             "值须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  角色 {name}: 主编未给JSON,跳过"); continue
        abilities = []
        for a in (d.get("能力") or []):
            if isinstance(a, dict) and (a.get("名称") or a.get("name")):
                abilities.append({"name": a.get("名称") or a.get("name"),
                                  "level": a.get("等级") or a.get("level") or "",
                                  "description": a.get("描述") or a.get("description") or ""})
        fields = {
            "appearance": s(d.get("外貌")),
            "personality_detail": s(d.get("性格深描")),
            "personality_tags": arr(d.get("性格标签")),
            "backstory": s(d.get("前史")) or c.traits.get("backstory"),
            "abilities": json.dumps(abilities, ensure_ascii=False) if abilities else None,
            "weaknesses": arr(d.get("弱点")),
            "surface_goal": s(d.get("表面目标")),
            "deep_need": s(d.get("深层需求")),
            "internal_conflict": s(d.get("内在冲突")),
            "fear": s(d.get("恐惧")),
            "importance": IMP.get(str(d.get("重要度", "")).strip()),
            "first_appearance": num(d.get("首次出场")),
        }
        fields = {k: v for k, v in fields.items() if v not in (None, [], "")}
        st.update_record(f"role:{name}", fields)
        print(f"  角色 {name}: 写入 {list(fields)}")


def enrich_factions(st):
    for f in st.list_factions():
        name = f.get("name")
        p = (f"基于《纸命》全书与已写4章,为势力「{name}」补全。只输出JSON,键:"
             "意识形态,公开面目,私下运作,领袖,已知成员(数组)。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  势力 {name}: 跳过"); continue
        st.add_faction(name, ideology=s(d.get("意识形态")), public_face=s(d.get("公开面目")),
                       private_operation=s(d.get("私下运作")), leader=s(d.get("领袖")),
                       known_members=arr(d.get("已知成员")),
                       private_operation_secret=bool(f.get("private_operation_secret")))
        print(f"  势力 {name}: ✓")


def enrich_items(st):
    for it in st.list_items():
        name = it.get("name")
        p = (f"基于《纸命》全书与已写4章,为物件「{name}」补全。只输出JSON,键:"
             "类别,描述,持有者,特殊属性(数组),首次出场章(数字)。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  物件 {name}: 跳过"); continue
        st.add_item(name, category=s(d.get("类别")), description=s(d.get("描述")),
                    current_owner=s(d.get("持有者")), special_properties=arr(d.get("特殊属性")),
                    first_chapter=num(d.get("首次出场章")))
        print(f"  物件 {name}: ✓")


def enrich_terms(st):
    for t in st.list_terms():
        name = t.get("name")
        p = (f"基于《纸命》全书与已写4章,为术语「{name}」补全。只输出JSON,键:"
             "类别,定义,首次提及章(数字)。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  术语 {name}: 跳过"); continue
        st.add_term(name, category=s(d.get("类别")), definition=s(d.get("定义")),
                    first_mention_chapter=num(d.get("首次提及章")))
        print(f"  术语 {name}: ✓")


def enrich_rules(st):
    for r in st.list_world_rules():
        name = r.get("name")
        p = (f"基于《纸命》全书与已写4章,为世界规则「{name}」补全。只输出JSON,键:"
             "源头,代价,限制条件(数组),例外情形(数组),赋予能力(数组),备注。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  规则 {name}: 跳过"); continue
        st.add_world_rule(name, category=r.get("category") or "magic", source=s(d.get("源头")),
                          cost=s(d.get("代价")), limitations=arr(d.get("限制条件")),
                          exceptions=arr(d.get("例外情形")), capabilities=arr(d.get("赋予能力")),
                          note=s(d.get("备注")))
        print(f"  规则 {name}: ✓")


def enrich_motifs(st):
    for mo in st.list_motifs():
        name = mo.get("name")
        p = (f"基于《纸命》全书与已写4章,为母题「{name}」补全。只输出JSON,键:"
             "绑定主题,隐喻展开,物质回声。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  母题 {name}: 跳过"); continue
        fields = {"theme": s(d.get("绑定主题")), "unfolding": s(d.get("隐喻展开")),
                  "echoes": s(d.get("物质回声"))}
        fields = {k: v for k, v in fields.items() if v not in (None, [], "")}
        if fields:
            st.update_motif(str(mo.get("id")).split(":")[-1], fields)
        print(f"  母题 {name}: ✓ {list(fields)}")


def enrich_promises(st):
    for pr in st.list_promises():
        text = pr.get("text", "")[:24]
        p = (f"基于《纸命》全书与已写4章,为伏笔「{text}…」补全。只输出JSON,键:"
             "线索(数组,埋设这条伏笔的具体线索/物象)。须与正文一致、简洁。不要JSON以外的字。")
        d = ask_chief(st, p)
        if not d:
            print(f"  伏笔 {text}: 跳过"); continue
        clues = arr(d.get("线索"))
        if clues:
            st._update_by("promise", str(pr.get("id")).split(":")[-1], {"clues": clues})
        print(f"  伏笔 {text}: ✓ ({len(clues)}条线索)")


CATS = {"角色": enrich_characters, "势力": enrich_factions, "物件": enrich_items,
        "术语": enrich_terms, "世界规则": enrich_rules, "母题": enrich_motifs, "伏笔": enrich_promises}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    st = SurrealStore(ns="scribe3", db=DB)
    for cat, fn in CATS.items():
        if only and cat != only:
            continue
        print(f"=== {cat} ===")
        fn(st)
    st.close()
    print("完成")


if __name__ == "__main__":
    main()
