"""方案B任务16:四题材包(可选,默认不装)· seed_genre_pack TDD。

背景(oh-story short-write/genre-styles/*.md 骨架;勘误篇层6):爽文题材包是
per-work 显式 opt-in 的可选包,scribe3 严肃/志怪定位默认不装,别删清单走
allow_pattern 路径,套路桥段只作 critique 反面词表(purple_regex),不作生成模板。
"""
import pytest


class TestGenrePacks:
    def test_seed_genre_pack(self, store):
        from scribe3.genres import seed_genre_pack, GENRE_PACKS
        assert "fuchou_daliao" in GENRE_PACKS   # 复仇打脸
        seed_genre_pack(store, "fuchou_daliao")
        rules = store.list_craft_rules()
        kinds = {r["kind"] for r in rules}
        assert "purple_regex" in kinds and "allow_pattern" in kinds  # 套路反面词表+别删清单

    def test_all_four_packs_present_and_well_formed(self):
        from scribe3.genres import GENRE_PACKS
        expected = {"fuchou_daliao", "zhuiqi", "zongcai", "zhaidou"}
        assert expected <= set(GENRE_PACKS)
        for pack_name, pack in GENRE_PACKS.items():
            assert 3 <= len(pack["opening_patterns"]) <= 5, pack_name
            assert 3 <= len(pack["hook_motifs"]) <= 5, pack_name
            assert 1 <= pack["intensity"] <= 5, pack_name
            assert len(pack["moves"]) >= 6, pack_name
            assert 2 <= len(pack["ending_patterns"]) <= 3, pack_name
            assert len(pack["keep_list"]) >= 3, pack_name
            assert len(pack["cliches"]) >= 3, pack_name
            assert pack["length_formula"]
            assert pack["name"]
            assert pack["pov_tone"]

    def test_seed_genre_pack_idempotent(self, store):
        from scribe3.genres import seed_genre_pack
        seed_genre_pack(store, "zhuiqi")
        first_count = len(store.list_craft_rules())
        seed_genre_pack(store, "zhuiqi")
        assert len(store.list_craft_rules()) == first_count

    def test_default_not_seeded(self, store):
        # 默认 work 不含任何题材包(严肃志怪定位)
        store.seed_craft_rules()
        notes = " ".join(r.get("note", "") for r in store.list_craft_rules())
        assert "题材包" not in notes

    def test_unknown_pack_raises(self, store):
        from scribe3.genres import seed_genre_pack
        with pytest.raises(ValueError):
            seed_genre_pack(store, "不存在的包")
