# lotm-full-cards · 号段 B

短名：`lotm-full-cards-B`。本文件只由 B 会话改进度。禁止改 A/C/D 号段文件，禁止改主 loop 进度表（除非 MERGE）。

## 范围

- 号段：546–826（本段缺约 279；开合 731、732 合格则跳过勿重写）
- 卡目录：`docs/worlds/诡秘之主-拆文/章卡/{seq}.md`
- 规则真源：`docs/plans/2026-08-25-lotm-full-cards-loop.md` + `PROMPTS.md` 第1轮厚卡
- 密度样板：`章卡/89.md`
- 原文：`docs/worlds/诡秘之主-全文.md`（UTF-8；禁止 git add/commit/push）

## 进度（只改本表）

| 项 | 值 |
|----|-----|
| shard | B |
| range | 546–826 |
| next_seq | 546 |
| 本段已写 | 0 |
| 本段仍缺 | 279 |
| status | **BLOCKED** |
| last_card | （尚未） |
| blocked_at | 2026-08-25T15:02Z |
| last_checked | 2026-08-25T15:25Z |
| blocked_reason | 缺原文 `docs/worlds/诡秘之主-全文.md` 与切章索引 `00-index.md`（按合同缺全文 → BLOCKED）。本分支已补可提交脚手架：`lotm-full-cards-loop.md`、`诡秘之主-拆文/PROMPTS.md`（第1轮厚卡）、`章卡/README.md`。密度暂对齐铜炉 `章卡/89.md`。不编造章卡、不外网扒书。全文+索引到位后 `status=running` 从 546 开写。 |

## 一夜 goal（本会话只贴这段）

```
执行 lotm-full-cards 号段 B。
先读 docs/plans/2026-08-25-lotm-full-cards-shard-B.md 进度。
再读 docs/plans/2026-08-25-lotm-full-cards-loop.md 规则 + docs/worlds/诡秘之主-拆文/PROMPTS.md 第1轮厚卡。
打开书学 docs/worlds/诡秘之主-拆文/章卡/89.md。
原文 docs/worlds/诡秘之主-全文.md（UTF-8）。缺全文则 BLOCKED。
只写号段 546–826。next_seq=本文件本段内最小缺号。开合 731/732 跳过。
一轮一张：索引行 → 只读该章 → 厚卡 → 验收 → 只改本 shard 进度。
禁止改 shard-A/C/D、禁止改主 loop 进度表、禁止改 SESSION.md、禁止灌 Surreal、禁止改铜炉拆文。
打开书压缩场面有标点；禁整章糊进打开书；书证≥3 条 L行号。
本会话写到被杀。禁止问继续吗。禁止 CAP。
本段缺号写完：本文件 status=SHARD_COMPLETE（不要写全书 COMPLETE）。
```

## 解阻清单（人侧 / 协调侧）

云端 B/C：gitignore 全文**不会**随 git 进 VM。

1. **已在本分支提供（可 merge）：** `docs/plans/2026-08-25-lotm-full-cards-loop.md`、`docs/worlds/诡秘之主-拆文/PROMPTS.md`、`章卡/README.md`。
2. **仍缺 · 切章索引（可 commit）：** 有全文后跑 PROMPTS 第0轮 → `00-index.md`（须含 546–826 行号）。密度样板 `章卡/89.md` 由较早号段落盘前，密度对齐铜炉 `章卡/89.md`。
3. **仍缺 · 全文（勿 commit）：** 放入本云端工作区 `docs/worlds/诡秘之主-全文.md`（scp/rsync/已授权 URL；禁止公开盗版源）。
4. 全文+索引齐后本会话改 `running`，从 `next_seq=546` 一轮一张。
