---
title: "https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql"
url: "https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql

Source: https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql

[SurrealQL](https://surrealdb.com/docs/reference/query-language) is the query language for SurrealDB. How they reach the database depends on your tool or integration. The sections below describe each path in more detail.
##  SurrealQL execution paths[](https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql#surrealql-execution-paths)
The following four approaches are the most commonly used ways to execute SurrealQL queries directly or indirectly via SDKs in one of many programming languages.  
| Approach  | Typical use  |  
| --- | --- |  
| [Surrealist](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist)  | Interactive editing, Sandbox, and visual results in the browser.  |  
| [CLI](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli)  | Local development, scripts, and [`surreal sql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql) against a running server.  |  
| [HTTP](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http)  | Services and integrations that call the [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) endpoint.  |  
| [SDKs](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks)  | Application code using the official clients (WebSocket or HTTP under the hood, depending on SDK and configuration).  |  
In Surrealist, the built-in Sandbox does not persist data. To keep experimental work, use **Deploy to Cloud** in the app to create a free SurrealDB Cloud instance.
For a single entry point into these guides, see **[Executing queries](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries)**.
Interactive clients (including the SDKs) usually speak to the database over **WebSocket** or **HTTP**. The [RPC protocol](https://surrealdb.com/docs/reference/rest-api/rpc-protocol) describes how queries and responses are framed on the wire.
Language syntax, statements, and functions are documented in the **[SurrealQL reference](https://surrealdb.com/docs/reference/query-language)**.
##  GraphQL[](https://surrealdb.com/docs/learn/querying/surrealql/writing-surrealql#graphql)
[GraphQL](https://surrealdb.com/docs/learn/querying/graphql/overview) is a separate query interface on top of SurrealDB: you describe fields and shapes in GraphQL, not in SurrealQL. You can use it from [Surrealist](https://surrealdb.com/docs/learn/querying/graphql/via-surrealist), over [HTTP](https://surrealdb.com/docs/learn/querying/graphql/via-http), or from tools such as Postman or Bruno.
