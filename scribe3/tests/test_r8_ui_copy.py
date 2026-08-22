"""R8 surface: shipped web source must not advertise engineering-green."""
import pytest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "src"


def _read(*parts: str) -> str:
    return (WEB.joinpath(*parts)).read_text(encoding="utf-8")


@pytest.mark.xfail(reason="未上线页面文案，挂牌停住", strict=False)
def test_reader_lamp_not_machine_pass():
    t = _read("lib", "readerReadyGate.js")
    assert "机判过关" not in t
    assert "机判" not in t
    assert "可开写" not in t or "材料参考" in t


@pytest.mark.xfail(reason="未上线页面文案，挂牌停住", strict=False)
def test_write_layout_has_no_dual_lamp_chips():
    t = _read("WriteLayout.jsx")
    assert 'data-testid="dual-lamp-chips"' not in t
    assert "材料诊断" in t


@pytest.mark.xfail(reason="未上线页面文案，挂牌停住", strict=False)
def test_meta_pane_one_scene_paper():
    t = _read("ChapterMetaPane.jsx")
    assert "loadEvidenceMustShow" in t
    assert "材料备忘" in t


def test_meta_pane_not_ready_to_write():
    t = _read("ChapterMetaPane.jsx")
    assert "材料够了，可以开写" not in t
    assert "可以开写" not in t


@pytest.mark.xfail(reason="未上线页面文案，挂牌停住", strict=False)
def test_chapter_open_defaults_to_manuscript():
    md = _read("layout", "ManuscriptDirectory.jsx")
    dp = _read("layout", "DirectoryPane.jsx")
    assert "phase: 'final'" in md
    assert "phase: 'outline'" not in md
    assert "phase: 'final'" in dp


def test_discuss_default_agentic_true():
    t = _read("ChiefDock.jsx")
    assert "agentic: true" in t
    # chapter-discuss send must not pin tools off
    assert "agentic: false, seq:" not in t.replace(" ", "")


def test_agentic_tools_hint_is_readonly():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "api" / "routers" / "misc_routes.py").read_text(encoding="utf-8")
    assert "查询/操作" not in src
    assert "写操作会进入待批" not in src
    assert "只读 s3_" in src or "只读工具" in src
