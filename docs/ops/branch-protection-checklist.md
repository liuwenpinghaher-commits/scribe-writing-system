# GitHub 分支保护（人工勾，机器进不去设置页）

仓库 → Settings → Branches → `main`

| 项 | 怎么勾 | 怎么验 |
| --- | --- | --- |
| 必须走 PR | Require a pull request before merging | 直推被拒 |
| 至少一人看 | Require approvals = 1 | 没人点通过合不进去 |
| 检查要绿 | Require status checks to pass（至少 `backend`，内含 compileall） | 红检查合不进去 |
| 管理员也不绕 | Do not allow bypassing | 管理员直推同样被拒，截一张证 |

本文件只备材料。真正生效以 GitHub 设置页为准。

催办：第十轮 P0 落地催办已执行。**尚未生效。**

第十轮核验（2026-08-22）：

- GitHub MCP `list_branches`：`main.protected=false`
- 本机无 `gh`、无 `GITHUB_TOKEN`；GitHub MCP 无改保护接口
- 截图目标路径：`docs/evidence/2026-08-22-branch-protection-screenshot.png`（未产生，因设置页进不去）
- 有管理员 PAT 时可跑 `scripts/apply_branch_protection.sh` 一键落地并留 JSON 证

第十一轮若仍未勾，评审判定阻断。
