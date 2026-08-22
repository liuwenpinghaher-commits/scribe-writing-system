# 前端错误解析面（N13）

统一形状：`detail` 为 `{code, message}`，`api.js` `handle()` 已把 `Error.message` 收成人话。

| 点 | 文件 | 现状 | 处置 |
| --- | --- | --- | --- |
| 总入口 | `web/src/api.js` `handle` | 对象 detail → message | 已修 |
| 痕迹页 | `web/src/admin/RunLogsPage.jsx` `Err` | `httpErrorMessage` | 已修 |
| 大纲容器 toast | `web/src/ContainerOutline.jsx` | `httpErrorMessage` | **已销**（2026-08-22） |
| 素材导入 | `web/src/MaterialImport.jsx` | catch 自有文案 | 豁免：不展示 raw detail；期限 2026-09-05，仍不展示 raw 则续挂 |
| 管理台 | `web/src/admin/AdminConsole.jsx` `Err` | `httpErrorMessage` | **已销**（2026-08-22） |

原则：作者看的提示必须是人话。对象 detail 不得直接进 toast。
