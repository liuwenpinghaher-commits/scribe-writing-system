"""CapabilityCatalog · 全域能力注册表（单一真相，非散落 if）。

每条 domain 含：match 信号、读写工具白名单、ui_directive 模板、required_outcome。
扩展能力 = 追加 CATALOG 项，禁止在发送路径再写独立 if 树。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# 写工具名必须与 mcp._common.WRITE_GATED / tools_* 一致（测试会校验子集）。
CATALOG: list[dict[str, Any]] = [
    # —— 意图 ——
    {
        "domain": "intent.northstar",
        "label": "北极星/作品意图",
        # 勿含「评分卡」——评分卡是 aux.scorecard 只读域
        "match_keywords": (
            "北极星", "读者感受", "读者感", "情感弧", "红线", "作品意图", "本书意图",
            "set_intent", "s3_set_intent",
        ),
        "match_force": ("登记/更新本书北极星", "写入落库", "北极星意图", "s3_set_intent"),
        "read_tools": ("s3_get_intent",),
        "write_tools": ("s3_set_intent",),
        "required_outcome": "write_proposal",
        # panel 必须是 northstar：前端 uiDirective 映射只有 northstar→capability
        "ui": {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "northstar"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(作品意图):用 s3_set_intent；**不是**评分卡 scorecard。"
        ),
    },
    # —— 设定 Codex ——
    {
        "domain": "codex.character",
        "label": "角色设定",
        "match_keywords": (
            "角色", "人物", "主角", "配角", "角色设定", "人物设定", "外貌", "欲望", "恐惧",
            "表层目标", "弧光", "锚点", "里程碑", "character", "s3_add_character", "s3_patch_character",
            "s3_set_char_anchors", "s3_add_arc_beat", "s3_delete_arc_beat", "s3_add_char_state",
            "更正角色", "更新角色",
        ),
        "match_force": (
            "s3_add_character", "s3_patch_character", "s3_set_char_anchors",
            "s3_add_arc_beat", "s3_delete_arc_beat", "s3_add_char_state",
            "更正角色", "更新角色", "里程碑", "弧光",
        ),
        "read_tools": ("s3_list_chapters", "s3_character_timeline", "s3_get_voice_profile"),
        "write_tools": (
            "s3_add_character", "s3_patch_character", "s3_patch_codex",
            "s3_generate_codex",
            "s3_set_char_anchors",
            "s3_set_voice_profile", "s3_add_char_state",
            "s3_add_arc_beat", "s3_delete_arc_beat",
        ),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "character"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex_character"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(角色设定):必须用 LLM 按合同写厚（性格/目标/需求/恐惧/冲突+能力弱点，公开包≥1200）；"
            "可用 s3_generate_codex(kind=character, persist=true) 一次待批；"
            "禁止口头补全、禁止把薄字段预填进 s3_patch_codex。"
        ),
    },
    {
        "domain": "codex.faction",
        "label": "势力",
        "match_keywords": ("势力", "组织", "门派", "faction", "s3_add_faction", "s3_patch_faction"),
        "match_force": ("s3_add_faction", "s3_patch_faction"),
        "read_tools": ("s3_list_factions",),
        "write_tools": ("s3_add_faction", "s3_patch_faction", "s3_patch_codex", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "faction"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex_faction"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(势力):必须用 LLM 写组织行为卡（意识形态/公开面目/结构或招募/领袖/阶段目标，公开包≥1200）；"
            "可用 s3_generate_codex(kind=faction, persist=true)；"
            "禁止口头补全、禁止 private_operation、禁止预填薄字段。"
        ),
    },
    {
        "domain": "codex.item",
        "label": "物件",
        "match_keywords": ("物件", "物品", "道具", "item", "s3_add_item", "s3_patch_item"),
        "match_force": ("s3_add_item", "s3_patch_item"),
        "read_tools": ("s3_list_items",),
        "write_tools": ("s3_add_item", "s3_patch_item", "s3_patch_codex", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "item"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex_item"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(物件):必须用 LLM 写叙事功能卡（描述≥400+持有者+属性或[\"无\"]，公开包≥1200）；"
            "可用 s3_generate_codex(kind=item, persist=true)；禁止只回名字、禁止预填薄描述。"
        ),
    },
    {
        "domain": "codex.term",
        "label": "术语",
        "match_keywords": ("术语", "名词", "term", "s3_add_term", "s3_patch_term"),
        "match_force": ("s3_add_term", "s3_patch_term"),
        "read_tools": ("s3_list_terms",),
        "write_tools": ("s3_add_term", "s3_patch_term", "s3_patch_codex", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "term"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex_term"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(术语):必须用 LLM 写四格定义（是什么/不是什么/本书用法/边界）≥1200；"
            "可用 s3_generate_codex(kind=term, persist=true)；禁止一句词典、禁止预填薄 definition。"
        ),
    },
    {
        "domain": "codex.world_rule",
        "label": "世界规则",
        "match_keywords": ("世界规则", "法则", "设定规则", "world_rule", "s3_add_world_rule", "s3_patch_world_rule"),
        "match_force": ("s3_add_world_rule", "s3_patch_world_rule"),
        "read_tools": ("s3_list_world_rules",),
        "write_tools": ("s3_add_world_rule", "s3_patch_world_rule", "s3_patch_codex", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "world_rule"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex_world_rule"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(世界规则):必须用 LLM 写代价/限制/例外/能力，公开包≥1200；"
            "可用 s3_generate_codex(kind=world_rule, persist=true)；禁止免费超能力、禁止预填薄 cost。"
        ),
    },
    {
        "domain": "codex.lifecycle",
        "label": "设定生命周期",
        "match_keywords": ("删除设定", "归档设定", "s3_delete_codex", "删角色", "全书写厚", "空壳写厚"),
        "match_force": ("s3_delete_codex", "s3_generate_codex_batch"),
        "read_tools": (),
        "write_tools": ("s3_delete_codex", "s3_generate_codex_batch"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "codex"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(设定生命周期):全书写厚用 s3_generate_codex_batch(persist=true)，过闸直接落库无需再批；"
            "一条失败继续下一条。删除/归档用 s3_delete_codex。禁止 enrich_all，禁止只口头补全。"
        ),
    },
    # —— 关系 / 事实 / 知识 ——
    {
        "domain": "relation.character",
        "label": "角色关系",
        "match_keywords": (
            "人物关系", "角色关系", "盟友", "仇敌", "师徒", "关系推进",
            "s3_add_character_relation", "s3_evolve_relation",
        ),
        "match_force": ("s3_add_character_relation", "s3_evolve_relation"),
        "read_tools": ("s3_relations_at",),
        "write_tools": ("s3_add_character_relation", "s3_evolve_relation"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "character"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "relation"},
        "channel": "world_write",
    },
    {
        "domain": "relation.entity",
        "label": "实体关系",
        "match_keywords": ("实体关系", "s3_add_entity_relation", "s3_list_entity_relations"),
        "match_force": ("s3_add_entity_relation",),
        "read_tools": ("s3_list_entity_relations",),
        "write_tools": ("s3_add_entity_relation",),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "entity_relation"},
        "channel": "world_write",
    },
    {
        "domain": "fact.proposition",
        "label": "命题/事实/世界真相",
        "match_keywords": (
            "命题", "事实", "世界真相", "登记事实",
            "s3_add_fact", "s3_supersede_fact",
        ),
        "match_force": ("s3_add_fact", "s3_supersede_fact"),
        "read_tools": ("s3_project_frame",),
        "write_tools": ("s3_add_fact", "s3_supersede_fact"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "proposition"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "proposition"},
        "channel": "world_write",
    },
    {
        "domain": "knowledge.record",
        "label": "知识边",
        "match_keywords": ("知识", "知情", "s3_record_knowledge", "s3_forget_knowledge"),
        "match_force": ("s3_record_knowledge", "s3_forget_knowledge"),
        "read_tools": ("s3_project_frame", "s3_dramatic_irony"),
        "write_tools": ("s3_record_knowledge", "s3_forget_knowledge"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "knowledge"},
        "channel": "world_write",
    },
    # —— 伏笔 / 母题 / 线索 ——
    {
        "domain": "promise.plant",
        "label": "埋设伏笔",
        "match_keywords": (
            "埋伏笔", "埋承诺", "埋一个承诺", "埋一个伏笔", "埋下承诺", "埋下伏笔",
            "埋一条", "埋设", "种下伏笔", "新伏笔", "新承诺", "plant", "s3_plant_promise",
        ),
        "match_force": ("s3_plant_promise", "埋一个承诺", "埋伏笔"),
        "read_tools": ("s3_list_promises",),
        "write_tools": ("s3_plant_promise",),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "promise"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "promise"},
        "channel": "world_write",
    },
    {
        "domain": "promise.lifecycle",
        "label": "伏笔生命周期",
        "match_keywords": (
            "伏笔", "承诺", "兑现", "回收", "展期", "弃置", "障眼法", "超期伏笔",
            "s3_advance_promise", "s3_touch_promise", "s3_abandon_promise",
            "s3_mark_herring", "s3_patch_promise",
        ),
        "match_force": (
            "s3_advance_promise", "s3_touch_promise", "s3_abandon_promise",
            "s3_mark_herring", "s3_patch_promise",
        ),
        "read_tools": ("s3_list_promises", "s3_promise_timeline"),
        "write_tools": (
            "s3_advance_promise", "s3_touch_promise", "s3_abandon_promise",
            "s3_mark_herring", "s3_patch_promise",
        ),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "promise"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "promise"},
        "channel": "world_write",
    },
    {
        "domain": "motif.manage",
        "label": "母题",
        "match_keywords": ("母题", "motif", "s3_add_motif", "s3_patch_motif", "回响"),
        "match_force": ("s3_add_motif", "s3_patch_motif"),
        "read_tools": ("s3_list_motifs",),
        "write_tools": ("s3_add_motif", "s3_patch_motif", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "motif"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "motif"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(母题):必须用 LLM 写轻量调度卡（theme≥40、echo_terms≥3、unfolding≥80）；"
            "可用 s3_generate_codex(kind=motif)；禁止写成 1200 字圣经散文、禁止预填薄 theme。"
        ),
    },
    {
        "domain": "clue.manage",
        "label": "线索",
        "match_keywords": ("线索", "clue", "s3_add_clue"),
        "match_force": ("s3_add_clue",),
        "read_tools": (),
        "write_tools": ("s3_add_clue",),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "clue"},
        "channel": "world_write",
    },
    # —— 结构 ——
    {
        "domain": "structure.volume",
        "label": "分卷结构",
        "match_keywords": ("分卷", "建卷", "删卷", "卷纲", "s3_add_volume", "s3_patch_volume",
                           "s3_delete_volume", "s3_reorder_chapters", "重排"),
        "match_force": ("s3_add_volume", "s3_patch_volume", "s3_delete_volume", "s3_reorder_chapters"),
        "read_tools": ("s3_list_volumes", "s3_list_chapters"),
        "write_tools": (
            "s3_add_volume", "s3_patch_volume", "s3_delete_volume", "s3_reorder_chapters",
        ),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "volume"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "volume"},
        "channel": "world_write",
    },
    {
        "domain": "structure.chapter",
        "label": "章节结构",
        "match_keywords": ("建章", "新章节", "s3_add_chapter", "s3_patch_chapter_meta", "章标题"),
        "match_force": ("s3_add_chapter", "s3_patch_chapter_meta"),
        "read_tools": ("s3_list_chapters", "s3_get_chapter"),
        "write_tools": ("s3_add_chapter", "s3_patch_chapter_meta"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "chapter"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "chapter_meta"},
        "channel": "world_write",
    },
    # —— 章阶段（大纲/节拍/演绎）——
    # match_force 含 s3_patch_chapter_plan：种子点名即 world_write（软门控；非 Hermes include）
    {
        "domain": "chapter.outline",
        "label": "章大纲",
        # 勿把 s3_patch_chapter_plan 放 keywords（与 force 双计分会压过 beats）
        "match_keywords": (
            "大纲", "章纲", "synopsis", "起草大纲", "写大纲", "本章大纲",
            "压力级", "chapter_role", "stakes", "赌注", "field=synopsis",
        ),
        "match_force": (
            "s3_patch_chapter_plan",
            "写大纲", "起草大纲", "更新大纲", "补大纲", "填大纲",
        ),
        "read_tools": ("s3_get_chapter", "s3_get_intent", "s3_list_promises"),
        "write_tools": ("s3_patch_chapter_meta", "s3_patch_chapter_plan", "s3_generate_stage"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": "outline", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "outline"},
        "channel": "world_write",
        "phase_hint": "outline",
        "context_pack": ("synopsis", "intent_snip", "open_promises", "volume_intro"),
        "instruction_duty": (
            "域纪律(章大纲):必须用 LLM 写因果大纲 ≥500 字；"
            "可用 s3_generate_stage(stage=outline) 或 s3_patch_chapter_plan 写 synopsis；"
            "禁止口号；禁止 s3_save_chapter 完成本任务。"
        ),
    },
    {
        "domain": "chapter.beats",
        "label": "章节拍",
        "match_keywords": (
            "节拍", "章节拍", "情节点", "beats", "字数预算", "展开节拍", "GCD",
            "更新节拍", "补节拍", "写节拍", "field=beats",
        ),
        "match_force": (
            "s3_patch_chapter_plan",
            "写节拍", "更新节拍", "展开节拍", "补节拍", "章节拍",
        ),
        "read_tools": ("s3_get_chapter",),
        "write_tools": ("s3_patch_chapter_plan", "s3_generate_stage"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": "beats", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "beats"},
        "channel": "world_write",
        "phase_hint": "beats",
        "context_pack": ("beats", "synopsis_snip", "drama_contract"),
        "instruction_duty": (
            "域纪律(章节拍):必须用 LLM 写场面纸，每拍≥500、合计≥2000；"
            "可用 s3_generate_stage(stage=beats) 或 s3_patch_chapter_plan 写 beats；"
            "禁止大纲切句充数；禁止 s3_save_chapter 完成本任务。"
        ),
    },
    {
        "domain": "chapter.deduce",
        "label": "章演绎",
        "match_keywords": (
            "演绎", "场景真相", "限知投影", "deduce", "scene_truth",
            "field=scene_truth", "更新演绎",
        ),
        "match_force": (
            "s3_patch_chapter_plan",
            "写场景真相", "补场景真相", "更新演绎", "场景真相",
        ),
        "read_tools": ("s3_get_chapter", "s3_project_frame", "s3_find_leaks"),
        "write_tools": ("s3_patch_chapter_plan", "s3_patch_chapter_meta", "s3_generate_stage"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": "deduce", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "deduce"},
        "channel": "world_write",
        "phase_hint": "deduce",
        "context_pack": ("scene_truth", "involved", "project_frame"),
        "instruction_duty": (
            "域纪律(章演绎):必须用 LLM 写 scene_truth+五层投影合计≥5000；"
            "可用 s3_generate_stage(stage=deduce) 或 s3_patch_chapter_plan；"
            "勿用 s3_add_fact 当场景真相；禁止摘录占位；禁止 s3_save_chapter 完成本任务。"
        ),
    },
    # —— 辅助只读（派生面 · LLM 不写 SSOT）——
    {
        "domain": "aux.brief",
        "label": "章前简报",
        "match_keywords": ("章前简报", "创作简报", "本章简报", "解读简报"),
        "match_force": (),
        "read_tools": ("s3_get_chapter", "s3_list_promises"),
        "write_tools": (),
        "required_outcome": "read_only_advice",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "brief"},
        "channel": "discuss",
        "context_pack": ("brief_sections",),
        "instruction_duty": (
            "域纪律(简报):只读解释/指引；改大纲走 s3_patch_chapter_plan；"
            "埋伏笔走 s3_plant_promise。禁止把简报当可写 SSOT。"
        ),
    },
    {
        "domain": "aux.scorecard",
        "label": "评分卡",
        "match_keywords": (
            "评分卡", "scorecard", "解读评分卡", "本章评分", "机器评分",
            "硬约束 setpoint", "advisory_scores",
        ),
        "match_force": (),
        "read_tools": (),
        "write_tools": (),
        "required_outcome": "read_only_advice",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "northstar"},
        "channel": "discuss",
        "context_pack": ("scorecard",),
        "instruction_duty": (
            "域纪律(评分卡):机器只读分；**不是**作品意图。"
            "改读者感受/红线请用 s3_set_intent；禁止 LLM 写评分卡 SSOT。"
        ),
    },
    {
        "domain": "aux.experience",
        "label": "经验复盘",
        "match_keywords": (
            "经验复盘", "六格", "Scene-Sequel", "问诊信", "续写快照",
            "goal/conflict/disaster", "经验六格",
        ),
        "match_force": (),
        "read_tools": (),
        "write_tools": (),
        "required_outcome": "read_only_advice",
        "ui": {"entry": "manuscript", "phase": None, "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "pressure"},
        "channel": "discuss",
        "context_pack": ("scene_grid", "letter"),
        "instruction_duty": (
            "域纪律(经验复盘):六格/问诊是作者复盘面，**不是** pressure_drive 力学合同，也不是 beats。"
            "改节拍请 s3_patch_chapter_plan；勿把六格当戏剧合同写入。"
        ),
    },
    # —— 正文（与世界写分离）——
    {
        "domain": "prose.generate",
        "label": "正文生成",
        "match_keywords": (
            "正文", "草稿", "续写", "写本章", "写整章", "完整正文", "润色", "扩写", "缩写",
            "改写段落", "文风", "镜头",
        ),
        "match_force": (),
        "read_tools": (),
        "write_tools": (),  # 正文走 PROPOSAL，不走 MCP 世界写
        "required_outcome": "prose_proposal",
        "ui": {"entry": "manuscript", "phase": "final", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "reading", "panel": "prose"},
        "channel": "prose_write",
        "phase_hint": "final",
    },
    {
        "domain": "prose.revise",
        "label": "正文修订",
        "match_keywords": ("改这段", "润色选区", "重写选区", "局部改写"),
        "match_force": (),
        "read_tools": (),
        "write_tools": (),
        "required_outcome": "prose_proposal",
        "ui": {"entry": "manuscript", "phase": "draft", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "draft"},
        "channel": "prose_write",
        "phase_hint": "draft",
    },
    # —— 工艺 / QC ——
    {
        "domain": "craft.rules",
        "label": "工艺规则",
        "match_keywords": ("工艺规则", "craft", "s3_craft_rule_add", "s3_craft_rule_remove", "克制"),
        "match_force": ("s3_craft_rule_add", "s3_craft_rule_remove"),
        "read_tools": ("s3_craft_rule_list",),
        "write_tools": ("s3_craft_rule_add", "s3_craft_rule_remove"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "craft"},
        "channel": "world_write",
    },
    {
        "domain": "qc.review",
        "label": "质量体检",
        "match_keywords": ("体检", "qc", "质量检查", "s3_qc_chapter", "跨章复读", "泄露"),
        "match_force": (),
        "read_tools": ("s3_qc_chapter", "s3_cross_repetition", "s3_find_leaks", "s3_discipline_check"),
        "write_tools": (),
        "required_outcome": "read_only_advice",
        "ui": {"entry": "manuscript", "phase": "final", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "reading", "panel": "qc"},
        "channel": "discuss",
    },
    # —— 声线 ——
    {
        "domain": "voice.manage",
        "label": "声线",
        "match_keywords": ("声线", "声音档案", "OOC", "s3_set_voice_profile", "s3_resolve_voice_flag"),
        "match_force": ("s3_set_voice_profile", "s3_resolve_voice_flag", "s3_fold_voice_flags"),
        "read_tools": ("s3_get_voice_profile", "s3_list_voice_flags", "s3_check_ooc"),
        "write_tools": ("s3_set_voice_profile", "s3_resolve_voice_flag", "s3_fold_voice_flags", "s3_generate_codex"),
        "required_outcome": "write_proposal",
        "ui": {"entry": "codex", "phase": None, "node": {"type": "character"}, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "voice"},
        "channel": "world_write",
        "instruction_duty": (
            "域纪律(声口):必须用 LLM 写 style_summary≥80 且至少两节"
            "（catchphrases/tone_rules/internal_monologue_style/sentence_patterns）；"
            "可用 s3_generate_codex(kind=voice) 或 s3_set_voice_profile；禁止一句标签。"
        ),
    },
    # —— 目的合同 ——
    {
        "domain": "purpose.register",
        "label": "目的合同",
        "match_keywords": ("目的合同", "s3_register_purpose", "本章目的"),
        "match_force": ("s3_register_purpose",),
        "read_tools": (),
        "write_tools": ("s3_register_purpose",),
        "required_outcome": "write_proposal",
        "ui": {"entry": "manuscript", "phase": "outline", "node": {"type": "chapter"},
               "right_tab": "chief", "layout_mode": "collaboration", "panel": "purpose"},
        "channel": "world_write",
    },
    # —— 默认讨论 ——
    {
        "domain": "discuss.general",
        "label": "一般讨论",
        "match_keywords": (),
        "match_force": (),
        "read_tools": ("s3_get_intent", "s3_list_chapters", "s3_list_promises"),
        "write_tools": (),
        "required_outcome": "read_only_advice",
        "ui": {"entry": "manuscript", "phase": None, "node": None, "right_tab": "chief",
               "layout_mode": "collaboration", "panel": "chief"},
        "channel": "discuss",
        "is_default": True,
    },
]


def list_domains() -> list[str]:
    return [c["domain"] for c in CATALOG]


def get_domain(domain: str) -> dict[str, Any] | None:
    for c in CATALOG:
        if c["domain"] == domain:
            return deepcopy(c)
    return None


def primary_domain_ids() -> frozenset[str]:
    """方案要求的主域（含 prose / craft / qc）。"""
    return frozenset(c["domain"] for c in CATALOG)


def all_write_tools_in_catalog() -> set[str]:
    out: set[str] = set()
    for c in CATALOG:
        out.update(c.get("write_tools") or ())
    return out
