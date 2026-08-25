"""playbook.3.2.25 identity + generate/judge prompts. 改法官问卷或门槛才升版本。"""
from __future__ import annotations

import json

from scribe3.playbook.chengse import craft_generate_block, craft_judge_block
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.schema import snapshot_body

IDENTITY_NOVELIST = (
    "你是一个写了二十年长篇的小说家。你从不写提纲式概括，你写还在过的日子："
    "具体的时间、具体的地方、谁在办哪一件。读完要能看见日子怎么变，"
    "不是报身份、扔钩子、升华收尾。"
)
IDENTITY_DUTY = "你是这本书的主编剧，管整本书的账房：先立还在过的日子，再立每章办什么事、付什么账。"
IDENTITY_PLAY = (
    "你是这本书的场记导演。你写的是给剧组看的一场戏："
    "谁在场、发生哪一件事、眼睛交给谁、切在哪一下、删了会塌的那一截、假破真落在哪个动作、账怎么付、章末悬着什么。"
    "你不写给读者的正文。完整对白和此刻能摸到的东西留给糙稿。"
)
IDENTITY_SCRIBE = "你是剧组里最较真的场记。你只抄，不写。戏里没有的一个字都不许添。"
IDENTITY_JUDGE = (
    "你是最苛刻的文学编辑，毙过的稿子比过稿多十倍。你只认纸面上的东西："
    "产物里有的才算数，『作者大概是想……』一律不算。你判案先引原文："
    "每个判断必须先引用产物原句作证据，再下结论。你的意见说人话，"
    "像老编辑在稿纸边上用红笔写的那种话。"
)

VERDICT_SCHEMA = (
    "输出 JSON（不输出任何别的文字）：\n"
    '{"answers": [{"q": 1, "evidence": "产物原句", "answer": "yes/no", "reason": "..."}],\n'
    ' "verdict": "pass/fail",\n'
    ' "opinion": "fail 时必填：老编辑红笔式的意见，只说作品本身，禁提字段名与指标"}'
)


def _state_json(ctx: dict) -> str:
    body = snapshot_body(ctx.get("prev_state") if isinstance(ctx, dict) else None)
    if not body:
        return "（无。第1章或上章尚未登记章末态——按本章所见写，不得发明前史伤势/物件位置。）"
    try:
        return json.dumps(body, ensure_ascii=False)
    except TypeError:
        return str(body)


def _cast_line(ctx: dict) -> str:
    cards = (ctx or {}).get("cast_cards") or []
    parts: list[str] = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        n = str(c.get("name") or "").strip()
        if not n:
            continue
        g = str(c.get("gender") or "").strip() or "性别未登记"
        parts.append(f"{n}（{g}）")
    if parts:
        return "、".join(parts)
    return str((ctx or {}).get("available_cast") or [])


def _imagery_line(ctx: dict) -> str:
    v = str((ctx or {}).get("imagery") or "").strip()
    return v or "（未设全书意象域）"


def _pov_line(ctx: dict) -> str:
    rec = (ctx or {}).get("prev_state") if isinstance(ctx, dict) else None
    pov = ""
    if isinstance(rec, dict):
        pov = str(rec.get("narrative_pov") or "").strip()
    if pov not in ("first", "third"):
        return "【叙事人称】第1章确立。这一章写完后系统会登记；后续章沿用，不得自己改口。"
    if pov == "first":
        return "【叙事人称】第一人称（沿用首章）。叙述里禁止用「他」指主角；对白里不受限。"
    return "【叙事人称】第三人称（沿用首章）。叙述里禁止出现「我」；对白里不受限。"


VOLUME_LEDGER_DISCIPLINE = (
    "今晚只办这一章该办的那一笔。后面几章的账可以在章末当没做完的事挂着，不许今晚演完。"
    "后面几章要办什么是给你看的账本，不是给角色或叙述者念的。"
    "正文里不许提这些、不许用任何形式预告后面的剧情。"
)

PACE_EXEMPT = (
    "若今晚要办的是给后面某笔做准备（把一件东西送到位置、埋下一句、只揭一角），"
    "只要这件事本身发生了，就算办了——不要因为没有当场高潮就判不过。"
    "但「今晚什么也没发生，只是酝酿情绪」不算做准备。"
)

IRON_RULES = (
    "1. 今晚只办这一章该办的那一笔。后面的可以挂着，不许演完。"
    "后面几章的账是给你看的，不是给角色念的，正文里不许预告。\n"
    "2. 今晚还不能拆穿的事，一个字都不要漏。\n"
    "3. 该在场的人各自做事，不能只站着。\n"
    "4. 账当场付成一个动作。\n"
    "5. 贴着这个焦点者看见、听见、摸到的写，不替别人想。\n"
    "6. 书里的人不知道自己在章里。不要升华，不要说教。\n"
    "7. 世界按这本书已经立下的规矩变贵，不许另造一套。"
)


def _volume_ledger_block(ctx: dict) -> str:
    body = (ctx or {}).get("volume_ledger") or "（无）"
    return f"【本卷还要办的】\n{VOLUME_LEDGER_DISCIPLINE}\n{body}"


