"""铜炉成色：日子/办事/假破真/远近/切。验戏，不验词表。

旗 SCRIBE3_CHENGSE_CRAFT 默认开。关 = 过滤与成色块停，不回古白话教学。
不过关不冒充成色：这里只挡反着教的套话/专名/空概括。日子翻没翻仍按尺子对照。
"""
from __future__ import annotations

import re
from typing import Any

FLAG = "SCRIBE3_CHENGSE_CRAFT"

# 写协议曾逼模型堆的套话。对白里角色可以偶尔说；叙述层不行。
_CLASSICAL = re.compile(r"端的是|怎禁得|却原来|岂料|端的")

# 拆文专名。样例必须换自己的名。对白里出现也算搬书。
TONGLU_PROPER = (
    "胡不为",
    "时闻盂",
    "单嫣",
    "秦苏",
    "胡炭",
    "三水村",
    "定马村",
    "圣手小青龙",
    "定神符",
    "灵龙镇煞钉",
    "刑兵铁令",
    "奇案司",
    "贺家庄",
    "赵家庄",
    "乱世铜炉",
    "梧桐村",
    "奈何谷",
)

_EMPTY_TAIL = re.compile(
    r"(他决定了|她决定了|他付出了代价|她付出了代价|夜色深了|叹了口气)[。！？…]*$"
)

CRAFT_GENERATE = (
    "【成色·验戏不验词表】\n"
    "1. 日子：先立还在过的日子，奇事从日子里来。开篇报身份、扔钩子、先宣布法会 = 废稿。"
    "热闹像翻了、处境没翻 = 废稿。\n"
    "2. 办事：看见谁办了哪一件、日子怎么变。嘴上要的和真正缺的打架。"
    "鉴定式人设、杯子余温、维特剖心 = 废稿。\n"
    "3. 假破真：要落一个真意，先给反面，再破功。上来掏底牌 = 废稿。\n"
    "4. 远近：共情就把眼睛交给当场那个人。旁观才站外头报年号。"
    "人还在办事时铺戒律、报年号 = 上课，不要。\n"
    "5. 因文：一行本事说不完。删了那一截场会塌的那一下必须写上。\n"
    "6. 切：热过再冷，切在能听见看见的那一下。不切在一段叹气上。\n"
    "7. 不要半文不白套话（端的、岂料一类），不要铜炉专名情节，不要网文开篇格子。\n"
    "概括只能写成「他决定了/他付出了代价/夜色深了」= 废稿。\n"
)

CRAFT_JUDGE = (
    "成色（验戏，不验词表。每条先引产物原句作证据，再给 yes/no。"
    "任一条 no → verdict=fail。答案 q 用 C1–C7）：\n"
    "C1. 日子：先立还在过的日子了吗？奇事是从日子里来的吗？热闹像翻了、处境没翻 → no。\n"
    "C2. 办事：能指出谁办了哪一件、日子怎么变吗？嘴上要的和真正缺的有没有打架？"
    "鉴定式人设/剖心 → no。\n"
    "C3. 假破真：先给了反面再破功吗？上来掏底牌 → no。\n"
    "C4. 远近：共情处眼睛交给当场那个人了吗？人还在办事时报年号/上课 → no。\n"
    "C5. 因文：有没有一截删了场会塌？整场能一行本事说完 → no。\n"
    "C6. 切：热过再冷，切在能听见看见的那一下了吗？切在叹气/夜色深了 → no。\n"
    "C7. 有没有半文不白套话、铜炉专名、网文开篇格子？有 → no。\n"
)

PROTOCOL_STYLE = (
    "\n\n## 文风基准:成色（验戏，不验词表）\n"
    "先立还在过的日子，奇事从日子里来。看见谁办了哪一件、日子怎么变。"
    "要落真意，先给反面再破功。共情就把眼睛交给当场那个人。"
    "热过再冷，切在能听见看见的那一下。旁边的人各有要办的事。\n"
    "禁：半文不白套话（端的、岂料、怎禁得）、把《乱世铜炉》专名情节搬进本书、"
    "开篇报身份扔钩子、黄金三章/三次失败、鉴定式人设与剖心、"
    "概括收尾（他决定了/他付出了代价/夜色深了）。\n"
    "世界要活，靠还在过的日子和当场办事，不靠古白话词表，不靠范例照抄。"
)



def chengse_enabled() -> bool:
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy(FLAG)
    except Exception:
        return True


def craft_generate_block() -> str:
    if not chengse_enabled():
        return ""
    return CRAFT_GENERATE


def craft_judge_block() -> str:
    if not chengse_enabled():
        return ""
    return CRAFT_JUDGE


def protocol_style_block(*, exemplar: str = "") -> str:
    """写协议文风段。开旗用成色；关旗不注入文风段，也不回古白话教学。"""
    del exemplar  # 范例曾教「岂料」，签名保留以免旧调用打爆
    if not chengse_enabled():
        return ""
    return PROTOCOL_STYLE


def _ok() -> dict[str, Any]:
    return {"ok": True}


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message}


def check_chengse_filter(text: str) -> dict[str, Any]:
    """叙述层套话 / 铜炉专名 / 空概括收尾。关旗不拦。"""
    if not chengse_enabled():
        return _ok()
    blob = text or ""
    if not blob.strip():
        return _ok()
    from scribe3.playbook.structural import narration_layer

    narr = narration_layer(blob)
    m = _CLASSICAL.search(narr)
    if m:
        return _fail(
            "chengse_classical",
            f"叙述里在堆古白话套话「{m.group(0)}」。用当场能看见的事重写，不要端的岂料。",
        )
    for name in TONGLU_PROPER:
        if name in blob:
            return _fail(
                "chengse_tonglu_name",
                f"正文搬进了铜炉专名「{name}」。换自己的名，办自己的日子。",
            )
    tail = re.sub(r"\s+", "", narr[-80:] if narr else "")
    if tail and _EMPTY_TAIL.search(tail):
        return _fail(
            "chengse_empty_summary",
            "收在「他决定了/他付出了代价/夜色深了」上。切在能听见看见的那一下。",
        )
    return _ok()
