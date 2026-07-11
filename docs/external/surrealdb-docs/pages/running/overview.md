---
title: "https://surrealdb.com/docs/running/overview"
url: "https://surrealdb.com/docs/running/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/running/overview

Source: https://surrealdb.com/docs/running/overview

You can start with SurrealDB in more than one way. This section orders them from **the least to the most** involved, so you can pick how much you want to set up.
##  Try it without installing[](https://surrealdb.com/docs/running/overview#try-it-without-installing)
  1. 1.
**[Surrealist Sandbox](https://surrealdb.com/docs/running/sandbox)** — Open Surrealist in the browser and use the built-in Sandbox. Nothing to install; data is not persistent, which is perfect for quick experiments and learning SurrealQL.
  2. 2.
**[SurrealDB Cloud](https://surrealdb.com/docs/running/cloud)** — Create a free [SurrealDB Cloud](https://surrealdb.com/docs/manage/cloud) instance (you will need an email to sign in). You keep persistence and a managed database without running a server on your own machine.
  3. 3.
**[Installation](https://surrealdb.com/docs/running/installation)** — Install the `surreal` binary and run SurrealDB locally or on your own infrastructure. This is the path when you want full control, offline work, or production self-hosting.

##  How you run the database on your own infrastructure[](https://surrealdb.com/docs/running/overview#how-you-run-the-database-on-your-own-infrastructure)
After you are running SurrealDB (locally or on servers you manage), you can choose storage and topology:
  * •
[Run a single-node, in-memory server](https://surrealdb.com/docs/running/in-memory) with optional persistence and versioning (SurrealMX)
  * •
[Run a single-node, on-disk server](https://surrealdb.com/docs/running/file-backed) (RocksDB or SurrealKV)
  * •
[Run a multi-node cluster](https://surrealdb.com/docs/running/multi-node)
  * •
[Run with Docker](https://surrealdb.com/docs/running/docker)
