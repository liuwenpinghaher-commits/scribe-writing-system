# 铜炉（tonglu）产品品牌

## 命名

| 语境 | 名称 | 说明 |
|------|------|------|
| 用户可见（中文 UI） | **铜炉** | 正式产品名 |
| 英文 / 配置 / 包名 / 日志 | **tonglu** | 拼音，全小写，无空格 |
| 历史代码与部署路径 | `scribe3` / `SCRIBE3_*` | **兼容保留**，逐步迁到 tonglu |

意象：铜鼎之炉——长篇在炉中炼、笔锋为火。与用户作品「乱世铜炉」同名呼应，但产品本身即「铜炉」。

## 标识资产

| 文件 | 用途 |
|------|------|
| `scribe3/web/public/brand/tonglu-mark.svg` | 应用 favicon / 顶栏小标（矢量） |
| `scribe3/web/public/brand/tonglu-mark.jpg` | 应用图标高清稿（深底铜鼎 + 笔锋火） |
| `scribe3/web/public/brand/tonglu-lockup.jpg` | 横版 lockup（炉 +「铜炉」字标） |
| `docs/brand/tonglu-*.jpg` | 设计存档（与 public 同源） |

前端常量：`scribe3/web/src/brand.js`  
组件：`scribe3/web/src/BrandMark.jsx`

## 色板（主）

| Token | 浅色 | 深色 |
|-------|------|------|
| brand | `#b45c2e` | `#e0a06a` |
| canvas | `#f3efe9` | `#12100e` |
| surface | `#fffcf8` | `#1a1614` |
| ink | `#1a1614` | `#f3ebe4` |

## 迁移原则（技术标识）

**本阶段已做：** 用户可见品牌、logo、title、package 名 `tonglu-web`、主色铜褐。

**暂不 bulk 改、以免打断已部署 demo：**

- 代码目录仍为 `scribe3/`（Python 包名、compose build context）
- 服务器路径 `/opt/scribe3/...`
- 环境变量 `SCRIBE3_*`、Hermes profile `scribe3` / `scribe3_write`
- MCP 工具前缀 `s3_*` / `mcp_scribe3_*`

后续迁移时优先顺序建议：

1. 文档与 UI 文案（已启动）
2. 新 env 键 `TONGLU_*` **双读**（同时认 `SCRIBE3_*`）
3. Hermes profile 别名 `tonglu` / `tonglu_write`
4. 目录与 `/opt` 路径（需维护窗 + 部署脚本）

禁止在未做双读前「只删 SCRIBE3、不认旧键」。

## 禁止

- 在用户 UI 再展示 `SCRIBE3` / `Scribe3` 作为产品名
- 把版本号、暂缓功能写进品牌常量
- 将 logo 图里的乱码文字当最终字标（字标以 UI 文本「铜炉」+ SVG mark 为准）
