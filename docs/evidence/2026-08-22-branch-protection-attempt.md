# 第十轮 L01 分支保护尝试（未落地）

日期：2026-08-22

## 核验

GitHub MCP `list_branches`（认证用户 `liuwenpinghaher-commits`）：

- `main` sha `2725edd5377c1765b4df8d53b22cbe7d496ab97c`
- **`protected: false`**

本机：

- `gh` 未安装
- 环境无 `GITHUB_TOKEN` / `GH_TOKEN`
- GitHub MCP 无 `update_branch_protection` / `get_branch_protection` 工具（已检索并试调，工具不存在）
- 设置页截图无法产生：`docs/evidence/2026-08-22-branch-protection-screenshot.png` 缺席

## 仍须仓库主人做的事

打开仓库 Settings → Branches → `main`，勾：

1. Require a pull request before merging（approvals = 1）
2. Require status checks to pass（至少 CI job `backend`，内含 compileall）
3. Do not allow bypassing the above settings

或把带 `repo` 管理权限的 PAT 放到 `GITHUB_TOKEN`，跑：

```
./scripts/apply_branch_protection.sh
```

直推 `main` 被拒的终端输出或设置页截图，才算落地。

第十一轮未落 = 评审阻断。