def _forbid_bits(ctx: dict) -> str:
    d = (ctx or {}).get("duty") if isinstance((ctx or {}).get("duty"), dict) else {}
    bits = (ctx or {}).get("forbidden_reveal") or d.get("forbidden_reveal") or (ctx or {}).get("secret_list") or "（无）"
    return bits


def _iron_enabled() -> bool:
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy("SCRIBE3_IRON_RULES_DUAL_ANCHOR")
    except Exception:
        return True


def _letter_grid_block(ctx: dict) -> str:
    letter = str((ctx or {}).get("revision_letter_digest") or "").strip()
    grid = str((ctx or {}).get("scene_grid") or "").strip()
    skills = (ctx or {}).get("craft_skills") or []
    note = str((ctx or {}).get("safety_note") or "").strip()
    parts: list[str] = []
    if note:
        parts.append(note)
    if letter:
        parts.append(f"上章问诊还没做完的事：{letter[:400]}")
    if grid:
        parts.append(f"这一场戏格：{grid[:400]}")
    if skills:
        parts.append("必须用上的技法：" + "、".join(str(s) for s in skills if s))
    return ("\n".join(parts) + "\n") if parts else ""


def _iron_head(ctx: dict) -> str:
    extra = _letter_grid_block(ctx)
    if not _iron_enabled():
        return extra
    return f"【今晚钉住】\n{IRON_RULES}\n今晚还不能拆穿：{_forbid_bits(ctx)}\n{extra}"


def _iron_tail(ctx: dict) -> str:
    if not _iron_enabled():
        return ""
    return (
        f"\n写完再核一次：今晚还不能拆穿的事（{_forbid_bits(ctx)}）有没有漏出去？"
        "后面几章的夜有没有提前演完？\n"
    )


def duty_generate(ctx: dict) -> str:
    return f"""你在为第 {ctx.get("seq")} 章立"责任"——这一章必须办成的事。
这份责任卡直接驱动下游写戏：写戏的严格按你立的来，立歪了整章歪。
{_iron_head(ctx)}{craft_generate_block()}
【全书定位】
卷纲：{ctx.get("volume_outline") or "（无）"}
北极星：{ctx.get("north_star") or "（无）"}
【本章责】{ctx.get("chapter_duty") or "（无）"}
{_volume_ledger_block(ctx)}

【本章焦点者】{ctx.get("focalizer") or "（未指定）"}（这一章贴着谁的视角走）
【上一章章末留下的钩子】（原文，必须接住）
{ctx.get("prev_hook_quote") or "（第1章无上章钩子）"}
【上一章没翻的处境】（这场还得过；只接钩子不算）
{ctx.get("prev_stay") or "（第1章无上场处境）"}
【上一章热闹像翻了的那一层】（这场不得同一套）
{ctx.get("prev_heat") or "（第1章无上场热闹）"}
【上一章日子种类】{ctx.get("prev_kind") or "（第1章无）"}　闯进来的人：{ctx.get("prev_intruder") or "（无）"}
【近 3 章的责任】（避免连续同类型账单）
{ctx.get("recent_duty_summary") or "（无）"}
【户口：可用的人】{_cast_line(ctx)}
【可绑的线】{ctx.get("available_lines") or []}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}
{_pov_line(ctx)}
【全书意象域】{_imagery_line(ctx)}
【相关设定】{ctx.get("codex_recall") or "（无）"}
【全书秘密清单】{ctx.get("secret_list") or []}

立十三件事：
1. day——还在过的日子。检验：读者能不能看见人正在过什么（排队、过秤、喜酒还没散），而不是报身份。
   开篇报身份、扔钩子、先宣布法会 = 废卡。
2. said——嘴上要的那一件（他开口要的、装出来的）。
3. needed——真正缺的那一件（日子里少了什么、他不敢说的）。
   said 和 needed 必须打架。鉴定式人设、杯子余温、剖心 = 废卡。
4. mask / crack / real——先给反面，再破功，再落真意。三句不能同一句。上来掏底牌 = 废卡。
5. eye / dist——眼睛交给谁。共情就交给当场那个人，dist=near。
   人还在办事时报年号、铺戒律、上课 = 废卡。要人旁观才写 dist=far。
6. cut——热过再冷，切在能听见看见的那一下（一声响、门开、杯子落地）。
   切在叹气、夜色深了、他决定了 = 废卡。
7. one_line / keep——一行本事是什么；删了场会塌的那一截必须另写。
   两句不能同一句。写成过场即可 / 说明书 = 废卡。
8. heat / stay——热闹像翻了的那一层；处境还停在哪。两句不能同一句。
   热闹不算翻。场面过了就算翻 = 废卡。
   第2章起 heat 不得和上场同一套。假翻不犯同一种热闹。
   第2章起还要写 owed：上场没翻的处境这场还在过。只接章末钩子、把上场 stay 清掉 = 废卡。
   kind 必填：酒宴 / 赶路 / 开坛 / 坐牢 / 同场。只换节号 = 废卡。连写同一种必须换谁闯进来（intruder）。
   同场连写超两场 = 废卡。必须换五套局里另一套，人从这儿走到那儿。
   kind=开坛：必须看见交差钱把人按住；热闹当社戏信了；井/灯/墓还在。高人下山伏魔 = 废卡。开坛做法是日子，不是宣布法会。
   kind=酒宴：必须先立还散不掉的酒；面子把人按在桌上；有人闯进来；嘴上贺、账还欠着。不要字面抄「那一桌」。先宣布法会再补喜事 = 废卡。
   kind=坐牢：必须先立进城/镇上找活路；官差收了东西改口；救人的人进了绳。藏东西的人进绳 = 废卡。清官断案、点名黑白 = 废卡。不要字面抄六百两。
   bill_holder / bill_place 必填。换气换丢人 = 废卡。声称转走却人地都没换 = 废卡。
9. must_happen——本章必须办的一件事。必须从 day 里长出来，用办事说。
   检验：能不能用一个动作说清（谁在什么物件上做什么）？
10. bill——本章的账：办成这件事必须付出的、收不回来的东西。
   账必须从这章的具体处境里长出来，不是从类型里挑一个。
11. who——在场做事的人，只能从户口里选。
   除焦点者外，至少还要有一个有意志的人（对手/同伴/旁观者——能说话或能对抗的）。
   整章只有焦点者一个人的责任卡，不成立。
12. forbidden_reveal——从秘密清单里选本章还不能揭的。
13. 第二人要能在这场戏里做事，不能只站着。
{_iron_tail(ctx)}
输出 JSON（不输出任何别的文字）：
{{"day": "还在过的日子", "said": "嘴上要的", "needed": "真正缺的",
 "mask": "先给的反面", "crack": "破功的那一下", "real": "破完才落的真意",
 "eye": "眼睛交给谁", "dist": "near 或 far",
 "cut": "切在能听见看见的那一下",
 "one_line": "一行本事", "keep": "删了场会塌的那一截",
 "heat": "热闹像翻了的那一层", "stay": "处境还停在哪",
 "owed": "上场没翻的处境这场还在过（第1章空）",
 "kind": "酒宴或赶路或开坛或坐牢或同场",
 "intruder": "这场闯进来的人（同一种日子必填）",
 "bill_holder": "这笔账此刻在谁手里",
 "bill_place": "这笔账此刻在哪一处",
 "must_happen": "...", "bill": "...", "who": ["..."],
 "forbidden_reveal": ["..."], "line_to_touch": "线id 或 null"}}
"""


