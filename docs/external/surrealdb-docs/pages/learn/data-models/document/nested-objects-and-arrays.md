---
title: "https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays"
url: "https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays

Source: https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays

Documents in SurrealDB behave like structured objects you might already use in application code: fields can hold primitives, nested objects, and arrays of values.
##  Example: a user with nested addresses[](https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays#example-a-user-with-nested-addresses)
The example below creates a `users` record with an `addresses` array of objects.
By clicking the **Run query** button, you will see a result similar to:

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
		id: 'users:a2ndbh1hsquvkvthws09',
		name: 'Alice Smith'
	}
]
```

You may notice that the `id` field has a `users:` prefix. This is because SurrealDB uses an [id](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) to uniquely identify each record, and the combination of the table name and the record id is used as the [record link](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links).
##  Embedding and linking[](https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays#embedding-and-linking)
Document model databases are designed to store data in a flexible, nested structure. **Data organisation** often means self-describing documents in JSON or a similar format. Relationships can be represented **inside** the document (embedding) or via **references** using record links to other documents.
For example, if you wanted to associate a `person` with an `article` they wrote, you could assign the person's ID to the `author` field of the article document. This binds the `person` and `article` together, allowing you to query the `article` by the `person`'s ID.
##  Retrieving documents[](https://surrealdb.com/docs/learn/data-models/document/nested-objects-and-arrays#retrieving-documents)
To read documents back, use a normal `SELECT`. For example, to return every field from the `users` table:

```surql
SELECT * FROM users;
```

SurrealDB automatically generates a unique [`id`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) for each document unless you supply your own identifiers.
For more on schema options and CRUD patterns, see [Schema modes](https://surrealdb.com/docs/learn/data-models/document/schema-modes) and [Common patterns](https://surrealdb.com/docs/learn/data-models/document/common-patterns).
