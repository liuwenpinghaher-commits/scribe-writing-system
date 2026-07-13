# 作品生命周期(废弃箱 + 重名硬拦)设计文档

日期:2026-07-13
状态:已与作者确认方向,待实施
背景:作者发现两个缺口——①作品库删书是**不可逆物理删除**(`store.delete_work` 直接 `REMOVE DATABASE {slug}`,整本书的正文/设定/伏笔/时间线/对话全部瞬间销毁),而同一系统里删**章节**却有软删+归档箱可恢复(`archive_chapter`),二者严重不对称;②建书/改名**完全不校验 title**,可以建出任意多个同名作品(slug 是随机 uuid,界面上又不显示),列表里只能靠位置区分。

## 已确认决策

1. **删书改为软删 + 废弃箱**(与章节归档箱同构):删=注册表标记 `archived=true`,**DB 一字不动**;作品库出「废弃箱」入口,可恢复;废弃箱内提供「永久删除」(强确认:输入书名才可执行,才真正 `REMOVE DATABASE`)。
2. **重名硬拦**:建书与改名时同名直接 **409 拒绝**(title 比对忽略首尾空白;**废弃箱里的书不占名**——已废弃的《纸命》不阻止你新建《纸命》)。界面提示「已有同名作品」。

## 交付内容

### 1. 后端注册表层(`scribe3/store.py`)

`work` 表加两个字段:`archived: bool`(缺省 NONE/false)、`archived_at: datetime`。注册表是 SurrealDB 的 `scribe3` ns 下的注册库(见 `_reg_conn`),字段追加无需 migration 表结构变更(SCHEMALESS),但**列表读取必须过滤**。

| 函数 | 改动 |
|---|---|
| `list_works()` | 只返回未废弃的书(`archived = NONE OR archived != true`);返回值保持 `{slug, title}` 不变(前端零感知) |
| `archived_works()` | **新增**:返回 `[{slug, title, archived_at}]`(倒序) |
| `archive_work(slug)` | **新增**:`UPDATE work:{slug} SET archived=true, archived_at=time::now()`;`main` 不可废弃(沿用现有保护) |
| `restore_work(slug)` | **新增**:`SET archived=false, archived_at=NONE`;**恢复前查重**——若已有同名活跃作品,抛错(前端提示"已有同名作品,请先改名") |
| `delete_work(slug)` | 语义收窄为**永久删除**:保留现有 `REMOVE DATABASE`,但**只允许删已废弃的书**(未废弃直接删 → 抛错;强制走"先废弃再永久删"两步) |
| `create_work(title)` | 加重名校验:活跃作品中已有同 title(strip 后)→ 抛 `ValueError("已有同名作品")` |
| `rename_work(slug, title)` | 同上查重(排除自己) |

### 2. REST(`scribe3/app.py`)

| 端点 | 语义 |
|---|---|
| `DELETE /works/{slug}` | 改为**废弃**(软删):调 `archive_work`;返回 `{ok, archived: true}`。**注意**:这是既有端点语义变更——前端删除按钮自动变成"移入废弃箱",无需改前端调用 |
| `GET /works/archived` | 新增:废弃箱列表 |
| `POST /works/{slug}/restore` | 新增:恢复;同名冲突 409 |
| `DELETE /works/{slug}/purge` | 新增:**永久删除**;body 需带 `{confirm_title: "<书名>"}`,与库中 title 不符则 422;非废弃状态 → 409 |
| `POST /works` / `PATCH /works/{slug}` | 重名 → 409(`detail: "已有同名作品:{title}"`) |

写路由台账登记:`("POST","/works/{slug}/restore")`、`("DELETE","/works/{slug}/purge")`(注明:purge 是唯一真删,需 confirm_title + 已废弃两道门)。

### 3. 前端(`scribe3/web/src/Library.jsx`)

- 现有删除按钮:确认框文案改为「移入废弃箱(可恢复)」,调用不变。
- 作品库底部加「废弃箱(N)」折叠区:列出已废弃作品(名 + 废弃时间),每条两个动作:
  - **恢复**:调 restore;同名冲突时红字提示;
  - **永久删除**:ConfirmDialog(danger)要求**输入书名**才启用确认按钮(与仓内高危操作惯例一致),文案明示"该书的正文/设定/伏笔/对话将被彻底销毁,无法恢复"。
- 新建/改名对话框:409 时就地红字「已有同名作品」,不清空输入。

### 4. 明确不做

- 不做删前自动备份(仓内已有 `surreal_backup.sh` 逐书备份脚本,作者可自行使用;废弃箱本身已是后悔药,再叠一层是过度设计);
- 不做废弃箱自动过期清理(书是重资产,不该自动销毁);
- 不改 `main` 主书的任何保护(仍不可废弃/不可删)。

## 测试

- store 层:废弃→list 不见/archived_works 可见→恢复→list 复现;`main` 不可废弃;未废弃直接 purge → 抛错;废弃后 purge → DB 真消失(用测试 DB);重名建书/改名抛错;**废弃的书不占名**(废弃《纸命》后可新建同名);恢复时同名冲突抛错。
- API:各端点状态码(409/422)、purge 的 confirm_title 校验、台账门禁绿。
- 前端:废弃箱渲染/恢复/永久删除需输入书名;建书重名 409 就地提示。
- 真机:建同名书被拦;删一本测试书→进废弃箱→恢复→再废弃→永久删除(用一次性测试书,**绝不碰《纸命》《未命名·古典志怪新作》等真实作品**)。

## 风险

| 风险 | 缓解 |
|---|---|
| `DELETE /works/{slug}` 语义变更(物理删→废弃)影响既有调用方 | 全仓 grep 该端点调用方(前端 Library + 可能的测试/脚本);这是**变安全**的方向,不会造成数据损失 |
| 已存在的同名作品(历史数据) | 校验只作用于新建/改名,存量同名不强制处理;作者可自行改名 |
| purge 误删 | 两道门(必须先废弃 + 必须输入正确书名);真删仍不可逆,文案明示 |
