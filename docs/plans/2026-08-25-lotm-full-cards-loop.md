# lotm-full-cards · 主 loop（规则真源）

短名：`lotm-full-cards`。产品参照书：《诡秘之主》。拆文目录：`docs/worlds/诡秘之主-拆文/`。

> **进度不在本文件。** 各号段只改自己的 shard 进度表。禁止在本文件写「全书 COMPLETE」。MERGE 时除外。

## 资产

| 项 | 路径 | 进 git？ |
|----|------|----------|
| 原文 | `docs/worlds/诡秘之主-全文.md`（UTF-8） | **否**（已 gitignore） |
| 切章索引 | `docs/worlds/诡秘之主-拆文/00-index.md` | 是 |
| 厚卡提示 | `docs/worlds/诡秘之主-拆文/PROMPTS.md` 第1轮 | 是 |
| 章卡 | `docs/worlds/诡秘之主-拆文/章卡/{seq}.md` | 是 |
| 密度样板 | 优先 `章卡/89.md`；若尚未落盘，密度对齐 `docs/worlds/乱世铜炉-拆文/章卡/89.md` 段结构 | 是 |

缺原文 → 写卡会话 **BLOCKED**（不编造、不外网扒书）。

## 号段（并行）

| shard | 文件 | range |
|-------|------|-------|
| A | `docs/plans/2026-08-25-lotm-full-cards-shard-A.md` | （协调侧给定） |
| B | `docs/plans/2026-08-25-lotm-full-cards-shard-B.md` | 546–826 |
| C | `docs/plans/2026-08-25-lotm-full-cards-shard-C.md` | 827–1107 |
| D | `docs/plans/2026-08-25-lotm-full-cards-shard-D.md` | （协调侧给定） |

各 shard：**只改本表**；禁止改他号段文件；禁止改 `docs/SESSION.md`；禁止灌 Surreal；禁止改铜炉拆文。

## 一轮一张（第1轮厚卡）

1. 读本 shard 进度 → `next_seq` = 本段内最小缺号。
2. 读 `00-index.md` 该行（标题、起始行、结束行）。
3. `read_file` 原文 **只读该节**（offset/limit）；禁止通读全文；禁止把整章糊进打开书。
4. 按 `PROMPTS.md` 第1轮厚卡写 `章卡/{seq}.md`。
5. 验收：打开书压缩场面、有标点；书证 ≥3 条带 `L` 行号；段齐全（见 PROMPTS 段题）。
6. 只改本 shard 进度：`本段已写++`、`本段仍缺--`、`last_card`、`next_seq`。
7. 开合格卡：已有合格则跳过勿重写（B：731/732；C：945/946；其余以本 shard 文件为准）。

本段缺号清零 → 本 shard `status=SHARD_COMPLETE`（**不要**写全书 COMPLETE）。

## 合格卡（跳过条件）

- `## 打开书` 下已写出谁的日子、哪一件、读完世界怎么变（不是空标题）。
- `## 书证` 至少 3 条可指回原文的 `L`+数字短句。
- 只有段题、无实质、或书证无 L → 不合格，必须重写。

## 铁律

- 只根据原文；没写到写「正文未写到」，不许补。
- 必须 `read_file` / `grep`；禁止凭记忆编场面。
- 打开书：压缩场面、有标点；禁整章粘贴。
- 专名原样记下；学结构，不把这本故事搬进下一本/Surreal。
