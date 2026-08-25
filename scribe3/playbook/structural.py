"""Allowlist-only structural gates.

登记过的检查（新增须写理由）：
- play 非空/字数/禁旧标签行
- duty 人/事/账/禁揭/户口/线/上章钩
- contract quote 保真 + beats 场数 + 恰好一场 stages_choice
- deduce 五层+矿条数
- draft 非空/场面立住 + 相对戏的 8 字重复率 + 章边界词 + 明喻密度（字数不作完成）
- final 字数 + 章边界词 + 明喻密度 + 必须有冻结契约 + finalize 最后一公里
- gender_pronoun：上章末态/户口有性别的角色，正文名旁代词不得翻转
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
    r"|报身份|开篇钩子|强钩子|先宣布法会|宣布法会|开坛做法"
    r"|黄金三章|三次失败"
)
_DAY_LIVED = re.compile(
    r"还在|还没|正在|尚未|仍有|排队|过秤|喝酒|喜酒|守夜|赶路|散不|过年|过节|井台|柜上|日子"
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
    r"一声|一响|响了|碎了|开了|停住|磕|砸|摔|落地|堕地"
    r"|啪|嚓|喀喇|尖鸣|穿|门开|钉子|杯子"
)
# 因文.md：一行本事说不完；删了那一截场会塌。
_ONE_LINE_OK = re.compile(r"一行就够|本事说完|过场即可|说明书")
# 参照本十七：热闹不算翻。热闹当场面也能过 = 还没这条。
_HEAT_AS_FLIP = re.compile(r"热闹就是翻|场面就算翻|热闹当翻|场面过了就算|热闹算翻")
_HEAT_ONLY = re.compile(r"热闹|场面过了|社戏完了|筵席散了|鼓掌过了")
_STAY_WORLD = re.compile(r"还|没|仍|停|在|日子|墓|路|安危|欠|信")
CLOCK_SPANS = frozenset({"scene", "day", "days"})
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


def check_contract_struct(
    contract: dict[str, Any],
    play_text: str,
    *,
    available_lines: list[Any] | None = None,
) -> dict[str, Any]:
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
    """角色名 ±30 字窗口内，对已登记男/女的角色统计他/她。反向上位则拦。

    同窗里出现另一个户口名字时跳过该窗：对手同框时「他」常指对方，不是把她写成男的。
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
    for name, gender in roster:
        windows: list[str] = []
        start = 0
        while True:
            i = blob.find(name, start)
            if i < 0:
                break
            lo = max(0, i - 30)
            hi = min(len(blob), i + len(name) + 30)
            win = blob[lo:hi]
            start = i + len(name)
            if any(other != name and other in win for other, _ in roster):
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
                f"{name} 户口为男，名旁窗口「她」{she_n} 多于「他」{he_n}",
                name,
            )
        if gender == "女" and he_n > she_n:
            return _fail(
                "gender_pronoun",
                f"{name} 户口为女，名旁窗口「他」{he_n} 多于「她」{she_n}",
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
        if rate > 0.15:
            return _fail("draft_copy_play", f"糙稿与戏重复率 {rate:.1%} 超过 15%")
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
    if n < 1000:
        return _fail("prose_len", f"正文字数 {n} 低于 1000")
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
