-- Scribe 领域 schema(SQLite)· Batch 0 子集 · 对齐 设计文档/00-总纲与数据模型.md §4
-- ponytail: Batch 0 只建协作回路最小闭环所需的表;门槛层(伏笔/一致性/记忆)等表在 Batch 2+ 按 00 §4 补齐。
-- 多本书:works.owner_id 为 owner 边界;子实体一律带 work_id,按书隔离(00 §2.7)。

CREATE TABLE IF NOT EXISTS works (
    id            TEXT PRIMARY KEY,
    owner_id      TEXT NOT NULL,
    title         TEXT NOT NULL,
    premise       TEXT,
    genre         TEXT,
    structure_type TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    deleted_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_works_owner ON works(owner_id) WHERE deleted_at IS NULL;

-- 北极星:与 work 1:1(00 §4.1 AuthorIntent)
CREATE TABLE IF NOT EXISTS author_intents (
    id             TEXT PRIMARY KEY,
    work_id        TEXT NOT NULL UNIQUE REFERENCES works(id),
    reader_feeling TEXT,
    core_emotional_arc TEXT,
    why_write      TEXT,
    central_promise TEXT,
    do_not_betray  TEXT,            -- jsonb(红线)
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS volumes (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    seq         INTEGER NOT NULL,
    title       TEXT,
    arc_goal    TEXT,
    structure_beats TEXT,           -- jsonb
    status      TEXT NOT NULL DEFAULT 'draft',
    UNIQUE(work_id, seq)
);

CREATE TABLE IF NOT EXISTS chapters (
    id          TEXT PRIMARY KEY,
    volume_id   TEXT REFERENCES volumes(id),
    work_id     TEXT NOT NULL REFERENCES works(id),
    seq         INTEGER NOT NULL,
    title       TEXT,
    outline     TEXT,               -- jsonb
    beat_targets TEXT,              -- jsonb
    hook_text   TEXT,
    hook_strength INTEGER,
    word_count  INTEGER DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'draft',  -- draft/reviewing/done
    UNIQUE(work_id, seq)
);

CREATE TABLE IF NOT EXISTS segments (
    id          TEXT PRIMARY KEY,
    chapter_id  TEXT NOT NULL REFERENCES chapters(id),
    work_id     TEXT NOT NULL REFERENCES works(id),
    seq         INTEGER NOT NULL,
    text        TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT 'ai',      -- ai/human
    citation_refs TEXT,                          -- jsonb:本段引用的设定/角色/伏笔(P0-2)
    UNIQUE(chapter_id, seq)
);

CREATE TABLE IF NOT EXISTS setting_items (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    type        TEXT NOT NULL,                   -- rule/item/place/faction/term
    name        TEXT NOT NULL,
    content     TEXT,                            -- jsonb
    first_chapter_seq INTEGER,
    UNIQUE(work_id, type, name)
);

-- 想象碎片(00 §4.1)· 状态机 captured→structured→scheduled→used
CREATE TABLE IF NOT EXISTS imaginations (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    raw_text    TEXT NOT NULL,                   -- 永不修改(保护原始输入)
    type        TEXT,
    structured  TEXT,                            -- jsonb
    status      TEXT NOT NULL DEFAULT 'captured',
    scheduled_for TEXT,                          -- jsonb
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_imag_work_status ON imaginations(work_id, status);

-- 意见(00 §4.1)
CREATE TABLE IF NOT EXISTS feedback_notes (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    target_type TEXT NOT NULL,                   -- segment/chapter/option/setting/outline
    target_id   TEXT,
    nl_critique TEXT NOT NULL,
    parsed_directive TEXT,                       -- jsonb
    resulted_snapshot_id TEXT,
    created_at  TEXT NOT NULL
);

-- 版本快照(00 §4.4)· AI 草稿 vs 人工定稿;parent_id 版本树
CREATE TABLE IF NOT EXISTS snapshots (
    id          TEXT PRIMARY KEY,
    chapter_id  TEXT NOT NULL REFERENCES chapters(id),
    work_id     TEXT NOT NULL REFERENCES works(id),
    content     TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT 'ai',      -- ai/human
    parent_id   TEXT REFERENCES snapshots(id),
    branch_label TEXT,
    is_human_locked INTEGER NOT NULL DEFAULT 0,  -- 工程9:AI 不可覆盖 human-locked
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snap_chapter ON snapshots(chapter_id);

-- ===== Batch 1:补齐 00 §4 全量 =====

-- 设定圣经:角色 / 关系 / 弧光时间线 / 时间线事件
CREATE TABLE IF NOT EXISTS characters (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    name        TEXT NOT NULL,
    traits      TEXT,                -- jsonb
    motivation  TEXT,
    voice_profile TEXT,              -- jsonb(声音指纹,供 OOC 检测/写作)
    relations   TEXT,                -- jsonb
    UNIQUE(work_id, name)
);
CREATE TABLE IF NOT EXISTS char_states (
    id          TEXT PRIMARY KEY,
    character_id TEXT NOT NULL REFERENCES characters(id),
    chapter_seq INTEGER NOT NULL,
    state_desc  TEXT,
    change_type TEXT                 -- ability/relation/personality
);
CREATE TABLE IF NOT EXISTS entity_relations (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    src_entity  TEXT NOT NULL,
    dst_entity  TEXT NOT NULL,
    relation    TEXT NOT NULL,
    valid_from_chapter INTEGER,
    valid_to_chapter   INTEGER       -- NULL=仍有效
);
CREATE TABLE IF NOT EXISTS timeline_events (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    chapter_seq INTEGER,
    abs_time    TEXT,
    rel_order   INTEGER,
    description TEXT,
    entity_refs TEXT                 -- jsonb
);

-- 伏笔 F-T-P 状态机(门槛1 / CFPG)
CREATE TABLE IF NOT EXISTS foreshadows (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    summary     TEXT NOT NULL,
    foreshadow_chapter INTEGER,      -- planted at
    trigger_chapter    INTEGER,
    payoff_chapter     INTEGER,
    state       TEXT NOT NULL DEFAULT 'planted',  -- planted/triggered/paid/abandoned
    importance  TEXT DEFAULT 'normal',            -- normal/critical
    payload     TEXT,                -- jsonb
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fore_work_state ON foreshadows(work_id, state);

-- 一致性标记(门槛1,error_class 取值见 00 §5)
CREATE TABLE IF NOT EXISTS consistency_flags (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    chapter_seq INTEGER,
    error_class TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'minor',    -- critical/major/minor/info
    detail      TEXT,
    evidence_refs TEXT,              -- jsonb
    status      TEXT NOT NULL DEFAULT 'open',     -- open/confirmed/dismissed/fixed
    created_at  TEXT NOT NULL
);

-- 记忆条目(实现4:章/卷/全局摘要)
CREATE TABLE IF NOT EXISTS memory_entries (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    scope       TEXT NOT NULL,       -- chapter/volume/global
    summary_text TEXT,
    source_chapter_range TEXT,
    updated_at  TEXT NOT NULL
);

-- 协作回路:多方案 / 讨论线程 / 主编札记
CREATE TABLE IF NOT EXISTS option_sets (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    decision_point TEXT,             -- jsonb
    options     TEXT NOT NULL,       -- jsonb(2-4 变体 + 代价/差异)
    chosen_option_id TEXT,
    choose_rationale TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discussion_threads (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    trigger     TEXT,                -- imagination/feedback/option/proactive
    topic       TEXT,
    messages    TEXT,                -- jsonb(role/text/evidence_refs/concern_type)
    resolution  TEXT,                -- jsonb
    status      TEXT NOT NULL DEFAULT 'open',     -- open/resolved/overridden
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proactive_insights (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    kind        TEXT NOT NULL,       -- foreshadow_overdue/arc_drift/intent_deviation/...
    summary     TEXT,
    evidence_refs TEXT,              -- jsonb
    confidence  REAL,
    severity    TEXT,
    suggested_action TEXT,
    status      TEXT NOT NULL DEFAULT 'new',      -- new/acked/acted/dismissed
    created_at  TEXT NOT NULL
);

-- 原料:素材 / 引用 / 文风范本(owner 级可跨书:work_id 可空)
CREATE TABLE IF NOT EXISTS materials (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    work_id     TEXT REFERENCES works(id),        -- NULL=用户级跨作品
    type        TEXT NOT NULL,
    title       TEXT,
    content     TEXT,                -- jsonb
    source      TEXT,
    tags        TEXT,                -- jsonb
    status      TEXT NOT NULL DEFAULT 'raw',       -- raw/processed/archived
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS material_refs (
    id          TEXT PRIMARY KEY,
    material_id TEXT NOT NULL REFERENCES materials(id),
    used_in     TEXT NOT NULL,       -- chapter/segment/setting_item/...
    target_id   TEXT,
    ref_type    TEXT,                -- manual_cite/ai_inject/distill_setting/...
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS style_exemplars (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    work_id     TEXT REFERENCES works(id),        -- NULL=全局
    label       TEXT,
    sample_text TEXT,
    style_descriptors TEXT,          -- jsonb
    scope       TEXT NOT NULL DEFAULT 'work'       -- work/character/global
);

-- 品味与偏好(内核2,跨书:work_id 可空)
CREATE TABLE IF NOT EXISTS preference_signals (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    work_id     TEXT REFERENCES works(id),        -- NULL=跨书
    source      TEXT NOT NULL,       -- option_choice/feedback/rating/revision_diff/exemplar
    signal      TEXT,                -- jsonb
    polarity    TEXT,                -- +/-
    weight      REAL DEFAULT 1.0,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS taste_models (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    work_id     TEXT REFERENCES works(id),        -- NULL=owner 级底色
    positive_exemplars TEXT,         -- jsonb
    negative_list TEXT,              -- jsonb(AI 腔黑名单/反例)
    learned_preferences TEXT,        -- jsonb
    version     INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT NOT NULL,
    UNIQUE(owner_id, work_id)
);

-- 主编跨会话记忆(内核0,五命名空间)
CREATE TABLE IF NOT EXISTS agent_memory (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    work_id     TEXT REFERENCES works(id),        -- NULL=跨书
    namespace   TEXT NOT NULL,       -- working/session/episodic/semantic/meta
    key         TEXT,
    value       TEXT,                -- jsonb
    confidence  REAL DEFAULT 1.0,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_skills (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    name        TEXT NOT NULL,
    spec        TEXT,                -- jsonb
    status      TEXT NOT NULL DEFAULT 'proposed',  -- proposed/approved/active/retired
    created_by  TEXT DEFAULT 'editor',             -- editor/human
    approved_by_human INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
