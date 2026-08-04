#!/usr/bin/env python3
"""阶段2：推演台设计——10章事件链+知识帧+伏笔+弧光。
基于阶段1的设定数据,设计与原文对标的10章fabula。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.store import SurrealStore
from scribe3.ontology import Event, Fact, KnowledgeEdge

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')

# 清理旧章节和事件(保留设定)
st._db.query("DELETE chapter")
st._db.query("DELETE event")
st._db.query("DELETE knows WHERE ingest_seq IS NONE")
st._db.query("DELETE promise")
st._db.query("DELETE char_state")
print("旧推演数据已清理", flush=True)

# ═══ 10章事件设计(对齐原文引子~第五章+原创5章) ═══
chapters_design = [
    # ── 第1章: 引子·贺客(对齐原文引子) ──
    dict(seq=1, title='引子·贺客', focalizer='role:时闻盂',
         events=[
             dict(id='ev:c1e1', etype='婚宴', chapter=1,
                  participants={'WITNESS':'role:时闻盂'},
                  location='place:三水村', goal='韩之敬大婚,时闻盂醉酒'),
             dict(id='ev:c1e2', etype='奇遇', chapter=1,
                  participants={'SUBJ':'role:时闻盂'},
                  effects=['fact:f001'],
                  location='place:三水村', goal='牛泪水染眼,时闻盂获阴阳眼'),
         ],
         knowledge=[
             ('role:时闻盂','fact:f001','saw',1),  # 时闻盂知道自己的能力
         ],
         promises=[
             dict(text='时闻盂开了阴阳眼后再也返不回从前', setup_chapter=1, kind='promise'),
         ],
         arcs=[
             dict(cid='role:时闻盂', ch=1, ct='ability', summary='获阴阳眼',
                  trigger='牛泪水意外染眼', arc_phase='引子·奇遇'),
         ]),

    # ── 第2章: 怪墓·玄机(对齐原文第一章) ──
    dict(seq=2, title='怪墓·玄机', focalizer='role:胡不为',
         events=[
             dict(id='ev:c2e1', etype='访村', chapter=2,
                  participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},
                  location='place:梧桐村', goal='胡不为被请来看风水'),
             dict(id='ev:c2e2', etype='发现', chapter=2,
                  participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},
                  effects=['fact:f002'],
                  location='place:墓室', goal='入奈何谷发现三百六十枚灵龙镇煞钉'),
             dict(id='ev:c2e3', etype='取物', chapter=2,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:墓室', goal='胡不为拾取跳出的镇煞钉'),
             dict(id='ev:c2e4', etype='法事', chapter=2,
                  participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},
                  location='place:梧桐村', goal='胡不为开坛做法假装降妖'),
         ],
         knowledge=[
             ('role:胡不为','fact:f004','told',2),  # 胡不为知道自己身份
             ('role:胡不为','fact:f005','told',2),  # 胡不为知道家藏炼真经
             ('role:胡不为','fact:f002','saw',2),    # 胡不为看到墓室
             ('role:老乌头','fact:f006','told',2),  # 老乌头知道自己是守墓人
             ('role:老乌头','fact:f007','told',2),  # 老乌头知道使命
             ('role:老乌头','fact:f008','told',2),  # 老乌头知道奈何谷
         ],
         promises=[
             dict(text='胡不为拾取镇煞钉,封印有缺口,寒妇随时可能脱困', setup_chapter=2, kind='promise'),
             dict(text='胡不为说三五五十内必有人来除害', setup_chapter=2, kind='promise'),
         ],
         arcs=[
             dict(cid='role:胡不为', ch=2, ct='ability', summary='获灵龙镇煞钉',
                  trigger='从墓室拾取钉子', arc_phase='引子·得物'),
             dict(cid='role:胡不为', ch=2, ct='personality', summary='恐惧与贪婪',
                  trigger='发现墓室诡异后仓皇逃离', arc_phase='引子·抉择'),
             dict(cid='role:老乌头', ch=2, ct='personality', summary='希望与狂喜',
                  trigger='终于请到风水师', arc_phase='希望'),
         ]),

    # ── 第3章: 遇险·山命(对齐原文第二章) ──
    dict(seq=3, title='遇险·山命', focalizer='role:胡不为',
         events=[
             dict(id='ev:c3e1', etype='逃离', chapter=3,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:梧桐村', goal='胡不为骑驴逃离梧桐村'),
             dict(id='ev:c3e2', etype='遭遇', chapter=3,
                  participants={'SUBJ':'role:胡不为','WITNESS':'role:蔺得岷'},
                  location='place:定马村', goal='夜林中遇严台山众人捉犯查'),
             dict(id='ev:c3e3', etype='对峙', chapter=3,
                  participants={'SUBJ':'role:蔺得岷','OBJ':'role:赵芙南','WITNESS':'role:胡不为'},
                  location='place:定马村', goal='蔺得岷与赵芙南争犯查兽'),
             dict(id='ev:c3e4', etype='逃脱', chapter=3,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='地震中犯查逃走,众人追去,胡不为独自逃命'),
         ],
         knowledge=[
             ('role:胡不为','fact:f009','saw',3),  # 胡不为知道蔺得岷在追犯查
             ('role:胡不为','fact:f010','saw',3),  # 胡不为知道赵芙南是青叶门
             ('role:蔺得岷','fact:f011','told',3), # 蔺得岷知道犯查特性
         ],
         promises=[
             dict(text='邪教堂主杀彦青灭口,某邪教在暗中活动', setup_chapter=3, kind='red_herring'),
         ],
         arcs=[
             dict(cid='role:蔺得岷', ch=3, ct='relation', summary='与赵芙南对立',
                  trigger='严台山与青叶门因犯查公开对立', arc_phase='冲突'),
             dict(cid='role:赵芙南', ch=3, ct='personality', summary='初登场',
                  trigger='白衣坐于树梢竹笛吹奏', arc_phase='登场'),
         ]),

    # ── 第4章: 守护兽(对齐原文第三章) ──
    dict(seq=4, title='守护兽·井中镜', focalizer='role:胡不为',
         events=[
             dict(id='ev:c4e1', etype='借宿', chapter=4,
                  participants={'SUBJ':'role:胡不为','WITNESS':'role:于老头'},
                  location='place:下林村', goal='胡不为逃到下林村借宿'),
             dict(id='ev:c4e2', etype='异象', chapter=4,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:下林村', goal='镇煞钉在守护神兽像前发光震动'),
             dict(id='ev:c4e3', etype='交易', chapter=4,
                  participants={'SUBJ':'role:胡不为','OBJ':'role:孙甲'},
                  location='place:下林村', goal='授孙甲求子术换枣红马'),
         ],
         knowledge=[
             ('role:胡不为','fact:f013','saw',4),  # 胡不为知道守护兽像灵验
         ],
         promises=[
             dict(text='下林村守护兽像的代价——"供我养我""得佑得福"', setup_chapter=4, kind='promise'),
         ],
         arcs=[
             dict(cid='role:胡不为', ch=4, ct='personality', summary='名声渐起',
                  trigger='镇煞钉发光被村民视为仙长', arc_phase='转折·名声'),
         ]),

    # ── 第5章: 来袭·祸福(对齐原文第四章) ──
    dict(seq=5, title='来袭·祸福只在一息间', focalizer='role:胡不为',
         events=[
             dict(id='ev:c5e1', etype='袭击', chapter=5,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:下林村', goal='人面怪鸟群袭下林村'),
             dict(id='ev:c5e2', etype='守护', chapter=5,
                  participants={},
                  location='place:下林村', goal='守护兽现身击退怪鸟群'),
             dict(id='ev:c5e3', etype='激战', chapter=5,
                  participants={},
                  location='place:下林村', goal='九头鸟来袭,守护兽掷戟击退'),
             dict(id='ev:c5e4', etype='离村', chapter=5,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:下林村', goal='村人神秘死亡,胡不为仓皇逃离'),
         ],
         knowledge=[
             ('role:胡不为','fact:f014','saw',5),  # 胡不为知道村人神秘死亡
         ],
         promises=[
             dict(text='铁匠和卖油郎臂上刻字而死,守护兽的代价', setup_chapter=5, kind='promise'),
         ]),

    # ── 第6章: 妖兽·将生却死(对齐原文第五章) ──
    dict(seq=6, title='妖兽·将生却死胡不惕', focalizer='role:胡不为',
         events=[
             dict(id='ev:c6e1', etype='追猎', chapter=6,
                  participants={'SUBJ':'role:蔺得岷','OBJ':'role:赵芙南'},
                  location='place:定马村', goal='蔺得岷赵芙南追犯查两天一夜'),
             dict(id='ev:c6e2', etype='战斗', chapter=6,
                  participants={'SUBJ':'role:蔺得岷','WITNESS':'role:赵芙南'},
                  location='place:定马村', goal='蔺得岷被蛀木妖偷袭,赵芙南救援,御土术击杀'),
             dict(id='ev:c6e3', etype='击杀', chapter=6,
                  participants={'SUBJ':'role:胡不为'},
                  effects=['fact:f003'],
                  location='place:定马村', goal='灵龙镇煞钉护主击杀犯查兽'),
             dict(id='ev:c6e4', etype='赠宝', chapter=6,
                  participants={'SUBJ':'role:赵芙南','OBJ':'role:胡不为'},
                  effects=['fact:f015'],
                  location='place:定马村', goal='赵芙南吹安神曲,留书赠还丹'),
         ],
         knowledge=[
             ('role:胡不为','fact:f003','saw',6),  # 胡不为知道镇煞钉杀犯查
             ('role:胡不为','fact:f015','told',6),  # 胡不为知道获得还丹
             ('role:蔺得岷','fact:f011','told',6), # 蔺得岷知道犯查被杀
         ],
         promises=[
             dict(text='胡不为获得还丹,赵芙南嘱咐不可外示', setup_chapter=6, kind='promise'),
             dict(text='蔺得岷弟弟被人夺魄,需还丹救治', setup_chapter=6, kind='promise'),
         ],
         arcs=[
             dict(cid='role:胡不为', ch=6, ct='composite', summary='误杀犯查获还丹',
                  trigger='灵龙镇煞钉护主击杀犯查', arc_phase='转折·获宝'),
             dict(cid='role:胡不为', ch=6, ct='personality', summary='良心发现',
                  trigger='赵芙南安神曲抚慰', arc_phase='转折·成长'),
             dict(cid='role:蔺得岷', ch=6, ct='ability', summary='受伤',
                  trigger='蛀木妖偷袭', arc_phase='挫折'),
             dict(cid='role:蔺得岷', ch=6, ct='personality', summary='誓言束缚',
                  trigger='犯查被胡不为所杀,还丹归胡', arc_phase='失去'),
             dict(cid='role:赵芙南', ch=6, ct='relation', summary='对胡不为改观',
                  trigger='吹安神曲赠还丹', arc_phase='转折·善意'),
         ]),

    # ── 第7章: 归途(原创,衔接原文第六章) ──
    dict(seq=7, title='归途·前因皆缘细物起', focalizer='role:胡不为',
         events=[
             dict(id='ev:c7e1', etype='赶路', chapter=7,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:汾州', goal='胡不为策马归家途中'),
             dict(id='ev:c7e2', etype='偶遇', chapter=7,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:汾州', goal='茶馆遇胖和尚掰腕赌胜,瘦汉北斗借力'),
         ],
         knowledge=[
             ('role:胡不为','fact:f015','told',7),  # 胡不为知道怀揣还丹
         ],
         promises=[
             dict(text='夜金砂——食人巨蝠所出治盲圣药', setup_chapter=7, kind='red_herring'),
         ]),

    # ── 第8章: 丽邻(原创,衔接原文第七章) ──
    dict(seq=8, title='丽邻·婉兮若兰毗为邻', focalizer='role:胡不为',
         events=[
             dict(id='ev:c8e1', etype='归家', chapter=8,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='胡不为回到定马村与妻子赵氏团聚'),
             dict(id='ev:c8e2', etype='日常', chapter=8,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='胡不为归家后日常,发现镇煞钉偶有异动'),
         ],
         knowledge=[
             ('role:胡不为','fact:f004','told',8),
             ('role:胡不为','fact:f005','told',8),
         ]),

    # ── 第9章: 晴天雷(原创,衔接原文第八章) ──
    dict(seq=9, title='晴天雷·晴天一雷惊心魄', focalizer='role:胡不为',
         events=[
             dict(id='ev:c9e1', etype='异变', chapter=9,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='定马村突现妖气,镇煞钉剧烈反应'),
             dict(id='ev:c9e2', etype='危机', chapter=9,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='胡不为被迫用镇煞钉护村,暴露实力'),
         ],
         knowledge=[
             ('role:胡不为','fact:f003','told',9),
         ],
         promises=[
             dict(text='定马村妖气来源不明,可能与奈何谷封印松动有关', setup_chapter=9, kind='promise'),
         ],
         arcs=[
             dict(cid='role:胡不为', ch=9, ct='personality', summary='被迫直面',
                  trigger='妖气逼近无法再逃', arc_phase='转折·觉醒'),
         ]),

    # ── 第10章: 抉择(原创,阶段总结) ──
    dict(seq=10, title='抉择·善恶是非岂人定', focalizer='role:胡不为',
         events=[
             dict(id='ev:c10e1', etype='抉择', chapter=10,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='胡不为决定回梧桐谷送还镇煞钉'),
             dict(id='ev:c10e2', etype='出发', chapter=10,
                  participants={'SUBJ':'role:胡不为'},
                  location='place:定马村', goal='胡不为携还丹和镇煞钉出发回梧桐村'),
         ],
         knowledge=[
             ('role:胡不为','fact:f002','told',10),
             ('role:胡不为','fact:f015','told',10),
         ],
         arcs=[
             dict(cid='role:胡不为', ch=10, ct='personality', summary='从逃跑到面对',
                  trigger='决定回梧桐村送还钉子', arc_phase='转折·救赎'),
         ]),
]

# ═══ 写入数据 ═══
for ch in chapters_design:
    # 事件
    for ev in ch['events']:
        e = Event(ev['id'], ev['etype'], story_time=ev['chapter'],
                  participants=ev.get('participants',{}),
                  location=ev.get('location'),
                  effects=ev.get('effects',[]),
                  motivated_by_goal=ev.get('goal'))
        st.add_event(e)

    # 知识边(角色知道某事实)
    for knower, fid, via, since in ch.get('knowledge', []):
        st.add_knowledge(KnowledgeEdge(knower, fid, since_chapter=since, acquired_via=via))

    # 伏笔
    for p in ch.get('promises', []):
        st._execute_write(
            "CREATE promise SET text=$t, setup_chapter=$sc, status='open', kind=$k",
            {'t': p['text'], 'sc': p['setup_chapter'], 'k': p['kind']})

    # 弧光
    for a in ch.get('arcs', []):
        st.add_char_state(a['cid'], a['ch'], a['ct'], a['summary'],
                          trigger_event=a.get('trigger'), arc_phase=a.get('arc_phase'))

    print(f"第{ch['seq']}章《{ch['title']}》: {len(ch['events'])}事件, {len(ch.get('knowledge',[]))}知识边, {len(ch.get('promises',[]))}伏笔, {len(ch.get('arcs',[]))}弧光", flush=True)

# ═══ 验证 ═══
total_events = len(st._query("SELECT id FROM event"))
total_knows = len(st._query("SELECT id FROM knows"))
total_promises = len(st._query("SELECT id FROM promise"))
total_arcs = len(st._query("SELECT id FROM char_state"))

print(f"\n═══ 推演台数据 ═══", flush=True)
print(f"事件: {total_events} | 知识边: {total_knows} | 伏笔: {total_promises} | 弧光: {total_arcs}", flush=True)

# 验证限知帧:第2章胡不为应该知道墓室,老乌头应该知道使命
frame_hbw = st._query("SELECT * FROM knows WHERE in=type::thing('character','胡不为') AND since_chapter<=2")
frame_lwt = st._query("SELECT * FROM knows WHERE in=type::thing('character','老乌头') AND since_chapter<=2")
print(f"限知帧验证: 胡不为第2章知{len(frame_hbw)}条, 老乌头第2章知{len(frame_lwt)}条", flush=True)

# 验证伏笔状态:全部应为open
open_promises = st._query("SELECT id FROM promise WHERE status='open'")
print(f"伏笔状态: {len(open_promises)}/{total_promises} 为open", flush=True)

st.close()
print("\n阶段2完成。", flush=True)
