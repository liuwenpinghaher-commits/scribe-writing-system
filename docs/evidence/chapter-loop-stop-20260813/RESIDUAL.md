# Residual · honest stop

## Accepted chain (only)

| seq | title | composite | Δ | notes |
|-----|-------|-----------|---|-------|
| 5 | 香债 | 9.46 | — | baseline |
| 20 | 夜审前夜 | 9.61 | 0.15 | honest new scene |
| 21 | 炉册点名 | 9.69 | 0.08 | multi-beat conflict |
| 22 | 侧门一寸 | 9.73 | 0.04 | 5 conflict beats |

## Rejected for stop (skeptic)

- ch16–19: ch5 paste + keyword stuffing — **not** in accepted series
- Fake UNIT_OK — replaced by per-case `narrative-unit.log`
- beat_shape「他走了」: now `action_hint_only` (shipped)

## Soft ceiling

D1–D3 already at 10 on ch5; later gains mainly D4 multi-beat + D5/D7. Stop Δ&lt;0.2 is real near-ceiling, not spam.

## Demo

- STORY_COMPLETE=1 SCENE_COVER_IN_CLAIM=0
- claim missing contract → 409
- claim seq22 + story-ack → 200 may_claim_story=true
