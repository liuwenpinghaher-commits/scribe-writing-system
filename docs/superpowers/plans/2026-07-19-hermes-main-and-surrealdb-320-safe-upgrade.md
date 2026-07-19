# Hermes Main and SurrealDB 3.2.0 Safe Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Hermes Agent 升级到执行时冻结的官方 `main` 最新提交，对已经运行在官方最新稳定版的 SurrealDB Server 3.2.0 和 Python SDK 2.0.0 完成恢复、兼容和真实业务验收，并且任何阶段失败都不影响已有生产数据和可用服务。

**Architecture:** 新增独立的 `scribe3.upgrade_runtime` 工具包作为升级控制面：冻结官方目标、生成不含密钥的运行清单、导出并恢复 SurrealDB、保护 Hermes 本地改动、在独立源码/venv/HERMES_HOME/端口上构建 canary、对比 HTTP/SSE/工具合同，最后由硬门禁决定是否允许切换。运行证据只落在权限受控的 `~/.scribe3-upgrades/` 中，不进入 Git。

**Tech Stack:** Python 3.14、stdlib dataclasses/json/hashlib/subprocess/pathlib/http.client、pytest、SurrealDB CLI 3.2.0、SurrealDB Python SDK 2.0.0、Hermes官方 installer/updater、launchd、Bash、HTTP/SSE、Git。

## Global Constraints

- SurrealDB 和 Scribe3 现有领域模型是小说业务数据的唯一持久化权威；Hermes 不得建立第二份业务真相。
- `CreativeContextEngine` 仍是上下文规划、检索、协调、装配和验证的唯一业务内核。
- “最新”必须在每次执行开始时从官方来源解析为不可变目标：SurrealDB 取最新稳定 release，Hermes 取官方 `main` SHA。
- 当前 SurrealDB Server 3.2.0 和 Python SDK 2.0.0 已是最新，不重复覆盖安装；本计划对它们做完整的生产兼容和恢复验收。
- Hermes 只有在 canary 、备份、差异、安全、真实 provider 和 Scribe3 合同门全绿时才允许切换。
- 禁止 `git reset --hard`、`git clean`、`git push --force`、数据库 reset/drop/truncate/delete 和手工删除生产数据目录。
- 不调用 updater 内部的硬重置分支：切换前必须证明本地 HEAD 是冻结 `origin/main` 的祖先，且本地没有未推送提交。
- 不让 Dashboard、三个 Gateway 或 MCP watchdog 在原地改动 venv 时继续运行。
- 不使用 `--no-backup`、`--force`、`--force-venv`；官方 updater 必须带 `--backup`。
- 不打印、序列化、比较或提交 secret/token/cookie/Authorization/`.env` 内容；运行证据只记录引用是否存在和认证结果。
- 每次运行使用独立 `run_id`；证据目录必须为 mode `0700`，文件默认 mode `0600`。
- 失败就停在当前阶段；不将“大部分通过”解释为可切换。
- 保留现有未跟踪 `cache_surrealdb_docs.py` 和 `surrealdb-docs-cache/`，不得修改、暂存或提交。
- 不使用可视化伴侣。

## File Structure

### New package

- `scribe3/upgrade_runtime/__init__.py`：稳定公共导出。
- `scribe3/upgrade_runtime/models.py`：目标、阶段、证据、合同差异和切换决策模型。
- `scribe3/upgrade_runtime/process.py`：去敏命令执行、超时、返回码和日志摘要。
- `scribe3/upgrade_runtime/targets.py`：官方版本/SHA解析、本机二进制事实和不可变目标冻结。
- `scribe3/upgrade_runtime/surreal_backup.py`：生产库列举、逻辑导出、哈希清单和不剪枝备份。
- `scribe3/upgrade_runtime/surreal_acceptance.py`：隔离恢复、双重启、数据对比和3.2.0查询能力验收。
- `scribe3/upgrade_runtime/hermes_state.py`：本地 Git/venv/profile/skills 去敏状态和本地改动保护。
- `scribe3/upgrade_runtime/hermes_canary.py`：隔离 installer、独立 HOME/venv/端口和 canary 生命周期。
- `scribe3/upgrade_runtime/contracts.py`：Hermes CLI、HTTP、SSE、approval、tools 和 provider 合同归一化/差异。
- `scribe3/upgrade_runtime/cutover_guard.py`：切换先决条件、launchd 进程门和回滚决策。
- `scribe3/upgrade_runtime/cli.py`：`targets/surreal/hermes-baseline/canary/gate/cutover/postcheck/all` 命令。

### Scripts and documentation

- Create `scribe3/scripts/upgrade_runtime.py`：只做 `python -m scribe3.upgrade_runtime.cli` 的稳定入口。
- Create `scribe3/scripts/hermes_launchd_control.sh`：精确控制四个已知 launchd label，不使用宽泛 kill 或通配符。
- Modify `scribe3/scripts/hermes_smoke.sh`：支持显式 base URL/profile 和归一化 JSON 证据输出。
- Modify `scribe3/HERMES_UPGRADE_EVAL.md`：更新为实际目标、差异、验收和回滚结论。
- Modify `scribe3/DEPLOY.md`：更正 SurrealDB 3.2.0/Hermes main 运行事实和 readiness。
- Modify `docs/系统架构/01-系统架构总览.md`：更新实际版本与权威边界。
- Modify `docs/系统架构/06-SurrealDB使用深度诊断.md`：记录3.2.0恢复和查询计划实证。
- Create `docs/superpowers/2026-07-19-hermes-main-surrealdb-320-upgrade-acceptance.md`：最终可审计验收报告，只引用去敏证据哈希和状态。

### Tests

- `scribe3/tests/test_upgrade_models.py`
- `scribe3/tests/test_upgrade_targets.py`
- `scribe3/tests/test_upgrade_process.py`
- `scribe3/tests/test_surreal_upgrade_backup.py`
- `scribe3/tests/test_surreal_320_acceptance.py`
- `scribe3/tests/test_hermes_upgrade_state.py`
- `scribe3/tests/test_hermes_canary.py`
- `scribe3/tests/test_hermes_upgrade_contracts.py`
- `scribe3/tests/test_hermes_cutover_guard.py`

### Runtime artifacts outside Git

Every implementation run creates one directory such as `~/.scribe3-upgrades/20260719T153000Z-a1b2c3d4/` containing:

