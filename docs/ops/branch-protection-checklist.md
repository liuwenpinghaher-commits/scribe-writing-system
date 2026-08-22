# GitHub 分支保护（人工勾，机器进不去设置页）

仓库 → Settings → Branches → `main`

| 项 | 怎么勾 | 怎么验 |
| --- | --- | --- |
| 必须走 PR | Require a pull request before merging | 直推被拒 |
| 至少一人看 | Require approvals = 1 | 没人点通过合不进去 |
| 检查要绿 | Require status checks to pass（至少 compileall） | 红检查合不进去 |
| 管理员也不绕 | Do not allow bypassing | 管理员直推同样被拒，截一张证 |

本文件只备材料。真正生效以 GitHub 设置页为准。
