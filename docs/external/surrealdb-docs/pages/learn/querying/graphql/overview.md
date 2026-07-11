---
title: "https://surrealdb.com/docs/learn/querying/graphql/overview"
url: "https://surrealdb.com/docs/learn/querying/graphql/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/graphql/overview

Source: https://surrealdb.com/docs/learn/querying/graphql/overview

SurrealDB supports [GraphQL](https://graphql.org/) through the [`/graphql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql) endpoint, which can be accessed via [Surrealist](https://app.surrealdb.com/), GraphiQL, Postman, or any other GraphQL client.
Note
**GraphQL is not GQL.** [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview) (`MATCH … RETURN …`) is a separate language on [`POST /gql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#gql). Do not abbreviate GraphQL to `gql` — in SurrealDB, `gql` always means ISO GQL.
##  Key features[](https://surrealdb.com/docs/learn/querying/graphql/overview#key-features)
GraphQL offers a number of key features that make it a powerful tool for working with SurrealDB:
  * •
**Declarative Data Fetching** : GraphQL allows you to request exactly the data you need, no more and no less. This reduces over-fetching and under-fetching of data, leading to more efficient queries.
  * •
**Strongly Typed Schema** : GraphQL uses a strong type system to define the capabilities of an API. This schema serves as a contract between the client and the server, ensuring that queries are valid before execution.
  * •
**Hierarchical Structure** : GraphQL queries mirror the shape of the data they return, making it intuitive to work with nested data structures.
  * •
**Single Endpoint** : When using GraphQL over HTTP, it typically uses a single endpoint, simplifying API architecture and reducing network overhead.
  * •
**Ecosystem and Tools** : GraphQL has a rich ecosystem of tools for development, testing, and monitoring, including GraphiQL for query exploration and Apollo Client for state management.

##  Getting started[](https://surrealdb.com/docs/learn/querying/graphql/overview#getting-started)
Enabling GraphQL queries for SurrealDB can be done through a single statement: [`DEFINE CONFIG GRAPHQL`](https://surrealdb.com/docs/reference/query-language/statements/define/config).
The simplest clause to follow this with is `AUTO`, which will automatically include all tables in the GraphQL schema.

```surql
DEFINE CONFIG GRAPHQL AUTO;
```

A query for `(INFO FOR DB).configs` will show that the above statement ends up having the clauses `TABLES AUTO FUNCTIONS AUTO`.

```surql
{ GraphQL: 'GRAPHQL TABLES AUTO FUNCTIONS AUTO' }
```

For more fine tuning of the configuration, the `TABLES` and `FUNCTIONS` clauses can be followed by [other clauses](https://surrealdb.com/docs/reference/query-language/statements/define/config#tables-configuration).
##  Schema naming 
Available since: v3.1.0
[](https://surrealdb.com/docs/learn/querying/graphql/overview#schema-naming-since-vv310-)
From SurrealDB 3.1.0, the auto-generated GraphQL schema follows a single **Apollo-style** naming convention (there is no `NAMING` switch):  
| Operation  | Example for table `person`  |  
| --- | --- |  
| Fetch one record  | `person(id: ID!)`  |  
| List records  |  `people(filter, where, order, limit, start, version)` — pluralised table name  |  
| Aggregate  | `people_aggregate(filter, groupBy, …)`  |  
| Create / update / delete  |  `createPerson`, `updatePerson`, `deletePerson` (bulk: `createPeople`, …)  |  
Field names on types mirror SurrealQL unless you set [`GRAPHQL_ALIAS`](https://surrealdb.com/docs/reference/query-language/statements/define/field) or [`GRAPHQL_DEPRECATED`](https://surrealdb.com/docs/reference/query-language/statements/define/field) on [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) / [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) / [`DEFINE FUNCTION`](https://surrealdb.com/docs/reference/query-language/statements/define/function). List queries also support Relay-style **`peopleConnection`**cursor pagination alongside offset`limit` / `start`.
If you upgrade from 3.0.x, regenerate client stubs and saved queries — names such as `_get_person` and `createManyPerson` are no longer generated for typical tables.
##  Next steps[](https://surrealdb.com/docs/learn/querying/graphql/overview#next-steps)
The next page introduces some common GraphQL patterns and their SurrealQL equivalents or near equivalents.
This is followed by the following pages that detail the various tools by which GraphQL queries can be run on a SurrealDB database:
  * •
Using the [`/graphql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql) endpoint [via HTTP (cURL)](https://surrealdb.com/docs/learn/querying/graphql/via-http)
  * •
Using the [`/graphql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql) endpoint [via Bruno](https://surrealdb.com/docs/learn/querying/graphql/via-bruno)
  * •
Using [Surrealist](https://app.surrealdb.com/), SurrealDB's interactive environment for experimenting with GraphQL queries and seeing results immediately in the UI.

Other tools such as Postman and many others can be used against the `/graphql` endpoint.