- `upgrade-targets.json`
- `run-manifest.json`
- `surreal/exports/`
- `surreal/backup-manifest.json`
- `surreal/restore-evidence.json`
- `hermes/baseline/`
- `hermes/local-changes/`
- `hermes/canary/`
- `hermes/contracts/`
- `cutover-decision.json`
- `postcheck.json`

---

### Task 1: Immutable Upgrade Run and Redacted Process Layer

**Files:**
- Create: `scribe3/upgrade_runtime/__init__.py`
- Create: `scribe3/upgrade_runtime/models.py`
- Create: `scribe3/upgrade_runtime/process.py`
- Create: `scribe3/tests/test_upgrade_models.py`
- Create: `scribe3/tests/test_upgrade_process.py`

**Interfaces:**
- Produces: `UpgradeRun`, `StageResult`, `EvidenceFile`, `GateCheck`, `CutoverDecision`
- Produces: `create_upgrade_run(root: Path, now: datetime, nonce: str) -> UpgradeRun`
- Produces: `run_checked(argv: Sequence[str], *, cwd: Path | None, timeout_s: float, env: Mapping[str, str] | None) -> CommandResult`
- Produces: `redact_text(text: str) -> str`

- [ ] **Step 1: Write failing run-directory and stable-manifest tests**

```python
from datetime import datetime, timezone
from pathlib import Path

from scribe3.upgrade_runtime.models import create_upgrade_run


def test_create_upgrade_run_is_private_and_stable(tmp_path: Path):
    run = create_upgrade_run(
        tmp_path,
        datetime(2026, 7, 19, 7, 30, tzinfo=timezone.utc),
        "a1b2c3d4",
    )
    assert run.run_id == "20260719T073000Z-a1b2c3d4"
    assert run.root.stat().st_mode & 0o777 == 0o700
    assert run.manifest_path.parent == run.root
    assert run.phase == "created"
```

- [ ] **Step 2: Run the tests and confirm import failure**

Run:

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_upgrade_models.py \
  scribe3/tests/test_upgrade_process.py
```

Expected: FAIL because `scribe3.upgrade_runtime` does not exist.

- [ ] **Step 3: Implement immutable models and exact phase transitions**

Use these phase values and no free-form alternatives:

```python
UpgradePhase = Literal[
    "created", "targets_frozen", "surreal_verified", "hermes_baselined",
    "canary_verified", "cutover_allowed", "cutover_complete",
    "postcheck_complete", "failed", "rolled_back",
]
```

`UpgradeRun.advance()` must reject skipped or reversed transitions. `failed` is reachable from every nonterminal phase; `rolled_back` is reachable only after `cutover_complete` or `failed` with `production_mutated=True`.

- [ ] **Step 4: Write failing redaction tests**

```python
from scribe3.upgrade_runtime.process import redact_text


def test_redaction_removes_common_secret_shapes():
    raw = (
        "Authorization: Bearer sk-test-secret\n"
        "DEEPSEEK_API_KEY=sk-another-secret\n"
        '"token":"abc.def.ghi"\n'
        "safe_version=3.2.0"
    )
    clean = redact_text(raw)
    assert "sk-test-secret" not in clean
    assert "sk-another-secret" not in clean
    assert "abc.def.ghi" not in clean
    assert "safe_version=3.2.0" in clean
```

- [ ] **Step 5: Implement argument-vector-only command execution**

`run_checked` must:

- call `subprocess.run(..., shell=False, text=True, capture_output=True)`;
- accept only an argument sequence, never a command string;
- redact stdout/stderr before persistence;
- preserve the exit code and duration;
- cap stored stdout/stderr at 200 KiB each while preserving full-stream SHA-256;
- never persist the provided environment mapping;
- raise a typed timeout result rather than losing partial output.

- [ ] **Step 6: Run focused tests**

Expected: PASS.

---

### Task 2: Freeze Official Targets From Live Binary and Primary Sources

**Files:**
- Create: `scribe3/upgrade_runtime/targets.py`
- Create: `scribe3/tests/test_upgrade_targets.py`
- Create: `scribe3/tests/fixtures/upgrade/surreal_latest_release.json`
- Create: `scribe3/tests/fixtures/upgrade/hermes_latest_release.json`
- Create: `scribe3/tests/fixtures/upgrade/hermes_main_ref.json`

**Interfaces:**
- Produces: `parse_surreal_version(output: str) -> SemVer`
- Produces: `parse_hermes_version(output: str) -> HermesVersion`
- Produces: `resolve_official_targets(http: HttpClient, commands: CommandRunner) -> UpgradeTargets`
- Consumes: `surreal version`, `hermes --version`, `python -m pip show surrealdb`

- [ ] **Step 1: Write fixture-based parser tests**

Cover exact current forms:

```text
3.2.0 for macos on aarch64
Hermes Agent v0.18.2 (2026.7.7.2) · upstream 36f2a966
Version: 2.0.0
```

Assert that a `pyproject.toml`, `package.json`, `vendor/` path or `site-packages` file is never accepted as a version source.

- [ ] **Step 2: Write official-source resolution tests**

Expected official endpoints:

- SurrealDB stable: `https://api.github.com/repos/surrealdb/surrealdb/releases/latest`
- Hermes stable: `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest`
- Hermes main SHA: `https://api.github.com/repos/NousResearch/hermes-agent/git/ref/heads/main`
- Python SDK latest: `https://pypi.org/pypi/surrealdb/json`

The test must reject draft/prerelease SurrealDB releases, missing SHAs, non-40-character SHAs and non-HTTPS source URLs.

- [ ] **Step 3: Implement target freeze with observed facts**

`UpgradeTargets` must store:

- source URL, fetched timestamp and response-body SHA-256;
- official SurrealDB tag and version;
- selected official macOS aarch64 asset URL plus its GitHub `digest` or official checksum-file SHA-256;
- local binary version and running `surreal-version` response header;
- installed SDK version and PyPI latest version;
- official Hermes stable tag;
- official Hermes main SHA;
- local Hermes HEAD/branch and `hermes --version` output;
- linked Hermes evidence snapshot manifest IDs from the prior evidence-cache plan.

If the SurrealDB release API does not expose a cryptographic asset digest, fetch the official checksum attachment and verify the selected asset entry. Never invent a digest from the release JSON body. Because the local binary is already 3.2.0, the asset itself need not be downloaded again unless its provenance cannot otherwise be established.

The resolver must mark the current expected decision as:

```json
{
  "surreal_server_action": "verify_existing_3_2_0",
  "surreal_sdk_action": "verify_existing_2_0_0",
  "hermes_action": "upgrade_to_frozen_main"
}
```