def duty_judge_v2(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【卷纲】{ctx.get("volume_outline") or "（无）"}
【本章责】{ctx.get("chapter_duty") or "（无）"}
{_volume_ledger_block(ctx)}
【近 3 章的责任】{ctx.get("recent_duty_summary") or "（无）"}
【上一章章末钩子】{ctx.get("prev_hook_quote") or "（第1章无）"}
【上一章没翻的处境】{ctx.get("prev_stay") or "（第1章无）"}
【上一章热闹像翻了的那一层】{ctx.get("prev_heat") or "（第1章无）"}

七问：
1. day 是还在过的日子吗？must_happen 是不是从日子里长出来的可演动作？开篇报身份/扔钩子/先宣布法会 → 不过。嘴上要的和真正缺的打架了吗？鉴定式人设/剖心 → 不过。先给了反面再破功吗？上来掏底牌 → 不过。眼睛交给当场那个人了吗？人还在办事时报年号/上课 → 不过。切在能听见看见的那一下了吗？切在叹气/夜色深了 → 不过。一行本事说不完吗？删了会塌的那截另写了吗？写成过场即可 → 不过。热闹像翻了、处境还停在原处吗？热闹当翻 → 不过。上场没翻的处境这场还在过吗？只接钩子、把上场 stay 清掉 → 不过。热闹和上场同一套 → 不过。日子种类写了吗？只换节号或同一种不换谁闯进来 → 不过。账在谁手里、在哪一处写了吗？换气换丢人、声称转走人地没换 → 不过。kind=开坛 看见交差钱了吗？热闹当社戏信了吗？井/灯/墓还在吗？高人下山伏魔 → 不过。kind=坐牢 先立进城/镇上找活路了吗？官差收了东西改口了吗？救人的人进绳了吗？清官断案、点名黑白 → 不过。
2. bill 是不是一笔收不回来的账（不是"付出代价"这种空话）？
3. 这份责任和近 3 章的账单同类型吗？（同质 → 不过。换了日子种类——酒宴/赶路/开坛/坐牢——不算同质。）
4. 这份责任接住上一章的钩子了吗？（字符串核对是机器的事，你只判「责任与钩子有没有关系」）
5. forbidden_reveal 有没有漏掉"照这章的写法极可能说漏嘴"的秘密？
6. 这章除了焦点者，有没有第二个有意志的在场者？（能说话或能对抗；远远看着不算）
7. 打开本卷还要办的几笔：这份责任是不是第 {ctx.get("seq")} 章该办的那一笔？后面的可以挂着当没做完的事。有没有把后面某章的夜提前写成了这一夜？

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def duty_judge(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【卷纲】{ctx.get("volume_outline") or "（无）"}
【本章责】{ctx.get("chapter_duty") or "（无）"}
{_volume_ledger_block(ctx)}
【近 3 章的责任】{ctx.get("recent_duty_summary") or "（无）"}
【上一章章末钩子】{ctx.get("prev_hook_quote") or "（第1章无）"}
【上一章没翻的处境】{ctx.get("prev_stay") or "（第1章无）"}
【上一章热闹像翻了的那一层】{ctx.get("prev_heat") or "（第1章无）"}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}
【全书意象域】{_imagery_line(ctx)}

八问：
1. day 是还在过的日子吗？must_happen 是不是从日子里长出来的可演动作（不是情绪/方向/主题）？开篇报身份/扔钩子/先宣布法会 → 不过。嘴上要的和真正缺的打架了吗？鉴定式人设/剖心 → 不过。先给了反面再破功吗？上来掏底牌 → 不过。眼睛交给当场那个人了吗？人还在办事时报年号/上课 → 不过。切在能听见看见的那一下了吗？切在叹气/夜色深了 → 不过。一行本事说不完吗？删了会塌的那截另写了吗？写成过场即可 → 不过。热闹像翻了、处境还停在原处吗？热闹当翻 → 不过。上场没翻的处境这场还在过吗？只接钩子、把上场 stay 清掉 → 不过。热闹和上场同一套 → 不过。日子种类写了吗？只换节号或同一种不换谁闯进来 → 不过。账在谁手里、在哪一处写了吗？换气换丢人、声称转走人地没换 → 不过。kind=开坛 看见交差钱了吗？热闹当社戏信了吗？井/灯/墓还在吗？高人下山伏魔 → 不过。kind=坐牢 先立进城/镇上找活路了吗？官差收了东西改口了吗？救人的人进绳了吗？清官断案、点名黑白 → 不过。
2. bill 是不是一笔收不回来的账（不是"付出代价"这种空话）？
3. 这份责任和近 3 章的账单同类型吗？（同质 → 不过。换了日子种类——酒宴/赶路/开坛/坐牢——不算同质。）
4. 这份责任接住上一章的钩子了吗？（字符串核对是机器的事，你只判「责任与钩子有没有关系」）
5. forbidden_reveal 有没有漏掉"照这章的写法极可能说漏嘴"的秘密？
6. 这章除了焦点者，有没有第二个有意志的在场者？（能说话或能对抗；远远看着不算）
7. 这章摸起来还是这本书吗？（全书意象域未设则本问 yes；若这章要跨到另一个世界的质感，责任卡必须先在场上放一个同时属于两个世界的物件作桥，否则 no）
8. 打开本卷还要办的几笔：这份责任是不是第 {ctx.get("seq")} 章该办的那一笔？后面的可以挂着当没做完的事。有没有把后面某章的夜提前写成了这一夜？{PACE_EXEMPT}

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def play_generate(ctx: dict) -> str:
    d = ctx.get("duty") or {}
    return f"""写第 {ctx.get("seq")} 章的戏。这是给全书定"这一章发生什么"的一篇短戏，不是给读者的正文。
{_iron_head(ctx)}{craft_generate_block()}
【本章责任】（责任卡已冻结，严格照此写，不得另办一件事）
- 还在过的日子：{d.get("day")}
- 嘴上要的：{d.get("said")}
- 真正缺的：{d.get("needed")}
- 先给的反面：{d.get("mask")}
- 破功的那一下：{d.get("crack")}
- 破完才落的真意：{d.get("real")}
- 眼睛交给：{d.get("eye")}
- 远近：{d.get("dist")}
- 切在哪一下：{d.get("cut")}
- 一行本事：{d.get("one_line")}
- 删了会塌的那截：{d.get("keep")}
- 热闹像翻了：{d.get("heat")}
- 处境还停在：{d.get("stay")}
- 上场还欠着：{d.get("owed")}
- 日子种类：{d.get("kind")}　闯进来的人：{d.get("intruder")}
- 账在谁手里：{d.get("bill_holder")}　在哪一处：{d.get("bill_place")}
- 要办的一件事：{d.get("must_happen")}
- 要付的账：{d.get("bill")}
- 在场做事的人：{d.get("who")}
- 必须接住的上章钩子：{d.get("bite_from_prev")}
- 禁止拆穿的事：{d.get("forbidden_reveal")}
- 本章焦点者：{d.get("focalizer")}（贴着这个人的处境写）
{_volume_ledger_block(ctx)}

【可用的人】{_cast_line({**ctx, "available_cast": d.get("available_cast") or ctx.get("available_cast")})}（编造户口外的人 = 废稿）
【上一章结束时世界变成了什么样】（身体、物件位置、未了的悬念——不得写拧）
{_state_json(ctx)}
{_pov_line(ctx)}
【相关设定】{ctx.get("codex_recall") or "（无）"}（设定以外的东西不许发明）
【近 3 章已经发生的戏】{ctx.get("recent_scene_summary") or "（无）"}（避免连着写同一场）

怎么写：
1. 400-900 字。这是设计图，不是给读者朗读的一章。不写标签、不写表格、不分场标题。
2. 点出一个具体场面：先给反面、再破功、账当场怎么付、章末悬着哪一件没做完的事。
   每件留一句能被契约原样引用的钉子。不要把场面铺成正文。
3. 对白最多一两句关键的。完整声口和对白留给糙稿。
4. 假破真是这章的骨头：先让人信反面，再破，真意才落。上来掏底牌 = 废稿。
5. 共情就把眼睛交给当场那个人。人还在办事时报年号、铺戒律、上课 = 废稿。要人旁观才站外头。
6. 热过再冷，切在能听见看见的那一下。切在叹气、夜色深了 = 废稿。
7. 一行本事说不完。删了场会塌的那一截必须写上。写成过场即可 = 废稿。
8. 热闹不算翻。热闹像翻了、处境还停在原处 = 废稿。上场没翻的处境这场还得过，只接钩子不算。热闹不得和上场同一套。
9. 破要落成动作（他做了什么），不是态度（他想了什么）。
10. 账要当场付：责任卡上那笔账，必须兑成一个可引用原句的具体动作
   （谁拿走了什么/谁失去了什么），不许用旁白概括。
11. 章末留一件没做完的事——让读者想翻页的那件。
12. 禁止拆穿 {d.get("forbidden_reveal")}。
13. 必须有对手拍：第二个有意志的人与焦点者发生正面交互
   （对话/对抗/交易/回避都算，远远看着不算）。
14. 禁止元叙述。元叙述包括：提及"章"本身（上一章/这一章/下一章/前章——
   书中人物不知道自己在章里）、谈论写作行为、主题词说教（命运/选择/代价，
   除非角色说出口）。

写完自己读一遍：
- 如果这页已经能当正文交给读者 → 删到只剩钉子，重写。
- 如果你只能用"他想通了/他决定了"来概括这章 → 重写。
- 如果删掉任何一个在场的人这章照样成立 → 那个人就不该在场。
{_iron_tail(ctx)}
"""


def play_judge_v2(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【戏】{ctx.get("play_text")}
{_volume_ledger_block(ctx)}

你是审稿的，不是改稿的——先判，判不过才写意见。
九问，每问必须先从戏里引用原句作证据，再给"yes/no"：

1. 责任里点名的人都在场做事吗？（站着看的不算）
2. 办的是责任卡上那件事吗？（办岔了、办多了都算不过）
3. 责任卡上那笔账，戏里真付出去了吗？引"付出"的原句——
   引不出字面原句，或引出的只是"他付出了代价"式旁白，一律 no。
4. 戏里有没有至少一个具体场面（具体时空中的动作与对话），还是通篇概括叙述？眼睛交给当场那个人了吗？人还在办事时报年号/上课 → no。热过再冷切在能听见看见的那一下了吗？切在叹气/夜色深了 → no。删了会塌的那一截写上了吗？整场能一行本事说完 → no。热闹像翻了、处境还停在原处吗？热闹当翻 → no。
5. 先给了反面再破功吗？上来掏底牌、先把真意说穿 → no。
6. 破完真意落成具体动作了吗？（他做了什么，不是他想了什么）
7. 章末有没有一件没做完的事？（能抄出原句的、悬着的那件——"夜色深了"式氛围收尾不算）
8. 有没有提前拆穿禁止拆穿的事？
9. 这场戏有没有把本卷后面的夜提前演完？章末挂着没做完的事不算演完。

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def play_judge(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【戏】{ctx.get("play_text")}
{_volume_ledger_block(ctx)}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}

你是审稿的，不是改稿的——先判，判不过才写意见。
十二问，每问必须先从戏里引用原句作证据，再给"yes/no"：

1. 责任里点名的人都在场做事吗？（站着看的不算）
2. 办的是责任卡上那件事吗？（办岔了、办多了都算不过）
3. 责任卡上那笔账，戏里真付出去了吗？引"付出"的原句——
   引不出字面原句，或引出的只是"他付出了代价"式旁白，一律 no。
4. 戏里有没有至少一个具体场面（具体时空中的动作与对话），还是通篇概括叙述？眼睛交给当场那个人了吗？人还在办事时报年号/上课 → no。热过再冷切在能听见看见的那一下了吗？切在叹气/夜色深了 → no。删了会塌的那一截写上了吗？整场能一行本事说完 → no。热闹像翻了、处境还停在原处吗？热闹当翻 → no。
5. 先给了反面再破功吗？上来掏底牌、先把真意说穿 → no。
6. 破完真意落成具体动作了吗？（他做了什么，不是他想了什么）
7. 章末有没有一件没做完的事？（能抄出原句的、悬着的那件——"夜色深了"式氛围收尾不算）
8. 有没有提前拆穿禁止拆穿的事？
9. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
10. 上章记下、到这章该响的悬念，这章戏里碰到了吗？（没有到期条目则 yes）
11. 这章戏里新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）
12. 这场戏有没有把本卷后面的夜提前演完？章末挂着没做完的事不算演完。{PACE_EXEMPT}

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def contract_extract(ctx: dict) -> str:
    hint = str(ctx.get("struct_hint") or "").strip()
    hint_block = (
        f"\n【上一稿没过，照这个改】{hint}\n"
        "quote 必须是戏里字面连续原句。找不到就换一句能找到的，禁止编。\n"
        if hint else ""
    )
    return f"""下面这篇戏已经过审冻结。你要从戏里抄出契约。{hint_block}

铁律：
1. 每个字段的 quote 必须是戏里字面出现的连续原句，10-50 字，一个标点都不许改。
   只许截取，不许编辑：不许裁前缀（「我希望你今晚」不得改成「你今晚」），
   截取起点必须落在句首或标点之后，不得从句中腰斩。
   输出前把每个 quote 拿回戏里找一遍：找不到，就换一句能找到的。
   不许删掉原句中间的「某某说」——删了就对不上。
2. 戏里没有的东西（人、物、线、账）禁止补。
3. clock/place 戏里没明写才留空（null），禁止编。
   cost 不同：戏里只要有人当场失去/被拿走的那一句，就必须抄进 fields.cost，
   禁止仍写 null。编一句不在戏里的账 = 废稿。
4. beats ≥3 场（通常 3-5 场，按戏的自然台阶走），只有一场 stages_choice=true——
   他真正站在两难前的那场。那一场的 conflict 必须抄对手与焦点者对上的原句，
   禁止 null。
5. choice 的 quote 是他【还没选】时的那句两难，不是选完之后的总结。
6. decision 的 quote 是他迈出去的那一步（动作句）。
7. hook 的 quote 是章末那句没做完的事。

输出 JSON（严格按 schema，不输出任何别的文字）：
{{"fields": {{"goal": {{"text": "", "quote": ""}},
 "choice": {{"text": "", "quote": "",
   "side_a": {{"text": "", "quote": ""}},
   "side_b": {{"text": "", "quote": ""}}}},
 "decision": {{"text": "", "quote": ""}},
 "cost": {{"text": "", "quote": ""}},
 "hook": {{"text": "", "quote": ""}}}},
 "beats": [{{"n": 1, "goal": {{"text": "", "quote": ""}},
   "conflict": {{"text": "", "quote": ""}}, "turn": {{"text": "", "quote": ""}},
   "cost": null, "stages_choice": false}}],
 "lines_touched": [],
 "clock": null,
 "place": null}}

【戏】
{ctx.get("play_text")}
"""


def contract_judge(ctx: dict) -> str:
    return f"""【戏】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}

三问，每问先引用契约原句和戏原句作证据：
1. 完整性：先列出戏里你认为最重要的 3 件事（各引一句戏原文），再逐一指认它们
   落在契约的哪个字段；指认不出的就是漏。
2. 忠实性：契约里每个 text 忠实于其 quote 吗？（没有添油加醋或歪曲）
3. 戏里那笔账的兑现句，在契约 cost 字段登记了吗？（戏里有而契约留空 = 漏抽，fail）

{VERDICT_SCHEMA}
"""


def deduce_generate(ctx: dict) -> str:
    return f"""基于这场戏，写水面下。戏是水面上发生的那一件；演绎是字缝里的算盘。

打开这段，读者应该看见：谁在心里要一件对方不知道的事、谁瞒了谁、
哪一件读者能拼出来而角色拼不出。不要上帝视角复盘，不要分析报告，
不要把这场戏再讲一遍。

【戏】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}
【各角色截至上一章的所知所信】
{ctx.get("characters_epistemic_history") or "（无）"}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}

该在场的人各写各的：看见听到了什么、知道什么、以为自己在干什么、做了说了什么、没察觉什么。
「以为」和「没察觉」必须能对上这场戏——有人看错，或有人各怀打算谁也不点破。
禁止拆穿的事不得写进任何人的「知道」。
不得与上一章已经知道的事拧。

输出 JSON：
{{"scene_truth": "字缝里那一件（读者能拼、角色拼不出）",
 "characters": [{{"id": "", "perceived": "", "known": "", "believed": "", "acted": "", "blind": ""}}],
 "ore": ["可选：能写进正文的一件具体物"]}}
"""


def deduce_judge(ctx: dict) -> str:
    return f"""【戏】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}
【演绎】{ctx.get("deduction_json")}
【各角色历史限知】{ctx.get("characters_epistemic_history") or "（无）"}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}

你是审稿的。问的是打开这段看见什么，不是格子填没填。

1. 字缝里那一件在不在？读者能拼、角色拼不出的那件事发生了没有？（复述水面、分析报告、KPI/取证腔 = 不在）
2. 该在场的人有没有各怀打算？全员透明、只当家具 = 不过。
3. 是这场戏的水面下吗？另一场、预演正文、把契约再讲一遍 = 不过。
4. 禁止拆穿的事有没有写进某人的「知道」？
5. 上一章已经知道的事，这章有没有写成不知道？

{VERDICT_SCHEMA}
"""


def draft_generate(ctx: dict) -> str:
    bite = ctx.get("bite_quote") or ctx.get("prev_hook_quote") or "（无）"
    hint = str(ctx.get("struct_hint") or "").strip()
    hint_block = (
        f"\n【上一稿没过，照这个改，不要只换词】{hint}\n" if hint else ""
    )
    return f"""按这场戏和演绎，写一遍糙稿。场面立住就停，不要为凑字注水。{hint_block}
{_iron_head(ctx)}{craft_generate_block()}
【戏（设计图，不是文）】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}
【演绎（矿与限知，施工材料）】{ctx.get("deduction_json")}
【上一章结束时世界变成了什么样】（身体、物件位置、未了的悬念——不得写拧）
{_state_json(ctx)}
{_pov_line(ctx)}

戏是设计图，糙稿是施工。戏里的句子是给创作者看的，不是给读者看的。
你交付的糙稿必须比戏多出三样东西：
1. 对白——戏里"谁说了什么"的概括，在糙稿里落成带引号的原话。
2. 感官施工——从演绎的矿里取料。这一场要有此刻能摸到或听到的东西；没有，就还是说明书。
3. 内心电阻——焦点者在两难前的具体迟疑（动作化的，不是"他想"）。

增量纪律：
- 这场里的两难、决断和账还要演完。设计图里的句子不要搬来凑。
  章首咬住上章钩子：{bite}。
- 戏的场面顺序照走，但语言全部重写。

必须做到：
1. 贴着焦点者 {ctx.get("focalizer") or ""} 写。
2. 两难要演到那个瞬间。
3. 决断落成具体动作；账当场付出，付出要占足篇幅（≥150 字），一笔带过不算付。
4. 章末钩子悬着——用场面收，不得直接抄写契约 hook 原文当末句。
5. 用演绎里的矿；不另造设定性细节。

禁令：
- 禁止元叙述。元叙述包括：提及"章"本身（上一章/这一章/下一章/前章——
  书中人物不知道自己在章里）、谈论写作行为、主题词说教（命运/选择/代价，
  除非角色说出口）。
- 禁止章末升华。
- 禁止泄露 {ctx.get("forbidden_reveal") or []}。
- 禁止上帝视角乱跳。
- 明喻（像/仿佛/似的）全文至多每 800 字一个；能用直陈就不用比喻。
  宁可写「黑线贴着静脉走」，不要写「像细铁丝」。
  写完自己数：「像/仿佛/似的」超标，整篇作废重写。字数不够不是废稿理由。
{_iron_tail(ctx)}
"""


def draft_judge(ctx: dict) -> str:
    return f"""【排演】{ctx.get("draft_text")}
【契约】{ctx.get("contract_json")}
【演绎（限知与矿）】{ctx.get("deduction_json")}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}

十一问：
1. 两难演了吗？能不能在排演里指出"他还没选"的那个瞬间？
2. 决断落了吗？他选的那边变成了一个具体动作吗（不是"他决定"）？
3. 代价付了吗？契约里那笔账在排演里真付出了吗？
4. 有没有泄露禁止拆穿的事？
5. 有没有章末升华或元叙述（含"上一章/这一章/下一章"）？
6. 视角守住焦点者限知了吗？
7. 是连续场面还是概括叙述？{PACE_EXEMPT}
8. 把糙稿和戏并排放：删掉戏里已有的句子，糙稿还剩实质内容吗？
   （引一处糙稿有而戏没有的对白或感官细节作证据）
9. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
10. 上章记下、到这章该响的悬念，这章碰到了吗？（没有到期条目则 yes）
11. 这章新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def final_generate(ctx: dict) -> str:
    cost_line = ""
    if ctx.get("cost_text"):
        cost_line = f"- 要付的账：{ctx.get('cost_text')}\n"
    hint = str(ctx.get("struct_hint") or "").strip()
    hint_block = (
        f"\n【上一稿没过，照这个改，不要只换词】{hint}\n" if hint else ""
    )
    return f"""把这份糙稿打磨成正文（面向读者的最终文本）。{hint_block}
{_iron_head(ctx)}{craft_generate_block()}
【糙稿（蓝本，结构照此）】{ctx.get("draft_text")}
【本章必须兑现的】
- 要办的事：{ctx.get("goal_text")}
- 两难：{ctx.get("choice_text")}
- 决断：{ctx.get("decision_text")}
- 章末钩子：{ctx.get("hook_text")}
{cost_line}【演绎（细节矿与限知，供取用）】{ctx.get("deduction_json")}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}
【上一章正文结尾】{ctx.get("prev_prose_tail") or "（无）"}
【声纹】{ctx.get("voice_anchor_block") or "（无）"}
【相关设定】{ctx.get("codex_recall") or "（无）"}
【上一章结束时世界变成了什么样】（身体、物件位置、未了的悬念——不得写拧）
{_state_json(ctx)}

打磨什么：
- 语言：删掉糙话。画面和声音要自己立起来；立不起来宁可糙着。
- 对话：贴每个角色的声纹。
- 节奏：场面内部该快的快该慢的慢（不设字数配额）。

不改什么：
- 结构上的一件事、两难、决断、账、钩子，照糙稿。
- 禁止拆穿的事，依然禁止。

禁令：
- 章末升华/感悟收尾。
- 同类比喻连续两段出现。全文明喻（像/仿佛/似的）≤ 每 800 字 1 个；
  两处例外：角色对白内、契约 quote 必须保留的原句。
- 元叙述（提及"上一章/这一章/下一章/本章"；"命运""选择""代价"这些词
  不进叙述层，除非角色说出口）。
- 复述排演的叙述原句（对话若已是声口对的原句可保留）。
- 泄露禁止拆穿的事。
{_iron_tail(ctx)}
"""


def final_judge_v2(ctx: dict) -> str:
    return f"""【正文】{ctx.get("prose_text")}
【契约核心四件+账】{ctx.get("contract_core_json")}
【演绎（限知）】{ctx.get("deduction_epistemic")}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}
【禁止清单】{ctx.get("ban_list") or "升华/连续同类比喻/元叙述/泄密"}

