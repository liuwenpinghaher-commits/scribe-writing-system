"""playbook.3.2 identity + generate/judge prompts. Changing this file requires a version bump."""
from __future__ import annotations

import json

from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.schema import snapshot_body

IDENTITY_NOVELIST = (
    "你是一个写了二十年长篇类型小说的小说家。你从不写提纲式概括，你写场面："
    "具体的时间、具体的地方、人在做什么说什么。你写的时候心里装着读者："
    "读完这章，要能说出发生了什么、谁付出了什么、还想不想翻下一页。"
)
IDENTITY_DUTY = "你是这本书的主编剧，管整本书的账房：每章办什么事、付什么账，你说了算。"
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


def duty_generate(ctx: dict) -> str:
    return f"""你在为第 {ctx.get("seq")} 章立"责任"——这一章必须办成的事。
这份责任卡直接驱动下游写戏：写戏的严格按你立的来，立歪了整章歪。

【全书定位】
卷纲：{ctx.get("volume_outline") or "（无）"}
北极星：{ctx.get("north_star") or "（无）"}

【本章焦点者】{ctx.get("focalizer") or "（未指定）"}（这一章贴着谁的视角走）
【上一章章末留下的钩子】（原文，必须接住）
{ctx.get("prev_hook_quote") or "（第1章无上章钩子）"}
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

立五件事：
1. must_happen——本章必须办的一件事。
   检验：能不能用一个动作说清（谁在什么物件上做什么）？
2. bill——本章的账：办成这件事必须付出的、收不回来的东西。
   账必须从这章的具体处境里长出来，不是从类型里挑一个。
3. who——在场做事的人，只能从户口里选。
   除焦点者外，至少还要有一个有意志的人（对手/同伴/旁观者——能说话或能对抗的）。
   整章只有焦点者一个人的责任卡，不成立。
4. forbidden_reveal——从秘密清单里选本章还不能揭的。
5. 第二人要能在这场戏里做事，不能只站着。

输出 JSON（不输出任何别的文字）：
{{"must_happen": "...", "bill": "...", "who": ["..."],
 "forbidden_reveal": ["..."], "line_to_touch": "线id 或 null"}}
"""


