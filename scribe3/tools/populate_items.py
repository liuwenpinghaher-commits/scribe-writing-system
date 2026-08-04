#!/usr/bin/env python3
"""灌入物品/术语/角色标签到运行DB"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.store import SurrealStore

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')

# 物品
existing = st.list_items()
if not existing:
    items = [
        ('灵龙镇煞钉','法器','铜钉色成赤黑,圆头方身。钉身镶镇煞灵龙,钉帽刻井字铭文。七七四十九天炼成,辟邪圣物。','role:胡不为','active',['辟邪圣物','镇魂锁煞']),
        ('大元炼真经','典籍','胡不为家藏古籍,记载灵龙镇煞钉熔造法等。','role:胡不为','active',['记载法器炼造之法']),
        ('天周盘','法器','严台山探测妖物方位的法器。','role:蔺得岷','active',['探测妖物']),
        ('竹笛','法器','青叶门弟子赵姑娘所吹,清脆如玉落银盘。','role:赵姑娘','active',['青叶门信物']),
        ('定神符','符咒','符水饮后清气由百会穴贯入,眼目清明。',None,'active',['提神醒脑']),
    ]
    for name,cat,desc,owner,state,props in items:
        st.add_item(name, category=cat, description=desc, current_owner=owner, symbolic_state=state, special_properties=props)
    print(f"物品: {len(items)}件", flush=True)

# 术语
existing = st.list_terms()
if not existing:
    terms = [
        ('寒妇','妖物','棺中所镇厉鬼,会吃人。乌家世代镇守。',['厉鬼']),
        ('罗天九头鬼','妖物','蛇身人首,九颗头颅,食人精血吸收魂魄。',['九头鬼']),
        ('犯查','妖兽','天地生养独个儿修炼成形,体内有还丹。修炼四百年。',['小乖','犯查兽']),
        ('还丹','修炼产物','妖兽体内修炼而成,夺取则死。',['内丹']),
        ('画井为狱','道家术法','井字铭文用于镇魂锁煞。',['镇煞']),
        ('九朵莲花开','门派切口','严台山门派暗号上半句。',['三香供严台']),
    ]
    for name,cat,defn,aliases in terms:
        st.add_term(name, category=cat, definition=defn, aliases=aliases)
    print(f"术语: {len(terms)}条", flush=True)

# 补角色标签
chars = st.characters()
n = 0
for c in chars:
    pt = c.traits.get('personality_tags') if c.traits else None
    if not pt:
        local = (c.id or '').split(':')[-1] if ':' in (c.id or '') else (c.id or '')
        if local:
            st._db.query("UPDATE type::thing('character', $l) SET personality_tags=$pt",
                        {"l": local, "pt": ["待补全"]})
            n += 1
print(f"补标签: {n}个角色", flush=True)

comp = st.setting_completeness()
print(f"完整度: {comp['completeness_score']}/100", flush=True)
print(f"物品: {len(st.list_items())}件, 术语: {len(st.list_terms())}条", flush=True)
st.close()
