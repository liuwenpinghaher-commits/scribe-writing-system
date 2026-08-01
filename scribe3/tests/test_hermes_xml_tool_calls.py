from __future__ import annotations

from scribe3.hermes_xml_tool_calls import extract_xml_tool_calls


def test_extracts_strict_allowed_xml_tool_call_and_removes_it_from_visible_text():
    calls, visible = extract_xml_tool_calls(
        "先执行。<tool_call>{\"name\":\"mcp__scribe3_write__s3_add_chapter\",\"arguments\":{\"work\":\"book_demo\",\"number\":1,\"title\":\"开篇\"}}</tool_call>",
        allowed_names={"mcp__scribe3_write__s3_add_chapter"},
    )

    assert len(calls) == 1
    assert calls[0].function.name == "mcp__scribe3_write__s3_add_chapter"
    assert calls[0].function.arguments == '{"number":1,"title":"开篇","work":"book_demo"}'
    assert visible == "先执行。"


def test_extracts_qwen_name_then_json_xml_tool_call():
    """TokenPlan/Qwen 会把函数名与 JSON 参数分成两行，仍须严格白名单后执行。"""
    calls, visible = extract_xml_tool_calls(
        "先检索。<tool_call>\ntool_search\n{\"query\":\"mcp__scribe3_read__s3_get_chapter\"}\n</tool_call>",
        allowed_names={"tool_search"},
    )

    assert len(calls) == 1
    assert calls[0].function.name == "tool_search"
    assert calls[0].function.arguments == '{"query":"mcp__scribe3_read__s3_get_chapter"}'
    assert visible == "先检索。"


def test_extracts_qwen_anthropic_style_json_tool_array():
    """TokenPlan/Qwen 的 reasoning 文本可能是 Anthropic 风格的工具数组。"""
    calls, visible = extract_xml_tool_calls(
        '先检索。[{"id":"toolu_1","name":"tool_search","args":{"query":"s3_get_chapter"}}]',
        allowed_names={"tool_search"},
    )

    assert len(calls) == 1
    assert calls[0].function.name == "tool_search"
    assert calls[0].function.arguments == '{"query":"s3_get_chapter"}'
    assert visible == "先检索。"


def test_rejects_malformed_or_unlisted_xml_without_hiding_the_text():
    text = (
        "<tool_call>{\"name\":\"mcp__scribe3_write__s3_add_chapter\",\"arguments\":[]}</tool_call>"
        "<tool_call>{\"name\":\"mcp__unknown\",\"arguments\":{}}</tool_call>"
    )

    calls, visible = extract_xml_tool_calls(
        text,
        allowed_names={"mcp__scribe3_write__s3_add_chapter"},
    )

    assert calls == []
    assert visible == text


def test_deduplicates_repeated_identical_xml_calls_but_keeps_distinct_calls():
    text = (
        '<tool_call>{"name":"mcp__scribe3_write__s3_add_chapter","arguments":{"work":"book_demo","number":1,"title":"开篇"}}</tool_call>'
        '<tool_call>{"name":"mcp__scribe3_write__s3_add_chapter","arguments":{"work":"book_demo","number":1,"title":"开篇"}}</tool_call>'
        '<tool_call>{"name":"mcp__scribe3_write__s3_patch_chapter_meta","arguments":{"work":"book_demo","number":1,"title":"改名"}}</tool_call>'
    )

    calls, visible = extract_xml_tool_calls(
        text,
        allowed_names={
            "mcp__scribe3_write__s3_add_chapter",
            "mcp__scribe3_write__s3_patch_chapter_meta",
        },
    )

    assert [call.function.name for call in calls] == [
        "mcp__scribe3_write__s3_add_chapter",
        "mcp__scribe3_write__s3_patch_chapter_meta",
    ]
    assert visible == ""