def duty_judge_v2(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【卷纲】{ctx.get("volume_outline") or "（无）"}
【近 3 章的责任】{ctx.get("recent_duty_summary") or "（无）"}
【上一章章末钩子】{ctx.get("prev_hook_quote") or "（第1章无）"}

六问：
1. must_happen 是不是一个可演的具体动作（不是情绪/方向/主题）？
2. bill 是不是一笔收不回来的账（不是"付出代价"这种空话）？
3. 这份责任和近 3 章的账单同类型吗？（同质 → 不过）
4. 这份责任接住上一章的钩子了吗？（字符串核对是机器的事，你只判「责任与钩子有没有关系」）
5. forbidden_reveal 有没有漏掉"照这章的写法极可能说漏嘴"的秘密？
6. 这章除了焦点者，有没有第二个有意志的在场者？（能说话或能对抗；远远看着不算）

{VERDICT_SCHEMA}
"""


def duty_judge(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【卷纲】{ctx.get("volume_outline") or "（无）"}
【近 3 章的责任】{ctx.get("recent_duty_summary") or "（无）"}
【上一章章末钩子】{ctx.get("prev_hook_quote") or "（第1章无）"}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}
【全书意象域】{_imagery_line(ctx)}

七问：
1. must_happen 是不是一个可演的具体动作（不是情绪/方向/主题）？
2. bill 是不是一笔收不回来的账（不是"付出代价"这种空话）？
3. 这份责任和近 3 章的账单同类型吗？（同质 → 不过）
4. 这份责任接住上一章的钩子了吗？（字符串核对是机器的事，你只判「责任与钩子有没有关系」）
5. forbidden_reveal 有没有漏掉"照这章的写法极可能说漏嘴"的秘密？
6. 这章除了焦点者，有没有第二个有意志的在场者？（能说话或能对抗；远远看着不算）
7. 这章摸起来还是这本书吗？（全书意象域未设则本问 yes；若这章要跨到另一个世界的质感，责任卡必须先在场上放一个同时属于两个世界的物件作桥，否则 no）

{VERDICT_SCHEMA}
"""


def play_generate(ctx: dict) -> str:
    d = ctx.get("duty") or {}
    return f"""写第 {ctx.get("seq")} 章的戏。这是给全书定"这一章发生什么"的一篇短戏，不是给读者的正文。

【本章责任】（责任卡已冻结，严格照此写，不得另办一件事）
- 要办的一件事：{d.get("must_happen")}
- 要付的账：{d.get("bill")}
- 在场做事的人：{d.get("who")}
- 必须接住的上章钩子：{d.get("bite_from_prev")}
- 禁止拆穿的事：{d.get("forbidden_reveal")}
- 本章焦点者：{d.get("focalizer")}（贴着这个人的处境写）

【可用的人】{_cast_line({**ctx, "available_cast": d.get("available_cast") or ctx.get("available_cast")})}（编造户口外的人 = 废稿）
【上一章结束时世界变成了什么样】（身体、物件位置、未了的悬念——不得写拧）
{_state_json(ctx)}
{_pov_line(ctx)}
【相关设定】{ctx.get("codex_recall") or "（无）"}（设定以外的东西不许发明）
【近 3 章戏的场面类型】{ctx.get("recent_scene_summary") or "（无）"}（避免连着写同类型的戏）

怎么写：
1. 800-2000 字，自然语言。不写标签、不写表格、不分场标题。
2. 写成戏，不写成梗概：至少要有一个具体场面。
3. 两难是这章的心脏：他还没选的时候，两头都让他疼。
   检验：如果读者能说"这还用想？当然选 A"，这道两难就死了，重写。
4. 他最后必须选，选要落成动作（他做了什么），不是态度（他想了什么）。
5. 账要当场付：责任卡上那笔账，必须兑成一个可引用原句的具体场面
   （谁拿走了什么/谁失去了什么），不许用旁白概括。
6. 章末留一件没做完的事——让读者想翻页的那件。
7. 禁止拆穿 {d.get("forbidden_reveal")}。
8. 必须有对手拍：第二个有意志的人与焦点者发生正面交互
   （对话/对抗/交易/回避都算，远远看着不算）。
9. 禁止元叙述。元叙述包括：提及"章"本身（上一章/这一章/下一章/前章——
   书中人物不知道自己在章里）、谈论写作行为、主题词说教（命运/选择/代价，
   除非角色说出口）。

写完自己读一遍：
- 如果你只能用"他想通了/他决定了"来概括这章 → 重写。
- 如果删掉任何一个在场的人这章照样成立 → 那个人就不该在场。
"""


def play_judge_v2(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【戏】{ctx.get("play_text")}

你是审稿的，不是改稿的——先判，判不过才写意见。
八问，每问必须先从戏里引用原句作证据，再给"yes/no"：

1. 责任里点名的人都在场做事吗？（站着看的不算）
2. 办的是责任卡上那件事吗？（办岔了、办多了都算不过）
3. 责任卡上那笔账，戏里真付出去了吗？引"付出"的原句——
   引不出字面原句，或引出的只是"他付出了代价"式旁白，一律 no。
4. 戏里有没有至少一个具体场面（具体时空中的动作与对话），还是通篇概括叙述？
5. 有没有一道"还没选"时两头都疼的两难？用"当然选 A"测试：读者能轻松替他选 → no。
6. 他的选择落成了具体动作吗？（他做了什么，不是他想了什么）
7. 章末有没有一件没做完的事？（能抄出原句的、悬着的那件——"夜色深了"式氛围收尾不算）
8. 有没有提前拆穿禁止拆穿的事？

{VERDICT_SCHEMA}
"""


def play_judge(ctx: dict) -> str:
    return f"""【责任卡】{ctx.get("duty_json")}
【戏】{ctx.get("play_text")}
【上一章结束时世界变成了什么样】
{_state_json(ctx)}

你是审稿的，不是改稿的——先判，判不过才写意见。
十一问，每问必须先从戏里引用原句作证据，再给"yes/no"：

1. 责任里点名的人都在场做事吗？（站着看的不算）
2. 办的是责任卡上那件事吗？（办岔了、办多了都算不过）
3. 责任卡上那笔账，戏里真付出去了吗？引"付出"的原句——
   引不出字面原句，或引出的只是"他付出了代价"式旁白，一律 no。
4. 戏里有没有至少一个具体场面（具体时空中的动作与对话），还是通篇概括叙述？
5. 有没有一道"还没选"时两头都疼的两难？用"当然选 A"测试：读者能轻松替他选 → no。
6. 他的选择落成了具体动作吗？（他做了什么，不是他想了什么）
7. 章末有没有一件没做完的事？（能抄出原句的、悬着的那件——"夜色深了"式氛围收尾不算）
8. 有没有提前拆穿禁止拆穿的事？
9. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
10. 上章记下、到这章该响的悬念，这章戏里碰到了吗？（没有到期条目则 yes）
11. 这章戏里新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）

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
    return f"""基于这场戏和契约，写演绎。
演绎写的是戏的字缝里的东西：每个人心里的算盘、动作背后的动机、
读者能拼出但角色拼不出的真相。戏是水面上的，演绎是水面下的。

【戏】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}
【各角色截至上一章的所知所信】
{ctx.get("characters_epistemic_history") or "（无）"}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}

写三块：
1. scene_truth（300-800 字）：这场戏实际发生了什么（上帝视角）。
2. 每个在场角色的五层限知：看到听到 / 知道 / 以为 / 做了说了 / 没察觉的。
   水面下要有暗流——「以为」与 scene_truth 有偏差（反讽），
   或者各方心知肚明但各怀打算、谁也不点破（暗斗），二者有其一即可。
3. 矿 3-8 条：感官级的具体物。

禁令：
- 禁止把契约字段复述一遍当演绎。
- 禁止把禁止拆穿的事写进任何角色的「知道」。
- 五层每层至少一句具体的话。
- 不得与【历史限知】矛盾。

输出 JSON：
{{"scene_truth": "...",
 "characters": [{{"id": "", "perceived": "", "known": "", "believed": "", "acted": "", "blind": ""}}],
 "ore": ["..."]}}
"""


def deduce_judge(ctx: dict) -> str:
    return f"""【戏】{ctx.get("play_text")}
【契约】{ctx.get("contract_json")}
【演绎】{ctx.get("deduction_json")}
【各角色历史限知】{ctx.get("characters_epistemic_history") or "（无）"}
【禁止拆穿】{ctx.get("forbidden_reveal") or []}

六问：
1. scene_truth 服务这场戏吗？（不是另一场、不是预演正文）
2. 每个在场角色五层齐且有具体内容吗？
3. 有没有把禁止拆穿的事写进某个角色的「知道」层？
4. 矿具体吗？（能在正文里变成一个可写的细节，且能在戏/演绎里找到根）
5. 这场戏水面下有暗流吗？二者有其一即可：反讽或暗斗。全员工具人式透明才不过。
6. 与历史限知矛盾吗？（上章知道的这章写成不知道 → 不过）

{VERDICT_SCHEMA}
"""


def draft_generate(ctx: dict) -> str:
    bite = ctx.get("bite_quote") or ctx.get("prev_hook_quote") or "（无）"
    hint = str(ctx.get("struct_hint") or "").strip()
    hint_block = (
        f"\n【上一稿没过，照这个改，不要只换词】{hint}\n" if hint else ""
    )
    return f"""按这场戏和演绎，写一遍糙稿（2000-4000 字）。{hint_block}

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
- 戏的任何连续 8 个字不得原样出现在糙稿里，
  唯一例外：章首承接上章钩子的那句（{bite}）。
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
  两千字稿最多两处。宁可写「黑线贴着静脉走」，不要写「像细铁丝」。
  写完自己数：去空白不足 2000 字，或「像/仿佛/似的」超标，整篇作废重写。
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
7. 是连续场面还是概括叙述？
8. 把糙稿和戏并排放：删掉戏里已有的句子，糙稿还剩实质内容吗？
   （引一处糙稿有而戏没有的对白或感官细节作证据）
9. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
10. 上章记下、到这章该响的悬念，这章碰到了吗？（没有到期条目则 yes）
11. 这章新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）

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
5. 有没有哪句是作者在使劲，不是人在做事？引出来。没有就说没有。
6. 对照上章末态，在场角色的身体状态、持有物、位置有矛盾吗？（无末态则 yes）
7. 上章记下、到这章该响的悬念，这章碰到了吗？（没有到期条目则 yes）
8. 这章新写出的可见事实，有没有跟上一章已经写死的事实打架？（无末态则 yes）

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
    if kind in ("contract", "state"):
        return IDENTITY_SCRIBE
    if kind.endswith("_judge") or kind == "judge":
        return IDENTITY_JUDGE
    return IDENTITY_NOVELIST


assert PLAYBOOK_VERSION == "playbook.3.2"
