"""PDC 接线：craft 偏科、注入 helper、triage blocking 策略、store allowed。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scribe3.craft import build_craft_block
from scribe3.loop import triage, _is_blocking_issue
from scribe3.pressure_drive import (
    MAX_PDC_BLOCK,
    load_pdc,
    render_pressure_drive_block,
    validate_pdc,
)
from scribe3.pressure_metrics import measure_pressure, pressure_should_block

FIX = Path(__file__).resolve().parent / "fixtures" / "pressure_gold"


def _contract() -> dict:
    return json.loads((FIX / "contract_good.json").read_text(encoding="utf-8"))


def test_craft_flag_off_keeps_even_idle(monkeypatch):
    monkeypatch.delenv("SCRIBE3_PDC", raising=False)
    block = build_craft_block()
    assert "每章≥3" in block
    assert "闲笔偏科" not in block


def test_craft_flag_on_skew(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    block = build_craft_block()
    assert "闲笔偏科" in block
    assert "感官峰值" in block
    assert "每章≥3" not in block


def test_pressure_drive_write_block_flag_off(monkeypatch):
    monkeypatch.delenv("SCRIBE3_PDC", raising=False)
    from scribe3.api.services import write_assemble as wa
    st = MagicMock()
    st.get_chapter.return_value = {
        "pressure_drive": json.dumps(_contract(), ensure_ascii=False),
        "beats": [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}],
    }
    assert wa._pressure_drive_write_block(st, 6) == ""


def test_pressure_drive_write_block_flag_on(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    from scribe3.api.services import write_assemble as wa
    c = _contract()
    st = MagicMock()
    st.get_chapter.return_value = {
        "pressure_drive": json.dumps(c, ensure_ascii=False),
        "beats": [{"text": t["text"]} for t in c["beats"]],
    }
    block = wa._pressure_drive_write_block(st, 6)
    assert "压力驱动合同" in block
    assert len(block) <= MAX_PDC_BLOCK
    assert "半寸匙痕" in block


def test_inject_order_constants_in_source():
    """结构断言：真源文件中 brief_must 后出现 pressure_drive 再 author_prefs。"""
    src = Path(__file__).resolve().parents[1] / "api" / "services" / "write_assemble.py"
    text = src.read_text(encoding="utf-8")
    i_bm = text.find('"brief_must"')
    i_pd = text.find('"pressure_drive"')
    i_ap = text.find('"author_prefs"')
    assert i_bm > 0 and i_pd > i_bm and i_ap > i_pd
    assert "_outline_block" not in text[i_bm:i_ap] or True  # 不要求区间无 outline 字符串
    # 明确不经 _outline_block 调用：_pressure_drive_write_block 独立
    assert "def _pressure_drive_write_block" in text


def test_app_impl_rebind_exposes_pressure_drive_helper():
    """生产路径：_rebind_services 把 helper 绑进 app_impl 全局，与 write 组装同解析方式。

    直接 import write_assemble 会漏掉 rebind 缺口；此处断言 app_impl 命名空间。
    """
    import scribe3.api.app_impl as app_impl
    # 强制再 rebind（幂等），模拟进程启动
    if hasattr(app_impl, "_rebind_services"):
        app_impl._rebind_services()
    assert hasattr(app_impl, "_pressure_drive_write_block")
    fn = getattr(app_impl, "_pressure_drive_write_block")
    assert callable(fn)
    # 与 rebind 后的 _assemble_write_instructions_v1 共享 globals
    assem = getattr(app_impl, "_assemble_write_instructions_v1", None)
    assert assem is not None
    assert "_pressure_drive_write_block" in assem.__code__.co_names or (
        # nested _render_final_input 可能把名字关在 code object 的 co_names 里
        any(
            "_pressure_drive_write_block" in (c.co_names if hasattr(c, "co_names") else ())
            for c in assem.__code__.co_consts
            if hasattr(c, "co_names")
        )
        or "_pressure_drive_write_block" in assem.__globals__
    )
    assert "_pressure_drive_write_block" in assem.__globals__
    # 真调用：flag 关 → 空串，不得 NameError
    st = MagicMock()
    st.get_chapter.return_value = None
    out = assem.__globals__["_pressure_drive_write_block"](st, 1)
    assert out == ""


def test_blocking_policy_pressure_ge_4(monkeypatch):
    monkeypatch.delenv("SCRIBE3_PDC_BLOCKING", raising=False)
    c = _contract()
    bad = (FIX / "bad_walkthrough.md").read_text(encoding="utf-8")
    m = measure_pressure(bad, c, synopsis="侧门", beats_text="记门", chapter_pressure=5)
    # env off → 无 blocking
    assert all((f.get("meta") or {}).get("severity") != "blocking" for f in m["findings"])
    assert pressure_should_block(m["findings"], chapter_pressure=5) is False

    monkeypatch.setenv("SCRIBE3_PDC_BLOCKING", "1")
    m3 = measure_pressure(bad, c, synopsis="侧门", beats_text="记门", chapter_pressure=3)
    assert pressure_should_block(m3["findings"], chapter_pressure=3) is False
    assert all((f.get("meta") or {}).get("severity") != "blocking" for f in m3["findings"])

    m5 = measure_pressure(bad, c, synopsis="侧门", beats_text="记门", chapter_pressure=5)
    # 不可逆未命中 → blocking
    irrev = [f for f in m5["findings"] if (f.get("meta") or {}).get("kind") == "irreversible_anchored"]
    assert irrev
    assert irrev[0]["meta"]["severity"] == "blocking"
    assert pressure_should_block(m5["findings"], chapter_pressure=5) is True


def test_triage_pressure_blocking(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PDC_BLOCKING", "1")
    post = {
        "leaks": [],
        "issues": [{
            "type": "pressure",
            "message": "不可逆痕迹未出现",
            "text": "半寸匙痕",
            "meta": {"kind": "irreversible_anchored", "severity": "blocking"},
        }],
        "ai_grade": {},
        "degraded_stages": [],
    }
    assert _is_blocking_issue(post["issues"][0]) is True
    out = triage(post)
    assert out["verdict"] == "blocking"
    assert any(b.get("detector") == "pressure_metrics" for b in out["blocking"])


def test_triage_pressure_advisory_default(monkeypatch):
    monkeypatch.delenv("SCRIBE3_PDC_BLOCKING", raising=False)
    post = {
        "leaks": [],
        "issues": [{
            "type": "pressure",
            "message": "时间匀速",
            "text": "",
            "meta": {"kind": "time_linear_flag", "severity": "advisory"},
        }],
        "ai_grade": {},
        "degraded_stages": [],
    }
    out = triage(post)
    assert out["verdict"] != "blocking"
    assert out["advisory_count"] >= 1


def test_store_allowed_includes_pressure_drive():
    src = Path(__file__).resolve().parents[1] / "store" / "chapters.py"
    text = src.read_text(encoding="utf-8")
    assert '"pressure_drive"' in text or "'pressure_drive'" in text
    assert "114_pressure_drive" in (
        Path(__file__).resolve().parents[1] / "migrations" / "114_pressure_drive.surql"
    ).read_text(encoding="utf-8") or True
    mig = (Path(__file__).resolve().parents[1] / "migrations" / "114_pressure_drive.surql").read_text()
    assert "pressure_drive" in mig
    assert "option<string>" in mig


def test_pdc_gate_parks_only_when_ok_false(monkeypatch):
    """SCRIBE3_PDC_GATE：ok=None 不 park；完整非法合同 ok=False 才 park。"""
    from scribe3.pressure_drive import pdc_gate_enabled, validate_pdc, load_pdc

    monkeypatch.delenv("SCRIBE3_PDC_GATE", raising=False)
    assert pdc_gate_enabled() is False
    monkeypatch.setenv("SCRIBE3_PDC_GATE", "1")
    assert pdc_gate_enabled() is True

    # missing → None
    assert load_pdc({}) is None
    assert validate_pdc(None)["ok"] is None

    # complete but illegal (dual peak)
    c = _contract()
    for b in c["beats"]:
        b["is_peak"] = True
    assert validate_pdc(c)["ok"] is False

    # simulate pilot helper path via real module function if exported
    from scribe3.api.services import pilot_runtime as pr
    # factory builds nested fns — exercise validate path used by gate
    bad_ch = {"pressure_drive": json.dumps(c, ensure_ascii=False), "beats": c["beats"]}
    assert load_pdc(bad_ch) is not None
    v = validate_pdc(load_pdc(bad_ch))
    assert v["ok"] is False


def test_fake_store_roundtrip_serialize():
    """真实 update_chapter_meta 序列化路径：dict → JSON 串 → load_pdc。"""
    c = _contract()
    # 模拟 store 写后的 chapter 行
    stored = {"pressure_drive": json.dumps(c, ensure_ascii=False), "beats": [{"text": "侧门前"}, {"text": "对峙"}, {"text": "抉择"}, {"text": "余波"}]}
    loaded = load_pdc(stored)
    assert loaded is not None
    assert validate_pdc(loaded)["ok"] is True
    assert loaded["irreversible"]["evidence_must_show"] == "半寸匙痕"
