---
title: "https://surrealdb.com/docs/learn/data-models/document/common-patterns"
url: "https://surrealdb.com/docs/learn/data-models/document/common-patterns"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/document/common-patterns

Source: https://surrealdb.com/docs/learn/data-models/document/common-patterns

When thinking in a document model database, you will often find that the concepts align closely with SurrealDB. The table below maps common terms.
##  Concept mapping[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#concept-mapping)  
| Document model  | SurrealDB  |  
| --- | --- |  
| database  | database  |  
| collection  | table  |  
| document  | record  |  
| field  | field  |  
| index  | index  |  
| Objectid  | record id  |  
| transactions  | transactions  |  
| reference and embedding  | record links, embedding and graph relations  |  
##  Benefits of using a document model database[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#benefits-of-using-a-document-model-database)
  1. 1.
**Flexibility** : You don’t need to define rigid schemas in advance. Changes to data structure are often just changes in the JSON object itself.
  2. 2.
**Natural data representation** : Since you’re working with JSON-like objects, document databases align well with modern programming languages that manipulate data as objects or dictionaries.
  3. 3.
**Simplicity of application code** : Because you can embed everything related to an entity in a single document, you often have fewer JOINs (or complex queries) and simpler code for retrieving complete objects.
  4. 4.
**Easier horizontal scaling** : Many document databases are built for horizontal partitioning (sharding), making them easier to scale for large workloads.

##  Using MongoDB syntax as a reference[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#using-mongodb-syntax-as-a-reference)
As a multi-model database, SurrealDB offers a lot of flexibility. SurrealQL often provides more than one way to achieve the same result, depending on developer preference. The mapping below focuses on syntax that most closely resembles the MongoDB query language (MQL).
For SurrealQL equivalents to MongoDB data types and how to import MongoDB data into SurrealDB, see the Surreal Sync migration tool:
  * •
[Surreal Sync for MongoDB](https://github.com/surrealdb/surreal-sync/blob/main/docs/mongodb.md)
  * •
[MongoDB data types support in Surreal Sync](https://github.com/surrealdb/surreal-sync/blob/main/docs/mongodb-data-types.md)

##  Syntax mapping[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#syntax-mapping)
###  Create[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#create)
As MongoDB is schemaless, only the SurrealQL schemaless approach is shown below. For a schemafull option, see the [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) page.
For more SurrealQL examples, see the [`CREATE`](https://surrealdb.com/docs/reference/query-language/statements/create) and [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) pages.  
| MQL  | SurrealQL  |  
| --- | --- |  
| db.createCollection("person")  | CREATE person  |  
| db.person.insertMany({ name: "John" }, { name: "Jane" })  | INSERT INTO person {name: "John"}, {name: "Jane"}  |  
| db.person.createIndex({ name: 1 })  | DEFINE INDEX idx_name ON TABLE person FIELDS name  |  
###  Read[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#read)
For more SurrealQL examples, see the [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select), [`LIVE SELECT`](https://surrealdb.com/docs/reference/query-language/statements/live-select) and [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) pages.  
| MQL  | SurrealQL  |  
| --- | --- |  
| db.person.find()  | SELECT * FROM person  |  
| db.person.find({}, { _id: 0, name: 1 })  | SELECT name FROM person  |  
| db.person.find({ name: “Jane” }, { _id: 0, name: 1 })  | SELECT name FROM person WHERE name = "Jane"  |  
| db.person.find({ name: “Jane” }, { _id: 0, name: 1 }).explain()  | SELECT name FROM person WHERE name = "Jane" EXPLAIN  |  
| db.person.aggregate({ $count: “personCount” })  | SELECT count() AS person_count FROM person GROUP ALL  |  
| db.person.aggregate({ $group: { _id: “$name” } })  | SELECT array::distinct(name) FROM person GROUP ALL  |  
| db.person.find().limit(10)  | SELECT * FROM person LIMIT 10  |  
| db.review.aggregate({ “$lookup”: { “from”: “person”, “localField”: “person”, “foreignField”: “_id”, “as”: “person_detail” } })  | SELECT *, person.name as reviewer FROM review  |  
###  Update[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#update)
For more SurrealQL examples, see the [`UPDATE`](https://surrealdb.com/docs/reference/query-language/statements/update) page.  
| MQL  | SurrealQL  |  
| --- | --- |  
| db.person.updateMany({ name: “Jane” }, { $set: { last_name: “Doe” } })  | UPDATE person SET last_name = "Doe" WHERE name = "Jane"  |  
| db.person.updateMany({ name: “Jane” }, { $unset: { last_name: 1 } })  | UPDATE person UNSET last_name WHERE name = "Jane"  |  
###  Delete[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#delete)
For more SurrealQL examples, see the [`DELETE`](https://surrealdb.com/docs/reference/query-language/statements/delete) and [`REMOVE`](https://surrealdb.com/docs/reference/query-language/statements/remove) pages.  
| MQL  | SurrealQL  |  
| --- | --- |  
| db.person.deleteMany({ name: “Jane” })  | DELETE person WHERE name = "Jane"  |  
| db.person.deleteMany({})  | DELETE person  |  
| db.person.drop()  | REMOVE TABLE person  |  
##  Resources[](https://surrealdb.com/docs/learn/data-models/document/common-patterns#resources)
  * •
[`CREATE` statement](https://surrealdb.com/docs/reference/query-language/statements/create)
  * •
[`SELECT` statement](https://surrealdb.com/docs/reference/query-language/statements/select)
  * •
[`UPDATE` statement](https://surrealdb.com/docs/reference/query-language/statements/update)
  * •
[`DELETE` statement](https://surrealdb.com/docs/reference/query-language/statements/delete)
  * •
[`RELATE` statement](https://surrealdb.com/docs/reference/query-language/statements/relate)
  * •
[SurrealQL documentation](https://surrealdb.com/docs/reference/query-language)
  * •
[SurrealDB University](https://surrealdb.com/learn)
