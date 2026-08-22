# xfail 挂牌清单

每次发版核对。新增 xfail 必须同步登记复核期限。

| 用例 | 文件 | 原因 | 复核期限 | 2026-08-22 复核 |
| --- | --- | --- | --- | --- |
| test_reader_lamp_not_machine_pass | scribe3/tests/test_r8_ui_copy.py | 未上线页面文案，挂牌停住 | 2026-09-22 | **续挂**：文案仍未上线，期限不变 |
| test_write_layout_has_no_dual_lamp_chips | scribe3/tests/test_r8_ui_copy.py | 未上线页面文案，挂牌停住 | 2026-09-22 | **续挂**：同上 |
| test_meta_pane_one_scene_paper | scribe3/tests/test_r8_ui_copy.py | 未上线页面文案，挂牌停住 | 2026-09-22 | **续挂**：同上 |
| test_chapter_open_defaults_to_manuscript | scribe3/tests/test_r8_ui_copy.py | 未上线页面文案，挂牌停住 | 2026-09-22 | **续挂**：同上 |

机制演练：2026-08-22 逐条看过原因，均仍成立，不销账、不改期限。

| test_pulse_endpoint | scribe3/tests/test_pulse.py | scene 维加入后 ==6 硬编码过期 | 2026-09-22 | **已修复（T01）** |
| test_dimension_failsoft_isolated | scribe3/tests/test_pulse.py | arc store mock 不充分 | 2026-09-22 | **已修复（T02）** |
| test_arc_lie_belief_jump_maps_to_decision | scribe3/tests/test_pulse.py | arc mock 不充分 | 2026-09-22 | **已修复（T03）** |
| test_discussion_instructions_contain_pulse | scribe3/tests/test_pulse.py | T04：测试桩须挂 hermes 函数名才能过 GAP-12 | 2026-09-22 | **已修复（T04）**：`fake_stream.__name__ = "hermes_complete_stream"` |
| test_arc_adjacent_decision_sparse_nudge | scribe3/tests/test_pulse.py | arc 未启用 | 2026-09-22 | **已修复（T05）** |
