#!/usr/bin/env python3
"""业务测试·第三轮:原创志怪世界《铜炉试炼》全量设定 + 推演数据 seed。
乱世铜炉风:乱世小人物误卷邪物秘局,限知双POV,伏笔回收。
每类设定≥10条;推演=事实/事件/知识帧/伏笔/弧光/关系,支撑限知生成。

跑: cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python tools/bt_seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.store import SurrealStore
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge

WORK = "book_bfd18b78"
st = SurrealStore(ns="scribe3", db=WORK)
try:
    st.apply_schema()
except Exception as e:
    print("apply_schema(可能已建):", e)

# 清旧(幂等重跑)
for t in ["character", "faction", "item", "term", "world_rule", "promise",
          "motif", "proposition", "event", "knows", "reader_knows", "char_state",
          "ingest_unverified", "chapter", "character_relation"]:
    try:
        st._db.query(f"DELETE {t}")
    except Exception:
        pass

# ═══════════ 1. 角色(10)═══════════
CHARS = [
    ("柳三更", "protagonist", "走方叫魂郎,替人招走失的魂魄为生,半真半骗。三十出头,面皮黄瘦,左眉一道旧疤。贪生怕死,嘴皮子利落,却存一点不肯昧尽的良心。无意中得了半截引魂铃。",
     ["贪生", "机变", "嘴利", "有底线"], "protagonist"),
    ("白姑", "major", "三十许青衣女子,鬓边一支素银簪。沉静寡言,眼底藏事。似村妇又非村妇,身手与谈吐都不寻常。她知道回煞炉与引魂铃的一部分真相,却处处隐瞒。",
     ["沉静", "隐忍", "决绝", "知情"], "major"),
    ("焦判官", "major", "城南义庄老仵作,姓焦名其,绰号'判官'。须发斑白,一手验骨绝活。守着一桩二十年前的旧案不肯放,见过太多无主尸骨。",
     ["阴沉", "执拗", "通透", "重旧情"], "major"),
    ("聋祖", "minor", "焚骨庵守庵人,又聋又哑,面覆半张烧伤。守着庵里那座蒙尘的铜炉,日日添香,不知守了多少年。",
     ["孤僻", "忠守", "诡秘"], "minor"),
    ("麻三娘", "major", "城西香堂堂主,四十上下,脸有麻点,笑里藏刀。明里开香烛铺,暗里养着回煞炉续香客的命,收人阳寿。手段毒辣。",
     ["精明", "狠辣", "笑面", "贪权"], "major"),
    ("卞捕头", "minor", "巡检司捕头,粗豪好酒,认死理。查城里接连出的'借寿案',却总差一步。",
     ["粗豪", "认死理", "莽撞"], "minor"),
    ("阿枝", "minor", "约莫八九岁的哑女童,白姑带在身边。眼睛清亮,能看见生人看不见的东西。来历不明。",
     ["怯生", "灵慧", "通阴阳"], "minor"),
    ("瘸九", "minor", "漕帮码头的瘸腿管事,消息灵通,认钱不认人,却也讲三分江湖义气。",
     ["市侩", "灵通", "讲义气"], "minor"),
    ("罗半仙", "minor", "同行叫魂郎,柳三更的对头,惯会抢生意、踩同行。油滑势利,关键时刻最先逃。",
     ["油滑", "势利", "怕死"], "minor"),
    ("慧远", "minor", "游方僧,芒鞋破衲,来去无踪。话里有话,似乎早知柳三更命里这一遭。真身存疑。",
     ["飘忽", "机锋", "莫测"], "minor"),
]
for name, imp, backstory, tags, impv in CHARS:
    st.add_entity(Entity(f"role:{name}", "character", name,
                         traits={"backstory": backstory, "personality_tags": tags}))
    st._db.query("UPDATE type::thing('character',$n) SET importance=$i", {"n": name, "i": impv})
print(f"角色: {len(CHARS)}")

# ═══════════ 2. 势力(10)═══════════
FACTIONS = [
    ("城西香堂", "明开香烛铺,暗养回煞炉收阳寿续命", "active", "麻三娘", "香烛纸马铺", "以回煞炉借生人阳寿续香客亡魂,牟暴利", 1),
    ("运河漕帮", "把持码头漕运,黑白通吃", "active", "瘸九(管事)", "漕运脚行", "走私盐铁,替各方递消息收钱", 1),
    ("城南义庄", "收殓无主尸骨,验尸断案", "active", "焦判官", "义庄殡葬", "暗中追查二十年借寿旧案", 1),
    ("巡检司", "缉拿盗匪,查办命案", "active", "卞捕头", "官府衙役", "查借寿案屡屡受阻,疑有内鬼通香堂", 1),
    ("焚骨庵", "看守回煞炉本炉,传承借寿邪法", "dormant", "聋祖(末代)", "荒废尼庵", "回煞炉真身所在,守庵人世代以香火镇炉", 1),
    ("白莲余党", "前朝崩后流散的会道门残部", "dormant", None, "民间香会", "借乱世聚众,觊觎回煞炉之力", 2),
    ("镖局(广通)", "保镖押运为业", "active", None, "走镖护院", "受香堂雇佣押运过'活炉',知情者灭口", 2),
    ("丐帮(城隍庙口)", "乞儿结社,耳目遍城", "active", None, "沿街乞讨", "替出价者打探消息,卖人行踪", 1),
    ("盐枭(黑风滩)", "贩私盐的武装", "active", None, "盐贩商队", "与漕帮争利,劫掠过往", 2),
    ("戏班(临江社)", "走村串镇唱戏", "active", None, "唱戏卖艺", "香堂安插的暗桩,以唱戏为名探听各村'寿厚'之人", 2),
]
for name, ideo, status, leader, pub, priv, ch in FACTIONS:
    st.add_faction(name, ideology=ideo, status=status, leader=leader,
                   public_face=pub, private_operation=priv, first_mention_chapter=ch)
print(f"势力: {len(FACTIONS)}")

# ═══════════ 3. 物品(10+)═══════════
ITEMS = [
    ("引魂铃", "法器", "半截黄铜小铃,无舌而能自鸣。铃身刻半幅缠枝纹,断口齐整,似被人硬生生掰去一半。摇之声细如游丝,亡魂可闻。柳三更无意中所得。", "role:柳三更", "active", ["招亡魂", "认主自鸣", "残缺"]),
    ("回煞炉", "邪器", "丈许高的乌沉铜炉,炉身九窍,刻满蝌蚪状古文。可借生人阳寿续亡魂之命,代价惨烈。本炉藏焚骨庵,香堂另有一座'活炉'游走城中。", None, "unknown", ["借寿续魂", "九窍纳魂", "镇于焚骨庵"]),
    ("招魂幡", "法器", "白布黑字三尺幡,叫魂郎行头。书亡者生辰八字,夜半举幡唤魂。", "role:柳三更", "active", ["唤魂", "书八字"]),
    ("纸人", "法器", "草纸扎成的替身小人,可代生人受一劫,用毕即焚。", "role:柳三更", "active", ["替身受劫"]),
    ("铜钱剑", "法器", "百枚旧铜钱以红绳缚成剑形,辟邪镇祟。剑尖缺了一枚钱,来历成谜。", "role:罗半仙", "active", ["辟邪", "缺一钱"]),
    ("黑狗血", "辟邪物", "纯黑公狗颈血,泼洒可破邪法、显形走尸。叫魂郎常备。", "role:柳三更", "active", ["破邪", "显形"]),
    ("阴阳簿", "典籍", "焦判官手抄的验骨断案册,记着二十年来无主尸骨的样貌与死状,内藏旧案线索。", "role:焦判官", "active", ["记死状", "藏旧案"]),
    ("白幡铭旌", "法器", "出殡引路的白幡,书亡者名讳,镇煞引魂归位。", None, "active", ["引魂归位", "镇煞"]),
    ("骨笛", "邪器", "胫骨所制短笛,吹之可乱人三魂,使生人如走尸般听命。香堂秘器。", "role:麻三娘", "active", ["乱魂", "驱使走尸"]),
    ("童子尿罐", "辟邪物", "陶罐盛童子晨尿,泼污邪物可解其法。市井土法。", None, "active", ["解邪法"]),
    ("素银簪", "信物", "白姑鬓边一支素银簪,簪头暗刻一个'潭'字,似某门派信物。", "role:白姑", "active", ["藏门派印记"]),
]
for name, cat, desc, owner, state, props in ITEMS:
    st.add_item(name, category=cat, description=desc, current_owner=owner,
                symbolic_state=state, special_properties=props)
print(f"物品: {len(ITEMS)}")

# ═══════════ 4. 术语(10+)═══════════
TERMS = [
    ("叫魂", "术法", "替魂魄走失之人(惊吓、重病、撞邪)招魂归窍的江湖术。半真半骗,真术士百中无一。", ["招魂", "喊惊"]),
    ("回煞", "术法", "人死后亡魂于'回煞'之夜返家一趟。回煞炉之名由此而来——可截留回煞之魂续命。", ["返煞"]),
    ("阳寿", "概念", "生人一世的命数年限。可被回煞炉'借'去续亡魂,被借者折寿乃至暴毙。", ["寿数", "命数"]),
    ("三魂七魄", "概念", "人有三魂(胎光/爽灵/幽精)七魄。魂散则魄不附,人即如走尸或痴傻。", ["魂魄"]),
    ("引魂铃", "法器术语", "古时引魂归位的整铃,声可贯通阴阳。今多残缺,半截亦能认主自鸣。", ["魂铃"]),
    ("焚骨", "习俗", "乱世无主尸骨太多,焚之以绝疫气。焚骨庵因此得名,却另藏镇炉之秘。", ["化骨"]),
    ("借寿", "邪法", "回煞炉之核心邪法:以生人阳寿为薪,续亡魂或续将死之人之命。借寿案即由此起。", ["续命"]),
    ("走尸", "异象", "三魂被乱、魄不散者,夜间起行如活人,实则魂去。骨笛可驱。", ["行尸"]),
    ("阴阳眼", "异禀", "生具或意外开启,可见亡魂阴物。一旦开启不可逆,见者多惊惧成疾。", ["天眼"]),
    ("香堂切口", "黑话", "香堂中人接头暗语,上半句'三炷敬回煞',下半句'一炉续千秋'。", ["切口", "暗号"]),
    ("活炉", "邪器术语", "回煞炉本炉太重不可移,香堂另铸小炉游走城中收寿,谓之'活炉'。", ["游炉"]),
]
for name, cat, defn, aliases in TERMS:
    st.add_term(name, category=cat, definition=defn, aliases=aliases)
print(f"术语: {len(TERMS)}")

# ═══════════ 5. 世界规则(10)═══════════
RULES = [
    ("叫魂术", "magic", "招魂幡书八字,夜半连唤三声,真魂未远者可归窍", "需亡者八字与三炷香",
     ["魂去三日以上不可招", "假术招不回真魂"], ["真术士百无一二"], "global", 1),
    ("回煞借寿", "magic", "回煞之夜以铜炉九窍纳生人阳寿,续亡魂之命", "每续一年需折生人三年阳寿",
     ["被借者必折寿,过则暴毙", "续来之魂非真活,渐成厉"], [], "global", 1),
    ("引魂铃认主", "magic", "残铃见有缘者自鸣认主,认主后他人不能夺", "半截铃只能认半主,力不全",
     ["认主后铃随主魂,主死铃哑"], ["整铃方能开阴阳"], "global", 1),
    ("黑狗血辟邪", "magic", "纯黑公狗颈血泼洒,可破低阶邪法、令走尸显形", None,
     ["对回煞炉这类大邪器无用"], [], "regional", 1),
    ("纸人替身", "magic", "草纸人书生人八字,可代受一劫,用毕自焚", None,
     ["一人一劫,不可再用", "大劫挡不住"], [], "global", 1),
    ("阳寿可量", "magic", "通阴阳者可观人头顶'寿灯'明暗,量其阳寿厚薄", None,
     ["只阴阳眼者可见", "量得准却改不得"], [], "global", 2),
    ("走尸夜行", "magic", "魂乱魄存者夜出如活人,鸡鸣即僵", None,
     ["见光则滞", "骨笛可驱使"], [], "regional", 2),
    ("阴阳眼不可逆", "magic", "一旦开启阴阳眼,终生可见阴物,不可复闭", "撞邪/邪法/异血所致",
     ["开则惊惧成疾", "无法返还"], [], "global", 1),
    ("香火续魂", "magic", "亡魂赖生人香火供奉而存,香断魂散", None,
     ["无人供奉则魂渐消", "回煞炉以邪火代香火,故能久续"], [], "global", 1),
    ("铭旌镇煞", "magic", "白幡书亡者名讳引魂归位,可镇暂起之煞", None,
     ["只镇小煞", "名讳错则无效"], [], "regional", 2),
]
for name, cat, src, cost, lims, excs, scope, ch in RULES:
    st.add_world_rule(name, cat, source=src, cost=cost, limitations=lims,
                      exceptions=excs, scope=scope, established_chapter=ch)
print(f"世界规则: {len(RULES)}")

# ═══════════ 6. 伏笔(10)═══════════
PROMISES = [
    ("柳三更手中的半截引魂铃,另半截在谁手里", 1, "promise"),
    ("白姑鬓边素银簪暗刻'潭'字,她究竟是何来历", 1, "promise"),
    ("回煞炉本炉藏于焚骨庵,聋祖为何世代死守", 1, "promise"),
    ("麻三娘香堂的'活炉'在城中游走收谁的阳寿", 1, "promise"),
    ("哑女阿枝能见阴物,她的来历与引魂铃是否相关", 2, "promise"),
    ("焦判官守的二十年旧案,与回煞炉借寿是否同源", 2, "promise"),
    ("柳三更的阳寿是否已在不知不觉中被'活炉'借走", 3, "promise"),
    ("游方僧慧远早知柳三更命里这一遭,他的真身是什么", 2, "promise"),
    ("罗半仙的铜钱剑缺一钱,那一钱去了何处", 3, "red_herring"),
    ("白姑处处隐瞒真相,她到底是想用柳三更还是想救他", 1, "promise"),
]
for text, sc, kind in PROMISES:
    st.plant_promise(text, sc, kind)
print(f"伏笔: {len(PROMISES)}")

# ═══════════ 7. 母题(10)═══════════
MOTIFS = [
    ("魂与寿的交易", "续命须折寿,有所得必有所偿", "回煞炉借寿/纸人替身/香火续魂", "贯穿全书的核心债"),
    ("乱世人命如草", "兵荒马乱,无主尸骨遍野,命贱如纸", "焚骨/义庄/流民", "底色"),
    ("铃声", "引魂铃细鸣,阴阳之声,认主与示警", "残铃自鸣/铃随主魂", "声音意象"),
    ("铜炉与火", "炉火不熄则魂不散,邪火代香火", "回煞炉/活炉/焚骨庵香火", "核心物象"),
    ("骨", "无主之骨,验骨断案,胫骨为笛", "义庄尸骨/阴阳簿/骨笛", "死亡意象"),
    ("招魂幡", "白布黑字唤魂,半真半骗的行当", "柳三更行头/夜半举幡", "身份物象"),
    ("贪生与底线", "怕死却不肯昧尽良心的小人物挣扎", "柳三更逃与不逃之间", "人物弧"),
    ("名与实", "真术士与江湖骗子之辨,名不副实之讽", "叫魂郎/半仙/游方僧", "讽喻"),
    ("阴阳之隔", "生死两隔,阴阳眼者立于隔上之苦", "阿枝/阴阳眼/走尸", "处境"),
    ("债与还", "前人造的孽,后人来还", "二十年旧案/焚骨庵之守", "因果"),
]
for name, theme, echoes, unfolding in MOTIFS:
    st.add_motif(name, theme=theme, echoes=echoes, unfolding=unfolding)
print(f"母题: {len(MOTIFS)}")

# ═══════════ 8. 声音档(主要角色)═══════════
st.set_voice_profile("role:柳三更", {
    "style_summary": "市井油滑,爱拿行话吹嘘壮胆,越慌越贫嘴。内心独白多,患得患失,常自我开解。被戳穿时讪讪改口。",
    "catchphrases": [{"phrase": "好说好说", "frequency": "medium"}, {"phrase": "罢了罢了", "frequency": "low"}],
    "ooc_signals": [
        {"description": "直接说出情感词(我很害怕/我爱你)", "detection_method": "rule", "severity": "high"},
        {"description": "连续超过3句长句(每句>25字)", "detection_method": "rule", "severity": "medium"},
    ], "version": 1,
})
st.set_voice_profile("role:白姑", {
    "style_summary": "话少而冷,半句藏半句,常以反问挡问。情绪克制,偶露一丝不忍即收。",
    "ooc_signals": [{"description": "长篇剖白心事", "detection_method": "rule", "severity": "high"}],
    "version": 1,
})
st.set_voice_profile("role:焦判官", {
    "style_summary": "阴沉简练,验骨人的冷静,谈死如谈饭。偶引旧案,语带沧桑。",
    "ooc_signals": [{"description": "情绪失控大喊", "detection_method": "rule", "severity": "medium"}],
    "version": 1,
})
print("声音档: 3")

# ═══════════ 9. 推演:事实/命题(限知核心)═══════════
FACTS = [
    ("fact:f01", "role:柳三更", "身份", "走方叫魂郎,半真半骗", 1, False),
    ("fact:f02", "role:柳三更", "得物", "无意得半截引魂铃", 1, False),
    ("fact:f03", "item:引魂铃", "真相", "另半截在白姑手中,合则可开阴阳", 1, True),
    ("fact:f04", "role:白姑", "真相", "清潭门弃徒,二十年前借寿旧案的知情者", 1, True),
    ("fact:f05", "item:回煞炉", "真相", "本炉藏焚骨庵,借寿续魂,续来之魂渐成厉", 1, True),
    ("fact:f06", "role:麻三娘", "私密", "香堂以活炉游走城中收阳寿牟利", 1, True),
    ("fact:f07", "role:聋祖", "身份", "焚骨庵末代守庵人,以香火镇炉", 1, False),
    ("fact:f08", "role:阿枝", "异禀", "生具阴阳眼,可见亡魂寿灯", 2, False),
    ("fact:f09", "role:柳三更", "危机", "阳寿已被活炉暗借三年", 3, True),
    ("fact:f10", "role:焦判官", "旧案", "二十年前满门借寿暴毙案,凶器指向回煞炉", 2, True),
    ("fact:f11", "role:白姑", "动机", "欲借引魂铃认主之力毁回煞炉,赎当年之过", 2, True),
    ("fact:f12", "item:活炉", "踪迹", "活炉藏于临江戏班的戏箱,随班游走", 3, True),
    ("fact:f13", "item:回煞炉", "本炉与活炉关系", "焚骨庵的回煞炉是本炉(丈许高、不可移),香堂另铸的活炉是它的分炉,游走城中代收阳寿", 1, True),
]
for fid, eid, attr, val, ch, secret in FACTS:
    st.add_fact(Fact(fid, eid, attr, val, valid_from=ch, secret=secret))
    try:
        st.semantic_index(fid, val)
    except Exception:
        pass
print(f"事实: {len(FACTS)}")

# ═══════════ 10. 角色关系═══════════
RELS = [
    ("role:柳三更", "role:白姑", "熟人", 1),
    ("role:白姑", "role:阿枝", "恩人", 1),
    ("role:麻三娘", "role:聋祖", "竞争者", 1),
    ("role:焦判官", "role:卞捕头", "战友", 2),
    ("role:柳三更", "role:罗半仙", "同行", 1),
    ("role:麻三娘", "role:柳三更", "利益对立", 2),
    ("role:瘸九", "role:柳三更", "雇主雇员", 1),
]
for src, dst, rel, ch in RELS:
    try:
        st.add_character_relation(src, dst, rel, since_chapter=ch)
    except Exception as e:
        print(f"  关系 {src}->{dst} 失败(实体或未建):", str(e)[:60])
print(f"关系: {len(RELS)}")

# ═══════════ 11. 推演:5章事件链 + 知识帧 + 弧光 ═══════════
DESIGN = [
    dict(seq=1, title="第一章·铃自鸣", foc="role:柳三更", syn="柳三更夜半为孙寡妇招魂,怀中半截引魂铃无端自鸣,引出白姑与阿枝。柳贪念与疑惧并起,白姑隐瞒。",
         events=[("ev:c1e1", "招魂", 1, {"SUBJ": "role:柳三更"}, "place:城郊乱葬岗", "柳三更夜半举幡招魂"),
                 ("ev:c1e2", "异鸣", 1, {"SUBJ": "role:柳三更", "WITNESS": "role:白姑"}, "place:城郊乱葬岗", "引魂铃无舌自鸣,白姑现身")],
         know=[("role:柳三更", "fact:f01", "told", 1), ("role:柳三更", "fact:f02", "saw", 1),
               ("role:白姑", "fact:f03", "told", 1), ("role:白姑", "fact:f04", "told", 1)],
         arcs=[("role:柳三更", 1, "ability", "得引魂铃并初识其异", "铃自鸣", "引子·得物"),
               ("role:白姑", 1, "personality", "隐忍现身", "铃鸣引她出面", "登场")]),
    dict(seq=2, title="第二章·义庄骨", foc="role:柳三更", syn="柳三更求焦判官辨铃,义庄夜里见阿枝看寿灯,撞知二十年旧案的一角。麻三娘香堂的活炉踪迹初现。",
         events=[("ev:c2e1", "求辨", 2, {"SUBJ": "role:柳三更", "WITNESS": "role:焦判官"}, "place:城南义庄", "柳求焦判官辨认引魂铃"),
                 ("ev:c2e2", "窥案", 2, {"SUBJ": "role:柳三更", "OBJ": "role:阿枝"}, "place:城南义庄", "阿枝看寿灯,柳撞见旧案线索")],
         know=[("role:焦判官", "fact:f10", "told", 2), ("role:柳三更", "fact:f08", "saw", 2),
               ("role:阿枝", "fact:f08", "told", 2)],
         arcs=[("role:焦判官", 2, "relation", "向柳吐露旧案半角", "辨铃牵出旧案", "牵连"),
               ("role:柳三更", 2, "personality", "疑惧渐深", "撞见寿灯与旧案", "卷入")]),
    dict(seq=3, title="第三章·活炉影", foc="role:白姑", syn="白姑限知视角:她追查活炉,揭活炉藏于临江戏班戏箱;同时察觉柳三更阳寿已被暗借。情感弧由'用柳'转向不忍。",
         events=[("ev:c3e1", "追炉", 3, {"SUBJ": "role:白姑"}, "place:临江戏班", "白姑追查活炉至戏班"),
                 ("ev:c3e2", "察寿", 3, {"SUBJ": "role:白姑", "WITNESS": "role:阿枝"}, "place:临江戏班", "阿枝看出柳寿灯转暗,白姑心生不忍")],
         know=[("role:白姑", "fact:f12", "saw", 3), ("role:白姑", "fact:f09", "told", 3),
               ("role:白姑", "fact:f11", "told", 3), ("role:白姑", "fact:f13", "told", 3)],
         arcs=[("role:白姑", 3, "personality", "由用到悔", "察觉柳被借寿", "转折·不忍")]),
    dict(seq=4, title="第四章·焚骨庵", foc="role:柳三更", syn="柳三更被白姑半哄半逼同往焚骨庵,见聋祖与蒙尘本炉,铃在炉前剧鸣认主。柳惊知自己卷入大局,与白姑就'毁炉'起冲突。",
         events=[("ev:c4e1", "入庵", 4, {"SUBJ": "role:柳三更", "WITNESS": "role:聋祖"}, "place:焚骨庵", "柳白同入焚骨庵见守庵聋祖"),
                 ("ev:c4e2", "认主", 4, {"SUBJ": "role:柳三更"}, "place:焚骨庵", "引魂铃在本炉前剧鸣认主"),
                 ("ev:c4e3", "争执", 4, {"SUBJ": "role:柳三更", "OBJ": "role:白姑"}, "place:焚骨庵", "柳白就毁炉与否正面冲突")],
         know=[("role:柳三更", "fact:f05", "saw", 4), ("role:柳三更", "fact:f07", "saw", 4),
               ("role:柳三更", "fact:f03", "told", 4)],
         arcs=[("role:柳三更", 4, "ability", "铃认主,初通其力", "本炉前剧鸣", "转折·认主"),
               ("role:柳三更", 4, "personality", "从想逃到被迫直面", "知卷入大局", "觉醒")]),
    dict(seq=5, title="第五章·借寿局", foc="role:白姑", syn="白姑限知视角:麻三娘携活炉与香堂众围焚骨庵抢本炉,白姑布清潭旧阵护柳。她坦白当年引线之过,赌'以铃制炉'的局。高潮前夜,留余韵。",
         events=[("ev:c5e1", "围庵", 5, {"SUBJ": "role:麻三娘", "OBJ": "role:白姑"}, "place:焚骨庵", "麻三娘率香堂围庵抢炉"),
                 ("ev:c5e2", "布阵", 5, {"SUBJ": "role:白姑", "WITNESS": "role:柳三更"}, "place:焚骨庵", "白姑布清潭封煞阵护柳"),
                 ("ev:c5e3", "坦白", 5, {"SUBJ": "role:白姑", "OBJ": "role:柳三更"}, "place:焚骨庵", "白姑坦白当年引线之过与以铃制炉之赌")],
         know=[("role:白姑", "fact:f06", "saw", 5), ("role:白姑", "fact:f11", "told", 5),
               ("role:柳三更", "fact:f04", "told", 5)],
         arcs=[("role:白姑", 5, "composite", "坦白旧过,决意制炉", "围庵摊牌", "高潮前·决"),
               ("role:柳三更", 5, "relation", "由互疑到并肩", "白姑坦白护他", "转折·信任")]),
]
ev_n = kn_n = ar_n = 0
for d in DESIGN:
    for eid, et, ch, parts, loc, goal in d["events"]:
        st.add_event(Event(eid, et, story_time=ch, participants=parts, location=loc, motivated_by_goal=goal))
        ev_n += 1
    for knower, fid, via, since in d["know"]:
        try:
            st.add_knowledge(KnowledgeEdge(knower, fid, since_chapter=since, acquired_via=via)); kn_n += 1
        except Exception as e:
            print(f"  知识边 {knower}->{fid} 失败:", str(e)[:60])
    for cid, ch, ct, summ, trig, phase in d["arcs"]:
        st.add_char_state(cid, ch, ct, summ, trigger_event=trig, arc_phase=phase); ar_n += 1
    # 大纲(章梗概)
    try:
        st.save_chapter(d["seq"], "", title=d["title"], focalizer=d["foc"])
        st.update_chapter_meta(d["seq"], {"synopsis": d["syn"]})
    except Exception as e:
        print(f"  章{d['seq']}梗概失败:", str(e)[:80])
print(f"推演: 事件{ev_n} 知识边{kn_n} 弧光{ar_n} 大纲5")

# ═══════════ 验证设定完整度 ═══════════
comp = st.setting_completeness()
print(f"\n设定完整度: {comp['completeness_score']}分")
def _count(t):
    try:
        return len(st._query(f"SELECT id FROM {t}"))
    except Exception:
        return 0
counts = {t: _count(t) for t in
          ["character", "faction", "item", "term", "world_rule", "promise", "motif", "proposition", "event", "knows", "char_state"]}
print("各表条数:", counts)
ten_ok = all(counts[t] >= 10 for t in ["character", "faction", "item", "term", "world_rule", "promise", "motif"])
print("七类设定每类≥10:", "✅" if ten_ok else "❌ " + str({t: counts[t] for t in ["character","faction","item","term","world_rule","promise","motif"] if counts[t] < 10}))
st.close()
print("\nseed 完成。")
