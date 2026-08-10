"""System Hub KD-6/11: Setting.audience RBAC pure tests (no Surreal)."""
from __future__ import annotations

import pytest

from scribe3 import settings as S


def test_registry_audience_partition():
    authors = [s for s in S.REGISTRY if s.audience == "author"]
    admins = [s for s in S.REGISTRY if s.audience == "admin"]
    assert len(S.REGISTRY) >= 70
    assert len(authors) + len(admins) == len(S.REGISTRY)
    # craft all author
    for s in S.REGISTRY:
        if s.category == "craft":
            assert s.audience == "author", s.key
        if s.category in ("connection", "flags", "gateway"):
            assert s.audience == "admin", s.key
    for k in ("llm.model", "llm.timeout_seconds", "llm.max_retries"):
        assert S._BY_KEY[k].audience == "author"
    assert S._BY_KEY["SCRIBE3_DAILY_CALL_CAP"].audience == "admin"


def test_assert_setting_writable_author_denied_gateway():
    for key in ("HERMES_API", "SCRIBE3_SURREAL_URL", "SCRIBE3_CRAFT_GATE", "SCRIBE3_DAILY_CALL_CAP"):
        with pytest.raises(PermissionError):
            S.assert_setting_writable(key, is_admin_user=False)
        S.assert_setting_writable(key, is_admin_user=True)  # no raise


def test_assert_setting_writable_author_allowed_craft():
    S.assert_setting_writable("craft.banned_density_per_k", is_admin_user=False)
    S.assert_setting_writable("llm.model", is_admin_user=False)


def test_author_may_write_setting():
    assert S.author_may_write_setting("llm.model") is True
    assert S.author_may_write_setting("HERMES_API") is False


def test_gateway_keys_all_admin():
    gw = [s.key for s in S.REGISTRY if s.category == "gateway"]
    assert len(gw) == 12
    for k in gw:
        assert S._BY_KEY[k].audience == "admin"
