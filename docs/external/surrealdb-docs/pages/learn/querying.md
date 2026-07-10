---
title: "https://surrealdb.com/docs/learn/querying"
url: "https://surrealdb.com/docs/learn/querying"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying

Source: https://surrealdb.com/docs/learn/querying

In this section we will learn about the multitude of ways to write and send queries to your SurrealDB database. The main focus is on the SurrealQL query language, which strongly resembles traditional SQL but differs in a number of ways to accommodate patterns such as graph traversal, record links, and other features unique to SurrealDB.
Queries can also be written without using direct SurrealQL through methods such as SDKs in your preferred programming language, [GraphQL](https://surrealdb.com/docs/learn/querying/graphql/overview), or [GQL](https://surrealdb.com/docs/learn/querying/gql/overview) (ISO graph pattern queries on the `/gql` endpoint). Built-in [`eval::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) functions can also run SurrealQL or GQL query strings from inside a transaction when explicitly enabled.
This section also includes tips and tricks to get the most out of your queries. For even more information after reading this section, feel free to look into the [reference](https://surrealdb.com/docs/reference/query-language) section of the documentation which has separate pages for each statement, data type, clause and more for the entire SurrealQL query language.
