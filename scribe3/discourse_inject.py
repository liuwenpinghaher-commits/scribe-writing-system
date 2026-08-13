"""话语层 L3 注入 discourse_soft（Week-2 · PR-D4/D7）。

- 仅 L3 supplemental；禁止并入 structure_diversity L0
- meso + serial 差异化短句，合计 ≤200 字
- 禁止列举 open_promise 正文
"""
from __future__ import annotations

from typing import Any

from scribe3.discourse_craft_ssot import MESO_DEFAULT, SERIAL_DEFAULT

DISCOURSE_SOFT_CAP = 200


def _flag(name: str, default: bool = True) -> bool:
    try:
        from scribe3.feature_flags import flag_truthy
        return flag_truthy(name)
    except Exception:
        import os
        raw = (os.environ.get(name) or ("1" if default else "0")).strip().lower()
        return raw in ("1", "true", "yes", "on")


def _s(v: Any) -> str:
    return str(v or "").strip()


def meso_line_from_chapter(chapter: dict | None) -> tuple[str, str]:
    """返回 (text, source) source ∈ beats_meta|default|off。"""
    if not _flag("SCRIBE3_DISCOURSE_MESO", default=True):
        return "", "off"
    ch = chapter if isinstance(chapter, dict) else {}
    bm = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
    # D7：distance_intent / pov_stance / time_strategy 任一非空 → beats_meta 源
    parts = []
    for key, label in (
        ("distance_intent", "距离"),
        ("pov_stance", "视角"),
        ("time_strategy", "时间"),
    ):
        v = _s(bm.get(key))
        if v:
            parts.append(f"{label}:{v[:40]}")
    custom = _s(bm.get("meso_note") or bm.get("discourse_meso"))
    if custom:
        parts.append(custom[:80])
    if parts:
        line = "讲法：" + "；".join(parts)
        if "限知" not in line and "全知" not in line:
            line = line.rstrip("。") + "。慎用叙述者越界全知。"
        return line[:120], "beats_meta"
    return MESO_DEFAULT, "default"


def serial_line_from_chapter(chapter: dict | None) -> tuple[str, str]:
    """连载一行；不读 open promises 正文。"""
    if not _flag("SCRIBE3_DISCOURSE_SERIAL", default=True):
        return "", "off"
    ch = chapter if isinstance(chapter, dict) else {}
    bm = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
    custom = _s(bm.get("serial_note") or bm.get("discourse_serial"))
    hook_type = _s(bm.get("chapter_hook_type"))
    bits = []
    if hook_type:
        bits.append("钩类型:" + hook_type[:20])
    if custom:
        bits.append(custom[:80])
    if bits:
        return ("连载：" + "；".join(bits))[:120], "beats_meta"
    return SERIAL_DEFAULT, "default"


def render_discourse_soft_text(
    chapter: dict | None = None,
    *,
    cap: int = DISCOURSE_SOFT_CAP,
) -> dict[str, Any]:
    """渲染 discourse_soft 正文与 budget 元数据。永不抛出。"""
    meta: dict[str, Any] = {
        "fed": False,
        "applied": False,
        "enabled": False,
        "chars": 0,
        "meso_source": "off",
        "serial_source": "off",
        "cap": int(cap),
        "truncated": False,
    }
    try:
        if not _flag("SCRIBE3_DISCOURSE_ADVISORY", default=True):
            return {"text": "", "meta": meta}
        meso, msrc = meso_line_from_chapter(chapter)
        serial, ssrc = serial_line_from_chapter(chapter)
        meta["meso_source"] = msrc
        meta["serial_source"] = ssrc
        meta["enabled"] = True
        lines = [x for x in (meso, serial) if x]
        if not lines:
            meta["fed"] = True
            return {"text": "", "meta": meta}
        body = "\n".join(f"- {ln}" for ln in lines)
        text = f"\n\n【话语提示｜讲法与连载】\n{body}\n"
        truncated = False
        if len(text) > cap:
            truncated = True
            # 超 cap：先丢 serial 再截 meso
            if serial and meso:
                body2 = f"- {meso}"
                text = f"\n\n【话语提示｜讲法与连载】\n{body2}\n"
                if len(text) > cap:
                    text = text[: max(0, cap - 1)] + "…\n"
                    meta["serial_source"] = "off"
            else:
                text = text[: max(0, cap - 1)] + "…\n"
            # 若仍超且两旗开：标记 serial off when dropped
            if serial and meso and truncated and "连载" not in text:
                meta["serial_source"] = "off"
        # 硬禁：不得出现开放伏笔正文形态
        if "开放伏笔：" in text:
            text = text.replace("开放伏笔：", "（已省略伏笔原文）")
        meta["fed"] = True
        meta["applied"] = bool(text.strip())
        meta["chars"] = len(text)
        meta["truncated"] = truncated
        return {"text": text, "meta": meta}
    except Exception as e:
        meta["error"] = str(e)[:160]
        meta["enabled"] = True
        return {"text": "", "meta": meta}


def prepare_write_discourse_soft(
    st: Any,
    *,
    chapter: int | None,
    work: str | None = "main",
) -> dict[str, Any]:
    """写路径入口：装章 dict → render。永不抛出。"""
    ch: dict = {}
    try:
        if st is not None and chapter is not None and hasattr(st, "get_chapter"):
            ch = st.get_chapter(int(chapter)) or {}
    except Exception:
        ch = {}
    return render_discourse_soft_text(ch)
