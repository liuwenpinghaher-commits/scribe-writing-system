# lotm-full-cards · 号段 C

短名：`lotm-full-cards-C`。本文件只由 C 会话改进度。禁止改 A/B/D 号段文件，禁止改主 loop 进度表（除非 MERGE）。

## 范围

- 号段：827–1107（本段缺约 279；开合 945、946 合格则跳过勿重写）
- 卡目录：`docs/worlds/诡秘之主-拆文/章卡/{seq}.md`
- 规则真源：`docs/plans/2026-08-25-lotm-full-cards-loop.md` + `docs/worlds/诡秘之主-拆文/PROMPTS.md` 第1轮厚卡
- 密度样板：`docs/worlds/诡秘之主-拆文/章卡/89.md`
- 原文：`docs/worlds/诡秘之主-全文.md`（UTF-8；禁止 git add/commit/push）

## 进度（只改本表）

| 项 | 值 |
|----|-----|
| shard | C |
| range | 827–1107 |
| next_seq | 827 |
| 本段已写 | 0 |
| 本段仍缺 | 279 |
| status | **BLOCKED** |
| last_card | （尚未） |
| blocked_at | 2026-08-25T15:02Z |
| blocked_reason | 缺原文 `docs/worlds/诡秘之主-全文.md`；同时缺规则真源 `docs/plans/2026-08-25-lotm-full-cards-loop.md`、`docs/worlds/诡秘之主-拆文/PROMPTS.md`、密度样板 `章卡/89.md`、索引与章卡目录内容。云端工作区仅有 `docs/worlds/乱世铜炉-拆文/`，无诡秘之主资产。按一夜 goal：缺全文则 BLOCKED，不编造章卡。 |

## 一夜 goal（本会话）

执行 lotm-full-cards 号段 C。

- 先读本文件进度。
- 再读 loop 规则 + PROMPTS 第1轮厚卡。
- 打开书学 `章卡/89.md`。
- 原文 UTF-8；缺全文则 BLOCKED。
- 只写号段 827–1107。`next_seq`=本段内最小缺号。开合 945/946 跳过。
- 一轮一张：索引行 → 只读该章 → 厚卡 → 验收 → 只改本 shard 进度。
- 禁止改 shard-A/B/D、禁止改主 loop 进度表、禁止改 SESSION.md、禁止灌 Surreal、禁止改铜炉拆文。
- 打开书压缩场面有标点；禁整章糊进打开书；书证≥3 条 L行号。
- 本段缺号写完：本文件 `status=SHARD_COMPLETE`（不要写全书 COMPLETE）。

## 解阻条件

任一会话把下列文件放进本工作区后，C 会话把 `status` 改回 `running` 并从 `next_seq=827` 续写：

1. `docs/worlds/诡秘之主-全文.md`（可 gitignore，勿 commit）
2. `docs/plans/2026-08-25-lotm-full-cards-loop.md`
3. `docs/worlds/诡秘之主-拆文/PROMPTS.md`（含第1轮厚卡）
4. `docs/worlds/诡秘之主-拆文/章卡/89.md`（密度样板）
5. 切章索引（供 827+ 取起始/结束行；路径以 loop 为准）
