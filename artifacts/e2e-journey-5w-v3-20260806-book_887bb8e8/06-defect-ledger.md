# defect ledger (v3)

| ID | 级 | 描述 | 处置 | 状态 |
|----|----|------|------|------|
| D-v2-offline | P0 | v2 离线 prose_pure 灌库冒充真路径 | 新书 v3 pilot 真链；v2 标题标不作PASS | closed |
| D-char-count | P0 | 旅程永卡世界（list_characters 空） | director._char_count→characters() | closed |
| D-orch-char-mem | P0 | orch patch 角色只写内存 | update_record 真落库 | closed |
| D-prose-none | P1 | 强制重写 SET prose=NONE 非法 | 改空串 | closed |
| D-ai-grade-loop | P1 | full_check 仅 AI 味死循环 | soft-pass + quality_warn | closed |
| D-force-loop | P1 | 够长后【强制重写】残留无限清稿 | 仅短于目标才清 | closed |

**开放 P0/P1**：无。

**缺陷线判定**：无开放 P0/P1 → 可 PASS。
