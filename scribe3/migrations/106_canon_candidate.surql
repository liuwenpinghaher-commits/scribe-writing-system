-- scribe3 · 106_canon_candidate.surql · 全类型设定候选（正文/讨论回写待确认）
-- 见 设计文档/2026-08-07-正文全类型设定回写-完善方案.md

DEFINE TABLE IF NOT EXISTS canon_candidate SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON canon_candidate TYPE option<int>;
DEFINE FIELD IF NOT EXISTS source ON canon_candidate TYPE string DEFAULT 'prose_finalize';
DEFINE FIELD IF NOT EXISTS extractor ON canon_candidate TYPE string DEFAULT 'marker';
DEFINE FIELD IF NOT EXISTS module ON canon_candidate TYPE string;
DEFINE FIELD IF NOT EXISTS op ON canon_candidate TYPE string DEFAULT 'patch';
DEFINE FIELD IF NOT EXISTS target ON canon_candidate TYPE string;
DEFINE FIELD IF NOT EXISTS field ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS before_json ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS after_json ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS evidence ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS confidence ON canon_candidate TYPE float DEFAULT 1.0;
DEFINE FIELD IF NOT EXISTS risk ON canon_candidate TYPE string DEFAULT 'med';
DEFINE FIELD IF NOT EXISTS layer ON canon_candidate TYPE string DEFAULT 'L1';
DEFINE FIELD IF NOT EXISTS status ON canon_candidate TYPE string DEFAULT 'pending'
    ASSERT $value IN ['pending', 'approved', 'rejected', 'merged', 'superseded', 'expired'];
DEFINE FIELD IF NOT EXISTS change_pack_id ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS impact_json ON canon_candidate TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON canon_candidate TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS decided_at ON canon_candidate TYPE option<datetime>;
DEFINE INDEX IF NOT EXISTS idx_cc_status ON canon_candidate FIELDS status;
DEFINE INDEX IF NOT EXISTS idx_cc_module ON canon_candidate FIELDS module;
DEFINE INDEX IF NOT EXISTS idx_cc_seq ON canon_candidate FIELDS seq;

DEFINE TABLE IF NOT EXISTS canon_apply_audit SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS candidate_id ON canon_apply_audit TYPE string;
DEFINE FIELD IF NOT EXISTS module ON canon_apply_audit TYPE string;
DEFINE FIELD IF NOT EXISTS target ON canon_apply_audit TYPE string;
DEFINE FIELD IF NOT EXISTS field ON canon_apply_audit TYPE option<string>;
DEFINE FIELD IF NOT EXISTS result ON canon_apply_audit TYPE string;
DEFINE FIELD IF NOT EXISTS detail ON canon_apply_audit TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created_at ON canon_apply_audit TYPE datetime DEFAULT time::now();
