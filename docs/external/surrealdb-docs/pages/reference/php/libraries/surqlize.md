---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize

[Surqlize](https://github.com/surrealdb/surqlize.php) is an object-relational mapper for SurrealDB in PHP. You describe tables as PHP classes with attributes, then compose SurrealQL through a typed query builder instead of writing strings. It is built on top of [version 2 of the SDK](https://surrealdb.com/docs/reference/php/v2) and uses the SDK to execute queries.
The core idea is small: describe your SurrealDB tables with models and attributes, then build queries through typed PHP APIs that your IDE and static analyser understand. Surqlize compiles each query to a deterministic SurrealQL string for tests, and runs it through the SDK with parameter-bound values at runtime.
Important
Surqlize is published as `0.0.1-alpha.2` and is in early development. It requires PHP `8.4` and depends on the alpha [v2 SDK](https://surrealdb.com/docs/reference/php/v2), so its API may change.
##  Getting started[](https://surrealdb.com/docs/reference/php/libraries/surqlize#getting-started)
[Installation Install Surqlize with Composer and the alpha SDK it depends on.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/installation)[Models Describe tables as PHP classes with attribute-driven fields.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/models)[Connections Register an SDK executor and inject one per query when needed.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections)
##  Building queries[](https://surrealdb.com/docs/reference/php/libraries/surqlize#building-queries)
[Querying Typed select, where, ordering, projections, and the execution methods.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying)[Mutations Create, update, upsert, and delete with model helpers and builders.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/mutations)[Edges and graph Edge models, graph traversal, and RELATE.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/edges-and-graph)[Search, vector, and geometry Full-text search, vector KNN, and geometry helpers.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/search-vector-geometry)
##  Schema and tooling[](https://surrealdb.com/docs/reference/php/libraries/surqlize#schema-and-tooling)
[Schema Define tables with a schema contract or the fluent DSL.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema)[Code generation and CLI Generate typed field adapters and run the CLI commands.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/code-generation-and-cli)[Transactions Batch ORM queries into a single transaction with rollback.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/transactions)
##  Sources[](https://surrealdb.com/docs/reference/php/libraries/surqlize#sources)
  * •
[GitHub repository](https://github.com/surrealdb/surqlize.php)
  * •
[PHP SDK v2](https://surrealdb.com/docs/reference/php/v2) that Surqlize builds on
  * •
[Laravel integration](https://surrealdb.com/docs/reference/php/frameworks/laravel) for using Surqlize in Laravel
