"""已批准参考指纹进入写作前的安全技法编译合同。"""
from __future__ import annotations

from scribe3.quality.references import ReferenceService


class _FingerprintLLM:
    def complete(self, messages, **kwargs):
        class _Result:
            content = '''{
              "local_mechanisms": ["局部张力"],
              "cross_chapter_aggregation": "跨章递进",
              "full_book_fingerprint": "克制的悬念组织",
              "evidence": [{"quote": "雾港的钟响了", "location": "第一章"}],
              "counter_evidence": [{"quote": "雾散以后", "location": "第二章"}],
              "transferable_mechanisms": ["以环境变化迫使人物做出主动选择", "用动作后果替代情绪解释", "潮汐旧书的段落节奏"],
              "non_copyable_elements": ["沈浪", "雾港", "参考作品的原句与句式"],
              "applicable_scope": "悬疑开场"
            }'''
        return _Result()


def _approved_fingerprint(store, *, work: str, title: str = "潮汐旧书"):
    service = ReferenceService(store)
    reference = service.import_reference(
        work=work,
        title=title,
        text="雾港的钟响了。沈浪没有回头，只把湿透的票根塞进掌心。",
    )
    pending = service.generate_fingerprint(
        reference_work_id=reference.reference_work_id, llm=_FingerprintLLM(),
    )
    return service.approve_fingerprint(fingerprint_id=pending.fingerprint_id)


def test_approved_fingerprint_compiles_to_safe_craft_sources(store):
    from scribe3.reference_craft import approved_craft_briefs, render_craft_briefs

    approved = _approved_fingerprint(store, work="book-a")
    briefs = approved_craft_briefs(store, "book-a")
    rendered = render_craft_briefs(briefs)

    assert [brief.fingerprint_id for brief in briefs] == [approved.fingerprint_id]
    assert "以环境变化迫使人物做出主动选择" in rendered
    assert "动作后果替代情绪解释" in rendered
    assert "不得复用参考作品的角色名、专名、情节、措辞或句式" in rendered
    for forbidden in ("潮汐旧书", "雾港的钟响了", "沈浪", "雾港", "参考作品的原句"):
        assert forbidden not in rendered
    source = briefs[0].context_source("book-a")
    assert source.source_kind == "reference_craft"
    assert source.source_id == f"reference_fingerprint:{approved.fingerprint_id}"
    assert source.content_digest


def test_reference_craft_is_strictly_scoped_to_current_work(store):
    from scribe3.reference_craft import approved_craft_briefs

    first = _approved_fingerprint(store, work="book-a", title="甲书")
    _approved_fingerprint(store, work="book-b", title="乙书")

    assert [brief.fingerprint_id for brief in approved_craft_briefs(store, "book-a")] == [
        first.fingerprint_id
    ]
    assert approved_craft_briefs(store, "book-missing") == ()