The frozen Hermes SHA must have an integrity-passing `main` snapshot from the evidence-cache plan. If main advanced after that snapshot, refresh and re-audit the fixed new SHA before canary installation; an evidence snapshot for an older SHA cannot satisfy this gate. If SurrealDB stable or SDK latest no longer equals 3.2.0/2.0.0, stop this plan and write the corresponding version-specific migration delta before changing production.

- [ ] **Step 4: Add live CLI command**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli targets \
  --run-root "$HOME/.scribe3-upgrades" \
  --write-current-run-id
```

Expected: prints only `run_id`, component action, safe version/SHA summaries and the path to `upgrade-targets.json`; atomically writes only that run ID to `~/.scribe3-upgrades/current-run-id`; no headers, tokens or `.env` values. Every later command reads this pointer and then verifies the run manifest and frozen target hash before doing work.

- [ ] **Step 5: Run parser tests and live target freeze**

Expected for the current environment:

- SurrealDB binary and running service both resolve to `3.2.0`;
- SDK installed/latest both resolve to `2.0.0`;
- Hermes installed version resolves to `v0.18.2 (2026.7.7.2)`;
- Hermes target is a full 40-character official main SHA;
- no install action has run yet.

---

### Task 3: Non-Pruning SurrealDB Logical Backup With Hash Manifest

**Files:**
- Create: `scribe3/upgrade_runtime/surreal_backup.py`
- Create: `scribe3/tests/test_surreal_upgrade_backup.py`
- Reuse: `scribe3/scripts/surreal_backup.sh`
- Reuse: `scribe3/store.py`

**Interfaces:**
- Produces: `list_databases(client: Surreal) -> tuple[str, ...]`
- Produces: `export_all_databases(config: SurrealBackupConfig, runner: CommandRunner) -> BackupManifest`
- Produces: `verify_backup_manifest(path: Path) -> BackupVerification`

- [ ] **Step 1: Write failing database enumeration and filename tests**

The tests must prove:

- all current databases in namespace `scribe3` are included;
- database names are encoded to safe filenames without collision;
- an empty database set fails instead of producing a false-success backup;
- no production password appears in argv snapshots or persisted results.

- [ ] **Step 2: Write failing atomic export tests with a fake Surreal CLI**

The fake CLI writes deterministic bytes for two databases and exits nonzero for a third. Assert:

- partial `.tmp` output is never promoted to `.surql`;
- one database failure marks the entire manifest failed;
- successful files record bytes and SHA-256;
- the export directory is never pruned.

- [ ] **Step 3: Implement exact export flow**

For each database:

1. open the official SurrealDB CLI using the exact binary captured in target freeze;
2. invoke `surreal export` against `ws://127.0.0.1:8001` and namespace `scribe3`;
3. pass credentials through the process environment or protected config, not persisted argv;
4. write to a temporary file inside the run directory;
5. fsync, hash and atomically rename only after exit code zero;
6. verify the file is nonempty and contains a Surreal export preamble or valid statements;
7. store per-database start/end/duration/bytes/hash/status.

Do not reuse `scribe3/scripts/surreal_backup.sh` for this run because its retention path removes older backups. Keep that script unchanged until the new non-pruning path is proven.

- [ ] **Step 4: Add read-only production inventory before export**

Record only aggregate counts and hashes for these authority classes where present:

- projects/novels and chapters;
- chapter versions and current text hashes;
- canon propositions and knowledge edges;
- material and memory records;
- context plans, traces and quality decisions;
- migrations.

The inventory must use the repository's existing Surreal connection and schema helpers rather than hard-coding guessed table names. Missing optional tables are recorded as absent; missing core tables fail the gate.