五问，每问先引正文原句作证据：
1. 契约四件（事/两难/决断/钩子）在正文里都兑现了吗？账（若契约有 cost）仍真付着吗？
2. 视角守住焦点者限知了吗？
3. 有没有踩禁令（升华/连续同类比喻/元叙述/泄密）？明喻是否密过每 800 字一个？
4. 这章读得下去吗？——一口气读下来，有没有哪里你会跳行？
5. 正文里有没有出现"上一章/这一章/下一章"这类章边界词？（引原句；有则 no）

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def final_judge(ctx: dict) -> str:
    return f"""【正文】{ctx.get("prose_text")}
【契约核心四件+账】{ctx.get("contract_core_json")}
【演绎（限知）】{ctx.get("deduction_epistemic")}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}
【禁止清单】{ctx.get("ban_list") or "升华/连续同类比喻/元叙述/泄密"}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}
【机器先检出的装腔原句（给法官当底，不必点名这些词才能过）】
{ctx.get("syntax_tics_block") or "无"}
【这一章句子长短（只给人看，不据此判过不过）】
{ctx.get("rhythm_block") or "无"}

八问，每问先引正文原句作证据：
1. 契约四件（事/两难/决断/钩子）在正文里都兑现了吗？账（若契约有 cost）仍真付着吗？
2. 视角守住焦点者限知了吗？
3. 有没有踩禁令（升华/连续同类比喻/元叙述/泄密）？明喻是否密过每 800 字一个？正文里有没有出现"上一章/这一章/下一章"这类章边界词？（有则 no）
4. 把开头念出声。第一处让你卡住的句子引出来。没有就说没有。
5. 有没有哪句是作者在使劲，不是人在做事？引出来。没有就说没有。{PACE_EXEMPT}
6. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
7. 上章记下、到这章该响的悬念，这章碰到了吗？（没有到期条目则 yes）
8. 这章新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）

{craft_judge_block()}
{VERDICT_SCHEMA}
"""


