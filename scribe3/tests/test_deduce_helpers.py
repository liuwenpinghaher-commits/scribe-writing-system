from scribe3.deduce_helpers import (
    has_five_layer_headings,
    is_heading_noise_role,
    is_layer_heading,
    normalize_role_id,
    resolve_against_cast,
)


def test_normalize_strips_projection_and_importance():
    assert normalize_role_id("投影·覃灰七") == "role:覃灰七"
    assert normalize_role_id("灰七（protagonist）") == "role:覃灰七"
    assert normalize_role_id("冷锅婆（major）") == "role:冷锅婆"
    assert normalize_role_id("## 灰狸") == "role:灰狸"


def test_resolve_against_existing_oids():
    cast = [
        {"id": "role:qin_huiqi", "name": "覃灰七"},
        {"id": "role:leng_guo_po", "name": "冷锅婆"},
    ]
    assert resolve_against_cast("灰七（protagonist）", cast) == "role:qin_huiqi"
    assert resolve_against_cast("冷锅婆", cast) == "role:leng_guo_po"


def test_fullwidth_yiwei_is_heading_not_role():
    assert is_layer_heading("以为（误读）")
    assert is_layer_heading("### 以为(误读)")
    assert is_heading_noise_role("role:以为")
    assert not is_layer_heading("投影·覃灰七")
    prose = "### 看到/听到\n甲\n### 知道\n乙\n### 以为（误读）\n丙\n### 做了/说了\n丁\n### 没察觉的\n戊"
    assert has_five_layer_headings(prose)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("all_pass")

