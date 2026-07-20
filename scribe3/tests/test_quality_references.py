"""Task 4: 参考作品导入与分层指纹服务 RED 测试。"""
import hashlib
import json

import pytest

from scribe3.quality.references import ReferenceService


class FakeConverter:
    def __init__(self, text: str):
        self._text = text

    def convert(self, src):
        class _R:
            text_content = self._text
        return _R()


class FakeDeepSeek:
    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or [])
        self._call_index = 0
        self.calls: list[list[dict]] = []

    def complete(self, messages, **kwargs):
        self.calls.append(messages)
        if self._call_index >= len(self._responses):
            raise RuntimeError("no more responses")
        text = self._responses[self._call_index]
        self._call_index += 1

        class _Result:
            content = text
            response_id = f"resp-{self._call_index}"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        return _Result()


def _fingerprint_json(**overrides) -> str:
    payload = {
        "local_mechanisms": ["悬念递进"],
        "cross_chapter_aggregation": "全书节奏呈三幕式",
        "full_book_fingerprint": "冷硬叙事与诗意意象交织",
        "evidence": [{"quote": "他走进雨中", "location": "第一章开头"}],
        "counter_evidence": [{"quote": "她笑了", "location": "第三章结尾"}],
        "transferable_mechanisms": ["视角切换制造悬念"],
        "non_copyable_elements": ["作者独特的方言运用"],
        "applicable_scope": "适合悬疑与文学小说",
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


@pytest.fixture
def store(store):
    return store


@pytest.fixture
def service(store):
    return ReferenceService(store)


class TestReferenceImport:
    def test_import_pasted_text(self, service, store):
        result = service.import_reference(
            work=store.db_name, title="测试参考",
            text="这是一段参考文本。" * 10,
        )
        assert result.reference_work_id
        assert result.title == "测试参考"
        assert result.source_hash
        assert result.import_revision == 1
        assert result.status == "imported"

    def test_import_file_txt(self, service, store):
        converter = FakeConverter("文件内容。" * 20)
        result = service.import_reference(
            work=store.db_name, title="文件参考",
            file_src="dummy.txt", converter=converter,
        )
        assert result.reference_work_id
        assert result.status == "imported"

    def test_import_file_md(self, service, store):
        converter = FakeConverter("# 标题\n\n内容。" * 10)
        result = service.import_reference(
            work=store.db_name, title="MD参考",
            file_src="dummy.md", converter=converter,
        )
        assert result.reference_work_id

    def test_import_file_pdf(self, service, store):
        converter = FakeConverter("PDF 内容。" * 10)
        result = service.import_reference(
            work=store.db_name, title="PDF参考",
            file_src="dummy.pdf", converter=converter,
        )
        assert result.reference_work_id

    def test_import_file_docx(self, service, store):
        converter = FakeConverter("DOCX 内容。" * 10)
        result = service.import_reference(
            work=store.db_name, title="DOCX参考",
            file_src="dummy.docx", converter=converter,
        )
        assert result.reference_work_id

    def test_same_source_hash_is_idempotent(self, service, store):
        text = "相同内容。" * 10
        r1 = service.import_reference(work=store.db_name, title="参考A", text=text)
        r2 = service.import_reference(work=store.db_name, title="参考A", text=text)
        assert r1.reference_work_id == r2.reference_work_id
        assert r1.import_revision == r2.import_revision

    def test_import_writes_to_reference_space_not_material(self, service, store):
        service.import_reference(
            work=store.db_name, title="参考B", text="内容。" * 10,
        )
        materials = store._query("SELECT * FROM material", {})
        assert len(materials) == 0
        refs = store._query("SELECT * FROM reference_work", {})
        assert len(refs) >= 1


class TestFingerprintGeneration:
    def test_generate_fingerprint_success(self, service, store):
        ref = service.import_reference(
            work=store.db_name, title="指纹参考", text="参考正文。" * 50,
        )
        llm = FakeDeepSeek([_fingerprint_json()])
        fingerprint = service.generate_fingerprint(
            reference_work_id=ref.reference_work_id, llm=llm,
        )
        assert fingerprint.fingerprint_id
        assert fingerprint.reference_work_id == ref.reference_work_id
        assert fingerprint.status == "pending_review"
        fp = fingerprint.fingerprint
        assert "local_mechanisms" in fp
        assert "cross_chapter_aggregation" in fp
        assert "full_book_fingerprint" in fp
        assert "evidence" in fp
        assert "counter_evidence" in fp
        assert "transferable_mechanisms" in fp
        assert "non_copyable_elements" in fp
        assert "applicable_scope" in fp

    def test_empty_json_response_fails(self, service, store):
        ref = service.import_reference(
            work=store.db_name, title="空响应", text="内容。" * 50,
        )
        llm = FakeDeepSeek([""])
        with pytest.raises(ValueError, match="[Ee]mpty|空"):
            service.generate_fingerprint(
                reference_work_id=ref.reference_work_id, llm=llm,
            )

    def test_missing_required_field_fails(self, service, store):
        ref = service.import_reference(
            work=store.db_name, title="缺字段", text="内容。" * 50,
        )
        incomplete = _fingerprint_json()
        parsed = json.loads(incomplete)
        del parsed["transferable_mechanisms"]
        llm = FakeDeepSeek([json.dumps(parsed, ensure_ascii=False)])
        with pytest.raises(ValueError, match="transferable_mechanisms|必需"):
            service.generate_fingerprint(
                reference_work_id=ref.reference_work_id, llm=llm,
            )


class TestAuthorCorrectionAndApproval:
    def test_author_corrects_and_approves_new_revision(self, service, store):
        ref = service.import_reference(
            work=store.db_name, title="校正参考", text="内容。" * 50,
        )
        llm = FakeDeepSeek([_fingerprint_json()])
        fp = service.generate_fingerprint(
            reference_work_id=ref.reference_work_id, llm=llm,
        )
        corrected = fp.fingerprint.copy()
        corrected["applicable_scope"] = "仅适合历史小说"
        approved = service.approve_fingerprint(
            fingerprint_id=fp.fingerprint_id,
            corrections=corrected,
        )
        assert approved.status == "approved"
        assert approved.revision > fp.revision
        assert approved.fingerprint["applicable_scope"] == "仅适合历史小说"

    def test_approve_without_correction_keeps_original(self, service, store):
        ref = service.import_reference(
            work=store.db_name, title="直接批准", text="内容。" * 50,
        )
        llm = FakeDeepSeek([_fingerprint_json()])
        fp = service.generate_fingerprint(
            reference_work_id=ref.reference_work_id, llm=llm,
        )
        approved = service.approve_fingerprint(
            fingerprint_id=fp.fingerprint_id, corrections=None,
        )
        assert approved.status == "approved"
        assert approved.fingerprint == fp.fingerprint
