# 第五章全流程（叙事优先）

```json
{
  "work": "book_qe_live5",
  "seq": 5,
  "title": "第五章 · 香债",
  "prose_cn": 1250,
  "syn_cn": 169,
  "truth_cn": 171,
  "beats": [
    "冷锅婆拦门讨香债",
    "灰狸扯袖口要跟去",
    "半袋热灰倒进空锅抵账"
  ],
  "narrative_contract": {
    "desire": "查侧门/弄清昨夜脚印与匙齿",
    "obstacle": "冷锅婆香债拦门 + 灰狸缠斗",
    "turn": "热灰抵半债 + 假片打发灰狸",
    "cost": "答应暂不碰侧门；父名阴影挂上夜审"
  },
  "gate_b": true,
  "anti_meta_ok": true,
  "danger_draft": false,
  "machine_reader_ok": true,
  "human_acked": true,
  "reader_phase": "green",
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
  "word_count_work": 4773,
  "chapter_count": 5,
  "channels": [
    "orch s3_add_chapter",
    "s3_patch_chapter_meta",
    "s3_patch_chapter_plan",
    "save-chapter",
    "post-check",
    "reader-ack",
    "reader-claim",
    "storyline inject omit"
  ],
  "no_meta_in_prose": true,
  "honest_note": "节拍为冲突句非道具词；机判 scene_cover 曾因逗号句式误伤，已拆句而非压回道具标签。工程绿≠文学满分。"
}
```