- [ ] **Step 5: Run focused tests, then perform the live no-prune export**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_surreal_upgrade_backup.py
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli surreal backup \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
```

Expected: every current `scribe3` database has a nonempty `.surql` file and SHA-256; `backup-manifest.json` status is `passed`; no pre-existing backup was removed.

---

### Task 4: Restore Drill and SurrealDB 3.2.0 Compatibility Harness

**Files:**
- Create: `scribe3/upgrade_runtime/surreal_acceptance.py`
- Create: `scribe3/tests/test_surreal_320_acceptance.py`
- Modify: `scribe3/tests/test_store.py`
- Modify: `scribe3/tests/test_store_reconnect.py`
- Reuse: `scribe3/tests/conftest.py`
- Reuse: `scribe3/migrations/*.surql`

**Interfaces:**
- Produces: `start_isolated_surreal(binary: Path, data_dir: Path, port: int) -> SurrealProcess`
- Produces: `restore_backup(manifest: BackupManifest, target: SurrealTarget) -> RestoreResult`
- Produces: `compare_authority_inventory(before: AuthorityInventory, after: AuthorityInventory) -> InventoryDiff`
- Produces: `probe_surreal_320(target: SurrealTarget) -> tuple[ProbeResult, ...]`

- [ ] **Step 1: Write failing lifecycle tests against a temporary real server**

The test fixture must:

- use `SURREAL_BIN` when set, otherwise `/Users/miaoma/.surrealdb/surreal`;
- use an ASCII-only `mktemp` directory under `/tmp`;
- allocate a random free localhost port;
- start `surreal start surrealkv:` on that temporary directory;
- wait for `/health` and `/ready` separately;
- stop only the PID it started.

Assert `/status`, `/health` and `/ready` are captured as three distinct semantics.

- [ ] **Step 2: Write a tiny round-trip restore test**

Create a temporary namespace/database with:

- two chapter records;
- one relation edge;
- a transaction that updates a version;
- one indexed lookup;
- one record-range query.

Export, start a second 3.2.0 server, import and compare IDs, values, relation endpoints and counts.

- [ ] **Step 3: Implement isolated restore with two restart checks**

The live drill must:

1. create a private temporary SurrealKV directory;
2. start target server and import every export;
3. compare database names and authority inventory;
4. stop the temporary process cleanly;
5. restart from the same temporary directory;
6. repeat readiness and inventory checks;
7. preserve JSON evidence and log hashes in the upgrade run;
8. leave the temporary directory in place until the final report is accepted; do not auto-delete it.

- [ ] **Step 4: Implement the 3.2.0 query probe matrix**

The matrix must include:

- all migrations on an empty database;
- migrations over a restored database;
- per-statement `query_raw` error scanning;
- bound `RecordID`, `RELATE`, `UPSERT` and transaction rollback;
- literal and parameterized record ranges;
- `EXPLAIN FULL` count/index plan and index ready state;
- BM25 text query;
- HNSW/vector query when the schema enables it;
- graph traversal and RRF fusion path;
- live query create/event/kill;
- forced disconnect and SDK reconnect;
- export/import round trip;
- read/write timeout behavior.

For query planner differences, assert the semantic invariant and record the operator tree. Only require `CountScan` or `IndexCountScan` where the current schema and 3.2.0 planner actually guarantee it.

- [ ] **Step 5: Run the focused real-server suite**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
SURREAL_BIN=/Users/miaoma/.surrealdb/surreal \
  scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_surreal_320_acceptance.py \
  scribe3/tests/test_store.py \
  scribe3/tests/test_store_reconnect.py
```

Expected: PASS against a temporary SurrealDB 3.2.0 process; production `127.0.0.1:8001` is never used by tests.

- [ ] **Step 6: Run the live restore drill from the verified backup**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli surreal restore \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli surreal probe \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
```

Expected: `restore-evidence.json` and `surreal-probes.json` both report `passed`; all core inventory deltas are empty.

---

### Task 5: Protect Hermes Dirty State and Capture a Redacted Baseline

**Files:**
- Create: `scribe3/upgrade_runtime/hermes_state.py`
- Create: `scribe3/tests/test_hermes_upgrade_state.py`
- Reuse: `scribe3/hermes_runtime.py`
- Reuse: `scribe3/scripts/provision_hermes.py`
- Reuse: `scribe3/scripts/hermes_smoke.sh`

**Interfaces:**
- Produces: `capture_git_state(repo: Path, evidence_dir: Path) -> HermesGitState`
- Produces: `backup_local_changes(repo: Path, evidence_dir: Path) -> LocalChangesBackup`
- Produces: `capture_hermes_baseline(config: HermesBaselineConfig) -> HermesBaseline`
- Produces: `verify_local_change_backup(backup: LocalChangesBackup) -> tuple[GateCheck, ...]`

- [ ] **Step 1: Write failing Git-state tests in a temporary repository**

Create one tracked modification and two untracked skill files. Assert the snapshot includes:

- branch and full HEAD;
- porcelain-v2 status;
- tracked binary patch SHA-256;
- untracked relative paths, bytes, SHA-256 and copied file hashes;
- remote URL with embedded credentials redacted;
- no Git mutation.

- [ ] **Step 2: Write conflict classification tests**

Given a frozen upstream tree, classify each local path as:

- `local_only`;
- `upstream_only`;
- `identical`;
- `content_conflict`.

`content_conflict` must fail automatic restoration and require an explicit merge artifact. Never silently choose local or upstream.

- [ ] **Step 3: Implement local-change protection**

For the current checkout `/Users/miaoma/.hermes/hermes-agent`, the live snapshot must explicitly cover:

- modified `package-lock.json`;
- every untracked `skills/meeting-*.md` path;
- current branch `main` and HEAD;
- `origin` URL with credentials stripped;
- `git diff --binary` stored outside Git;
- exact hashes of copied untracked files.

Do not stage, stash, reset, checkout or delete anything during baseline capture.

- [ ] **Step 4: Implement the runtime baseline contract**

Capture:

- `hermes --version`;
- `hermes update --check`;
- `hermes doctor` and `hermes security audit` results;
- `venv/bin/python -m pip freeze` and `pip check` with secret scanning;
- launchd label/PID/executable mapping;
- default, `scribe3`, and `scribe3_write` profile capabilities/toolsets;
- MCP, skills, plugins, hooks, cron and fallback inventory;
- one real Responses SSE sample;
- one real Runs SSE sample, including an approval request and approve/deny behavior;
- current `hermes_smoke.sh --live` result.

Normalize IDs, timestamps, durations and token counts before comparison, but preserve event order and event type.

- [ ] **Step 5: Run focused tests, then the live baseline**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_hermes_upgrade_state.py
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli hermes-baseline \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
```

Expected: local change backup verifies byte-for-byte; baseline status is `passed` or names a concrete pre-existing failure. Any pre-existing failure must be repaired and re-baselined before canary promotion.

---

### Task 6: Build an Isolated Hermes Canary at the Frozen Main SHA

**Files:**
- Create: `scribe3/upgrade_runtime/hermes_canary.py`
- Create: `scribe3/tests/test_hermes_canary.py`
- Modify: `scribe3/scripts/hermes_smoke.sh`

**Interfaces:**
- Produces: `CanaryPorts`, `CanaryLayout`, `CanaryProcess`
- Produces: `install_canary(targets: UpgradeTargets, layout: CanaryLayout, runner: CommandRunner) -> CanaryInstallResult`
- Produces: `start_canary_profiles(layout: CanaryLayout, ports: CanaryPorts) -> tuple[CanaryProcess, ...]`
- Produces: `stop_canary(processes: Sequence[CanaryProcess]) -> tuple[StageResult, ...]`

- [ ] **Step 1: Write failing layout and port-isolation tests**

Assert:

- code, venv, data and logs live under the upgrade run, never under production `~/.hermes/hermes-agent`;
- all canary ports are loopback-only and different from `8642`, `8643`, `8644` and the dashboard port;
- a port already in use is rejected;
- process shutdown targets exact recorded PIDs only.

- [ ] **Step 2: Write installer argument tests**

The exact canary installer shape must be:

```text
bash scripts/install.sh --dir CANARY_CODE --hermes-home CANARY_HOME --branch main --commit FROZEN_SHA --skip-setup --skip-browser --non-interactive
```

Tests must fail if `--commit` is absent, if production paths are passed, or if `--no-venv`, `--force`, `--no-backup` appears.

- [ ] **Step 3: Implement canary home preparation without copying secrets into evidence**

Create isolated profile directories and:

- copy non-secret configuration through a schema-aware filter;
- copy `SOUL.md`, `USER.md` and profile instructions only into mode-0600 runtime files excluded from evidence hashing by content;
- use the active provider credentials only as inherited process environment;
- record secret variable names as booleans, never values;
- give canary its own sessions/logs/memory/cache directories;
- provision Scribe3-specific skills and MCP overlay through the existing `provision_hermes.py`, with explicit canary paths.

- [ ] **Step 4: Implement exact pinned installation**

The implementation must invoke the installer from a clean copy of the frozen official tree and pass:

```bash
bash scripts/install.sh \
  --dir "$SCRIBE3_HERMES_CANARY_CODE" \
  --hermes-home "$SCRIBE3_HERMES_CANARY_HOME" \
  --branch main \
  --commit "$SCRIBE3_HERMES_TARGET_SHA" \
  --skip-setup \
  --skip-browser \
  --non-interactive
```

After install, verify with the canary binary commands, not metadata files:

```bash
"$SCRIBE3_HERMES_CANARY_CODE/venv/bin/hermes" --version
"$SCRIBE3_HERMES_CANARY_CODE/venv/bin/python" -m pip check
git -C "$SCRIBE3_HERMES_CANARY_CODE" rev-parse HEAD
```

The Git HEAD must exactly equal the frozen SHA.

- [ ] **Step 5: Start three canary gateways**

Start default/read/write profiles on the allocated ports with loopback binding. Wait for health and capability endpoints, record PID/executable/port, and confirm no process references the production venv.

- [ ] **Step 6: Run upstream diagnostics and the official test entry point inside canary**

```bash
"$SCRIBE3_HERMES_CANARY_CODE/venv/bin/hermes" --help
"$SCRIBE3_HERMES_CANARY_CODE/venv/bin/hermes" doctor
"$SCRIBE3_HERMES_CANARY_CODE/venv/bin/hermes" security audit
cd "$SCRIBE3_HERMES_CANARY_CODE"
scripts/run_tests.sh
```

Expected: CLI loads, doctor has no blocking issue, security audit has no unresolved high-severity issue, and the upstream test entry point exits zero. Save redacted logs and exact duration. A flaky or environment-ineligible upstream test must be individually reproduced and classified; it cannot be silently ignored.

- [ ] **Step 7: Run Scribe3 unit tests and live canary installation**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_hermes_canary.py
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli canary install \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli canary start \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID"
```

Expected: pinned HEAD exact match, `pip check` passes, three isolated canary gateways are healthy, production ports and processes are unchanged.

---

### Task 7: Compare Hermes HTTP, SSE, Tool, Approval, and Provider Contracts

**Files:**
- Create: `scribe3/upgrade_runtime/contracts.py`
- Create: `scribe3/tests/test_hermes_upgrade_contracts.py`
- Modify: `scribe3/hermes_runtime.py`
- Modify: `scribe3/tests/test_hermes_runtime.py`
- Modify: `scribe3/scripts/hermes_smoke.sh`

**Interfaces:**
- Produces: `normalize_http_contract(payload: object) -> object`
- Produces: `normalize_sse(events: Sequence[Mapping[str, object]]) -> tuple[NormalizedEvent, ...]`
- Produces: `compare_contracts(baseline: ContractSnapshot, candidate: ContractSnapshot) -> ContractDiff`
- Consumes: `HermesRuntime`, `HermesEventAdapter`

- [ ] **Step 1: Write failing normalization tests using captured synthetic fixtures**

Normalize only volatile fields:

- run/response/session IDs;
- timestamps;
- elapsed durations;
- usage/token counters;
- randomized canary ports.

Do not normalize away:

- endpoint/status code;
- event type and order;
- approval request ID linkage;
- tool name, arguments schema and result/error shape;
- finish reason;
- provider/model identity;
- capability and toolset membership.

- [ ] **Step 2: Write compatibility policy tests**

The candidate may add optional fields and capabilities. It must fail on:

- removed required endpoint;
- changed required field type;
- missing `approval.request` or broken request/decision correlation;
- SSE stream closing before parallel approval is accepted;
- tool-call/result correlation loss;
- profile isolation loss;
- missing Scribe3 MCP tool;
- fallback/mock response where the baseline used a real provider;
- secret leakage in response or logs.

- [ ] **Step 3: Exercise the canary with real provider calls**

Use human-authored, low-cost prompts that still cover the real path:

1. Responses streaming text generation;
2. Runs streaming with one read-only Scribe3 tool;
3. Runs streaming with one approval-required write proposal, first deny then approve in an isolated test project;
4. malformed/unauthorized request;
5. provider timeout/cancel path;
6. explicit stop followed by terminal-event verification;
7. stream disconnect, session continuation and run-recovery replay;
8. Memory Provider initialize/retrieve/store/close and Context Engine/compression lifecycle;
9. concurrent read/write profile calls.

The write test must target an isolated upgrade-test work, never a real author project.

For approve/deny, compare `write_effect.objects`, Surreal authority rows and trace correlation: deny must produce zero authority writes; approve must produce exactly the isolated intended write. Tool output, usage, provider/model/fallback and recovery events remain visible after normalization.

- [ ] **Step 4: Repair adapters only from concrete diffs**

If main changed payload shape, first add the captured failing fixture to `test_hermes_runtime.py`, then make the narrowest compatibility change in `HermesEventAdapter` or `HermesRuntime`. Preserve old and new input contracts when both can be normalized unambiguously. Do not mask semantically incompatible changes.

- [ ] **Step 5: Run contract tests and live comparison**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_hermes_upgrade_contracts.py \
  scribe3/tests/test_hermes_runtime.py
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli canary contracts \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID" \
  --real-provider
```

Expected: all required contracts pass; additive differences are listed separately; mock/fallback usage count is zero.

---

### Task 8: Implement a Hard Cutover Guard and Exact launchd Control

**Files:**
- Create: `scribe3/upgrade_runtime/cutover_guard.py`
- Create: `scribe3/tests/test_hermes_cutover_guard.py`
- Create: `scribe3/scripts/hermes_launchd_control.sh`

**Interfaces:**
- Produces: `evaluate_cutover(run: UpgradeRun, state: CurrentState) -> CutoverDecision`
- Produces: `verify_fast_forward_only(repo: Path, frozen_sha: str) -> tuple[GateCheck, ...]`
- Produces: `verify_runtime_quiescence(processes: Sequence[ProcessInfo]) -> tuple[GateCheck, ...]`

- [ ] **Step 1: Write exhaustive gate truth-table tests**

Cutover is allowed only if every item is true:

- target sources and hashes verified;
- Surreal backup complete and hashes verified;
- Surreal restore drill and 3.2.0 probes pass;
- Hermes dirty-state backup byte-verifies;
- canary install HEAD equals frozen main SHA;
- canary security, dependency, HTTP/SSE/tool/provider contracts pass;
- current production Hermes HEAD has not changed since baseline;
- `git merge-base --is-ancestor HEAD FROZEN_SHA` exits zero;
- `git rev-list FROZEN_SHA..HEAD` is empty;
- frozen SHA still belongs to official `origin/main` history;
- no active Scribe3 AI run or pending approval exists;
- all four launchd labels can be resolved exactly;
- rollback anchor exists and verifies.

One false or unknown value must produce `allowed=false`.

- [ ] **Step 2: Add explicit protection against updater hard-reset fallback**

The guard must run these read-only checks before updater invocation:

```bash
git -C /Users/miaoma/.hermes/hermes-agent fetch origin main
git -C /Users/miaoma/.hermes/hermes-agent merge-base --is-ancestor \
  HEAD "$SCRIBE3_HERMES_TARGET_SHA"
git -C /Users/miaoma/.hermes/hermes-agent rev-list \
  "$SCRIBE3_HERMES_TARGET_SHA"..HEAD
```

It must also confirm `origin/main` still resolves to the frozen SHA. If upstream advanced, this run stops and creates a new target-freeze run; it does not silently chase the new commit during cutover.

- [ ] **Step 3: Implement exact launchd control**

The script may act only on these labels:

```text
ai.hermes.dashboard
ai.hermes.gateway
ai.hermes.gateway-scribe3
ai.hermes.gateway-scribe3_write
```

Required commands:

```bash
scribe3/scripts/hermes_launchd_control.sh status
scribe3/scripts/hermes_launchd_control.sh stop
scribe3/scripts/hermes_launchd_control.sh start-gateways
scribe3/scripts/hermes_launchd_control.sh start-dashboard
scribe3/scripts/hermes_launchd_control.sh verify
```

It must use `launchctl print`/`bootout`/`bootstrap` with exact user-domain labels and known plist paths, verify recorded executable paths, and refuse missing or unexpected definitions. `start-gateways` starts and verifies default/read/write only; `start-dashboard` is rejected until all three gateways pass their core contracts. No `pkill`, broad `killall`, wildcard or process-name matching.

- [ ] **Step 4: Write process-quiescence tests**

Before update, require:

- no Dashboard/Gateway process points into `/Users/miaoma/.hermes/hermes-agent/venv`;
- no MCP watchdog spawned by those gateways remains;
- production ports are closed;
- SurrealDB on `127.0.0.1:8001` remains healthy;
- Scribe3 has stopped accepting new AI runs but remains able to read existing content.

- [ ] **Step 5: Run gate tests and a dry-run decision**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_hermes_cutover_guard.py
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli gate \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID" \
  --dry-run
```

Expected: a signed-by-hash `cutover-decision.json` listing every check. Do not proceed unless `allowed=true`.

---

### Task 9: Perform the Production Hermes Cutover With an Independent Rollback Anchor

**Files:**
- Modify: `scribe3/upgrade_runtime/cli.py`
- Modify: `scribe3/upgrade_runtime/cutover_guard.py`
- Modify: `scribe3/scripts/provision_hermes.py`
- Reuse: `scribe3/scripts/hermes_launchd_control.sh`

**Interfaces:**
- Produces: `perform_cutover(run: UpgradeRun) -> StageResult`
- Produces: `restore_local_changes(run: UpgradeRun, new_tree: Path) -> LocalRestoreResult`
- Produces: `rollback_hermes(run: UpgradeRun) -> StageResult`

- [ ] **Step 1: Write a state-machine test that forbids cutover from every non-allowed phase**

Also assert that a second cutover call is idempotently rejected and that rollback cannot target an unverified anchor.

- [ ] **Step 2: Create the independent rollback anchor before stopping services**

The anchor must contain, outside Git:

- current Git bundle or verified repository snapshot sufficient to restore the old commit without network;
- old full HEAD and branch;
- old venv dependency freeze and binary version output;
- existing configuration/profile/skills/hooks/cron inventory;
- local tracked patch and untracked file copies with hashes;
- exact launchd plist hashes and label/executable mapping;
- official updater backup path after it is created.

Secret-bearing production configuration may be referenced in place and hashed with a keyed/non-content exposure mechanism; do not copy its contents into a commit-capable directory.

- [ ] **Step 3: Quiesce production and re-evaluate the gate**

Sequence:

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/scripts/hermes_launchd_control.sh stop
scribe3/scripts/hermes_launchd_control.sh verify
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli gate \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID" \
  --require-quiescent
```

If the target SHA, local HEAD, dirty file hashes, pending-run count or any backup hash changed, restart old services and abort.

After quiescence, make a private byte-preserving filesystem copy of the complete old install tree, including its venv, into the run's rollback directory using macOS `ditto`. Verify old `hermes --version`, Python executable, Git HEAD and a deterministic inventory/hash manifest from that copy. Do not remove or rename the production install during backup creation.

- [ ] **Step 4: Invoke the official updater only after the fast-forward gate**

The production command is:

```bash
hermes update --backup --yes --branch main
```

Immediately after it returns, verify:

```bash
git -C /Users/miaoma/.hermes/hermes-agent rev-parse HEAD
hermes --version
/Users/miaoma/.hermes/hermes-agent/venv/bin/python -m pip check
```

HEAD must equal the frozen SHA. A different HEAD, nonzero update, missing backup or failed `pip check` triggers rollback before gateways restart.

- [ ] **Step 5: Restore local content by classification, not blanket overwrite**

- `local_only`: restore exact bytes and verify hash;
- `identical`: leave upstream copy and verify expected hash;
- `upstream_only`: leave upstream copy;
- `content_conflict`: generate `base/local/upstream` evidence and stop before service restart.

For `package-lock.json`, do not blindly reapply the old diff if the new installer legitimately changed dependencies. Preserve the original patch as evidence, compare its intent, and restore only a proven local requirement. For `skills/meeting-*.md`, verify the resulting skills are discoverable exactly once.

- [ ] **Step 6: Re-provision only Scribe3-owned overlays**

Run the existing provisioner in a dry-run/diff mode first. It may update Scribe3 skill/MCP/profile integration but must not overwrite upstream Hermes code or user-owned skills. Apply only after the diff is classified and tested.

- [ ] **Step 7: Restart exact launchd services and verify new executables**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/scripts/hermes_launchd_control.sh start-gateways
scribe3/scripts/hermes_launchd_control.sh verify
scribe3/scripts/hermes_launchd_control.sh start-dashboard
scribe3/scripts/hermes_launchd_control.sh verify
```

Expected: three gateways first run from the upgraded install/venv and pass core contracts; only then Dashboard starts. All four labels end healthy, and no process references the canary or old backup venv.

- [ ] **Step 8: Implement and test rollback before declaring cutover complete**

Rollback must:

1. stop the exact four labels;
2. move the failed new install to a run-ID-suffixed forensic path, then restore the verified old code/venv copy without a destructive Git reset or deletion;
3. restore local-change hashes;
4. restart exact labels;
5. rerun baseline smoke;
6. record `rolled_back` and the triggering failure.

Test the rollback algorithm in a temporary fake install tree. Do not deliberately roll production back after a successful live cutover merely to prove it.

---

### Task 10: Post-Cutover Security, Contract, and Real-Provider Verification

**Files:**
- Modify: `scribe3/upgrade_runtime/contracts.py`
- Modify: `scribe3/upgrade_runtime/cli.py`
- Modify: `scribe3/tests/test_hermes_upgrade_contracts.py`
- Modify: `scribe3/HERMES_UPGRADE_EVAL.md`

- [ ] **Step 1: Re-run binary and dependency truth commands**

```bash
hermes --version
hermes doctor
hermes security audit
/Users/miaoma/.hermes/hermes-agent/venv/bin/python -m pip check
git -C /Users/miaoma/.hermes/hermes-agent rev-parse HEAD
```

Record redacted outputs and hashes. Do not infer any version from `pyproject.toml`, `package.json`, `vendor/` or installed metadata files.

Compare the pre/post dependency freezes and structured security findings. The gate fails on a newly introduced unresolved high-severity finding, a previously patched vulnerable pin reappearing, or `pip check` inconsistency. If an upstream pin is vulnerable, first verify the official compatibility path; apply a minimal targeted patch only in the production venv after reproducing it in canary, then rerun upstream tests, all three gateways and the complete contract suite.

- [ ] **Step 2: Re-run the entire live contract suite against production ports**

Cover:

- health/readiness/capabilities/toolsets for all profiles;
- Responses text and SSE;
- Runs text and SSE;
- approval request, deny, approve and stream-continuation behavior;
- Scribe3 MCP read and isolated write;
- concurrency, cancellation, timeout and malformed request;
- real provider/model identity;
- no mock/fallback;
- no secret leakage.

- [ ] **Step 3: Compare baseline, canary, and production**

Every required contract must match the canary result. Allowed additive changes are documented; any candidate-only success that production cannot reproduce fails postcheck and triggers rollback.

- [ ] **Step 4: Run the production smoke entry point**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/scripts/hermes_smoke.sh --live
SCRIBE3_UPGRADE_RUN_ID="$(tr -d '\r\n' < "$HOME/.scribe3-upgrades/current-run-id")"
scribe3/.venv/bin/python -m scribe3.upgrade_runtime.cli postcheck \
  --run-id "$SCRIBE3_UPGRADE_RUN_ID" \
  --real-provider
```

Expected: `postcheck.json` is `passed`, production HEAD equals frozen SHA, all profile contracts pass and real-provider count is greater than zero.

---

### Task 11: Full Scribe3 Regression and Isolated Novel-Quality Business Loop

**Files:**
- Modify only when a failing regression demonstrates a concrete compatibility defect.
- Reuse: `scribe3/tests/`
- Reuse: `scribe3/web/`
- Reuse: existing real-author E2E and quality audit scripts.
- Create: `docs/superpowers/2026-07-19-hermes-main-surrealdb-320-upgrade-acceptance.md`

- [ ] **Step 1: Run the focused integration suite first**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
SURREAL_BIN=/Users/miaoma/.surrealdb/surreal \
  scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_hermes_runtime.py \
  scribe3/tests/test_provision_hermes.py \
  scribe3/tests/test_store.py \
  scribe3/tests/test_store_reconnect.py \
  scribe3/tests/test_upgrade_models.py \
  scribe3/tests/test_upgrade_targets.py \
  scribe3/tests/test_upgrade_process.py \
  scribe3/tests/test_surreal_upgrade_backup.py \
  scribe3/tests/test_surreal_320_acceptance.py \
  scribe3/tests/test_hermes_upgrade_state.py \
  scribe3/tests/test_hermes_canary.py \
  scribe3/tests/test_hermes_upgrade_contracts.py \
  scribe3/tests/test_hermes_cutover_guard.py
```

Expected: PASS.

- [ ] **Step 2: Run the full backend suite against isolated test infrastructure**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
SURREAL_BIN=/Users/miaoma/.surrealdb/surreal \
  scribe3/.venv/bin/python -m pytest -q scribe3/tests
```

Expected: PASS with no production-data test mutation.

- [ ] **Step 3: Run frontend tests and production build serially**

```bash
cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm test
npm run build
```

Expected: Vitest and the production build both exit zero.

- [ ] **Step 4: Build a field-and-function coverage manifest from authority schemas**

Before E2E, use CodeGraph and the actual frontend/backend schemas to enumerate:

- every author-visible form field;
- every accepted API payload field and enum value;
- every chapter/scene/context/quality/reference/approval/export action;
- every Hermes-facing runtime operation;
- every negative, cancel, reconnect and recovery path.

Generate a machine-readable coverage manifest keyed by exact field/action identifier. The E2E must fill every applicable field with meaningful non-default content, exercise every action, and record an explicit schema-backed reason for any inapplicable field. A visually present field or mocked action does not count as covered.

- [ ] **Step 5: Run a real-browser, real-provider, isolated novel workflow**

Create a disposable test work through the real UI/API path and exercise:

- premise/genre/audience/voice/reference-work preferences;
- setting, characters, relationships, timeline, themes and constraints;
- outline, volume, chapter, scene and beat planning;
- Creative Context plan/assembly/trace;
- material/reference recall with provenance;
- draft generation, continuation, revision and approval;
- fixed-dimension LLM quality analysis and comparison with preferred works;
- human decision weighting greater than system score without treating the human as the only evaluator;
- canon/inconsistency checks, memory write-back and next-chapter reuse;
- export and reload.

Generate enough text to cover the established long-form path, but do not claim a full 50,000-character acceptance unless the actual run reaches the target and its artifacts are inspected. If cost/time gates stop the run earlier, report the exact achieved length and keep the 50,000-character gate open.

Run the existing real journey after the backend and frontend are confirmed to be the new processes:

```bash
cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm run e2e:real
```

Before accepting the result, independently probe backend `/health`, `/ready`, `/ai/runtime-status`, all three Hermes profiles and SurrealDB `/health`/`/ready`; record PID/executable/version so a stale service cannot create a false pass.

- [ ] **Step 6: Analyze business quality, not only transport success**

For every stage record:

- expected business intent;
- context sources selected and omitted;
- backend trace and authority writes;
- output quality across fixed dimensions;
- preferred-work comparison without imitation;
- detected defect and direct repair;
- re-run result;
- author override and final decision.

No step passes merely because HTTP returned 2xx or an LLM emitted text.

- [ ] **Step 7: Verify context and authority invariants explicitly**

Inspect `ContextRequest`, `ContextManifest`, `ContextEnvelope`, working summary, cross-session recall and Memory Provider traces. Assert no cross-work recall, no hidden POV leak, no Hermes memory promoted to canon, no second context authority, and every authority mutation has approval/write-effect provenance.

- [ ] **Step 8: Repair every reproducible regression with TDD**

For each failure:

1. isolate root cause using `superpowers:systematic-debugging`;
2. add a minimal failing automated test or captured contract fixture;
3. make the smallest source-of-truth fix;
4. rerun the focused test;
5. rerun the affected end-to-end stage;
6. keep unrelated dirty files untouched.

- [ ] **Step 9: Write the acceptance report**

The report must state:

- frozen target SHA and versions;
- Surreal backup and restore hashes/status;
- canary versus production contract result;
- local dirty files and how each was preserved/merged;
- every test/build/E2E command and exit status;
- real provider/model identity without key values;
- achieved long-form length and quality scores;
- remaining failures or explicitly open gates;
- rollback anchor location and retention decision.

---

### Task 12: Documentation Truth, Generated-Artifact Boundary, and Final Verification

**Files:**
- Modify: `scribe3/HERMES_UPGRADE_EVAL.md`
- Modify: `scribe3/DEPLOY.md`
- Modify: `docs/系统架构/01-系统架构总览.md`
- Modify: `docs/系统架构/06-SurrealDB使用深度诊断.md`
- Modify: repository `.gitignore` only if `~/.scribe3-upgrades/` can appear inside the worktree through configuration.
- Verify: all files changed by this plan.

- [ ] **Step 1: Update docs from observed results only**

Document:

- SurrealDB Server 3.2.0 and SDK 2.0.0 as the verified current versions;
- Hermes exact `hermes --version` output and frozen main SHA;
- current health/readiness endpoints and profile topology;
- supported versus actively enabled SurrealDB 3.2.0 capabilities;
- canary and rollback procedure;
- latest-run evidence lookup without embedding secrets or absolute secret-file paths.

- [ ] **Step 2: Scan the Git diff for secrets and forbidden artifacts**

Run:

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
git diff --check
git status --short
git diff -- . ':(exclude)cache_surrealdb_docs.py' ':(exclude)surrealdb-docs-cache/**' | \
  rg -n '(sk-[A-Za-z0-9_-]{16,}|Bearer [A-Za-z0-9._-]{12,}|API_KEY\s*=\s*[^$[:space:]])'
```

Expected: `git diff --check` exits zero; the secret scan prints nothing; runtime backup/canary/export files do not appear in Git status.

- [ ] **Step 3: Verify no user-owned untracked cache entered the diff**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
git status --short -- cache_surrealdb_docs.py surrealdb-docs-cache
```

Expected: the two user-owned paths remain untracked and unchanged.

- [ ] **Step 4: Run final verification in risk order**

Run focused tests, full backend, frontend tests, frontend build, live Hermes smoke, production Surreal read-only inventory, and the isolated real-provider novel workflow in that order. Save the exact start/end time, exit code and redacted log SHA for every command.

- [ ] **Step 5: Require a final all-gates decision**

The upgrade can be reported complete only when:

- every required test and runtime contract is green;
- production Hermes HEAD equals the frozen official main SHA;
- SurrealDB binary and running process both report 3.2.0;
- SDK binary/package command reports 2.0.0;
- backup, restore and restart drill pass;
- local Hermes changes are hash-accounted;
- real provider, SSE, approval, tools and novel business loop pass;
- the report contains no unsupported completeness claim.

If any item remains open, the final state is `partial` or `rolled_back`, never `complete`.

- [ ] **Step 6: Review staging scope but do not commit or push**

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
git diff --name-only
git status --short
```

Expected: only planned source/tests/docs are candidates for staging. Do not run `git add`, `git commit` or `git push` unless the user separately requests them.

---

## Spec Traceability

| Upgrade gate | Implementation task | Passing evidence |
|---|---:|---|
| U0 target truth | 2, 8, 9 | primary-source target file, binary version commands, exact frozen Hermes SHA |
| U1 data safety | 3, 4 | all-database export hashes, isolated restore, restart and authority-inventory equality |
| U2 compatibility | 4, 7, 11 | Surreal query probes, Hermes normalized contracts, backend/frontend full regression |
| U3 runtime identity | 5, 6, 9, 10 | profile/PID/executable/venv/port mapping and live calls on all three gateways |
| U4 approval truth | 7, 10, 11 | deny zero-write, approve exact-write, open SSE and trace/write-effect correlation |
| U5 context authority | 7, 11 | Context contracts, Memory Provider lifecycle and no-second-authority assertions |
| U6 provider truth | 5, 7, 10 | actual provider/model/fallback/usage evidence with real-provider calls |
| U7 security and local assets | 1, 5, 6, 9, 10 | secret redaction, dirty-file hashes, upstream tests, dependency/security diff |
| U8 whole-system regression | 11, 12 | full tests/build, real browser, every-field/function manifest and long-form quality loop |
| Rollback | 8, 9 | verified old code/venv anchor, exact label control and tested non-destructive restore algorithm |

---

## Execution Order and Stop Conditions

Execute Tasks 1–8 without production Hermes mutation. Task 9 is the only production Hermes cutover point. Tasks 10–12 determine whether the cutover remains or is rolled back.

Stop immediately and keep/restart the old production service when any of these occurs:

- official target cannot be verified or advances after freeze;
- backup/restore hash or authority inventory differs;
- local Hermes changes cannot be losslessly classified;
- canary install does not land on the frozen SHA;
- dependency/security/contract/provider gate fails;
- updater would need a non-fast-forward or hard-reset path;
- post-cutover production differs from the verified canary;
- Scribe3 real business behavior regresses.

The implementation agent must repair deterministic Scribe3 compatibility defects and rerun the affected gate. Upstream-only defects that cannot be safely repaired locally require rollback and an evidence-backed blocked report rather than weakening a gate.
