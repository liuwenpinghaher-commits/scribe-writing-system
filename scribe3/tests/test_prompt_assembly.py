"""Task 11:稳定/动态层边界 + 会话 key 稳定化(导航切章不换 Hermes session)。

裁决(已落地,不推翻):
- 主编身份与恒定纪律(剧情事实不进 Hermes memory、s3_ 必带 work、写入待批)→ profile SOUL.md。
- 讨论/动稿围栏协议、限知/文风等强制纪律 → prompt 内嵌(_write_protocol_block/assembler)。
- scribe-novel-v2 SKILL.md → 只保留按需查阅的写作工序参考,不承载强制纪律围栏协议。
- ContextEnvelope → 每轮动态层(默认关)。
"""
from pathlib import Path


# ---- 会话 key 稳定:导航切章不换 Hermes session(主编历史连续)----

def test_hermes_session_key_is_thread_stable_across_chapters():
    from scribe3.app import _hermes_session_key

    assert (_hermes_session_key("book-a", "thread-1", chapter=1)
            == _hermes_session_key("book-a", "thread-1", chapter=9))


def test_hermes_session_key_only_encodes_work_and_thread():
    from scribe3.app import _hermes_session_key

    key = _hermes_session_key("book-a", "thread-1", chapter=7)
    assert key == "scribe3|work:book-a|thread:thread-1"
    # 焦点/章不进 session key —— 它们只存 ContextEnvelope.focus。
    assert "chapter" not in key


def test_run_session_key_stays_work_scoped_and_isolated_from_threads():
    """Runs(写 profile 长任务)仍用 work|runs,与主编讨论线程隔离——不被本次改动波及。"""
    from scribe3.app import _run_session_key

    assert _run_session_key("book_x") == "scribe3|work:book_x|runs"


# ---- 稳定/动态层边界 ----

_SKILL = Path(__file__).resolve().parent.parent / "hermes_skills" / "scribe-novel-v2" / "SKILL.md"


def test_hard_write_protocol_stays_prompt_embedded_not_in_skill():
    """讨论 vs 动稿的 ⟦PROPOSAL⟧ 围栏协议是强制纪律,必须 prompt 内嵌,绝不放 skill
    (Hermes skills 渐进披露,强制纪律放 skill 必失守)。"""
    from scribe3.app import _write_protocol_block

    protocol = _write_protocol_block()
    assert "⟦PROPOSAL" in protocol
    assert "讨论" in protocol and "动稿" in protocol

    skill = _SKILL.read_text(encoding="utf-8")
    assert "⟦PROPOSAL" not in skill, "围栏协议属强制纪律,不得搬进 skill"


def test_skill_keeps_writing_process_reference():
    """SKILL.md 保留按需查阅的写作工序参考(写一章的环 / QC 序列 / 知识帧投影)。"""
    skill = _SKILL.read_text(encoding="utf-8")
    assert "s3_project_frame" in skill
    assert "写一章" in skill
    assert "s3_qc_chapter" in skill
    # frontmatter 名字不变,smoke 才能在 /v1/skills 扫到。
    assert "name: scribe-novel-v2" in skill


def test_skill_defers_enforced_discipline_to_soul_and_prompt():
    """SKILL.md 不再以"任何动作不得绕过"的命令式承载强制纪律——恒定纪律归 SOUL/instructions。"""
    skill = _SKILL.read_text(encoding="utf-8")
    assert "任何动作不得绕过" not in skill


def test_secret_guard_block_hides_leak_markers():
    """S-002:写作prompt对secret命题注入藏匿约束+禁破绽词;无secret则空串(字节不变)。"""
    from scribe3 import app as A
    class _F:
        def __init__(s,secret,lm): s.secret=secret; s.leak_markers=lm
    class _St:
        def __init__(s,facts): s._f=facts
        def facts_at(s,ch): return s._f
    # 有 secret → 含破绽词 + 藏匿指令
    b = A._secret_guard_block(_St([_F(True,["沈错","替兄顶罪"]), _F(False,["公开"])]))
    assert "沈错" in b and "替兄顶罪" in b and "公开" not in b
    assert "绝不明写" in b and "核心悬念" in b
    # 无 secret → 空串(默认字节不变)
    assert A._secret_guard_block(_St([_F(False,["x"])])) == ""
    assert A._secret_guard_block(_St([])) == ""
