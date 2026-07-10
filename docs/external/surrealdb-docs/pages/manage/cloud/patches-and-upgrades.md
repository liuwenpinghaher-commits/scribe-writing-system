---
title: "https://surrealdb.com/docs/manage/cloud/patches-and-upgrades"
url: "https://surrealdb.com/docs/manage/cloud/patches-and-upgrades"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/cloud/patches-and-upgrades

Source: https://surrealdb.com/docs/manage/cloud/patches-and-upgrades

SurrealDB Cloud runs a **managed SurrealDB release** on each instance. You choose the version at creation time and can **upgrade** to a newer supported release from the Cloud console or Surrealist without replacing binaries yourself.
##  Changing the SurrealDB version[](https://surrealdb.com/docs/manage/cloud/patches-and-upgrades#changing-the-surrealdb-version)
Open the instance in Surrealist or the Cloud dashboard and select a new **version** from the supported list. The platform validates that the target is an **upgrade** from your current release (downgrades are not supported through this flow).
Before a version change on paid instances, the platform may take a **pre-upgrade backup snapshot** (visible in the instance backup list) so you can restore to a new instance if needed. See [Backups & recovery](https://surrealdb.com/docs/manage/cloud/backups-and-recovery).
Note
**Pre-release builds** (for example nightly or beta tags) are only available when enabled for your organisation. Production workloads should stay on stable releases unless you are explicitly testing a preview.
##  Start vs Scale during upgrades[](https://surrealdb.com/docs/manage/cloud/patches-and-upgrades#start-vs-scale-during-upgrades)  
| Plan  | Typical upgrade behaviour  |  
| --- | --- |  
| **Start**  | The single node is updated to the new image. Expect a **short reconnect window** while the instance restarts on the new version.  |  
| **Scale**  | Upgrades roll the new SurrealDB image through compute nodes **one at a time** while SurrealDS maintains storage consistency. The cluster stays available; you may see briefly reduced query capacity while each node restarts.  |  
Exact timing depends on instance size, storage volume, and cluster layout. Watch **metrics and logs** during and after an upgrade to confirm query latency and error rates return to normal.
##  Planning an upgrade[](https://surrealdb.com/docs/manage/cloud/patches-and-upgrades#planning-an-upgrade)
  1. 1.
Read the **[release notes](https://surrealdb.com/releases)** for breaking changes, new defaults, or removed flags.
  2. 2.
Confirm **application and SDK compatibility** with the target version in a non-production instance first.
  3. 3.
Ensure **recent backups** exist (paid plans) or export logical data with [`surreal export`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export) if you need a portable copy outside Cloud backup restore.
  4. 4.
Apply the version change and verify health checks, smoke tests, and critical queries.

For major-version data migrations, follow [Migrating from older SurrealDB versions](https://surrealdb.com/docs/build/migrating/from-old-surrealdb-versions/overview) in a staging instance before upgrading production.
##  Self-hosted comparison[](https://surrealdb.com/docs/manage/cloud/patches-and-upgrades#self-hosted-comparison)
Self-hosted operators replace the `surreal` binary and run rolling upgrades node by node. On Cloud, the control plane performs the equivalent orchestration for you. For the underlying concepts, see [Self-hosted upgrades & patching](https://surrealdb.com/docs/manage/self-hosted/upgrades-and-patching).
