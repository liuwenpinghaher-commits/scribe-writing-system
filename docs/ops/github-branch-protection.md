# GitHub 分支保护（人工项 N17）

方案专用机不能代劳。请仓库管理员在 GitHub 打开：

仓库 → Settings → Branches → Branch protection rules → `main`

至少勾：

- Require a pull request before merging（可按团队习惯关，但 **Require status checks to pass** 必须开）
- Require status checks to pass before merging
- 勾上现网 CI job（至少 `ci.yml` 里 compileall 那一档）
- Do not allow bypassing the above settings（管理员也不直推红）

目的：`37b0a988` 那种「启动即死」不能再直推 `main`。

本文件只登记待办。真正生效以 GitHub 设置页为准；做完后把截图或设置导出贴回本目录。

期间最低防线仍是 `ci.yml` compileall 冒烟。
