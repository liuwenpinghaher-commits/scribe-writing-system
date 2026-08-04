#!/usr/bin/env python3
"""将乱世铜炉设定数据 + 10章写入运行中的 scribe3 数据库"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.store import SurrealStore
from scribe3.ontology import Entity, Event

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')
# DB 已有旧 schema,不需要 apply_schema

# 角色
chars = [
    ('胡不为','protagonist','风水师/江湖骗子。瘦弱,黄布直裰,唇上细髭。贪财怕死但心有底线。',['贪财','怕死','机敏','有底线']),
    ('老乌头','major','乌家第32代守墓人。半脸烧伤疤痕,左手齐肘断。孤独坚守。',['坚守','孤独','忠义','丑陋']),
    ('韩之敬','minor','三水村韩诤次子,新婚。',['老实','疲惫']),
    ('时闻盂','minor','瘦小青年,牛泪水染眼后可见阴阳。',['胆小','机缘']),
    ('犀香','minor','韩之敬之妻,眉眼清秀。',['朴实']),
    ('蔺得岷','major','严台山大师兄。面如重枣,长须剑眉。',['威严','正统','好面子']),
    ('赵姑娘','major','青叶门弟子。白衣竹笛,声音稚嫩温柔。',['娇俏','锋芒','洒脱']),
    ('顾有全','minor','严台山五师弟。粗豪,暴躁莽撞。',['暴躁','莽撞','直爽']),
]
for name, imp, bs, pt in chars:
    oid = f"role:{name}"
    if not st.entity(oid):
        st.add_entity(Entity(oid, 'character', name, traits={'backstory': bs, 'personality_tags': pt}))
    st._db.query("UPDATE type::thing('character', $n) SET importance=$i", {'n': name, 'i': imp})
print(f"角色: {len(chars)}", flush=True)

# 地点
places = ['三水村','梧桐村','奈何谷','碧玉潭','严台山']
for name in places:
    try: st._db.query("CREATE type::thing('place', $n) SET name=$n", {'n': name})
    except: pass
print(f"地点: {len(places)}", flush=True)

# 世界规则
existing_rules = st.list_world_rules()
if not existing_rules:
    for name, cat, src, cost, lims, excs in [
        ('灵龙镇煞钉','magic','阳铜熔炼+黑狗血浸染+四十九天','三百六十枚可封死大罗神仙',['造法费心费力'],[]),
        ('牛泪水通阴阳','magic','阴日阴时的牛泪水染眼','可开不可逆',[],[]),
        ('犯查兽还丹','magic','天地生养修炼成形','还丹被夺则死',[],[]),
    ]:
        st.add_world_rule(name, cat, source=src, cost=cost, limitations=lims, exceptions=excs)
print(f"世界规则: {len(st.list_world_rules())}", flush=True)

# 势力
existing_f = st.list_factions()
if not existing_f:
    for name, ideo, status, leader, pub, priv in [
        ('严台山','捉妖除魔','active','蔺得岷','名门正派','实力一般'),
        ('青叶门','养妖兽取还丹','active',None,'仙子门派','深不可测'),
        ('乌家','镇守奈何谷','dormant','老乌头','道术世家','火灾后失传'),
    ]:
        st.add_faction(name, ideology=ideo, status=status, leader=leader, public_face=pub, private_operation=priv)
print(f"势力: {len(st.list_factions())}", flush=True)

# 事件
if not st._query("SELECT id FROM event LIMIT 1"):
    for n in ['胡不为','老乌头','时闻盂','蔺得岷','赵姑娘','韩之敬']:
        if not st.entity(f"role:{n}"):
            st.add_entity(Entity(f"role:{n}", 'character', n))
    events = [
        Event('ev:001','婚宴',story_time=1,participants={'WITNESS':'role:时闻盂'},motivated_by_goal='韩之敬大婚'),
        Event('ev:002','牛泪',story_time=1,participants={'SUBJ':'role:时闻盂'},motivated_by_goal='获阴阳眼'),
        Event('ev:003','怪墓',story_time=2,participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},motivated_by_goal='查看风水'),
        Event('ev:004','开坛',story_time=2,participants={'SUBJ':'role:胡不为'},motivated_by_goal='假装降妖'),
        Event('ev:005','遇险',story_time=3,participants={'SUBJ':'role:胡不为','WITNESS':'role:蔺得岷'},motivated_by_goal='返家途中'),
        Event('ev:006','对峙',story_time=3,participants={'SUBJ':'role:蔺得岷','OBJ':'role:赵姑娘','WITNESS':'role:胡不为'},motivated_by_goal='争犯查兽'),
    ]
    for ev in events: st.add_event(ev)
    print(f"事件: {len(events)}", flush=True)

# 10章正文
chapters = [
    (1,'引子·贺客','role:时闻盂','夜幕渐落。三水村韩诤次子韩之敬今日大喜,酒宴从一早开始,直至夜黑仍未散席。时闻盂喝得烂醉,到庭院僻静处呕吐。他不知醉卧何处,只觉四肢百骸似棉花捏成,膝一软,仰身扑通倒下。睡过去之前,似乎看到了头上有星光一闪。旁边似乎有物动作,此时他闻到了一股浓烈的腥膻味。次日醒来,眼中染了牛泪水,竟可见异物——堂屋正中站满了已故先人的魂灵,脚不着地,踮脚漂移,烛光之下竟无一块影子。时闻盂撕心裂肺地惨叫。自此,他眼中可见阴阳,再也返不回从前。'),
    (2,'怪墓·玄机','role:胡不为','梧桐村。风水先生胡不为被请来看风水。他画了数道定神符让村长烧水服下,众人便觉眼目清明。胡不为勘察后言道:贵村风水格局古怪,有外气骑欺,必有不明之物镇锁关窍。老乌头闻言大喜,引众人入奈何谷。峡谷两脉峰峦南北而来,中间只留一道峡谷。墓室深入峡谷腹地,悬壁凿室。室内一具黑色棺椁,周围三百六十枚灵龙镇煞钉围成太极阵。胡不为大骇,拾起一枚跳出的钉子收入怀中。这灵龙镇煞钉,阳铜熔炼七日,黑狗血浸染七日,七七四十九天方成,辟邪圣物。棺中究竟为何物,竟要动用三百六十支灵龙镇煞钉?'),
    (3,'遇险·山命','role:胡不为','胡不为骑花脚驴子仓皇逃离梧桐村。驴子贪嘴好吃,走走停停,行了十余里。他心中患得患失,反复劝慰自己:自己并无伏魔之能,守在村里也不过是多添一条人命。夜深,在小树林歇脚。取出灵龙镇煞钉在月光下验看,钉子似乎亮了一下,如通透的青玉。忽听一支响箭从头顶激射过去。西面和南面树林里响起细声,似乎有多个妖怪同时接近。胡不为腿软如面条,翻倒在地。却听得林中有人以切口对答——严台山蔺得岷率众弟子捉拿犯查兽。他蹿将起来,望众人狂奔:是我!我是人,众位大侠手下留情!'),
    (4,'对峙·竹笛','role:胡不为','一阵清脆的竹笛声传来,如玉落银盘。青叶门赵姑娘白衣坐于树枝上,裙幅低垂,长袖翩翩。蔺得岷冷哼:想不到青叶门也想来赶这个场子了。赵姑娘笑道:我们门主后院养的宠物被小贼偷走了,一只修炼了四百年的小兽犯查。顾有全不忿:这只犯查是天地生养,怎么会是你们门主的宠物?赵姑娘嘻嘻笑:我们门主说了,她的后院大的很,这天地么,好象就是我们门主后院的一部分。蔺得岷怒极。赵姑娘却只想要犯查体内的还丹。二人舌战方酣,蓦然一阵震天巨响,犯查兽伺机逃走。'),
    (5,'独行·夜路','role:胡不为','众人追犯查兽而去,只剩胡不为呆立原地。风吹入林,幽幽如叹,宛若泣妇夜哭。他心如鹿撞,欲哭无泪。左右为难之下,想到自己还有一只驴子可以依靠。胡不为牵着驴子,在月色下踉跄前行。怀中的灵龙镇煞钉沉甸甸的,是他此刻唯一的倚仗。他反复摩挲钉子,只觉那钉身似乎微微发烫。不知是月光作祟,还是钉中真有灵龙苏醒。走了约莫半个时辰,前方隐约可见灯火。是一座小客栈,挂着太平二字破旧招牌。胡不为大喜,牵驴奔去。却不料,这客栈中正有人在等他。'),
    (6,'客栈·暗算','role:胡不为','客栈中冷冷清清,只有一个驼背老妪在柜台后打盹。胡不为要了一间房,将驴子拴在后院。他关上房门,取出灵龙镇煞钉仔细端详。钉上的灵龙似乎在烛光下微微游动,鳞甲宛然。正看得出神,窗外忽然传来一阵细碎的脚步声。胡不为心头一紧,将钉子藏入怀中。门被推开一条缝,一只手伸了进来,手中握着一把匕首,寒光闪闪。胡不为大叫一声,抄起板凳砸去。那手缩了回去,紧接着是急促的脚步声远去。他冲到窗前,只见一个黑影翻墙而走。墙头上留下了一道符纸。胡不为颤着手拾起符纸,隐约觉得,这世上想要灵龙镇煞钉的人,恐怕不止他一个。'),
    (7,'旧识·乌家','role:胡不为','次日清晨,胡不为仓皇离开客栈。他不敢走大路,专拣小道穿行。行至午后,前方出现一座破败的道观。门楣上依稀可辨乌家祠三字。胡不为一惊——老乌头曾说过,乌家本是道术之家,四百年前便开始镇守梧桐村。他推门而入,只见院中杂草丛生,正殿供桌上摆着一排牌位,正是乌家历代守墓人。最末一个牌位上刻着乌承光三字——正是老乌头的本名。牌位旁放着一本残破的手抄本,封面写着乌家镇守录。胡不为翻开,只见里面记载着奈何谷墓室的来历:四百年前,一位道术高人将一具寒妇封镇于此。寒妇不是鬼,是一种以人为食的异类。每过数百年便会苏醒一次,方圆百里生灵涂炭。乌家世代以灵龙镇煞钉加固封印。'),
    (8,'危机·封印','role:胡不为','胡不为将乌家镇守录收入怀中,快步离开道观。他现在明白了——自己从墓室中取走的那枚钉子,正是三百六十枚灵龙镇煞钉之一。少了一枚,封印便有了缺口。寒妇随时可能从缺口中挣脱。他必须尽快把钉子送回去。但送回去谈何容易?奈何谷中妖气弥漫,他一个风水骗子,哪里敢再回去?正自焦虑,身后传来急促的马蹄声。回头一看,竟是严台山的顾有全,满脸怒容,策马追来。胡不为!你往哪里跑!大师兄让我来问你——那枚灵龙镇煞钉是不是在你手里?!'),
    (9,'抉择·归途','role:胡不为','胡不为心知瞒不过,只得承认。顾有全一把将他拎上马背,调头往梧桐村方向疾驰。路上,顾有全告知:蔺得岷发现犯查兽逃入奈何谷,追入墓室时发现少了一枚钉子。封印已经松动,墓室中传出异响。老乌头得知后,当场瘫倒。胡不为心中五味杂陈。他贪财怕死,但也不想让一村人因自己而死。怀中的灵龙镇煞钉似乎感应到了什么,温度越来越高,钉身上的灵龙纹路隐隐发出红光。他想起大元炼真经中的话:钉成后法力非凡,辟邪圣物。也许,这枚钉子不只能害人,也能救人。'),
    (10,'封镇·铜炉','role:胡不为','众人赶到奈何谷时,天色已暗。峡谷中青濛雾气弥漫,比往日浓烈数倍。墓室洞口传来低沉的撞击声,一下又一下,震得崖壁簌簌落土。老乌头面如死灰,颤声道:它要出来了。三百六十枚钉子少了一枚,封印撑不了多久。胡不为深吸一口气,从怀中取出灵龙镇煞钉。钉子此刻烫得几乎握不住,灵龙纹路通红如火。他想起乌家镇守录中的记载:钉归原位,封印自复。众人护卫着他冲入墓室。棺椁正在剧烈震动,黑色棺盖上出现了裂纹。胡不为跪在跳出的钉洞前,将灵龙镇煞钉狠狠钉入。刹那间,三百六十枚钉子同时发出红光,灵龙纹路活了过来,沿着太极阵游走一圈。棺椁的震动停了下来。裂纹缓缓合拢。墓室中恢复了死寂。胡不为瘫坐在地,大口喘气。他怀里那九两银子还在,但此刻他觉得,活着比银子更重要。'),
]
for seq, title, focalizer, prose in chapters:
    st.save_chapter(seq, prose, title=title, focalizer=focalizer)
print(f"章节: {len(chapters)} 章已写入", flush=True)

# 验证
s = st.stats()
print(f"\n数据库状态: {s['chapter_count']} 章, {s['word_count']} 字", flush=True)
print(f"角色: {len(st.characters())} 个", flush=True)
print(f"事件: {len(st.events_at(2))} 个(第2章)", flush=True)
print(f"世界规则: {len(st.list_world_rules())} 条", flush=True)
print(f"势力: {len(st.list_factions())} 个", flush=True)
print("\n数据已写入运行数据库。浏览器刷新 http://localhost:3311 即可看到。", flush=True)
st.close()
