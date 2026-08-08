# 铜炉（tonglu）产品品牌

## 命名

| 语境 | 名称 | 说明 |
|------|------|------|
| 用户可见（中文 UI） | **铜炉** | 正式产品名 |
| 英文语境短标识 | **tonglu** | 拼音，全小写（title/`application-name` 等） |

## 范围（刻意收窄）

**只做：** 用户可见文案、logo / favicon、页面 title。

**不动：** 画布与主色 token、代码目录 `scribe3/`、`SCRIBE3_*` 环境变量、部署路径、Hermes profile、MCP 工具前缀等。

## 标识资产

| 文件 | 用途 |
|------|------|
| `scribe3/web/public/brand/tonglu-mark.svg` | **主 mark**（透明底矢量）：favicon / 顶栏 / 登录大标 |
| `scribe3/web/public/brand/tonglu-mark-app.svg` | 浅灰圆角底 + 同一 mark（apple-touch） |
| `scribe3/web/public/brand/tonglu-mark.jpg` | 旧栅格稿（可弃用） |
| `scribe3/web/public/brand/tonglu-lockup.jpg` | 横版 lockup 参考稿 |

设计要点：

- **透明底**矢量，无圆角色块底板
- **赛博朋克 / 未来科幻**：HUD 六边形徽章 · 反应堆核心 · 等离子笔锋 · 电青/品红霓虹 + 铜线辅色
- 登录页大标约 **120px** 居中 + 霓虹 glow；顶栏仍 **22px** 小标

前端：`scribe3/web/src/brand.js`、`BrandMark.jsx`、`Login.jsx`
