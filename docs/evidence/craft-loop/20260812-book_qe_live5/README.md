# craft-loop 证据会话 · 20260812-book_qe_live5

| 项 | 值 |
|----|-----|
| **协议** | `docs/plans/craft-loop.md` Accepted Draft **0.3.1** |
| **session_id** | `20260812-book_qe_live5` |
| **work** | `book_qe_live5`（铜炉·质量验证两章） |
| **demo** | https://tonglu.qing.blue |
| **焦点章** | seq=2（第二章 · 齿边） |
| **author_human** | `false`（本会话以认证 HTTP 合法通道驱动；镜像 SPA discuss/world_write+approve/prose_write 路径） |
| **verdict** | 见 `PASS.md` |

## 合法通道（本会话实际使用）

1. **工程配额**：`PUT /api/intent-goals` → `total_word_goal=45000`（闸外，非叙事 intent）
2. **world_write+approve**：`POST /api/orchestration/proposal/apply` `decision=approve` `execute=true` → `s3_patch_chapter_plan` 加长 synopsis≥80
3. **prose 手稿**：`POST /api/save-chapter` 写入正文 cn_len≥1500 + focalizer
4. **只读验收**：`GET /api/intent|entities|chapter|craft-gates|promises|motifs|…`

**未使用**：`SCRIBE3_EMERGENCY_REST_WRITE`、REST 灌设定、API 静默 prose inject。

## disclaimer（会话级）

```text
1. 本包 craft-loop PASS ≠ 50k-e2e PASS
2. 本包 craft-loop PASS ≠ v6.3.4 体验总 PASS
3. gate_a.ok ∧ gate_b.ok ∧ gate_c ≠ craft-loop 块 hard 自动绿（见 machine-ssot-eval.json 自算 SSOT）
```
