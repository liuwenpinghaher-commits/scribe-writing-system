"""Allowlist-only structural gates.

登记过的检查（新增须写理由）：
- play 非空/字数/禁旧标签行
- duty 人/事/账/禁揭/户口/线/上章钩
- contract quote 保真 + beats 场数 + 恰好一场 stages_choice
- deduce 五层+矿条数
- draft 非空/场面立住 + 相对戏的 8 字重复率 + 章边界词 + 明喻密度（字数不作完成）
- final 字数 + 章边界词 + 明喻密度 + 必须有冻结契约 + finalize 最后一公里
- gender_pronoun：上章末态/户口有性别的角色，名后短窗代词不得翻转（限知「他」落在女人名旁不算翻户口）
- state_quote：章末态每条人物/物件 quote 必须字面存在于冻稿
- simile_density：明喻密度（draft/final 已有；对白内与豁免原句不计入）
- pov_consistency：叙述人称沿用首章（剥对白后数「我」）
- dialogue_floor：糙稿对白行字数比 ≥15%
- syntax_tics：叙述层「不是A是B」/毒句式 ≥2 处在定稿拦住（对白不计；糙稿只记账不硬拦）
- chengse_filter：叙述层古白话套话 / 铜炉专名 / 空概括收尾（关旗不拦）
- duty.day：必须先立还在过的日子；开篇报身份/扔钩子/先宣布法会不过
- duty.work：嘴上要的和真正缺的必须打架；鉴定式人设/杯子余温/剖心不过
- duty.mask：假破真；先反面再破功；上来掏底牌不过
- duty.dist：远近；共情就把眼睛交给当场那个人；人还在办事时报年号/上课不过
- duty.cut：切；热过再冷，切在能听见看见的那一下；切在叹气/夜色深了不过
- duty.yin：因文；一行本事说不完；删了会塌的那截必须另写
- duty.flip：热闹像翻了、处境没翻不过；热闹不算翻
- duty.owed：上场 stay 这场还在过；只接 hook.quote 不算
- duty.heat_new：热闹不得和上场同一套
- duty.kind：这场进的是哪一种日子；只换节号 / 同一种不换谁闯进来 / 同场连写超两场不过
- duty.bill_move：账换持有人或换地；换气换丢人不过
- duty.altar：kind=开坛 必须看见交差钱把人按住；热闹当社戏信了；井/灯/墓还在；高人下山伏魔不过
- duty.feast：kind=酒宴 必须酒还不散、面子按桌、有人闯进来、嘴上贺而账还欠。不要字面「那一桌」
- duty.jail：kind=坐牢 必须先立进城/镇上找活路；官差收了东西改口；救人的人进了绳。清官断案、点名黑白不过。不要字面「六百两」
- duty.skip_year：kind=跳年 必须写成街上还在过的一天；补日历 / N年后说明书不过。不要字面六年、不要铜炉歌名
- duty.choice_name：kind=选择 必须还能跑、自己掉头、自己人把命名交出去；遇袭丢魂 / 当场打死不过。不要铜炉专名
- duty.xin：kind=心藏腹 必须锋藏进肚子、放过钉成可破的誓；小孩要心眼 / 铜炉专名不过
- duty.men：kind=天下第一门 必须铁律压场再抢场；开门就骑龙 / 铜炉专名不过
- duty.soul：kind=塑魂 必须醒了先叫从前的人；一醒就完整 / 铜炉专名不过
- duty.bie：kind=别亦难 必须钉认杀机不认亲；误伤劝停 / 铜炉专名不过
"""
from __future__ import annotations

import re
from typing import Any  # store is duck-typed; finalize_gate is optional last mile

from scribe3.playbook.quote import quote_in_play, quote_is_slice, snap_quote
from scribe3.playbook.schema import check_chapter_state_schema

