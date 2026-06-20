"""生成转向修复:continue/rewrite/expand 的 prompt 构建是纯函数,
必须吃 instruction(可steer)、看得到 prev(连贯续写)、长度可控(不再硬编码150)。
旧 bug:_ACTION_PROMPT['continue'] 只引用 {seq},丢弃 API 已接收的 instruction 与 prev。
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["SCRIBE_DB"] = _tmp.name

from scribe_mcp.api import _action_prompt  # noqa: E402


def test_continue_uses_instruction_prev_and_length():
    p = _action_prompt("continue", 3, instruction="醉汉倒在祠堂旁的古铜炉边",
                       prev="村中喜宴正酣,灯火彻夜不熄。", target_chars=700)
    assert "醉汉倒在祠堂旁的古铜炉边" in p   # 旧 bug:instruction 被丢弃
    assert "村中喜宴正酣" in p              # 旧 bug:prev 看不到,无法连贯
    assert "700" in p                       # 旧 bug:硬编码 150,长度不可控
    assert "3" in p                         # 章序保留


def test_continue_handles_empty_instruction_and_prev():
    # UI「续写」按钮传空 instruction、本章尚无正文 —— 必须仍生成合法 prompt
    p = _action_prompt("continue", 1, instruction="", prev="", target_chars=150)
    assert isinstance(p, str) and len(p) > 0
    assert "150" in p


def test_rewrite_keeps_instruction_and_prev():
    p = _action_prompt("rewrite", 2, instruction="节奏太慢,删冗句",
                       prev="他慢慢地走了过去。", target_chars=0)
    assert "节奏太慢,删冗句" in p
    assert "他慢慢地走了过去" in p
