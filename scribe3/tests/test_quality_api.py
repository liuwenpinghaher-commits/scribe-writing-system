"""Task 4: 参考作品 API 端点 RED 测试。"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scribe3.quality.api import quality_router


@pytest.fixture
def client(store):
    app = FastAPI()
    app.include_router(quality_router)
    app.state.store = store
    return TestClient(app)


class TestImportEndpoint:
    def test_import_pasted_text(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "粘贴参考",
            "text": "参考内容。" * 20,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["reference_work_id"]
        assert body["title"] == "粘贴参考"
        assert body["status"] == "imported"

    def test_import_requires_title(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "text": "内容",
        })
        assert resp.status_code == 422

    def test_import_requires_text_or_file(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "空导入",
        })
        assert resp.status_code == 422


class TestFingerprintEndpoints:
    def _import(self, client, store, title="指纹参考"):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": title,
            "text": "参考正文。" * 50,
        })
        return resp.json()["reference_work_id"]

    def test_generate_fingerprint(self, client, store, monkeypatch):
        ref_id = self._import(client, store)
        fp_json = json.dumps({
            "local_mechanisms": ["悬念"], "cross_chapter_aggregation": "三幕",
            "full_book_fingerprint": "冷硬", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [{"quote": "c", "location": "d"}],
            "transferable_mechanisms": ["视角"], "non_copyable_elements": ["方言"],
            "applicable_scope": "悬疑",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: FakeClient()
        )
        resp = client.post(f"/references/{ref_id}/fingerprints", json={
            "work": store.db_name,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["fingerprint_id"]
        assert body["status"] == "pending_review"

    def test_list_fingerprints(self, client, store, monkeypatch):
        ref_id = self._import(client, store)
        fp_json = json.dumps({
            "local_mechanisms": ["x"], "cross_chapter_aggregation": "y",
            "full_book_fingerprint": "z", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [], "transferable_mechanisms": ["m"],
            "non_copyable_elements": ["n"], "applicable_scope": "s",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: FakeClient()
        )
        client.post(f"/references/{ref_id}/fingerprints", json={"work": store.db_name})
        resp = client.get(f"/references/{ref_id}/fingerprints", params={"work": store.db_name})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestPatchReference:
    def test_patch_returns_current_record(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "原标题", "text": "内容。" * 10,
        })
        ref_id = resp.json()["reference_work_id"]
        patch_resp = client.patch(f"/references/{ref_id}", json={
            "work": store.db_name,
        })
        assert patch_resp.status_code == 200
        assert patch_resp.json()["reference_work_id"] == ref_id