_LABEL_HEAD = re.compile(
    r"^(时空|在场|本章要|选择|决断|代价)\s*[：:]",
)
_METAPHOR = re.compile(r"像|仿佛|似的")
_DIALOGUE = re.compile(r"[「『“\"].*?[」』”\"]", re.DOTALL)
_HE = re.compile(r"(?<![其])他(?![们人处日乡后])")
_SHE = re.compile(r"她(?![们])")
_QUOTE_LINE = re.compile(r"[「」『』“”\"']")
_STRAIGHT_Q = re.compile(r'"[^"]*"|\'[^\']*\'')
_NEG_LIKE = re.compile(r"并不像是|并不像|不像是|不像似|不像")
_RESIDUE = re.compile(r"不似乎|，又[烧冻碎压]|确实[一-龥]{2}[^的]|([一-龥])\1\1")
_SENT_SPLIT = re.compile(r"(?<=[。！？\n])")
# 开篇报身份 / 扔钩子 / 先宣布法会。对照.md 三、参照本二十二.1。
_OPENER_ANNOUNCE = re.compile(
    r"(我是|他是|她是).{0,16}(先生|掌门|神汉|风水|侦探|杀手|看井|管闸)"
    r"|报身份|开篇钩子|强钩子|先宣布法会|宣布法会"
    r"|黄金三章|三次失败"
)
_DAY_LIVED = re.compile(
    r"还在|还没|正在|尚未|仍有|排队|过秤|喝酒|喜酒|守夜|赶路|散不|过年|过节|井台|柜上|日子"
    r"|往家|回家|土路|巷口|窄巷|开坛|改运|交差|酬劳"
    r"|进城|进镇|镇上|城里|找活|活路|官差|绳"
    r"|街上|茶馆|店还|开张|早上|行人|还在过|还在唱|还在讲|还在走"
    r"|还能跑|还能走|掉头|交名|报名"
    r"|装疼|还疼|藏锋|自保|交符|誓"
    r"|铁律|朝廷|收成罪|官差还在|酒还没散"
    r"|破坛|屋顶|皮影|先叫|不认亲|布包|泥里|认杀机"
)
# 对照.md 三：办事不剖心。
_APPRAISAL_TELL = re.compile(
    r"鉴定式|杯子余温|维特|剖心|人设是|性格是|他是一个|她是一个"
)
# 对照.md 二：假破真。上来掏底牌不过。
_DUMP_TRUTH = re.compile(r"掏底牌|真相是|原来是|其实是|底牌就是|先把真意")
# 对照.md 一：远近。人还在办事时报年号/上课不过。
_LECTURE = re.compile(
    r"报年号|铺戒律|先上课|评点先|说书站到外头"
    r"|北宋[，,、]?\s*雍熙|雍熙三年|把天地比成"
)
_CAMERA_OUT = re.compile(r"说书|旁白|作者视角|站到外头")
# 参照本十七：切在手上那一下，不切在一段叹气上。
_SIGH_CUT = re.compile(
    r"叹气|叹了口气|一声叹息|夜色深了|他决定了|她决定了"
    r"|他付出了代价|她付出了代价|一段抒情|气氛收"
)
_CUT_SENSED = re.compile(
    r"一声|一响|响了|闷响|碎了|开了|停住|磕|砸|摔|撞|落地|堕地"
    r"|啪|嚓|喀喇|尖鸣|穿|门开|钉子|杯子|酒盅|碰杯"
    r"|捆|勒|绳|塞嘴|押走"
    r"|枯腐|枯了|铜子|帘"
    r"|报名|交名|掉头|封"
    r"|掠鬓|乱画|装疼"
    r"|扔下|屋顶|阵法|先叫|布包|泥里|倒下"
)
# 因文.md：一行本事说不完；删了那一截场会塌。
_ONE_LINE_OK = re.compile(r"一行就够|本事说完|过场即可|说明书")
# 参照本十七：热闹不算翻。热闹当场面也能过 = 还没这条。
_HEAT_AS_FLIP = re.compile(r"热闹就是翻|场面就算翻|热闹当翻|场面过了就算|热闹算翻")
_HEAT_ONLY = re.compile(r"热闹|场面过了|社戏完了|筵席散了|鼓掌过了")
_STAY_WORLD = re.compile(r"还|没|仍|停|在|日子|墓|路|安危|欠|信")
CLOCK_SPANS = frozenset({"scene", "day", "days"})
DAY_KINDS = frozenset({"酒宴", "赶路", "开坛", "坐牢", "跳年", "选择", "心藏腹", "天下第一门", "塑魂", "别亦难", "同场"})
_KIND_CHAPTER = re.compile(r"换节号|下一节|第[一二三四五六七八九十0-9]+章")
_KIND_WELL_QUEUE = re.compile(r"井台|排队|队尾|横担")
SAME_KIND_RUN_MAX = 2
# 章法开坛 / 怪墓批注：银子是交差钱；热闹当社戏；墓还在。不要高人下山伏魔。
_ALTAR_HERO = re.compile(r"高人下山|下山伏魔|高人伏魔|伏魔除害")
_ALTAR_FEE = re.compile(r"交差|酬劳|柜上账|油账|油罐|银子|赊")
_ALTAR_HEAT_BELIEVE = re.compile(r"信了|当社戏|社戏|鼓掌")
_ALTAR_STAY_WORLD = re.compile(r"井|灯|墓")
# 章法酒宴：酒还不散；面子按桌；有人闯进来；嘴上贺、账还欠。不要铜炉原词「那一桌」。
_FEAST_UNENDED = re.compile(r"还不散|还没散|散不掉|喜酒|还在喝")
_FEAST_FACE = re.compile(r"面子|桌上|敬酒|端杯|按在桌|酒盅|酒桌|桌旁|按住")
_FEAST_IN = re.compile(r"进来|坐进|闯|掀帘|掀棉|推门|带进|进了|进供")
_FEAST_CONGRATS = re.compile(r"贺|敬|道喜|喝完|来贺")
_FEAST_UNPAID = re.compile(r"欠|灯|账|回不去|当不成|坐不住")
# 章法坐牢 / 冤狱批注：进城找活路；官差收了东西改口；救人的人进绳。不要清官断案、不要点名黑白、不要字面六百两。
_JAIL_JUDGE = re.compile(r"清官断案|清官明断|明察私访|大义凛然|黑白")
# 因文·一沙一世界：削日历，补街上还在过的一天。不要 N年后说明书，不要字面六年，不要铜炉歌名。
_SKIP_CALENDAR = re.compile(
    r"\d+年后|[一二三四五六七八九十百]+年后|几年后|若干年后|六年后|六年"
    r"|补日历|跳过了六年|跳过六年|光阴荏苒|一晃就|转眼就|说明书|淳化"
)
_SKIP_STREET = re.compile(r"街上|茶馆|店还|开张|早上|还在过|行人|唱|还在讲|还在走")
_SKIP_SONG = re.compile(r"乱世铜炉|十八摸")
_SKIP_STILL = re.compile(r"还|欠|没")
# 因文·选择：还能跑；自己掉头；自己人交名。遇袭丢魂 / 当场打死不过。不要铜炉专名。
_CHOICE_AMBUSH = re.compile(r"遇袭丢魂|中暗器|当场打死|打死了|一击毙")
_CHOICE_PROPER = re.compile(r"圣手小青龙|胡不为|秦苏")
_CHOICE_RUN = re.compile(r"还能跑|还能走|还能逃|本可跑|本可走")
_CHOICE_TURN = re.compile(r"掉头|折回|停住|回身")
_CHOICE_NAME = re.compile(r"交名|报名|报出|真名|自己人")
_CHOICE_KEEP = re.compile(r"不杀|没死|交出去|封|还欠|人交")
# 因文·心藏腹：锋藏进肚子；放过钉成可破的誓。小孩要心眼不过。不要铜炉专名。
_XIN_TRICK = re.compile(r"小孩要心眼|要心眼|门派互坑")
_XIN_PROPER = re.compile(r"胡炭|白娴|小胡兄弟|逆沉慑斗阵|三五千金")
_XIN_HIDE = re.compile(r"藏进肚子|藏锋|装疼|还疼|乱画")
_XIN_OATH = re.compile(r"除非自保|自保|可破的誓|誓留")
_XIN_KEEP = re.compile(r"追杀还在|放过|符交|交符|还欠")
# 因文·天下第一门：铁律压场再抢场。开门就骑龙 / 救星出场不过。不要铜炉专名。
_MEN_STAR = re.compile(r"开门就骑龙|救星出场|骑龙来了")
_MEN_PROPER = re.compile(r"赵东升|蜀山|凌飞|奇案司|鲁大人")
_MEN_LAW = re.compile(r"铁律|朝廷命令|收成罪|谋反")
_MEN_STEAL = re.compile(r"扔下|顾不上|场不围")
_MEN_KEEP = re.compile(r"官差还在|酒还没散|灯还欠")
# 因文·塑魂：醒了先叫从前的人。一醒就完整 / 复活成功不过。不要铜炉专名。
_SOUL_TRICK = re.compile(r"复活成功|一醒就完整")
_SOUL_PROPER = re.compile(r"秦苏|萱儿")
_SOUL_BREAK = re.compile(r"破坛|屋顶没了|阵法完了")
_SOUL_ASK = re.compile(r"皮影|要爹")
_SOUL_CALL = re.compile(r"先叫|数名字|空洞的眼")
_SOUL_KEEP = re.compile(r"人没有完整回来|账转到孩子|魂还没回来")
# 因文·别亦难钉：认杀机不认亲。误伤 / 有话好好说 / 劝停不过。不要铜炉专名。
_BIE_TRICK = re.compile(r"误伤|有话好好说|劝停|劝开")
_BIE_PROPER = re.compile(r"单嫣|炭儿|青龙")
_BIE_KILL = re.compile(r"认杀机不认亲|不认亲")
_BIE_THROW = re.compile(r"自己扔|布包")
_BIE_FALL = re.compile(r"泥里|倒下|面上无光")
_BIE_KEEP = re.compile(r"钉还在|人不认亲")
_JAIL_CITY = re.compile(r"进城|进镇|镇上|城里|城门|找活|活路|找活路|找工")
_JAIL_BRIBE = re.compile(r"收了|接了|递上|递了|小包|包裹|收银|银子|收东西")
_JAIL_FLIP = re.compile(r"改口|眉花|良民|改叫|笑着说")
_JAIL_ROPE = re.compile(r"进牢|进绳|捆走|捆了|绳子|破布|塞嘴|押走|拿到大牢")
_JAIL_SAVE = re.compile(r"救人|替他|替人|遮掩|拦下|护住|替杏")
_SHAME_SWAP = re.compile(r"换气换丢人|换气|换丢人|丢人换人|换个人丢人")
_CLAIM_MOVE = re.compile(r"转走|交到别人|换地|账走了|还清了")
CORE_FIELDS = ("goal", "choice", "decision", "hook")
FIVE_LAYERS = ("perceived", "known", "believed", "acted", "blind")


def _fail(code: str, message: str, field: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "code": code, "message": message}
    if field:
        out["field"] = field
    return out


def _ok() -> dict[str, Any]:
    return {"ok": True}


def check_duty_day(duty: dict[str, Any]) -> dict[str, Any]:
    """日子必须先立还在过的世界。报身份/扔钩子/先宣布法会不过。"""
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    blob = f"{day}\n{happen}"
    if _OPENER_ANNOUNCE.search(blob):
        return _fail("duty_day_announce", "先立还在过的日子，不要开篇报身份、扔钩子、先宣布法会", "day")
    if not day:
        return _fail("duty_day_empty", "day 不能空：先写还在过的日子，再写必须办的那一件", "day")
    if not _DAY_LIVED.search(day):
        return _fail("duty_day_not_lived", "day 要能看见还在过的日子，不能只报一件动作", "day")
    return _ok()


