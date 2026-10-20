# SurrealDB 3.2.4 运行手册（demo / prod compose）

> 与 `docs/plans/2026-08-08-surrealdb-3.2.4-optimization-plan.md` M0 对应。  
> 更新：2026-08-08

## 版本与数据

| 项 | 值 |
|----|-----|
| 镜像 | `surrealdb/surrealdb:v3.2.4`（**禁止** `latest` / `v2.*` 挂本卷） |
| 引擎路径 | `surrealkv:/data/data.db` |
| 主机卷 | `${SCRIBE3_DATA_DIR:-/opt/scribe3/data}/surreal` |
| 健康检查 | `/surreal is-ready --endpoint http://127.0.0.1:8000` |

**不可回退**：3.x 数据目录不能用 2.1.x 镜像打开。应用可回滚，数据需 export/import 到新 3.x 卷。

## 已启用 start 参数（compose）

| 参数 | 默认 | 说明 |
|------|------|------|
| `--log info` | info | 常规日志 |
| `--query-timeout` | **300s**（`SURREAL_QUERY_TIMEOUT`） | 单组语句上限；迁移多语句需足够长 |
| `--transaction-timeout` | **120s**（`SURREAL_TRANSACTION_TIMEOUT`） | 单事务上限 |

### CLI 盘点摘要（3.2.4 容器实测）

- **有**：`--query-timeout`、`--transaction-timeout`、`--startup-operation-timeout`、index compaction / reclaim 等后台间隔、capabilities deny/allow 族。  
- **未默认打开**：`--deny-all`（需单独安全加固窗口）、durable sessions（HTTP 会话持久化，当前主路径为 WS + 应用会话）。  
- **慢查询专用 flag**：start help 无独立 `--slow-log-threshold`；靠应用埋点 + `--log` 级别。

## 冒烟

```bash
# 本机有密钥时对公网 demo：
./scripts/smoke_s32.sh

# 在 demo 机上（可读 /opt/scribe3/app/deploy/prod/.env bootstrap）：
./scripts/smoke_s32.sh
# 或
BASE_URL=https://www.example.com ./scripts/smoke_s32.sh
```

检查项：ready/health、登录、capabilities.memory_fabric_v1、works、chapters、codex/health、memory/pending-claims、容器 3.2.x。

## 备份

```bash
# 在 demo 机
export SURREAL_ENV_FILE=/opt/scribe3/app/deploy/prod/.env
./scripts/backup_surreal_demo.sh
# 指定库：
DBS="_reg main demo_s32b" ./scripts/backup_surreal_demo.sh
```

产出：`/opt/scribe3/backups/surreal/<stamp>/` 下 `scribe3__<db>.surql` + `META.txt`。

### 恢复原则（推荐两阶段）

**不要**对全量 export 直接 `surreal import` 到空库（3.2 export 的 SCHEMAFULL 常与运行时 migration 字段集不一致，会报 `field does not exist`）。

推荐：

```bash
# 1) 逻辑备份已有 .surql
# 2) 两阶段恢复到旁路库名（apply_schema → data-only import）
./scripts/restore_scribe_two_phase.sh /opt/scribe3/backups/surreal/.../scribe3__main.surql
# 保留演练库：
KEEP=1 TARGET_DB=restore_tp_main ./scripts/restore_scribe_two_phase.sh ...

# 仅抽出数据文件：
python3 scripts/surreal_export_data_only.py full.surql -o data_only.surql
```

灾难恢复整卷时：新 3.2.4 空卷 → 起 backend → 各作品 `apply_schema` → data-only import 或业务重灌。  

## 记忆边界（运维勿误配）

- 书/过程记忆在 **Surreal**（正典 + `memory_fabric`），**不是** Hermes memory。  
- **不**部署 Spectron 作为第二真相源。  
- `SCRIBE3_MEMORY_FABRIC_V1` 产品默认开；仅测试/关闸时显式 `0`。

## 相关脚本

| 脚本 | 作用 |
|------|------|
| `scripts/smoke_s32.sh` | M0 冒烟 |
| `scripts/backup_surreal_demo.sh` | export 备份 |
| `scripts/deploy_demo.sh` | 应用热更/部署 |

## M1/M2 基线

详见 `docs/ops/surrealdb-3.2.4-m1-baseline.md`。
