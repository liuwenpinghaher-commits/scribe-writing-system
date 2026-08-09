# pressure_progress_ab_v1 · machine 列说明

消费 `measure_pressure` 返回字段；**scorer 须标明 heuristic/human**；含 `literary_claim_ban=true`。

| 列 | 来源 |
|----|------|
| stairs_hit | metrics.progress_stairs_anchored.value |
| stairs_need | progress.min_stairs |
| stairs_tier | progress_stairs_anchored.tier |
| grind_tier / grind_chars | location_grind_run |
| retreat_no_cost | retreat_no_cost.value |
| zero_advance | progress_zero_advance.value |
| irrev_tier | irreversible_anchored.tier |
| literary_claim_ban | 恒 true（machine 禁单独文学达标） |