def check_duty_work(duty: dict[str, Any]) -> dict[str, Any]:
    """办事：看见谁办哪一件。嘴上要的和真正缺的必须打架。鉴定/剖心不过。"""
    said = str((duty or {}).get("said") or "").strip()
    needed = str((duty or {}).get("needed") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    blob = f"{said}\n{needed}\n{happen}"
    if _APPRAISAL_TELL.search(blob):
        return _fail("duty_work_appraisal", "用办事说。不要鉴定式人设、杯子余温、剖心", "said")
    if not said:
        return _fail("duty_said_empty", "said 不能空：嘴上要的那一件", "said")
    if not needed:
        return _fail("duty_needed_empty", "needed 不能空：真正缺的那一件", "needed")
    if re.sub(r"\s+", "", said) == re.sub(r"\s+", "", needed):
        return _fail("duty_work_no_fight", "嘴上要的和真正缺的不能同一句。要打架", "needed")
    return _ok()


def check_duty_mask(duty: dict[str, Any]) -> dict[str, Any]:
    """假破真：先给反面，再破功。上来掏底牌不过。"""
    mask = str((duty or {}).get("mask") or "").strip()
    crack = str((duty or {}).get("crack") or "").strip()
    real = str((duty or {}).get("real") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    blob = f"{mask}\n{crack}\n{real}\n{happen}"
    if _DUMP_TRUTH.search(blob):
        return _fail("duty_mask_dump", "要落真意，先给反面再破功。不要上来就掏底牌", "mask")
    if not mask:
        return _fail("duty_mask_empty", "mask 不能空：先给的反面", "mask")
    if not crack:
        return _fail("duty_crack_empty", "crack 不能空：破功的那一下", "crack")
    if not real:
        return _fail("duty_real_empty", "real 不能空：破完才落的真意", "real")
    compact = [re.sub(r"\s+", "", x) for x in (mask, crack, real)]
    if len(set(compact)) < 3:
        return _fail("duty_mask_no_turn", "假、破、真不能同一句。先反面，再破功", "crack")
    if compact[2] and compact[2] in compact[0]:
        return _fail("duty_mask_dump", "反面里已经把真意说穿了。先给假的，再破", "mask")
    return _ok()


def check_duty_dist(duty: dict[str, Any]) -> dict[str, Any]:
    """远近：共情就把眼睛交给当场那个人。人还在办事时报年号/上课不过。"""
    eye = str((duty or {}).get("eye") or "").strip()
    dist = str((duty or {}).get("dist") or "near").strip().lower()
    if dist in ("远", "旁观"):
        dist = "far"
    if dist in ("近", "共情", ""):
        dist = "near"
    happen = str((duty or {}).get("must_happen") or "").strip()
    blob = f"{eye}\n{happen}\n{str((duty or {}).get('day') or '')}"
    if not eye:
        return _fail("duty_eye_empty", "eye 不能空：共情就把眼睛交给当场那个人", "eye")
    if dist not in ("near", "far"):
        return _fail("duty_dist_bad", "dist 只能是 near 或 far。要人旁观才写 far", "dist")
    if dist != "far":
        if _LECTURE.search(blob) or _LECTURE.search(eye):
            return _fail("duty_dist_lecture", "要人共情，把眼睛交给当场那个人。人还在办事时报年号、上课不过", "eye")
        if _CAMERA_OUT.search(eye):
            return _fail("duty_dist_outside", "眼睛交给了说书/旁白。要人旁观才站外头", "eye")
    return _ok()


def check_duty_cut(duty: dict[str, Any]) -> dict[str, Any]:
    """切：热过再冷，切在能听见看见的那一下。不切在叹气/夜色深了上。"""
    cut = str((duty or {}).get("cut") or "").strip()
    if not cut:
        return _fail("duty_cut_empty", "cut 不能空：切在能听见看见的那一下", "cut")
    if _SIGH_CUT.search(cut):
        return _fail("duty_cut_sigh", "切在叹气或夜色深了上。切在手上、门上、杯子上那一下", "cut")
    if not _CUT_SENSED.search(cut):
        return _fail("duty_cut_not_sensed", "切要能听见看见：一声响、门开、杯子落地，不是气氛词", "cut")
    return _ok()


def check_duty_yin(duty: dict[str, Any]) -> dict[str, Any]:
    """因文：一行本事说不完。删了会塌的那截必须另写。"""
    one = str((duty or {}).get("one_line") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    if not one:
        return _fail("duty_one_line_empty", "one_line 不能空：一行本事是什么", "one_line")
    if not keep:
        return _fail("duty_keep_empty", "keep 不能空：删了场会塌的那一截", "keep")
    if _ONE_LINE_OK.search(keep) or _ONE_LINE_OK.search(one):
        return _fail("duty_yin_one_line", "一行本事说不完。不要写过场即可", "keep")
    compact_one = re.sub(r"\s+", "", one)
    compact_keep = re.sub(r"\s+", "", keep)
    compact_happen = re.sub(r"\s+", "", happen)
    if compact_keep == compact_one:
        return _fail("duty_yin_same", "删了会塌的那截不能跟一行本事同一句", "keep")
    if compact_happen and compact_keep == compact_happen:
        return _fail("duty_yin_same", "删了会塌的那截不能只复述 must_happen", "keep")
    if len(compact_keep) < 6:
        return _fail("duty_keep_empty", "keep 太短：要写出删了场会塌的那一截", "keep")
    return _ok()


def _stay_grams(text: str) -> list[str]:
    """上场处境里还能认的两字。虚词两字丢掉。"""
    stop = set("的了着在是把被与和及就都还没不人那这一个上下来去过")
    blob = re.sub(r"\s+", "", str(text or ""))
    out: list[str] = []
    for i in range(len(blob) - 1):
        g = blob[i : i + 2]
        if all(ch in stop for ch in g):
            continue
        if g not in out:
            out.append(g)
    return out


def check_duty_owed(duty: dict[str, Any], *, prev_stay: str | None = None) -> dict[str, Any]:
    """上场没翻的处境这场还得过。只接章末钩子不算。"""
    seq = int((duty or {}).get("seq") or 0)
    stay_prev = str(prev_stay or "").strip()
    if seq <= 1 or not stay_prev:
        return _ok()
    owed = str((duty or {}).get("owed") or "").strip()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    blob = f"{owed}\n{day}\n{happen}\n{stay}"
    grams = _stay_grams(stay_prev)
    need = 2 if len(grams) >= 2 else max(1, len(grams))
    hits = [g for g in grams if g and g in blob]
    if len(hits) < need:
        return _fail(
            "duty_stay_unpaid",
            "上场没翻的处境这场还得过。只接章末钩子、把上场 stay 清掉，不算",
            "owed",
        )
    return _ok()


def check_duty_heat_new(duty: dict[str, Any], *, prev_heat: str | None = None) -> dict[str, Any]:
    """热闹不得和上场同一套。假翻不犯同一种热闹。"""
    seq = int((duty or {}).get("seq") or 0)
    heat_prev = str(prev_heat or "").strip()
    if seq <= 1 or not heat_prev:
        return _ok()
    heat = str((duty or {}).get("heat") or "").strip()
    if not heat:
        return _ok()
    a = re.sub(r"\s+", "", heat)
    b = re.sub(r"\s+", "", heat_prev)
    if a == b:
        return _fail("duty_heat_repeat", "热闹不得和上场同一套。假翻不犯同一种热闹", "heat")
    grams = _stay_grams(heat_prev)
    need = 3 if len(grams) >= 3 else max(2, len(grams))
    hits = [g for g in grams if g and g in heat]
    if len(hits) >= need:
        return _fail("duty_heat_repeat", "热闹不得和上场同一套。假翻不犯同一种热闹", "heat")
    return _ok()


def infer_duty_kind(duty: dict[str, Any] | None) -> str:
    """责任卡日子种类。旧卡没 kind、日子还停在井台排队，算同场。"""
    rec = duty or {}
    kind = str(rec.get("kind") or "").strip()
    if kind in DAY_KINDS:
        return kind
    blob = f"{rec.get('day') or ''}\n{rec.get('stay') or ''}\n{rec.get('owed') or ''}"
    if _KIND_WELL_QUEUE.search(blob):
        return "同场"
    return kind


def check_duty_kind(
    duty: dict[str, Any],
    *,
    prev_kind: str | None = None,
    prev_intruder: str | None = None,
    prev_holder: str | None = None,
    prev_place: str | None = None,
    same_kind_run: int = 0,
) -> dict[str, Any]:
    """这场进的是哪一种还在过的日子。只换节号不过；同一种不换谁闯进来不过；同场连写超两场不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    day = str((duty or {}).get("day") or "").strip()
    if _KIND_CHAPTER.search(kind) or _KIND_CHAPTER.search(day):
        return _fail("duty_kind_chapter", "只换节号不算换日子。要写进的是哪一种还在过的日子", "kind")
    if not kind:
        return _fail("duty_kind_empty", "kind 不能空：这场进的是酒宴/赶路/开坛/坐牢/跳年/选择/心藏腹/天下第一门/塑魂/别亦难/同场哪一种", "kind")
    if kind not in DAY_KINDS:
        return _fail("duty_kind_unknown", "kind 只能是酒宴、赶路、开坛、坐牢、跳年、选择、心藏腹、天下第一门、塑魂、别亦难、同场", "kind")
    seq = int((duty or {}).get("seq") or 0)
    if seq > 1 and kind == "同场":
        try:
            run = int(same_kind_run or 0)
        except (TypeError, ValueError):
            run = 0
        if run >= SAME_KIND_RUN_MAX:
            return _fail(
                "duty_kind_stuck",
                "同场连写超两场。叠同一种日子过了就空。换五套局里另一套，人从这儿走到那儿",
                "kind",
            )
    prev = str(prev_kind or "").strip() or infer_duty_kind({"kind": prev_kind} if prev_kind else {})
    if seq <= 1 or not prev or prev != kind:
        return _ok()
    now = re.sub(r"\s+", "", str((duty or {}).get("intruder") or ""))
    was = re.sub(r"\s+", "", str(prev_intruder or ""))
    if not now:
        return _fail("duty_kind_same", "连写同一种日子，必须换谁闯进来。只换节号不过", "intruder")
    if was and now == was:
        return _fail("duty_kind_same", "连写同一种日子，必须换谁闯进来。只换节号不过", "intruder")
    return _ok()



def check_duty_bill_move(
    duty: dict[str, Any],
    *,
    prev_holder: str | None = None,
    prev_place: str | None = None,
) -> dict[str, Any]:
    """账要落在谁手里、在哪一处。换气换丢人不过。声称转走却人地都没换，不过。"""
    holder = str((duty or {}).get("bill_holder") or "").strip()
    place = str((duty or {}).get("bill_place") or "").strip()
    bill = str((duty or {}).get("bill") or "").strip()
    blob = f"{holder}\n{place}\n{bill}"
    if _SHAME_SWAP.search(blob):
        return _fail("duty_bill_shame", "不要换气换丢人。账要换持有人或换地", "bill_holder")
    if not holder:
        return _fail("duty_holder_empty", "bill_holder 不能空：这笔账此刻在谁手里", "bill_holder")
    if not place:
        return _fail("duty_place_empty", "bill_place 不能空：这笔账此刻在哪一处", "bill_place")
    prev_h = re.sub(r"\s+", "", str(prev_holder or ""))
    prev_p = re.sub(r"\s+", "", str(prev_place or ""))
    now_h = re.sub(r"\s+", "", holder)
    now_p = re.sub(r"\s+", "", place)
    if prev_h and prev_p and now_h == prev_h and now_p == prev_p and _CLAIM_MOVE.search(bill):
        return _fail("duty_bill_stuck", "声称账转走了，持有人和地都没换。换气换丢人也不算", "bill_holder")
    return _ok()


def check_duty_altar(duty: dict[str, Any]) -> dict[str, Any]:
    """开坛：交差钱把人按住；热闹当社戏信了；井/灯/墓还在。高人下山伏魔不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "开坛":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    bill = str((duty or {}).get("bill") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    blob = f"{day}\n{happen}\n{bill}\n{heat}\n{stay}\n{owed}"
    if _ALTAR_HERO.search(blob):
        return _fail("duty_altar_hero", "不要学成高人下山伏魔。银子是交差钱，开坛可以假，墓必须还在", "kind")
    fee_blob = f"{day}\n{happen}\n{bill}"
    if not _ALTAR_FEE.search(fee_blob):
        return _fail("duty_altar_fee", "开坛必须看见交差钱把人按住。银子是交差钱不是救命钱", "bill")
    if not _ALTAR_HEAT_BELIEVE.search(heat):
        return _fail("duty_altar_heat", "开坛的热闹要当社戏信了。村人信了不算翻", "heat")
    if not _ALTAR_STAY_WORLD.search(stay):
        return _fail("duty_altar_stay", "开坛读完井/灯/墓还得在。热闹当社戏，处境没翻", "stay")
    return _ok()


def check_duty_feast(duty: dict[str, Any]) -> dict[str, Any]:
    """酒宴：酒还不散；面子按桌；有人闯进来；嘴上贺而账还欠。不要字面「那一桌」。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "酒宴":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    bill = str((duty or {}).get("bill") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    live = f"{day}\n{happen}\n{said}"
    if not _FEAST_UNENDED.search(live):
        return _fail("duty_feast_day", "酒宴必须先立还散不掉的酒。不要先宣布法会再补喜事", "day")
    if not _FEAST_FACE.search(live):
        return _fail("duty_feast_face", "酒宴要看见面子把人按在桌上", "day")
    if not who:
        return _fail("duty_feast_in", "酒宴必须有人闯进来。不要字面抄「那一桌」", "intruder")
    if not _FEAST_IN.search(f"{happen}\n{heat}\n{who}"):
        return _fail("duty_feast_in", "酒宴必须看见有人闯进来办事。不要字面抄「那一桌」", "must_happen")
    if not _FEAST_CONGRATS.search(said):
        return _fail("duty_feast_guest", "酒宴嘴上要贺。真正缺的还欠着", "said")
    if not _FEAST_UNPAID.search(f"{stay}\n{owed}\n{bill}"):
        return _fail("duty_feast_guest", "酒宴读完账还欠着。热闹散了不算翻", "stay")
    return _ok()


def check_duty_jail(duty: dict[str, Any]) -> dict[str, Any]:
    """坐牢：进城/镇上找活路；官差收了东西改口；救人的人进绳。清官断案、点名黑白不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "坐牢":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    bill = str((duty or {}).get("bill") or "").strip()
    crack = str((duty or {}).get("crack") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{bill}\n{crack}\n{who}"
    if _JAIL_JUDGE.search(blob):
        return _fail("duty_jail_judge", "不要学成清官断案。不要点名黑白。看见银子到了谁进绳", "kind")
    if not _JAIL_CITY.search(day):
        return _fail("duty_jail_city", "坐牢必须先立进城/镇上找活路。不要先宣布断案", "day")
    flip_blob = f"{happen}\n{heat}\n{crack}\n{said}"
    if not _JAIL_BRIBE.search(flip_blob):
        return _fail("duty_jail_bribe", "坐牢必须看见官差收了东西。银子把日子倒过来，不是讲清了理", "must_happen")
    if not _JAIL_FLIP.search(flip_blob):
        return _fail("duty_jail_flip", "坐牢必须看见官差改口。银子到了，场上谁的日子倒过来", "crack")
    rope_blob = f"{happen}\n{stay}\n{owed}\n{heat}"
    if not _JAIL_ROPE.search(rope_blob):
        return _fail("duty_jail_rope", "坐牢读完救人的人进了绳。不要把黑白两个字当写好", "stay")
    if not _JAIL_SAVE.search(f"{happen}\n{stay}\n{heat}\n{said}\n{who}"):
        return _fail("duty_jail_rope", "坐牢必须看见救人的人进绳。藏东西的人进绳不算", "stay")
    return _ok()


def check_duty_skip_year(duty: dict[str, Any]) -> dict[str, Any]:
    """跳年：削日历，补街上还在过的一天。N年后说明书、铜炉歌名不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "跳年":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    one_line = str((duty or {}).get("one_line") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{keep}\n{one_line}\n{who}"
    if _SKIP_SONG.search(blob):
        return _fail("duty_skip_song", "不要铜炉歌名。主题可以当街不值钱，换自己的名", "kind")
    if _SKIP_CALENDAR.search(blob):
        return _fail("duty_skip_calendar", "跳年不要补日历。不要写成 N 年后说明书。削日历，补街上还在过的一天", "day")
    live = f"{day}\n{happen}\n{said}\n{heat}"
    if not _SKIP_STREET.search(live):
        return _fail("duty_skip_street", "跳年必须写成街上还在过的一天。店还没开张的早上、茶馆还在讲、行人还在走", "day")
    if not _SKIP_STILL.search(f"{stay}\n{owed}"):
        return _fail("duty_skip_stay", "跳年读完账还欠着。删掉街上那一天只剩说明书", "stay")
    return _ok()


def check_duty_choice(duty: dict[str, Any]) -> dict[str, Any]:
    """选择：还能跑；自己掉头；自己人交名。遇袭丢魂 / 当场打死不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "选择":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    one_line = str((duty or {}).get("one_line") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{keep}\n{one_line}\n{who}"
    if _CHOICE_PROPER.search(blob):
        return _fail("duty_choice_name", "不要铜炉专名。恩人可以是送命的人，换自己的名", "kind")
    if _CHOICE_AMBUSH.search(blob):
        return _fail("duty_choice_ambush", "不要写成遇袭丢魂或当场打死。还能跑，自己掉头，自己人交名", "must_happen")
    live = f"{day}\n{happen}\n{said}"
    if not _CHOICE_RUN.search(live):
        return _fail("duty_choice_run", "选择必须先看见还能跑。删掉还能跑，只剩中暗器", "day")
    if not _CHOICE_TURN.search(f"{happen}\n{keep}\n{said}"):
        return _fail("duty_choice_turn", "选择必须看见自己掉头。路是自己选断的", "must_happen")
    if not _CHOICE_NAME.search(f"{happen}\n{keep}\n{said}\n{who}"):
        return _fail("duty_choice_name", "选择必须看见自己人把命名交出去。真名从自己人嘴里出来才是文", "must_happen")
    if not _CHOICE_KEEP.search(f"{stay}\n{owed}\n{keep}\n{happen}"):
        return _fail("duty_choice_keep", "选择读完人不等于放了。不杀，人交出去了", "stay")
    return _ok()


def check_duty_men(duty: dict[str, Any]) -> dict[str, Any]:
    """天下第一门：铁律压场再抢场。开门就骑龙不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "天下第一门":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{who}"
    if _MEN_PROPER.search(blob):
        return _fail("duty_men_name", "不要铜炉专名。官差进场可以不换地，换自己的名", "kind")
    if _MEN_STAR.search(blob):
        return _fail("duty_men_star", "不要开门就骑龙。先让这桌酒被收成罪，再让救星把场抢走", "must_happen")
    live = f"{day}\n{happen}\n{said}"
    if not _MEN_LAW.search(live):
        return _fail("duty_men_law", "天下第一门必须先看见铁律把酒收成罪。删掉铁律只剩官差扰宴", "day")
    if not _MEN_STEAL.search(f"{happen}\n{keep}\n{said}\n{heat}"):
        return _fail("duty_men_steal", "天下第一门必须看见救星把场抢走。删掉扔下捕快只剩骑龙热闹", "must_happen")
    if not _MEN_KEEP.search(f"{stay}\n{owed}\n{keep}\n{happen}"):
        return _fail("duty_men_keep", "天下第一门读完官差还在。场不围他们，酒还没散", "stay")
    return _ok()


def check_duty_soul(duty: dict[str, Any]) -> dict[str, Any]:
    """塑魂：醒了先叫从前的人。一醒就完整不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "塑魂":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{who}"
    if _SOUL_PROPER.search(blob):
        return _fail("duty_soul_name", "不要铜炉专名。醒了先叫谁，换自己的名", "kind")
    if _SOUL_TRICK.search(blob):
        return _fail("duty_soul_revive", "不要写成一醒就完整。破坛不是失败过场，醒了先叫从前的人", "must_happen")
    live = f"{day}\n{happen}\n{said}"
    if not _SOUL_BREAK.search(live):
        return _fail("duty_soul_break", "塑魂必须看见破坛。酒把关口推半寸，屋顶先没了", "day")
    if not _SOUL_ASK.search(f"{happen}\n{keep}\n{said}\n{who}"):
        return _fail("duty_soul_ask", "塑魂必须看见孩子那一问。魂还没回来，账已经转到下一辈", "must_happen")
    if not _SOUL_CALL.search(f"{happen}\n{keep}\n{said}\n{stay}"):
        return _fail("duty_soul_call", "塑魂必须看见醒了先叫从前的人。删掉数名字，读者会当人完整回来了", "must_happen")
    if not _SOUL_KEEP.search(f"{stay}\n{owed}\n{keep}\n{happen}"):
        return _fail("duty_soul_keep", "塑魂读完人没有完整回来。账可以转到孩子手里", "stay")
    return _ok()


def check_duty_bie(duty: dict[str, Any]) -> dict[str, Any]:
    """别亦难：钉认杀机不认亲。误伤劝停不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "别亦难":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{who}"
    if _BIE_PROPER.search(blob):
        return _fail("duty_bie_name", "不要铜炉专名。克邪的东西可以不认亲，换自己的名", "kind")
    if _BIE_TRICK.search(blob):
        return _fail("duty_bie_accident", "不要写成误伤或有话好好说。钉认杀机不认亲，孩子自己扔", "must_happen")
    live = f"{day}\n{happen}\n{said}"
    if not _BIE_KILL.search(live):
        return _fail("duty_bie_kill", "别亦难必须看见钉认杀机不认亲。删掉这一截只剩法宝误伤", "day")
    if not _BIE_THROW.search(f"{happen}\n{keep}\n{said}\n{who}"):
        return _fail("duty_bie_throw", "别亦难必须看见孩子自己扔布包。删掉自己扔只剩法宝误伤", "must_happen")
    if not _BIE_FALL.search(f"{happen}\n{keep}\n{said}\n{stay}"):
        return _fail("duty_bie_fall", "别亦难必须看见无辜的人倒下。删掉泥里那一躺，架像助开的", "must_happen")
    if not _BIE_KEEP.search(f"{stay}\n{owed}\n{keep}\n{happen}"):
        return _fail("duty_bie_keep", "别亦难读完钉还在。人不认亲", "stay")
    return _ok()


def check_duty_xin(duty: dict[str, Any]) -> dict[str, Any]:
    """心藏腹：锋藏进肚子；放过钉成可破的誓。小孩要心眼不过。"""
    kind = str((duty or {}).get("kind") or "").strip()
    if kind != "心藏腹":
        return _ok()
    day = str((duty or {}).get("day") or "").strip()
    happen = str((duty or {}).get("must_happen") or "").strip()
    said = str((duty or {}).get("said") or "").strip()
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    owed = str((duty or {}).get("owed") or "").strip()
    keep = str((duty or {}).get("keep") or "").strip()
    one_line = str((duty or {}).get("one_line") or "").strip()
    who = str((duty or {}).get("intruder") or "").strip()
    blob = f"{day}\n{happen}\n{said}\n{heat}\n{stay}\n{owed}\n{who}"
    if _XIN_PROPER.search(blob):
        return _fail("duty_xin_name", "不要铜炉专名。救命可以是料，换自己的名", "kind")
    if _XIN_TRICK.search(blob):
        return _fail("duty_xin_trick", "不要写成小孩要心眼。锋藏进肚子，放过钉成可破的誓", "must_happen")
    live = f"{day}\n{happen}\n{said}"
    if not _XIN_HIDE.search(live):
        return _fail("duty_xin_hide", "心藏腹必须看见锋藏进肚子。删掉装疼和乱画，只剩小孩要心眼", "day")
    if not _XIN_OATH.search(f"{happen}\n{keep}\n{said}\n{stay}"):
        return _fail("duty_xin_oath", "心藏腹必须把放过钉成可破的誓。删掉除非自保，掠鬓只是反咬", "must_happen")
    if not _XIN_KEEP.search(f"{stay}\n{owed}\n{keep}\n{happen}"):
        return _fail("duty_xin_keep", "心藏腹读完追杀还在。誓是假放过，符交出去了", "stay")
    return _ok()


def check_duty_flip(duty: dict[str, Any]) -> dict[str, Any]:
    """热闹不算翻。热闹像翻了、处境还停在原处，不过。"""
    heat = str((duty or {}).get("heat") or "").strip()
    stay = str((duty or {}).get("stay") or "").strip()
    blob = f"{heat}\n{stay}"
    if not heat:
        return _fail("duty_heat_empty", "heat 不能空：热闹像翻了的那一层", "heat")
    if not stay:
        return _fail("duty_stay_empty", "stay 不能空：处境还停在哪。热闹不算翻", "stay")
    if _HEAT_AS_FLIP.search(blob):
        return _fail("duty_flip_heat", "热闹不算翻。不要把场面过了写成日子翻了", "stay")
    compact = [re.sub(r"\s+", "", x) for x in (heat, stay)]
    if compact[0] == compact[1]:
        return _fail("duty_flip_same", "热闹像翻了的那一层，和处境还停在哪，不能同一句", "stay")
    if _HEAT_ONLY.search(stay) and not _STAY_WORLD.search(stay):
        return _fail("duty_flip_heat", "处境还停在哪，不能只写场面过了。热闹不算翻", "stay")
    return _ok()


def check_opener_announce(text: str) -> dict[str, Any]:
    """开篇头一段叙述不得报身份/扔钩子/先宣布法会。"""
    narr = narration_layer(text or "")
    head = re.sub(r"\s+", "", narr)[:180]
    if not head:
        return _ok()
    m = _OPENER_ANNOUNCE.search(head)
    if m:
        return _fail("opener_announce", f"开篇在报身份或先宣布法会：「{m.group(0)}」。先立还在过的日子。")
    lec = check_opener_lecture(text)
    if not lec.get("ok"):
        return lec
    return _ok()


def check_opener_lecture(text: str) -> dict[str, Any]:
    """开篇叙述不得报年号、铺戒律、先上课。"""
    narr = narration_layer(text or "")
    head = re.sub(r"\s+", "", narr)[:180]
    if not head:
        return _ok()
    m = _LECTURE.search(head)
    if m:
        return _fail("opener_lecture", f"开篇在报年号或上课：「{m.group(0)}」。共情就把眼睛交给当场那个人。")
    return _ok()


def _quoted(node: Any) -> tuple[str, str]:
    if not isinstance(node, dict):
        return "", ""
    return str(node.get("text") or "").strip(), str(node.get("quote") or "").strip()


def _line_ids(available_lines: list[Any] | None) -> set[str]:
    out: set[str] = set()
    for item in available_lines or []:
        if isinstance(item, dict):
            i = item.get("id")
            if i:
                out.add(str(i))
        elif item:
            out.add(str(item))
    return out


def check_play_struct(play_text: str) -> dict[str, Any]:
    text = (play_text or "").strip()
    if not text:
        return _fail("play_empty", "戏是空的")
    n = len(re.sub(r"\s+", "", text))
    if n < 200 or n > 4000:
        return _fail("play_len", f"戏字数 {n} 不在 200–4000")
    head = text.splitlines()[:3]
    for line in head:
        if _LABEL_HEAD.match((line or "").strip()):
            return _fail("play_label", "戏开头三行带了旧标签行")
    return _ok()


def check_duty_struct(
    duty: dict[str, Any],
    *,
    available_cast: list[str] | None = None,
    available_lines: list[Any] | None = None,
    prev_hook_quote: str | None = None,
    prev_stay: str | None = None,
    prev_heat: str | None = None,
    prev_kind: str | None = None,
    prev_intruder: str | None = None,
    prev_holder: str | None = None,
    prev_place: str | None = None,
    same_kind_run: int = 0,
) -> dict[str, Any]:
    def _who(x: str) -> str:
        s = str(x or "").strip()
        return s[5:] if s.startswith("role:") else s

    who = [_who(x) for x in (duty.get("who") or []) if _who(x)]
    if not who:
        return _fail("duty_who_empty", "who 不能空", "who")
    if not str(duty.get("must_happen") or "").strip():
        return _fail("duty_must_empty", "must_happen 不能空", "must_happen")
    if not str(duty.get("bill") or "").strip():
        return _fail("duty_bill_empty", "bill 不能空", "bill")
    day_hit = check_duty_day(duty)
    if not day_hit.get("ok"):
        return day_hit
    work_hit = check_duty_work(duty)
    if not work_hit.get("ok"):
        return work_hit
    mask_hit = check_duty_mask(duty)
    if not mask_hit.get("ok"):
        return mask_hit
    dist_hit = check_duty_dist(duty)
    if not dist_hit.get("ok"):
        return dist_hit
    cut_hit = check_duty_cut(duty)
    if not cut_hit.get("ok"):
        return cut_hit
    yin_hit = check_duty_yin(duty)
    if not yin_hit.get("ok"):
        return yin_hit
    flip_hit = check_duty_flip(duty)
    if not flip_hit.get("ok"):
        return flip_hit
    owed_hit = check_duty_owed(duty, prev_stay=prev_stay)
    if not owed_hit.get("ok"):
        return owed_hit
    heat_hit = check_duty_heat_new(duty, prev_heat=prev_heat)
    if not heat_hit.get("ok"):
        return heat_hit
    kind_hit = check_duty_kind(
        duty, prev_kind=prev_kind, prev_intruder=prev_intruder, same_kind_run=same_kind_run,
    )
    if not kind_hit.get("ok"):
        return kind_hit
    bill_hit = check_duty_bill_move(duty, prev_holder=prev_holder, prev_place=prev_place)
    if not bill_hit.get("ok"):
        return bill_hit
    altar_hit = check_duty_altar(duty)
    if not altar_hit.get("ok"):
        return altar_hit
    feast_hit = check_duty_feast(duty)
    if not feast_hit.get("ok"):
        return feast_hit
    jail_hit = check_duty_jail(duty)
    if not jail_hit.get("ok"):
        return jail_hit
    skip_hit = check_duty_skip_year(duty)
    if not skip_hit.get("ok"):
        return skip_hit
    choice_hit = check_duty_choice(duty)
    if not choice_hit.get("ok"):
        return choice_hit
    xin_hit = check_duty_xin(duty)
    if not xin_hit.get("ok"):
        return xin_hit
    men_hit = check_duty_men(duty)
    if not men_hit.get("ok"):
        return men_hit
    soul_hit = check_duty_soul(duty)
    if not soul_hit.get("ok"):
        return soul_hit
    bie_hit = check_duty_bie(duty)
    if not bie_hit.get("ok"):
        return bie_hit
    fr = duty.get("forbidden_reveal")
    if not isinstance(fr, list) or not [x for x in fr if str(x).strip()]:
        return _fail("duty_forbid_empty", "forbidden_reveal 不能空", "forbidden_reveal")
    cast = {_who(x) for x in (available_cast or []) if _who(x)}
    if cast:
        extra = [n for n in who if n not in cast]
        if extra:
            return _fail("duty_who_cast", f"编了户口外的人: {extra}", "who")
    line = duty.get("line_to_touch")
    if line not in (None, "", "null"):
        ids = _line_ids(available_lines)
        if ids and str(line) not in ids:
            return _fail("duty_line", f"编了不存在的线: {line}", "line_to_touch")
    seq = int(duty.get("seq") or 0)
    bite = duty.get("bite_from_prev")
    if seq == 1:
        if bite not in (None, ""):
            return _fail("duty_bite_ch1", "第1章 bite_from_prev 必须是空", "bite_from_prev")
    else:
        expect = prev_hook_quote
        if expect is not None and bite != expect:
            return _fail("duty_bite", "bite_from_prev 必须等于上章 hook.quote", "bite_from_prev")
    return _ok()


def _need_quote(node: Any, play_text: str, field: str, *, required: bool) -> dict[str, Any] | None:
    if node in (None, "", {}):
        if required:
            return _fail("quote_missing", f"{field} 不能空", field)
        return None
    text, quote = _quoted(node)
    if required and (not text or not quote):
        return _fail("quote_missing", f"{field} 缺 text/quote", field)
    if (text or quote) and not quote:
        return _fail("quote_missing", f"{field} 有 text 无 quote", field)
    if quote and not quote_is_slice(quote, play_text):
        if quote_in_play(quote, play_text):
            return _fail("quote_edited", f"{field} 的 quote 改过字（裁了前缀或动了标点）", field)
        return _fail("quote_not_in_play", f"{field} 的 quote 不在戏里", field)
    return None


def nest_choice_sides(contract: dict[str, Any]) -> dict[str, Any]:
    """把抄到 fields.side_a/side_b 的两难收回 choice 里。戏已立住，不许因外层键毙。"""
    rec = contract if isinstance(contract, dict) else {}
    fields = rec.get("fields") if isinstance(rec.get("fields"), dict) else {}
    choice = fields.get("choice") if isinstance(fields.get("choice"), dict) else {}
    if not isinstance(choice, dict):
        choice = {}
        fields["choice"] = choice
    for side in ("side_a", "side_b"):
        inner = choice.get(side)
        outer = fields.get(side)
        empty = inner in (None, "", {}) or (
            isinstance(inner, dict) and not str(inner.get("quote") or "").strip()
        )
        if empty and isinstance(outer, dict) and str(outer.get("quote") or "").strip():
            choice[side] = outer
            fields.pop(side, None)
    rec["fields"] = fields
    return rec


def check_contract_struct(
    contract: dict[str, Any],
    play_text: str,
    *,
    available_lines: list[Any] | None = None,
) -> dict[str, Any]:
    nest_choice_sides(contract)
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    choice = fields.get("choice") if isinstance(fields.get("choice"), dict) else {}
    for name in CORE_FIELDS:
        hit = _need_quote(fields.get(name), play_text, name, required=True)
        if hit:
            return hit
    for side in ("side_a", "side_b"):
        hit = _need_quote(choice.get(side), play_text, f"choice.{side}", required=True)
        if hit:
            return hit
    hit = _need_quote(choice, play_text, "choice", required=True)
    if hit:
        return hit
    cost = fields.get("cost")
    if cost not in (None, "", {}):
        hit = _need_quote(cost, play_text, "cost", required=True)
        if hit:
            return hit
    beats = contract.get("beats") or []
    if not isinstance(beats, list) or len(beats) < 3:
        return _fail("beats_count", f"beats 要 ≥3，现有 {len(beats) if isinstance(beats, list) else 0}")
    staged = 0
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            return _fail("beat_shape", f"beat[{i}] 不是对象")
        hit = _need_quote(beat.get("goal"), play_text, f"beats[{i}].goal", required=True)
        if hit:
            return hit
        hit = _need_quote(beat.get("turn"), play_text, f"beats[{i}].turn", required=True)
        if hit:
            return hit
        for opt in ("conflict", "cost"):
            if beat.get(opt) not in (None, "", {}):
                hit = _need_quote(beat.get(opt), play_text, f"beats[{i}].{opt}", required=True)
                if hit:
                    return hit
        if beat.get("stages_choice") is True:
            staged += 1
    if staged != 1:
        return _fail("stages_choice", f"stages_choice=true 必须恰好 1 场，现有 {staged}")
    ids = _line_ids(available_lines)
    for i, line in enumerate(contract.get("lines_touched") or []):
        if not isinstance(line, dict):
            continue
        lid = str(line.get("id") or "")
        if ids and lid and lid not in ids:
            return _fail("line_unknown", f"编了不存在的线: {lid}", f"lines_touched[{i}]")
        q = str(line.get("quote") or "")
        if q and not quote_is_slice(q, play_text):
            code = "quote_edited" if quote_in_play(q, play_text) else "quote_not_in_play"
            return _fail(code, "线的 quote 不在戏里或改过字", f"lines_touched[{i}]")
    clock = contract.get("clock")
    if isinstance(clock, dict) and clock:
        span = clock.get("span")
        if span not in CLOCK_SPANS:
            return _fail("clock_span", f"clock.span 只允许 {sorted(CLOCK_SPANS)}", "clock")
        hit = _need_quote(clock, play_text, "clock", required=True)
        if hit:
            return hit
    place = contract.get("place")
    if isinstance(place, dict) and (place.get("name") or place.get("quote") or place.get("text")):
        hit = _need_quote(place, play_text, "place", required=bool(place.get("quote") or place.get("text")))
        if hit:
            return hit
    return _ok()


def check_deduce_struct(deduction: dict[str, Any]) -> dict[str, Any]:
    if not str(deduction.get("scene_truth") or "").strip():
        return _fail("scene_truth_empty", "字缝里那一件还没写")
    chars = deduction.get("characters") or []
    if not isinstance(chars, list) or not chars:
        return _fail("chars_empty", "该在场的人还没有各自的算盘")
    for i, ch in enumerate(chars):
        if not isinstance(ch, dict):
            return _fail("char_shape", f"characters[{i}] 不是对象")
        name = str(ch.get("id") or i)
        believed = str(ch.get("believed") or "").strip()
        blind = str(ch.get("blind") or "").strip()
        if not believed and not blind:
            return _fail("no_undercurrent", f"{name} 没有以为或没察觉，字缝不成立")
    return _ok()


def _plain(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def draft_ngrams(text: str, n: int = 8) -> list[str]:
    s = _plain(text)
    if len(s) < n:
        return []
    return [s[i : i + n] for i in range(len(s) - n + 1)]


def draft_play_overlap(draft_text: str, play_text: str, *, exempt_quotes: tuple[str, ...] = ()) -> float:
    """draft 相对 play 的 8 字窗命中率。豁免窗（上章/本章钩子）不进分子。"""
    play_set = set(draft_ngrams(play_text))
    grams = draft_ngrams(draft_text)
    if not grams or not play_set:
        return 0.0
    exempt: set[str] = set()
    for q in exempt_quotes or ():
        exempt.update(draft_ngrams(q))
    hits = 0
    denom = 0
    for g in grams:
        if g in exempt:
            continue
        denom += 1
        if g in play_set:
            hits += 1
    if denom <= 0:
        return 0.0
    return hits / denom


def _metaphor_source(text: str, *, exempt_quotes: tuple[str, ...] = ()) -> str:
    """对白内、必须保留的原句不计入明喻密度。"""
    s = text or ""
    for q in exempt_quotes or ():
        if q:
            s = s.replace(str(q), "")
    return _DIALOGUE.sub("", s)


def metaphor_per_800(text: str, *, exempt_quotes: tuple[str, ...] = ()) -> float:
    """与 quality_metrics 同一把尺子：明喻次数 / max(去空白字数/800, 1)。"""
    src = _metaphor_source(text, exempt_quotes=exempt_quotes)
    n = len(_plain(text))
    hits = len(_METAPHOR.findall(src))
    units = max(n / 800.0, 1.0)
    return hits / units


def _metaphor_fail(
    text: str, *, code: str, exempt_quotes: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    src = _metaphor_source(text, exempt_quotes=exempt_quotes)
    n = len(_plain(text))
    hits = len(_METAPHOR.findall(src))
    rate = metaphor_per_800(text, exempt_quotes=exempt_quotes)
    if rate <= 1.0:
        return None
    return _fail(code, f"明喻 {hits} 处 / {n} 字 = {rate:.2f} 每800字，超过 1")


def _thin_narr(s: str) -> str:
    s = _NEG_LIKE.sub("不似", s or "")
    s = s.replace("好像", "似乎").replace("像是", "似乎是")
    s = s.replace("仿佛", "").replace("似的", "")
    return re.sub(r"(?<![其])像", "", s)


def _thin_narr_keep_clean(s: str) -> str:
    """逐句清洗；洗出残渣的句子退回原句。"""
    parts = _SENT_SPLIT.split(s or "")
    out: list[str] = []
    for p in parts:
        t = _thin_narr(p)
        out.append(p if _RESIDUE.search(t) else t)
    return "".join(out)


def residue_hits(text: str) -> list[str]:
    return [m.group(0) for m in _RESIDUE.finditer(text or "")]


def thin_metaphors(text: str, *, exempt_quotes: tuple[str, ...] = ()) -> str:
    """叙述层去掉过密的像/仿佛/似的；对白和豁免原句原样保留。密度已合格则不动。"""
    if metaphor_per_800(text, exempt_quotes=exempt_quotes) <= 1.0:
        return text or ""
    raw = text or ""
    held: list[str] = []

    def stash(chunk: str) -> str:
        held.append(chunk)
        return f"\x00H{len(held) - 1}\x00"

    work = raw
    for q in exempt_quotes or ():
        if q and q in work:
            work = work.replace(str(q), stash(str(q)))
    out: list[str] = []
    last = 0
    for m in _DIALOGUE.finditer(work):
        out.append(_thin_narr_keep_clean(work[last:m.start()]))
        out.append(m.group())
        last = m.end()
    out.append(_thin_narr_keep_clean(work[last:]))
    work = "".join(out)
    for i, chunk in enumerate(held):
        work = work.replace(f"\x00H{i}\x00", chunk)
    return work


def narration_layer(text: str) -> str:
    """剥配对引号后的叙述层。"""
    s = _DIALOGUE.sub("", text or "")
    return _STRAIGHT_Q.sub("", s)


def detect_narrative_pov(text: str) -> str:
    """first if 叙述层「我」≥10 且 > 「他」÷3，否则 third。"""
    narr = narration_layer(text)
    wo = narr.count("我")
    ta = len(_HE.findall(narr))
    if wo >= 10 and wo > (ta / 3.0):
        return "first"
    return "third"


def list_syntax_tics(text: str) -> list[dict[str, Any]]:
    """剥对白后的装腔句：否定翻转 + 现成毒句式。不重写正则。"""
    from scribe3.critique import find_negation_flips
    from scribe3.critique._common import _TOXIC_PATTERNS

    narr = narration_layer(text)
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for h in find_negation_flips(narr):
        phrase = str(h.get("phrase") or "").strip()
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        hits.append({
            "kind": "not_a_but_b",
            "phrase": phrase,
            "variant": h.get("variant"),
        })
    for name, pat in _TOXIC_PATTERNS:
        for m in pat.finditer(narr):
            phrase = m.group(0)
            if not phrase or phrase in seen:
                continue
            seen.add(phrase)
            hits.append({"kind": "toxic_pattern", "phrase": phrase, "pattern": name})
    return hits


def check_syntax_tics(text: str) -> dict[str, Any]:
    """叙述里两处及以上装腔句才拦。一处交给法官看。"""
    hits = list_syntax_tics(text)
    if len(hits) < 2:
        return _ok()
    quoted = "；".join(f"「{h['phrase'][:40]}」" for h in hits[:4])
    return _fail(
        "syntax_tics",
        f"叙述里有 {len(hits)} 处在装腔，不是人在做事：{quoted}。"
        "用他此刻正在做的事重写这些句子。",
    )


def check_pov_consistency(text: str, expected_pov: str | None = None) -> dict[str, Any]:
    want = str(expected_pov or "").strip()
    if want not in ("first", "third"):
        return _ok()
    got = detect_narrative_pov(text)
    if got == want:
        return _ok()
    return _fail(
        "pov_consistency",
        f"叙述人称应为{'第一' if want == 'first' else '第三'}人称，测得{got}",
        "narrative_pov",
    )


def dialogue_ratio(text: str) -> float:
    """引号行字数 / 全文去空白字数。"""
    lines = (text or "").splitlines()
    total = 0
    quoted = 0
    for ln in lines:
        n = len(_plain(ln))
        if n <= 0:
            continue
        total += n
        if _QUOTE_LINE.search(ln):
            quoted += n
    if total <= 0:
        return 0.0
    return quoted / total


def check_gender_pronoun(text: str, characters: list[Any] | None = None) -> dict[str, Any]:
    """角色名后短窗内，对已登记男/女的角色统计他/她。反向上位则拦。

    只看名后，不看名前：限知第三人称的「他」常落在女人名旁，不是把她写成男的。
    同窗里出现另一个户口名字时跳过该窗：对手同框时「他」常指对方。
    """
    blob = text or ""
    roster: list[tuple[str, str]] = []
    for ch in characters or []:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("name") or "").strip()
        gender = str(ch.get("gender") or "").strip()
        if name and gender in ("男", "女"):
            roster.append((name, gender))
    after = 16
    around = 16
    for name, gender in roster:
        windows: list[str] = []
        start = 0
        while True:
            i = blob.find(name, start)
            if i < 0:
                break
            lo = max(0, i - around)
            hi = min(len(blob), i + len(name) + after)
            ctx = blob[lo:hi]
            win = blob[i + len(name) : hi]
            start = i + len(name)
            if any(other != name and other in ctx for other, _ in roster):
                continue
            windows.append(win)
        if not windows:
            continue
        joined = "".join(windows)
        he_n = len(_HE.findall(joined))
        she_n = len(_SHE.findall(joined))
        if gender == "男" and she_n > he_n:
            return _fail(
                "gender_pronoun",
                f"{name} 户口为男，名后窗口「她」{she_n} 多于「他」{he_n}",
                name,
            )
        if gender == "女" and he_n > she_n:
            return _fail(
                "gender_pronoun",
                f"{name} 户口为女，名后窗口「他」{he_n} 多于「她」{she_n}",
                name,
            )
    return _ok()


def check_chapter_state_struct(state: dict[str, Any], source_text: str) -> dict[str, Any]:
    """章末态形状 + 每条人物/物件 quote 必须在冻稿正文里。"""
    hit = check_chapter_state_schema(state)
    if not hit.get("ok"):
        return hit
    src = source_text or ""
    for i, ch in enumerate(state.get("characters") or []):
        q = str((ch or {}).get("quote") or "")
        if q and not quote_in_play(q, src):
            return _fail("state_quote", f"characters[{i}] 的 quote 不在正文里", f"characters[{i}].quote")
    for i, obj in enumerate(state.get("objects") or []):
        q = str((obj or {}).get("quote") or "")
        if q and not quote_in_play(q, src):
            return _fail("state_quote", f"objects[{i}] 的 quote 不在正文里", f"objects[{i}].quote")
    return _ok()


def realign_state_quotes(state: dict[str, Any], source: str) -> tuple[dict[str, Any], list[str]]:
    """把人物/物件 quote 对回 source 的字面切片。对不上的路径进 misses。"""
    import copy

    out = copy.deepcopy(state) if isinstance(state, dict) else {}
    misses: list[str] = []
    src = source or ""
    for kind in ("characters", "objects"):
        rows = out.get(kind) if isinstance(out.get(kind), list) else []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            q = str(row.get("quote") or "").strip()
            if not q:
                continue
            snapped = snap_quote(q, src)
            if snapped and quote_in_play(snapped, src):
                row["quote"] = snapped
            else:
                misses.append(f"{kind}[{i}].quote")
    return out, misses


def _meta_chapter_fail(text: str) -> dict[str, Any] | None:
    try:
        from scribe3.anti_meta_narration import scan_anti_meta
        hits = scan_anti_meta(text or "").get("hits") or []
    except Exception:
        return None
    m8 = [h for h in hits if (h.get("id") == "M8")]
    if not m8:
        return None
    quote = str((m8[0] or {}).get("quote") or "")[:80]
    return _fail("meta_chapter_ref", f"正文出现章边界词：{quote}")


def check_draft_struct(
    draft_text: str,
    *,
    play_text: str = "",
    exempt_quotes: tuple[str, ...] = (),
    characters: list[Any] | None = None,
    expected_pov: str | None = None,
) -> dict[str, Any]:
    text = (draft_text or "").strip()
    if not text:
        return _fail("draft_empty", "排演是空的")
    n = len(_plain(text))
    if n < 400:
        return _fail("draft_len", f"排演还没立住一场（{n} 字）。场面立住就停，不要为凑字注水")
    meta = _meta_chapter_fail(text)
    if meta:
        return meta
    if (play_text or "").strip():
        rate = draft_play_overlap(text, play_text, exempt_quotes=exempt_quotes)
        # 字数不作完成的同一条：场面已立住的扩写不得因跟戏重复被毙。整段搬戏才拦。
        if rate > 0.50:
            return _fail("draft_copy_play", f"糙稿几乎整段搬了戏（重复率 {rate:.1%}）")
    dens = _metaphor_fail(text, code="draft_metaphor", exempt_quotes=exempt_quotes)
    if dens:
        return dens
    gp = check_gender_pronoun(text, characters)
    if not gp.get("ok"):
        return gp
    pov = check_pov_consistency(text, expected_pov)
    if not pov.get("ok"):
        return pov
    dlg = dialogue_ratio(text)
    if dlg < 0.15:
        return _fail("dialogue_floor", f"对白占比 {dlg:.1%} 低于 15%")
    opener = check_opener_announce(text)
    if not opener.get("ok"):
        return opener
    from scribe3.playbook.chengse import check_chengse_filter
    ch = check_chengse_filter(text)
    if not ch.get("ok"):
        return ch
    return _ok()


def check_final_struct(prose_text: str, *, expected_pov: str | None = None) -> dict[str, Any]:
    text = (prose_text or "").strip()
    if not text:
        return _fail("prose_empty", "正文是空的")
    n = len(re.sub(r"\s+", "", text))
    if n < 400:
        return _fail("prose_len", f"正文还没立住一场（{n} 字）。场面立住就停，不要为凑字注水")
    pov = check_pov_consistency(text, expected_pov)
    if not pov.get("ok"):
        return pov
    return _ok()


def check_final_last_mile(
    prose_text: str,
    *,
    store: Any = None,
    seq: int | None = None,
    characters: list[Any] | None = None,
    exempt_quotes: tuple[str, ...] = (),
    expected_pov: str | None = None,
) -> dict[str, Any]:
    """Length floor + 章边界 + 冻结契约 + 代词/人称连续 + finalize 最后一公里。"""
    hit = check_final_struct(prose_text, expected_pov=expected_pov)
    if not hit.get("ok"):
        return hit
    meta = _meta_chapter_fail(prose_text)
    if meta:
        return meta
    dens = _metaphor_fail(prose_text, code="final_metaphor", exempt_quotes=exempt_quotes)
    if dens:
        return dens
    gp = check_gender_pronoun(prose_text, characters)
    if not gp.get("ok"):
        return gp
    tics = check_syntax_tics(prose_text)
    if not tics.get("ok"):
        return tics
    opener = check_opener_announce(prose_text)
    if not opener.get("ok"):
        return opener
    from scribe3.playbook.chengse import check_chengse_filter
    ch = check_chengse_filter(prose_text)
    if not ch.get("ok"):
        return ch
    if store is None:
        return hit
    getter = getattr(store, "get_frozen", None)
    if callable(getter):
        contract = getter("chapter_contract", int(seq or 0))
        if not contract:
            return _fail("no_chapter_contract", "还没有冻结的契约，不能定稿")
    try:
        from scribe3.finalize_gate import check_finalize_for_save
        fg = check_finalize_for_save(store, int(seq or 0), prose_text or "")
    except Exception as exc:
        return _fail("finalize_gate_error", str(exc)[:240])
    if not fg.get("allowed"):
        return _fail(
            str(fg.get("code") or "finalize_gate"),
            str(fg.get("detail") or "定稿门没过"),
        )
    return hit
