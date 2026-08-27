# craft-samples

评测侧给人看的样章。现行：[`docs/plans/2026-08-26-craft-v3.md`](../plans/2026-08-26-craft-v3.md)。

**不作任何闸的证据。** 不进 Surreal，不上现网，不 overlay 已删除的《井台灯》《腕账》《手术室》。作者读完说「像 / 不像」即可。脚本过了不等于样章过了。

v3：处境来自 `premises.json` 随机抽签；提示不给 21 段；写完后跑 `prose_check.py`。不调用 playbook。

| 文件 | 题材 | 抽签 | prose_check | 通道 |
|------|------|------|-------------|------|
| `A1-当代职场.md` | 当代职场 | v2，作者已判不合格 | 0/6（负样本） | coding |
| `D1-当代家庭.md` | 当代家庭 | p04 | 6/6 | coding |
| `D2-海运.md` | 海运 | p07 | 6/6 | coding |
| `D3-幼儿园.md` | 幼儿园 | p11 | 6/6 | coding |

抽签日志：`D-draw-log.json`（seed=20260826）。
