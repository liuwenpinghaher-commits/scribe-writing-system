---
title: "https://surrealdb.com/docs/learn/data-models/document/overview"
url: "https://surrealdb.com/docs/learn/data-models/document/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/document/overview

Source: https://surrealdb.com/docs/learn/data-models/document/overview

One of the most popular database models is that of a document database. It provides a flexible way to store data, allowing for nested structures and relationships to be stored within a single document.
In a document database, data is stored in the form of documents (which usually resemble JSON objects) rather than in rows and columns.
This model offers a level of simplicity and flexibility that can be especially appealing when your data does not naturally fit into a strict tabular format or when the structure of your data frequently changes.
Over the last decade, we have seen a surge of NoSQL databases such as [MongoDB](https://www.mongodb.com/), [CouchDB](https://couchdb.apache.org/), and [DynamoDB](https://aws.amazon.com/dynamodb/), all of which are in the broad category of document stores (although with varying specific features).
But how do you “think” in a document model database? Thinking in a document model means orienting your data design around the entities as you naturally represent them in your applications, rather than forcing your data into normalized or heavily structured relational schemas.
##  Core concepts of document-oriented modelling[](https://surrealdb.com/docs/learn/data-models/document/overview#core-concepts-of-document-oriented-modelling)
In a document-oriented system you typically work with:
  * •
**Self-describing records** : Data is grouped into records that carry their own structure (fields, nested objects, arrays), often similar to JSON in application code.
  * •
**Embedding vs linking** : Related data can live inside the same document (embedding) or be referenced with [record links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links) or graph-style relations when you need shared entities or strict edges.
  * •
**Flexible schema** : Tables can mix different shapes when you choose a schemaless workflow, or you can tighten definitions with [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) and field types when you need validation and tooling support.

##  Where to go next[](https://surrealdb.com/docs/learn/data-models/document/overview#where-to-go-next)
The guides in this section break these ideas down in more detail:
  * •
[Nested objects and arrays](https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays): worked examples with nested structures, record IDs, and linking documents.
  * •
[Schema modes](https://surrealdb.com/docs/learn/data-models/document/schema-modes): creating and retrieving documents, and how schemaless usage compares to defining a schema.
  * •
[Common patterns](https://surrealdb.com/docs/learn/data-models/document/common-patterns): concept mapping to other document stores, benefits, MongoDB-style SurrealQL examples, and further resources.

For statement-level reference and CRUD details, see the [`CREATE`](https://surrealdb.com/docs/reference/query-language/statements/create), [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select), [`UPDATE`](https://surrealdb.com/docs/reference/query-language/statements/update), and [`DELETE`](https://surrealdb.com/docs/reference/query-language/statements/delete) statements, and the [SurrealQL documentation](https://surrealdb.com/docs/reference/query-language).
