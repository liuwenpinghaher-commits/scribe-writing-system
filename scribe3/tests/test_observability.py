"""Test observability: silent except blocks now log warnings (G枢纽 P17).

验证失败路径保留 fail-open 行为(返回默认值不变),但落 WARNING 日志(失败可见)。
"""
import logging

from scribe3.critique import parse_discipline, parse_knowledge_delta
from scribe3.soak import parse_soak


class TestParseDisciplineLogging:
    def test_garbage_returns_default_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="scribe3.critique"):
            result = parse_discipline("{无效内容,不是合法JSON}")
        assert result["ok"] is True
        assert result["violations"] == []
        assert result["cut_after"] == ""
        assert "parse_discipline" in caplog.text or "失败" in caplog.text

    def test_valid_json_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="scribe3.critique"):
            result = parse_discipline('{"ok": false, "violations": ["x"], "cut_after": "abc"}')
        assert result["ok"] is False
        assert "失败" not in caplog.text


class TestParseKnowledgeDeltaLogging:
    def test_garbage_returns_default_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="scribe3.critique"):
            result = parse_knowledge_delta("{无效内容,不是合法JSON}")
        assert result["learned"] == []
        assert result["did"] == []
        assert result["voice_shift"] == []
        assert "parse_knowledge_delta" in caplog.text or "失败" in caplog.text


class TestParseSoakLogging:
    def test_garbage_returns_default_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="scribe3.soak"):
            result = parse_soak("{无效内容,不是合法JSON}")
        assert result["emotion_arc"] == ""
        assert result["seed_words"] == []
        assert "parse_soak" in caplog.text or "失败" in caplog.text

    def test_valid_json_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="scribe3.soak"):
            result = parse_soak('{"emotion_arc":"平静→愤怒","turn":"他拔刀","seed_words":["刀","血"]}')
        assert result["emotion_arc"] == "平静→愤怒"
        assert "失败" not in caplog.text
