# 第四章全流程

```json
{
  "work": "book_qe_live5",
  "seq": 4,
  "title": "第四章 · 湿痕",
  "prose_cn": 888,
  "syn_cn": 122,
  "truth_cn": 105,
  "gate_b": true,
  "anti_meta_ok": true,
  "reader_phase": "green",
  "machine_reader_ok": true,
  "human_acked": true,
  "may_claim_readable": true,
  "scene_cover": {
    "ok": true,
    "degraded": false,
    "beat_ratio": 1.0,
    "valid": 3,
    "total": 3
  },
  "reader_claim_http": 200,
  "save_status": "saved",
  "danger_draft": false,
  "channels": [
    "orch proposal/apply s3_add_chapter",
    "s3_patch_chapter_meta",
    "s3_patch_chapter_plan",
    "save-chapter",
    "post-check",
    "reader-ack",
    "reader-claim",
    "storyline/inject-preview promise_mode=omit"
  ],
  "no_meta_in_prose": true,
  "beats": [
    "湿脚印",
    "侧门灰",
    "匙齿缺口"
  ],
  "soft": [],
  "word_count_work": 3523,
  "chapter_count": 4
}
```

合法通道完成：建章→大纲节拍真相演绎→正文→craft/双灯→人读确认→宣称。
相对 ch3：save 首跳 200（无 danger_draft）；scene_cover 3/3；reader-claim allowed。
