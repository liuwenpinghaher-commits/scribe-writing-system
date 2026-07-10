---
title: "https://surrealdb.com/docs/learn/data-models/document/schema-modes"
url: "https://surrealdb.com/docs/learn/data-models/document/schema-modes"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/document/schema-modes

Source: https://surrealdb.com/docs/learn/data-models/document/schema-modes

SurrealDB supports both **schemaless** workflows (insert records of varying shape into the same table) and **schemafull** definitions when you want validation and clearer contracts. This page focuses on the schemaless style that feels closest to typical document databases.
##  Schema flexibility[](https://surrealdb.com/docs/learn/data-models/document/schema-modes#schema-flexibility)
Document model databases are often chosen because:
  1. 1.
**Data organisation** : Data is contained in self-describing documents, typically in JSON or a similar format. Relationships can be done within the document itself (embedding) or via [record links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links) to other documents.
  2. 2.
**Schema flexibility** : Schemas are often flexible, allowing for documents of varying shapes in the same collection (or table-like structure). When you need stricter rules, you can use [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) and [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field).

##  Creating and managing documents[](https://surrealdb.com/docs/learn/data-models/document/schema-modes#creating-and-managing-documents)
In SurrealDB, you can create a database and then store collections of documents (often referred to as “tables”) without strict schema definitions. This is conceptually similar to creating a table in a relational database, but you do not need to define all columns upfront. Instead, you can insert JSON-like objects directly.
###  Adding a document[](https://surrealdb.com/docs/learn/data-models/document/schema-modes#adding-a-document)

```surql
CREATE users CONTENT {
    name: "Alice Smith",
    email: "alice@example.com",
    age: 29,
    addresses: [
        {
            type: "home",
            address_line: "123 Maple St",
            city: "Springfield",
            country: "USA"
        },
        {
            type: "work",
            address_line: "456 Oak Ave",
            city: "Metropolis",
            country: "USA"
        }
    ]
};
```

Here, a user document includes nested objects (`addresses`) in the same record. You can add nested objects or properties without modifying a central schema first.
###  Retrieving documents[](https://surrealdb.com/docs/learn/data-models/document/schema-modes#retrieving-documents)

```surql
SELECT * FROM users;
```

The query returns all documents in the `users` table, similar to a traditional SQL `SELECT`:

```surql
[
	{
		addresses: [
			{
				address_line: '123 Maple St',
				city: 'Springfield',
				country: 'USA',
				type: 'home'
			},
			{
				address_line: '456 Oak Ave',
				city: 'Metropolis',
				country: 'USA',
				type: 'work'
			}
		],
		age: 29,
		email: 'alice@example.com',
		id: 'users:xyz123',
		name: 'Alice Smith'
	}
]
```

SurrealDB automatically generates a unique [`id`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) for the document. You can also specify your own custom IDs if you prefer more human-readable or domain-specific identifiers.
##  Next steps[](https://surrealdb.com/docs/learn/data-models/document/schema-modes#next-steps)
For concept mapping to other document stores and MongoDB-style SurrealQL examples, see [Common patterns](https://surrealdb.com/docs/learn/data-models/document/common-patterns).
