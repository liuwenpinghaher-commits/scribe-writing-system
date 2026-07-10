---
title: "https://surrealdb.com/docs/manage/cloud/high-availability"
url: "https://surrealdb.com/docs/manage/cloud/high-availability"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/cloud/high-availability

Source: https://surrealdb.com/docs/manage/cloud/high-availability

**High availability (HA)** means your database stays reachable and consistent when individual components fail or during planned maintenance. What you get on SurrealDB Cloud depends on your **plan** and instance topology.
##  Start (single-node)[](https://surrealdb.com/docs/manage/cloud/high-availability#start-single-node)
**Start** instances run SurrealDB on a **single compute node** with dedicated storage. This model is simple and cost-effective for development, staging, and workloads that tolerate brief downtime.
  * •
There is **no multi-node failover** within the instance — if the node, disk, or underlying host fails, connections drop until the platform recovers it.
  * •
**Pausing** an instance stops compute deliberately; **resuming** brings it back on the same configuration.
  * •
Protect production data with **[automated backups](https://surrealdb.com/docs/manage/cloud/backups-and-recovery)** and tested restore procedures rather than assuming in-instance redundancy.

Start on Cloud adds managed patching, snapshots, and operations without you running the server. For workloads that must keep serving through hardware or zone failures, use **Scale** or architect retries and failover at the application layer.
##  Scale (multi-node on SurrealDS)[](https://surrealdb.com/docs/manage/cloud/high-availability#scale-multi-node-on-surrealds)
**Scale** clusters run multiple SurrealDB query nodes against [SurrealDS](https://surrealdb.com/platform/surrealds) distributed storage. HA is built into the architecture:
  * •
**Multi-node clusters** — Scale starts at **three nodes** and you can add more horizontally as throughput grows.
  * •
**Survive node loss** — SurrealDS coordinates replication and quorum consensus so the cluster keeps serving when one node is unavailable, instead of treating three separate single-node databases.

Scale’s **three-node minimum** leaves headroom during failures, upgrades, and maintenance while one node is out of service.
Scale is the managed option when you need fault-tolerant production without operating your own Kubernetes cluster, storage replication, and upgrade runbooks. SurrealDB Cloud provisions the cluster, applies patches, manages backups, and coordinates rolling version upgrades.
See [Cloud architecture](https://surrealdb.com/docs/manage/cloud/architecture) and [Scaling](https://surrealdb.com/docs/manage/cloud/scaling).
##  Choosing between Start and Scale for HA[](https://surrealdb.com/docs/manage/cloud/high-availability#choosing-between-start-and-scale-for-ha)  
| Requirement  | Start  | Scale  |  
| --- | --- | --- |  
| Accept brief maintenance or node recovery windows  | Suitable  | Suitable  |  
| Survive node failure without manual failover  | Limited  | Built-in (multi-node + SurrealDS)  |  
| Horizontal query scale  | Resize vertically only  | Resize vertically or add nodes  |  
##  Related topics[](https://surrealdb.com/docs/manage/cloud/high-availability#related-topics)
  * •
[Instance management](https://surrealdb.com/docs/manage/cloud/instance-management) — pause, resume, and delete instances.
  * •
[Backups & recovery](https://surrealdb.com/docs/manage/cloud/backups-and-recovery) — recover from logical mistakes or regional issues.
  * •
[Patches & upgrades](https://surrealdb.com/docs/manage/cloud/patches-and-upgrades) — change SurrealDB version with platform-managed rollouts.