def state_extract(ctx: dict) -> str:
    seq = ctx.get("seq") or 0
    return f"""下面这篇已经过审的正文。你是场记，只抄不编。

你要登记的是：这章写完时，世界变成了什么样。
不是下一章必须发生什么。

铁律：
1. 每条人物/物件状态必须带 quote：正文里字面出现的连续原句，10-50 字。找不到原句的状态不许写。
2. 性别从户口或上章末态抄，禁止根据本章代词改写。
3. 上一章未了的悬念：对照正文，已经碰到的删掉；还悬着的原样保留；本章新悬的补上。到期章号没写就按开始章+3。
4. 这是这章结束时的完整快照，不是和上一章的差量。
5. narrative_pov 不要自己编，系统会按叙述层的「我」测定；你可抄上章的值。

【户口（含性别）】{_cast_line(ctx)}
【上一章章末态】
{_state_json(ctx)}
【本章正文】
{ctx.get("source_text") or ""}

输出 JSON（不输出任何别的文字）：
{{"seq": {seq},
  "characters": [{{"name": "", "gender": "男或女或空", "state": "", "quote": ""}}],
  "objects": [{{"name": "", "location": "", "state": "", "quote": ""}}],
  "open_loops": [{{"text": "", "from_seq": 1, "due_seq": 4}}],
  "timeline": {{"at": "", "elapsed_from_prev": ""}},
  "imagery": ["..."],
  "narrative_pov": "first 或 third"}}
"""


def identity_for(kind: str) -> str:
    if kind == "duty":
        return IDENTITY_DUTY
    if kind == "play":
        return IDENTITY_PLAY
    if kind in ("contract", "state"):
        return IDENTITY_SCRIBE
    if kind.endswith("_judge") or kind == "judge":
        return IDENTITY_JUDGE
    return IDENTITY_NOVELIST


assert PLAYBOOK_VERSION == "playbook.3.2.25"
