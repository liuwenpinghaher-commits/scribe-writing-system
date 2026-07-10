---
title: "https://surrealdb.com/docs/manage/cloud/architecture"
url: "https://surrealdb.com/docs/manage/cloud/architecture"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/cloud/architecture

Source: https://surrealdb.com/docs/manage/cloud/architecture

SurrealDB Cloud benefits from [SurrealDB's layered architecture](https://surrealdb.com/docs/architecture), which separates storage from compute, enabling improved scalability, durability and availability without the need to operate, manage, scale or shard your database.
##  Start[](https://surrealdb.com/docs/manage/cloud/architecture#start)
For development and staging applications with vertically scalable requirements. SurrealDB Cloud **Start** provides dedicated storage and a single compute node that you can resize as workloads grow.
![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/light/start-single-node-light.png)![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/start-single-node.png)
##  Scale[](https://surrealdb.com/docs/manage/cloud/architecture#scale)
For **business-critical** applications that must stay available when a node fails and scale query throughput horizontally. **Scale** clusters run on [SurrealDS](https://surrealdb.com/platform/surrealds), SurrealDB's distributed storage engine — with quorum consensus, compute–storage separation, and object-storage-backed durability — and start at **three nodes** , with the ability to scale horizontally beyond that. Scale automatically handles data replication and distributed transactions.
Provisioning a production cluster on SurrealDB Cloud avoids the operational work of self-hosting: Kubernetes, replication, patching, backups, and upgrade orchestration are managed for you.
![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/light/enterprise-multi-node-light.png)![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/enterprise-multi-node.png)
Note
Some Scale capabilities — such as read replicas, database branching, and database forking — are still rolling out. See [Pricing](https://surrealdb.com/pricing) and [Roadmap](https://surrealdb.com/roadmap) for current availability.
To learn more about deployment models and self-hosted SurrealDS, see [Deployment](https://surrealdb.com/docs/build/deployment) and [SurrealDS](https://surrealdb.com/platform/surrealds).
