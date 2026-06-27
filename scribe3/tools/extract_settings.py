#!/usr/bin/env python3
"""阶段1：从乱世铜炉前10章提取全部设定数据，灌入运行数据库。
基于通读原文(引子~第六章)的人工提取，非LLM生成。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.store import SurrealStore
from scribe3.ontology import Entity, Event, Fact

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')

# ═══ 清理旧数据(保留章节) ═══
for tbl in ['character','place','world_rule','faction','item','term','proposition','event','knows','character_relation','char_state','voice_profile','ingest_unverified']:
    try: st._db.query(f"DELETE TYPE::table('{tbl}')")
    except: pass
print("旧设定已清理", flush=True)

# ═══ 角色(20个) ═══
chars = [
    dict(name='胡不为', importance='protagonist', backstory='定马村风水先生/江湖骗子。三十一二年纪,瘦弱,黄布直裰,唇上细髭。家藏《大元炼真经》。在西江一带以定神符闻名,其余符咒尽无效验。贪财怕死但良心未泯,关键时刻能做正确选择。获得灵龙镇煞钉后多次被妖怪追杀,镇煞钉护主杀犯查兽,误打误撞成为"高手"。',
         appearance='三十一二年纪,甚是瘦弱,着一袭半旧的黄布直裰,长相颇清雅,唇上留两条细细的髭胡。被吓时面色白极,可演丑角不抹粉。',
         personality_tags=['贪财','怕死','机敏','有底线','爱吹牛','嘴硬心软'],
         personality_detail='嘴上天花乱坠实则胆子极小。骗人时从容不迫,遇险时腿软如面条。但关键时刻良心未泯——从墓室取钉后终究送回封镇。反复劝慰自己"九两银子挣得不亏心",实则心中有愧。对妻子赵氏温柔,对陌生人满口大话,被揭穿时讪讪。内心独白多,患得患失。',
         abilities='[{"name":"定神符","level":"有效(唯一)","description":"画符饮后清气贯百会,眼目清明精神健旺。胡不为唯一有效的符咒。"},{"name":"灵龙镇煞钉","level":"持有(被动护主)","description":"从梧桐村墓室拾取,灵龙物化护主杀犯查兽。对妖物有效,对人无效。"},{"name":"风水堪舆","level":"忽悠级","description":"嘴头功夫,最多瞟过《阴宅注经》,知癸水阴煞等词。实战底子比纸薄。"}]',
         weaknesses=['贪财','怕死','爱吹牛','对妖怪毫无抵抗之力','除定神符外符咒尽无效','驴子脾气比他大'],
         surface_goal='挣钱糊口,安全回家', deep_need='活下去,不做亏心事', internal_conflict='贪财vs良心', fear='妖怪、厉鬼、黑暗中独自一人',
         first_appearance=1),
    dict(name='老乌头', importance='major', backstory='乌家第32代守墓人,本名乌承光。四百年前乌家先人封镇寒妇于奈何谷,世代守护。五十六年前村中大火,烧去半片脸和一只手臂,父母双亡,道术典藏尽毁。一生孤独坚守,残废丑陋无人肯嫁,乌家一脉单传到他断绝。',
         appearance='半边脸上扭曲突结,连到额头上方,毛发尽无,疤痕板结光润。左手齐肘断掉,只余一副空荡荡的袖子。满头苍苍,委琐且恐怖的老头。',
         personality_tags=['坚守','孤独','忠义','刚烈','丑陋'],
         personality_detail='沉默寡言,一生坚守家族使命。孤独而执着,明知力不从心仍不放弃。为守护梧桐村可以怒斥退缩的村民,一张丑脸颇有狰狞之态。身世凄惨却恪守家道,数十年来无人知其功绩。',
         abilities='[{"name":"镇守巡查","level":"仅余巡查","description":"每年六时节气入谷烧纸钱洒狗血,填补镇煞灵气。道术已失传。"}]',
         weaknesses=['残废','孤独','无道术传承','一脉单传断绝'],
         surface_goal='守住奈何谷封印', deep_need='完成家族四百年使命', internal_conflict='力不从心vs不能放弃', fear='寒妇脱困涂炭生灵',
         first_appearance=1),
    dict(name='蔺得岷', importance='major', backstory='严台山大师兄,掌教之子。其弟六年前与人斗法被打成重伤,被人夺了一魄,至今神智不清。奉命追杀四百年犯查兽取还丹救弟。追查两年,从黔南一路追至梧桐村附近。',
         appearance='面如重枣的长须老者,剑眉朗目,颇有威严。年纪已不轻,声音苍老。',
         personality_tags=['威严','正统','好面子','老当益壮'],
         personality_detail='正统名门大师兄,爱面子,但遇事能拿主意。对门派声誉看得极重。习术法多年,临战经验丰富。使用通路符、御土符(泥臂/偃月刀/土枪)等法术。被蛀木妖偷袭受伤后仍能反击,老当益壮。对青叶门心怀忌惮。',
         abilities='[{"name":"通路符","level":"熟练","description":"持剑引路,藤萝树木退避让路。一张符支持半柱香。"},{"name":"御土符","level":"熟练","description":"操控泥土凝成手臂、偃月刀、土枪等武器攻击。"},{"name":"天周盘","level":"熟练","description":"形如鸡子的乌黑之物,可追查妖气确定妖物位置。"},{"name":"长剑术","level":"中等","description":"持剑战斗,能斩断三人合抱的巨木。"}]',
         weaknesses=['好面子','实力不及青叶门','被蛀木妖偷袭受伤','誓言约束不能取还丹'],
         surface_goal='捉拿犯查兽取还丹救弟', deep_need='维护严台山声誉与家族', internal_conflict='实力vs面子', fear='在师弟面前丢脸,弟弟不治',
         first_appearance=2),
    dict(name='赵芙南', importance='major', backstory='青叶门弟子,赵姑娘。白衣竹笛,声音稚嫩温柔如黄莺出谷。奉门主叶蘅之命追回逃出的犯查兽(门主称其为"宠物")。实际只想要还丹。感念胡不为好心之举,吹《星沉碧落》安神,留书赠还丹。',
         appearance='年轻女子,白衣,裙幅低垂,长袖翩翩,由风而动。仙姿妙态,直如凌波神女。夜色里看不清面目,人如其音则清丽非常。',
         personality_tags=['娇俏','锋芒','洒脱','心细','善良'],
         personality_detail='说话稚嫩温柔如黄莺,但暗藏锋芒。好整以暇,不急不躁。用反问和比喻讥嘲对手。竹镖投掷精准如斯,劲力角度掌握可惊可叹。心思缜密,看破蔺得岷的诡计。感念胡不为本心不坏,吹曲安神并赠还丹留书。',
         abilities='[{"name":"竹笛术","level":"不明(极高)","description":"传讯竹笛+安神曲《星沉碧落》。可抚神定惊。"},{"name":"竹镖术","level":"极高","description":"六枝碧绿竹镖,投掷精准,可擦过人体不伤,劲力控制如神。"},{"name":"轻功","level":"极高","description":"踏枝而行,比地上奔跑快得多。裙裾展开如雪白大蘑菇。"}]',
         weaknesses=['自负','青叶门护短'],
         surface_goal='夺取犯查还丹', deep_need='完成门主任务', internal_conflict='玩闹vs认真', fear='无',
         first_appearance=2),
    dict(name='顾有全', importance='minor', backstory='严台山五师弟。粗豪暴躁,虬须如铁。名为有全,行事全不顾。',
         appearance='长相粗豪,虬须如铁,一看就知道缺心眼。',
         personality_tags=['暴躁','莽撞','直爽','缺心眼'],
         personality_detail='性格极为暴躁,动辄骂人。但对大师兄敬畏,不敢放肆。好面子,摔了几跤也不肯示弱。被十一师弟讥笑就暴怒。',
         abilities='[]', weaknesses=['莽撞','缺心眼','好面子'],
         surface_goal='帮大师兄捉犯查', deep_need='尽师弟本分', internal_conflict='无', fear='大师兄发怒',
         first_appearance=2),
    dict(name='时闻盂', importance='minor', backstory='三水村瘦小青年。韩之敬婚宴上醉酒,牛泪水染眼后可见异物——堂中站满已故先人魂灵。自此做了神汉,专为周乡村民沟通阴阳。',
         appearance='体格瘦小的青年,一双黝黑的细爪子如抖筛子般。',
         personality_tags=['胆小','好面子','机缘'],
         personality_detail='村中普通青年,好面子能喝酒。牛泪水意外染眼后可见阴阳,从此人生改变。',
         abilities='[{"name":"阴阳眼","level":"天生(不可逆)","description":"牛泪水染眼后可见魂灵异物,再也返不回从前。"}]',
         weaknesses=['胆小','好面子'],
         surface_goal='适应阴阳眼', deep_need='找到人生方向', internal_conflict='普通人vs通灵者', fear='看到不该看的东西',
         first_appearance=0),
    dict(name='韩之敬', importance='minor', backstory='三水村韩诤次子,与犀香新婚。婚宴上被灌酒至吐八次。',
         appearance='普通村乡青年。', personality_tags=['老实','疲惫'],
         personality_detail='老实人,被灌酒也不好逐客,面上挂假笑勉力应付。',
         abilities='[]', weaknesses=['不善拒绝'],
         surface_goal='完成婚宴', deep_need='正常生活', internal_conflict='无', fear='无', first_appearance=0),
    dict(name='犀香', importance='minor', backstory='孙寡妇之女,韩之敬之妻。眉眼清秀,体段玲珑,八分人才。',
         appearance='眉眼清秀,体段玲珑,算得八分人才。', personality_tags=['朴实'],
         personality_detail='村乡寡妇孤女,自小衣食粗砺兼农事沉重。女十八而大变,长得清秀。',
         abilities='[]', weaknesses=['无'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=0),
    dict(name='韩诤', importance='minor', backstory='三水村韩之敬之父,年迈体衰。婚宴上被灌醉,从中午睡到夜深。',
         appearance='年迈老人。', personality_tags=['和善'],
         personality_detail='满脸堆欢,对帮衬的村民心存感激。年岁已高,不胜酒力。',
         abilities='[]', weaknesses=['年迈'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=0),
    dict(name='吴中', importance='minor', backstory='三水村青年,韩之敬玩伴。性情最是外放。',
         appearance='着青色短衫的小伙子。', personality_tags=['外放','好客'],
         personality_detail='性情最是外放,当先答话,热情好客。好意献策(狐狸皮袄做媳妇),引发哄笑。',
         abilities='[]', weaknesses=['无'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=0),
    dict(name='刘时喜', importance='minor', backstory='三水村打更人。婚宴当晚在门口来回好几遭讨水酒喝。',
         appearance='打更人。', personality_tags=['勤恳'],
         personality_detail='尽责打更,"天干物燥——小心火烛——！"是他夜夜喊的号子。',
         abilities='[]', weaknesses=['无'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=0),
    dict(name='吴若圃', importance='minor', backstory='梧桐村教书先生。提议去谷场看风水,对入奈何谷有疑虑。',
         appearance='教书先生。', personality_tags=['谨慎','犹豫'],
         personality_detail='谨慎之人,对老乌头的提议有疑虑但无言以对,只低头退到一旁看着村长。',
         abilities='[]', weaknesses=['无'], surface_goal='无', deep_need='无', internal_conflict='无', fear='奈何谷', first_appearance=1),
    dict(name='孙甲', importance='minor', backstory='下林村贩马者。身材高大,二十四五年纪,性情温和。求子心切,赠胡不为枣红骏马换求子秘方。胡不为授《床第述密》求子术+定神符(谎称求子咒)。',
         appearance='身材高大,神情温和,二十四五年纪。', personality_tags=['温和','求子心切','恭敬'],
         personality_detail='求子心切,与妻容氏结缡近十年无子。遍问医药无效,请过几位风水先生迁葬阴宅也无后效。听闻胡不为异事,认定是有道之士,跪求相助。对胡不为极为恭敬。',
         abilities='[]', weaknesses=['无子','信风水'], surface_goal='求子', deep_need='传宗接代', internal_conflict='无', fear='无后', first_appearance=3),
    dict(name='于老头', importance='minor', backstory='下林村老夫妇,年老无儿无女。收留胡不为借宿,殷勤款待。胡不为留定神符相赠。',
         appearance='年老夫妇。', personality_tags=['善良','好客','见闻广'],
         personality_detail='年老来膝下无儿无女,老两口互相扶持度日。极好客,对胡不为殷殷惜别。年纪大了倒有些见闻,说起刀圭炼丹约略通点门道。',
         abilities='[]', weaknesses=['年老无依'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=3),
    dict(name='赵氏', importance='minor', backstory='胡不为妻子,定马村。性格温柔,任着胡不为好吃懒做。爱惜牲口,从不鞭打驴子。',
         appearance='未出场(被提及)。', personality_tags=['温柔','贤惠'],
         personality_detail='性格温柔,任着丈夫。爱惜牲口,买来的驴子从不鞭打,把它惯得不成话。',
         abilities='[]', weaknesses=['无'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=2),
    dict(name='二师兄', importance='minor', backstory='严台山二师兄。面皮白净的中年人,身材不高大,眼神凌厉异常。性情冷静。',
         appearance='面皮白净的中年人,身材不高大,眼神凌厉。', personality_tags=['冷静','凌厉','稳重'],
         personality_detail='性情冷静,面上看不出表情。在同门中颇有威望,一声"噤声"众人便都沉默。功力比大师兄差许多但比师弟快,独自跑在中段。',
         abilities='[]', weaknesses=['无'], surface_goal='帮大师兄', deep_need='无', internal_conflict='无', fear='无', first_appearance=2),
    dict(name='十一师弟', importance='minor', backstory='严台山十一师弟。瘦小青年,爱笑,嘴贱。',
         appearance='瘦小青年。', personality_tags=['嘴贱','爱笑','机灵'],
         personality_detail='满眼笑意看着顾有全折腾,若非师兄在场只怕早出言笑话。笑五师兄"扑住母兔子"艳福不浅。被顾有全怒吼也不怕。',
         abilities='[]', weaknesses=['嘴贱'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=2),
    dict(name='叶蘅', importance='minor', backstory='青叶门门主。专精控水之法,传说"腾海凝冰刃,霜珠捻栊帘"——可聚沧海之水凝成巨大冰刃,用霜尘串成千万颗帘珠。极为护短。养犯查兽为"宠物"。',
         appearance='未出场(被提及)。', personality_tags=['护短','实力深不可测'],
         personality_detail='江湖上人人皆知叶蘅极为护短,若伤她弟子,只怕水淹严台山。控水之法已达到极致。',
         abilities='[{"name":"控水术","level":"极致","description":"聚沧海凝冰刃,霜尘串帘珠。"}]', weaknesses=['护短'],
         surface_goal='收回犯查兽', deep_need='无', internal_conflict='无', fear='无', first_appearance=2),
    dict(name='彦青', importance='minor', backstory='某邪教弟子。与堂主任务失败后欲回教请罪,被堂主灭口。',
         appearance='未详细描写。', personality_tags=['犹豫','念家'],
         personality_detail='舍不得家中娇妻幼子,不愿逃往苗疆。想回教请罪,被堂主杀了灭口。',
         abilities='[]', weaknesses=['无'], surface_goal='回教请罪', deep_need='保全家人', internal_conflict='无', fear='教主罚责', first_appearance=2),
    dict(name='容氏', importance='minor', backstory='孙甲之妻。端庄贤惠。与孙甲结缡近十年无子。',
         appearance='未出场(被提及)。', personality_tags=['端庄','贤惠'],
         personality_detail='端庄贤惠,对丈夫忙于商事无怨言。',
         abilities='[]', weaknesses=['无子'], surface_goal='无', deep_need='无', internal_conflict='无', fear='无', first_appearance=3),
]

for c in chars:
    oid = f"role:{c['name']}"
    st.add_entity(Entity(oid, 'character', c['name'], traits={'backstory': c.get('backstory',''), 'personality_tags': c.get('personality_tags',[])}))
    st._db.query("UPDATE type::record('character', $n) SET importance=$i, appearance=$ap, personality_detail=$pd, abilities=$ab, weaknesses=$wk, surface_goal=$sg, deep_need=$dn, internal_conflict=$ic, fear=$fr, first_appearance=$fa",
                 {'n': c['name'], 'i': c.get('importance'), 'ap': c.get('appearance'), 'pd': c.get('personality_detail'),
                  'ab': c.get('abilities'), 'wk': c.get('weaknesses',[]), 'sg': c.get('surface_goal'),
                  'dn': c.get('deep_need'), 'ic': c.get('internal_conflict'), 'fr': c.get('fear'),
                  'fa': c.get('first_appearance')})
print(f"角色: {len(chars)}个", flush=True)

# ═══ 地点(10个) ═══
places = [
    dict(name='三水村', desc='韩之敬家乡,普通村乡。婚宴发生地。'),
    dict(name='梧桐村', desc='一姓村,百十来户吴姓。地偏中原西北,湿寒尤重。宗祠飞檐叠角金碧辉煌,鹤立鸡群。村中央宗族祠堂。'),
    dict(name='奈何谷', desc='梧桐村西八里。两脉峰峦南北汇合却不相接,中间峡谷宽六驾车马,长四里。峡高而峭,藤葛缠绕。数十年来猎户樵夫路过多有殒命,传为妖魔聚集之地。月圆时青濛雾气升腾,妖影幢幢。悬壁凿室藏墓室。'),
    dict(name='碧玉潭', desc='梧桐村西口。地河破岩堆积而成,水质甘美清冽。薄烟聚笼,如翡翠般碧水悠悠转旋。接靠岩壁处有泉汩汩涌动。岸草润若露染。'),
    dict(name='谷场', desc='梧桐村西北。方圆数十丈平平展展的黄土地,夯得结实。村民晾晒谷物之场。'),
    dict(name='定马村', desc='胡不为家乡。距梧桐村四百里。'),
    dict(name='下林村', desc='距梧桐村不远。四五十户人家,百来人口。原是荒凉之地,二百多年前逃荒者到此落脚。村口有守护神兽像(乌木雕,两翅龙面狮身)。'),
    dict(name='严台山', desc='蔺得岷所在门派驻地。门人数百,民间和江湖颇有威望。'),
    dict(name='汾州', desc='当朝重镇。大道畅通,商贾旅者如云。胡不为归家途经之地。'),
    dict(name='墓室', desc='奈何谷腹地,悬壁凿室。方圆一丈有余,一人半高。室壁有斩劈痕迹,朱砂符咒从顶到地。棺椁居中,黑狗血涂染墨黑,柚木制。三百六十枚灵龙镇煞钉围太极阵。十二个镇墓兽俑,四角青铜照妖镜。'),
]
for p in places:
    st._db.query("CREATE type::record('place', $n) SET name=$n", {'n': p['name']})
print(f"地点: {len(places)}个", flush=True)

# ═══ 世界规则(8条) ═══
rules = [
    dict(name='灵龙镇煞钉', cat='magic', src='阳铜熔炼七日+金鼎培气七日+黑狗血浸染七日+刻井字文狱+镶镂盘钉灵龙,共七七四十九天', cost='三百六十枚围太极阵可封死大罗神仙', lims=['造法费心费力,合四时阴阳','对人无效,只对妖物有效'], excs=['混元体可三修(传说)'], scope='global', ch=1),
    dict(name='牛泪水通阴阳', cat='magic', src='阴日阴时的牛泪水染眼', cost=None, lims=['一旦开了阴阳眼不可逆转'], excs=[], scope='global', ch=0),
    dict(name='犯查兽还丹', cat='magic', src='天地生养独个儿修炼成形', cost='四百年犯查内丹可聚魂活死人(还丹),五百年后内丹只能助功力', lims=['还丹被夺则妖兽死','四百年犯查最是难求'], excs=[], scope='global', ch=2),
    dict(name='定神符', cat='magic', src='《大元炼真经》中习画', cost=None, lims=['胡不为唯一有效的符咒,其余符咒尽无效验'], excs=[], scope='regional', ch=1),
    dict(name='守护神兽像', cat='magic', src='下林村村口乌木雕像,二百多年前立', cost='守护兽灵验,现身击退怪鸟群和九头鸟', lims=['能惑乱精神,令人心驰神迷想跪下痛哭','灵龙镇煞钉可破其惑乱'], excs=[], scope='regional', ch=3),
    dict(name='御土符', cat='magic', src='严台山术法', cost='操控泥土凝成武器(手臂/偃月刀/土枪)', lims=['需念咒引动,消耗灵力'], excs=[], scope='global', ch=5),
    dict(name='通路符', cat='magic', src='严台山术法', cost='所指处藤萝树木退避让路', lims=['一张符支持半柱香,林木密处消耗更快'], excs=[], scope='global', ch=5),
    dict(name='北斗借力', cat='magic', src='符纸烧后和茶饮,念咒引动', cost='借临近鬼怪之力,龙象巨力', lims=['非真引天上七星之力'], excs=[], scope='global', ch=6),
]
for r in rules:
    st.add_world_rule(r['name'], r['cat'], source=r['src'], cost=r.get('cost'), limitations=r.get('lims',[]), exceptions=r.get('excs',[]), scope=r.get('scope','global'), established_chapter=r.get('ch'))
print(f"世界规则: {len(rules)}条", flush=True)

# ═══ 势力(6个) ═══
factions = [
    dict(name='严台山', ideo='捉妖除魔,维护正统', status='active', leader='蔺得岷(大师兄)', pub='名门正派,门人数百', priv='掌教之子被人夺魄,追杀犯查取还丹救子', ch=2),
    dict(name='青叶门', ideo='养妖兽取还丹', status='active', leader='叶蘅(门主)', pub='仙子门派,竹笛为号,控水绝技', priv='掠夺妖兽内丹,门主养犯查为宠物,极为护短', ch=2),
    dict(name='乌家', ideo='世代镇守梧桐村奈何谷墓室', status='dormant', leader='老乌头(末代)', pub='道术世家', priv='火灾后道术失传,仅余巡查使命,一脉单传断绝', ch=1),
    dict(name='蜀山', ideo='术法大教', status='active', leader=None, pub='术法大教之一', priv=None, ch=5),
    dict(name='仙都观', ideo='术法大教', status='active', leader=None, pub='术法大教之一', priv=None, ch=5),
    dict(name='某邪教', ideo='不明', status='active', leader='堂主', pub='不明', priv='任务失败杀人灭口,教主手段严酷', ch=2),
]
for f in factions:
    st.add_faction(f['name'], ideology=f['ideo'], status=f['status'], leader=f.get('leader'), public_face=f.get('pub'), private_operation=f.get('priv'), first_mention_chapter=f.get('ch'))
print(f"势力: {len(factions)}个", flush=True)

# ═══ 物品(12件) ═══
items = [
    dict(name='灵龙镇煞钉', cat='法器', desc='铜钉色成赤黑,圆头方身,三指长。钉身镶镇煞灵龙,钉帽刻井字铭文,朱砂填染。阳铜黑狗血七七四十九天炼成。对妖物有效,灵龙物化护主。', owner='role:胡不为', state='active', props=['辟邪圣物','镇魂锁煞','只对妖物有效','灵龙物化克敌']),
    dict(name='《大元炼真经》', cat='典籍', desc='胡不为家藏古籍,记载灵龙镇煞钉熔造法、定神符画法等。胡不为从中学了各种符咒,但只有定神符有效。', owner='role:胡不为', state='active', props=['记载法器炼造','记载符咒画法']),
    dict(name='天周盘', cat='法器', desc='形如鸡子的乌黑之物,可追查妖气,配合算法确定妖物位置。蔺得岷使用。', owner='role:蔺得岷', state='active', props=['探测妖物方位']),
    dict(name='竹笛', cat='法器', desc='赵芙南所吹。传讯竹笛+安神曲《星沉碧落》。清脆如玉落银盘。', owner='role:赵芙南', state='active', props=['青叶门信物','安神抚惊']),
    dict(name='定神符', cat='符咒', desc='胡从《大元炼真经》习画。符水饮后清气由百会穴贯入,眼目清明精神健旺。胡唯一有效的符。', owner='role:胡不为', state='active', props=['提神醒脑','唯一有效符咒']),
    dict(name='《床第述密》', cat='典籍', desc='合欢书典,记述男女之道、交接之法、求子求女等篇章。胡不为少年时看过,记力甚佳。', owner='role:胡不为', state='active', props=['求子秘术']),
    dict(name='守护神兽像', cat='法器', desc='下林村村口乌木雕像。两翅,宽吻暴牙,龙面狮身。箕踞作势,顾盼生威。底座刻"养我供我""得佑得福"。能惑乱精神,灵验时现身护村。', owner=None, state='active', props=['守护村庄','惑乱精神','现身击退怪鸟群和九头鸟']),
    dict(name='桃木剑', cat='法器', desc='胡不为作法用具。开坛做法时手持,脚踏七星步。', owner='role:胡不为', state='active', props=['作法道具']),
    dict(name='镇墓兽俑', cat='法器', desc='墓室中十二个,青铜铸就。半人高,头上长角,胁生双翅,凸睛暴牙,面目狞恶。大异于民间所见。', owner=None, state='active', props=['镇墓']),
    dict(name='青铜照妖镜', cat='法器', desc='墓室四角,人面大小。幽光隐然,齐齐对准棺木。', owner=None, state='active', props=['照妖']),
    dict(name='还丹', cat='修炼产物', desc='犯查兽体内修炼四百年而成的内丹。指头大小,色成橙黄。有聚魂活命之功,可肉白骨活死人。人间至宝。', owner='role:胡不为', state='active', props=['聚魂活命','肉白骨活死人','人间至宝','不可外示']),
    dict(name='夜金砂', cat='药材', desc='深山食人巨蝠所出。服一粒可治盲眼,极有神效。胖和尚赌胜的彩头。', owner=None, state='active', props=['治盲眼']),
]
for i in items:
    st.add_item(i['name'], category=i['cat'], description=i['desc'], current_owner=i.get('owner'), symbolic_state=i['state'], special_properties=i['props'])
print(f"物品: {len(items)}件", flush=True)

# ═══ 术语(15条) ═══
terms = [
    dict(name='寒妇', cat='妖物', defn='棺中所镇厉鬼。会吃人。乌家世代镇守。老乌头称之为"寒妇"。', aliases=['厉鬼']),
    dict(name='罗天九头鬼', cat='妖物', defn='蛇身人首,九颗头颅,食人精血吸收魂魄。胡不为信口编造,并非棺中实际所镇。', aliases=['九头鬼']),
    dict(name='犯查', cat='妖兽', defn='天地生养独个儿修炼成形,体内有还丹。修炼四百年。山羊大小,褐黄皮毛白旋斑,阔嘴黄牙,青色小眼,黑爪。', aliases=['犯查兽','小乖']),
    dict(name='还丹', cat='修炼产物', defn='四百年犯查体内丹。指头大小橙黄。聚魂活命,肉白骨活死人。五百年后只能助功力。', aliases=['内丹']),
    dict(name='画井为狱', cat='道家术法', defn='井字铭文用于镇魂锁煞。灵龙镇煞钉钉帽刻井字,朱砂填染。', aliases=['镇煞']),
    dict(name='九朵莲花开', cat='门派切口', defn='严台山门派暗号上半句,对答下半句"三香供严台"。', aliases=['三香供严台']),
    dict(name='青青竹叶悠悠流水', cat='门派切口', defn='青叶门暗号。赵芙南以此自报家门。', aliases=[]),
    dict(name='玄青大圣', cat='妖物', defn='被赵师爷灵符召唤的蛇狼妖。狼头蛇身,四条,可从地下袭击。被灵龙镇煞钉全部击杀。', aliases=['蛇狼']),
    dict(name='九头鸟', cat='妖物', defn='不祥之物。身如飞梭,九首,叫如婴儿。传言每见必遇洪涝大旱或瘟疫。攻击下林村被守护兽击退。', aliases=[]),
    dict(name='人面怪鸟', cat='妖物', defn='宽脸深目如人面,羽色乌黑,家犬大小。身后长蛇状尾巴。群袭下林村。', aliases=[]),
    dict(name='蛀木妖', cat='妖物', defn='形如木桩的浅黄色怪物,高可及人,九足如拉长的章鱼。蛀木为屋藏其中修炼。喷腥臭黏液腐蚀衣物。被蔺得岷御土法术击杀。', aliases=[]),
    dict(name='定神符', cat='符咒', defn='胡不为从《大元炼真经》习画。饮后清气贯百会,眼目清明。胡唯一有效的符。', aliases=[]),
    dict(name='般若龙象力', cat='武功', defn='胖和尚所用力拔山河功夫。气劲转换之妙,丹田守重之法。右臂通红如烫,暴然发力。', aliases=[]),
    dict(name='天雷地火阵法', cat='道家术法', defn='胡不为声称用来加固封印的阵法(实则骗人)。', aliases=[]),
    dict(name='黑狗血', cat='法术材料', defn='镇煞灵气填补材料。老乌头每年六时节气入谷烧纸钱洒狗血。墓室棺椁用黑狗血涂染。', aliases=[]),
]
for t in terms:
    st.add_term(t['name'], category=t['cat'], definition=t['defn'], aliases=t.get('aliases',[]))
print(f"术语: {len(terms)}条", flush=True)

# ═══ 事件(20个) ═══
events = [
    Event('ev:001','婚宴',story_time=0,participants={'WITNESS':'role:时闻盂'},location='place:三水村',motivated_by_goal='韩之敬大婚'),
    Event('ev:002','牛泪染眼',story_time=0,participants={'SUBJ':'role:时闻盂'},effects=['fact:f001'],location='place:三水村',motivated_by_goal='时闻盂获阴阳眼'),
    Event('ev:003','怪墓发现',story_time=1,participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},effects=['fact:f002'],location='place:墓室',motivated_by_goal='查看梧桐村风水'),
    Event('ev:004','拾取镇煞钉',story_time=1,participants={'SUBJ':'role:胡不为'},location='place:墓室',motivated_by_goal='胡不为偷取灵龙镇煞钉'),
    Event('ev:005','开坛做法',story_time=1,participants={'SUBJ':'role:胡不为','WITNESS':'role:老乌头'},location='place:梧桐村',motivated_by_goal='胡不为假装降妖骗钱'),
    Event('ev:006','逃离梧桐村',story_time=1,participants={'SUBJ':'role:胡不为'},location='place:梧桐村',motivated_by_goal='胡不为携钉逃跑'),
    Event('ev:007','遇严台山众人',story_time=2,participants={'SUBJ':'role:胡不为','WITNESS':'role:蔺得岷'},location='place:定马村',motivated_by_goal='返家途中遇严台山捉犯查'),
    Event('ev:008','蔺赵对峙',story_time=2,participants={'SUBJ':'role:蔺得岷','OBJ':'role:赵芙南','WITNESS':'role:胡不为'},location='place:定马村',motivated_by_goal='蔺得岷与赵芙南争犯查兽'),
    Event('ev:009','犯查逃走',story_time=2,participants={},location='place:定马村',motivated_by_goal='地震中犯查兽趁乱逃脱'),
    Event('ev:010','夜逃听杀人',story_time=2,participants={'SUBJ':'role:胡不为'},location='place:定马村',motivated_by_goal='胡不为夜逃听到邪教堂主杀彦青'),
    Event('ev:011','下林村借宿',story_time=3,participants={'SUBJ':'role:胡不为','WITNESS':'role:于老头'},location='place:下林村',motivated_by_goal='借宿休息'),
    Event('ev:012','神兽像前异象',story_time=3,participants={'SUBJ':'role:胡不为'},location='place:下林村',motivated_by_goal='镇煞钉在守护神兽像前发光震动'),
    Event('ev:013','孙甲求子',story_time=3,participants={'SUBJ':'role:胡不为','OBJ':'role:孙甲'},location='place:下林村',motivated_by_goal='胡不为授求子术换马'),
    Event('ev:014','怪鸟袭村',story_time=3,participants={'SUBJ':'role:胡不为'},location='place:下林村',motivated_by_goal='人面怪鸟群袭下林村,守护兽现身击退'),
    Event('ev:015','九头鸟来袭',story_time=3,participants={},location='place:下林村',motivated_by_goal='九头鸟攻击,守护兽掷戟击退'),
    Event('ev:016','村人神秘死亡',story_time=3,participants={},location='place:下林村',motivated_by_goal='铁匠和卖油郎面带微笑而死,臂上有"供我养我""得佑得福"'),
    Event('ev:017','蔺赵追犯查',story_time=4,participants={'SUBJ':'role:蔺得岷','OBJ':'role:赵芙南'},location='place:定马村',motivated_by_goal='追杀犯查兽两天一夜'),
    Event('ev:018','蔺得岷战蛀木妖',story_time=5,participants={'SUBJ':'role:蔺得岷','WITNESS':'role:赵芙南'},location='place:定马村',motivated_by_goal='蔺得岷被蛀木妖偷袭,赵芙南救援,御土法术击杀'),
    Event('ev:019','镇煞钉杀犯查',story_time=5,participants={'SUBJ':'role:胡不为'},effects=['fact:f003'],location='place:定马村',motivated_by_goal='灵龙镇煞钉护主,击杀犯查兽'),
    Event('ev:020','赵芙南赠还丹',story_time=5,participants={'SUBJ':'role:赵芙南','OBJ':'role:胡不为'},location='place:定马村',motivated_by_goal='赵芙南吹安神曲,留书赠还丹'),
]
for ev in events:
    st.add_event(ev)
print(f"事件: {len(events)}个", flush=True)

# ═══ 事实/命题(15条) ═══
facts = [
    ('fact:f001','role:时闻盂','能力','牛泪水染眼后可见阴阳,不可逆',0,True),
    ('fact:f002','place:墓室','结构','三百六十枚灵龙镇煞钉围太极阵,十二镇墓兽俑,四照妖镜,朱砂符咒',1,True),
    ('fact:f003','role:胡不为','能力','灵龙镇煞钉护主物化,击杀犯查兽',5,False),
    ('fact:f004','role:胡不为','身份','风水先生/江湖骗子,定马村人',1,False),
    ('fact:f005','role:胡不为','藏物','家藏《大元炼真经》,记载法器炼造与符咒画法',1,True),
    ('fact:f006','role:老乌头','身份','乌家第32代守墓人,本名乌承光',1,False),
    ('fact:f007','role:老乌头','使命','世代镇守奈何谷墓室,每年六时节气入谷烧纸洒血',1,False),
    ('fact:f008','place:奈何谷','特性','妖魔聚集之地,月圆时青濛雾气升腾',1,True),
    ('fact:f009','role:蔺得岷','使命','奉命追杀四百年犯查兽取还丹救弟',2,False),
    ('fact:f010','role:赵芙南','身份','青叶门弟子,奉门主叶蘅之命追回犯查',2,False),
    ('fact:f011','term:犯查','特性','天地生养修炼四百年,体内有还丹',2,False),
    ('fact:f012','role:叶蘅','能力','控水术极致:腾海凝冰刃,霜珠捻栊帘',2,False),
    ('fact:f013','place:下林村','守护','守护神兽像灵验,现身击退怪鸟群和九头鸟',3,False),
    ('fact:f014','place:下林村','异象','村人神秘死亡,臂上刻"供我养我""得佑得福"',3,True),
    ('fact:f015','role:胡不为','获得','赵芙南留书赠还丹,嘱咐重重包裹不可外示',5,True),
]
for fid, eid, attr, val, ch, secret in facts:
    st.add_fact(Fact(fid, eid, attr, val, valid_from=ch, secret=secret))
    st.semantic_index(fid, val)
print(f"事实: {len(facts)}条", flush=True)

# ═══ 角色关系(15条) ═══
relations = [
    ('role:韩之敬','role:犀香','夫妻',0),
    ('role:韩之敬','role:时闻盂','同门',0),
    ('role:韩之敬','role:吴中','同门',0),
    ('role:韩诤','role:韩之敬','父子',0),
    ('role:胡不为','role:老乌头','熟人',1),
    ('role:胡不为','role:赵氏','夫妻',2),
    ('role:蔺得岷','role:顾有全','同门',2),
    ('role:蔺得岷','role:二师兄','同门',2),
    ('role:蔺得岷','role:十一师弟','同门',2),
    ('role:蔺得岷','role:赵芙南','利益对立',2),
    ('role:赵芙南','role:叶蘅','师徒',2),
    ('role:胡不为','role:蔺得岷','同行',2),
    ('role:胡不为','role:赵芙南','恩人',5),
    ('role:胡不为','role:孙甲','交易',3),
    ('role:胡不为','role:于老头','熟人',3),
]
for src, dst, rel, ch in relations:
    try: st.add_character_relation(src, dst, rel, since_chapter=ch)
    except Exception as e: print(f"  关系跳过: {src}-{dst}: {e}")
print(f"角色关系: {len(relations)}条", flush=True)

# ═══ 弧光(12条) ═══
states = [
    ('role:时闻盂',0,'ability','获阴阳眼','牛泪水意外染眼后可见异物——堂中站满已故先人魂灵','引子·奇遇'),
    ('role:胡不为',1,'ability','获灵龙镇煞钉','从奈何谷墓室拾取一枚跳出的钉子,收入怀中','引子·得物'),
    ('role:胡不为',1,'personality','恐惧与贪婪','发现墓室诡异后仓皇逃离,既贪财又怕死,反复劝慰自己','引子·抉择'),
    ('role:胡不为',3,'personality','名声渐起','在下林村神兽像前镇煞钉发光,被村民视为仙长','转折·名声'),
    ('role:胡不为',5,'composite','误杀犯查获还丹','灵龙镇煞钉护主击杀犯查兽,赵芙南留书赠还丹','转折·获宝'),
    ('role:胡不为',5,'personality','良心发现','被赵芙南安神曲抚慰后,获得还丹,开始有了保护他人的念头','转折·成长'),
    ('role:老乌头',1,'personality','希望与狂喜','终于请到风水师,引众人入奈何谷,以为梧桐村有救了','希望'),
    ('role:蔺得岷',2,'relation','与赵芙南对立','严台山与青叶门因犯查兽公开对立,互不退让','冲突'),
    ('role:蔺得岷',5,'ability','受伤','被蛀木妖偷袭,左臂皮开肉绽,被赵芙南救','挫折'),
    ('role:蔺得岷',5,'personality','誓言束缚','立誓不亲手杀犯查不可取还丹,犯查被胡不为所杀,还丹归胡','失去'),
    ('role:赵芙南',2,'personality','初登场','白衣坐于树梢,竹笛吹奏,嬉笑中暗藏锋芒','登场'),
    ('role:赵芙南',5,'relation','对胡不为改观','从轻视到感念,吹安神曲赠还丹留书','转折·善意'),
]
for cid, ch, ct, summary, trigger, arc in states:
    st.add_char_state(cid, ch, ct, summary, trigger_event=trigger, arc_phase=arc)
print(f"弧光: {len(states)}条", flush=True)

# ═══ VoiceProfile(3个) ═══
voices = [
    ('role:胡不为', dict(style_summary='说话啰嗦爱吹嘘,紧张时结巴。对陌生人满口大话,被揭穿时讪讪。内心独白多,患得患失。反复劝慰自己"九两银子挣得不亏心"。',
        tone_rules=[{'situation':'对陌生人','tone':'夸大其辞,避重就轻'},{'situation':'危险关头','tone':'语速加快,反复问怎么办,腿软如面条'},{'situation':'内心独白','tone':'患得患失,反复盘算'}],
        ooc_signals=[{'signal_id':'v1','description':'主动赞美或感谢他人','detection_method':'rule','severity':'high'},{'signal_id':'v2','description':'面对危险从容不迫','detection_method':'rule','severity':'high'}], version=1)),
    ('role:老乌头', dict(style_summary='说话简短有力,语气沉重。不解释多余。偶有悲凉自嘲。字字带着四百年的坚守。',
        tone_rules=[{'situation':'谈及使命','tone':'庄严沉重,不容置疑'},{'situation':'怒斥退缩者','tone':'大声,丑脸狰狞'}],
        ooc_signals=[{'signal_id':'v2','description':'轻松笑谈或说俏皮话','detection_method':'rule','severity':'high'}], version=1)),
    ('role:赵芙南', dict(style_summary='说话稚嫩温柔,含讥嘲。爱用反问和比喻。不急不躁,好整以暇。声音如黄莺出谷。',
        tone_rules=[{'situation':'谈判','tone':'轻松写意,暗藏杀机'},{'situation':'救人','tone':'温柔体贴'}],
        ooc_signals=[{'signal_id':'v3','description':'着急或慌乱','detection_method':'rule','severity':'high'}], version=1)),
]
for cid, vp in voices:
    st.set_voice_profile(cid, vp)
print(f"VoiceProfile: {len(voices)}个", flush=True)

# ═══ 伏笔(6条) ═══
promises = [
    dict(text='胡不为拾取灵龙镇煞钉,封印有缺口,寒妇随时可能脱困', setup_chapter=1, kind='promise'),
    dict(text='下林村村人臂上出现"供我养我""得佑得福",守护兽像的代价', setup_chapter=3, kind='promise'),
    dict(text='蔺得岷弟弟被人夺魄,需还丹救治', setup_chapter=2, kind='promise'),
    dict(text='胡不为获得还丹,赵芙南嘱咐不可外示', setup_chapter=5, kind='promise'),
    dict(text='邪教堂主杀彦青灭口,某邪教在暗中活动', setup_chapter=2, kind='red_herring'),
    dict(text='胡不为在梧桐村开坛做法后说"三五十年内必有人来除害"', setup_chapter=1, kind='promise'),
]
for p in promises:
    st._execute_write("CREATE promise SET text=$t, setup_chapter=$sc, status='open', kind=$k", {'t': p['text'], 'sc': p['setup_chapter'], 'k': p['kind']})
print(f"伏笔: {len(promises)}条", flush=True)

# ═══ 验证 ═══
comp = st.setting_completeness()
print(f"\n═══ 设定完整度: {comp['completeness_score']}/100 ═══", flush=True)
print(f"角色: {comp['total_chars']} | 规则: {comp['total_rules']} | 势力: {comp['total_factions']} | 地点: {comp['total_places']} | 事实: {comp['total_facts']}", flush=True)
print(f"物品: {len(st.list_items())} | 术语: {len(st.list_terms())} | 事件: {len(st._query('SELECT id FROM event'))} | 关系: {len(st.relations_at(99))} | 弧光: {len(st._query('SELECT id FROM char_state'))} | 伏笔: {len(st._query('SELECT id FROM promise'))}", flush=True)
if comp['missing_dimensions']: print(f"缺项: {comp['missing_dimensions']}", flush=True)
if comp['char_issues']: print(f"角色问题: {comp['char_issues']}", flush=True)
st.close()
print("\n阶段1完成。", flush=True)
