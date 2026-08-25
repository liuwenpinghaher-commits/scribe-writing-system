"""铜炉成色：词表过滤 + 对照.md 真源。

旗 SCRIBE3_CHENGSE_CRAFT 默认开。关 = 过滤停，不回古白话教学。
对照.md 是生成/审判真源，不跟旗走。找不到文件 = 失败，不许用复述顶上。
"""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import re
from typing import Any

FLAG = "SCRIBE3_CHENGSE_CRAFT"
DUIZHAO_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "worlds" / "乱世铜炉-拆文" / "对照.md"
)

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

class DuizhaoMissing(RuntimeError):
    """对照.md 读不到。生成/审判不许用复述顶上。"""


def _duizhao_path() -> Path:
    """对照真源路径。容器可用 SCRIBE3_DUIZHAO_PATH 盖掉，默认仍是仓库根下那份。"""
    override = (os.environ.get("SCRIBE3_DUIZHAO_PATH") or "").strip()
    return Path(override) if override else DUIZHAO_PATH


@lru_cache(maxsize=1)
def load_duizhao() -> str:
    """读对照.md 原文。空或没有 = 失败。"""
    path = _duizhao_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DuizhaoMissing(f"对照.md 读不到：{path}") from exc
    body = text.strip()
    if not body:
        raise DuizhaoMissing(f"对照.md 是空的：{path}")
    if "把眼睛交给当场那个人" not in body or "不要上来就掏底牌" not in body:
        raise DuizhaoMissing(f"对照.md 不像真源：{path}")
    return body


def duizhao_generate_block() -> str:
    """生成真源：对照.md 原文。不跟成色旗走。"""
    return (
        "【对照·真源】\n"
        "按这份对照写。对照和代码冲突，改代码。不要另造一套成色理论。\n"
        f"{load_duizhao()}\n"
    )


def duizhao_judge_block() -> str:
    """审判真源：对照.md 原文。不跟成色旗走。"""
    return (
        "【对照·真源·审判】\n"
        "按这份对照原文判。产物对不上对照 → verdict=fail。"
        "每条先引产物原句作证据，再给 yes/no。不要用旁路成色词表顶上。\n"
        f"{load_duizhao()}\n"
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
    """生成块 = 对照.md。旗关也不撤真源。"""
    return duizhao_generate_block()


def craft_judge_block() -> str:
    """审判块 = 对照.md。旗关也不撤真源。"""
    return duizhao_judge_block()


def protocol_style_block(*, exemplar: str = "") -> str:
    """写协议文风段。开旗注入对照原文；关旗不注入文风段，也不回古白话教学。"""
    del exemplar  # 范例曾教「岂料」，签名保留以免旧调用打爆
    if not chengse_enabled():
        return ""
    return PROTOCOL_STYLE + "\n" + duizhao_generate_block()


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
