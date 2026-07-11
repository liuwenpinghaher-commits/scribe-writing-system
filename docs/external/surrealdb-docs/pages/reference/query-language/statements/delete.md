---
title: "https://surrealdb.com/docs/reference/query-language/statements/delete"
url: "https://surrealdb.com/docs/reference/query-language/statements/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/delete

Source: https://surrealdb.com/docs/reference/query-language/statements/delete

The `DELETE` statement can be used to delete records from the database.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/delete#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DELETE [ FROM | ONLY ] @targets
	[ WHERE @condition ]
	[ RETURN NONE | RETURN BEFORE | RETURN AFTER | RETURN DIFF | RETURN @statement_param, ... ]
	[ TIMEOUT @duration ]
	[ EXPLAIN [ FULL ]]
;
```

DELETEFROMONLY@targetsWHERE@conditionRETURNNONEBEFOREAFTERDIFF@statement_param, ...TIMEOUT@durationEXPLAINFULL;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/delete#example-usage)
###  Basic usage[](https://surrealdb.com/docs/reference/query-language/statements/delete#basic-usage)
The following queries shows basic usage of the DELETE statement, which is used to delete records from a table or a graph edge.
Deleting records can be done in multiple ways.
Specifying only the table name will delete all the records from a table. Note that a `DELETE` statement returns nothing (i.e. an empty array) by default.

```surql
-- Delete all records from a table
DELETE person;
```

Output

```surql
[]
```

A `DELETE` statement on a specific ID will delete a single record.

```surql
-- Delete a record with a specific numeric id
DELETE person:100;

-- Delete a record with a specific string id
DELETE person:tobie;
```

The `ONLY` keyword can be followed by a `RETURN BEFORE` clause to return just the object for the record in question before it was deleted.

```surql
CREATE ONLY person:tobie;
DELETE ONLY person:tobie RETURN BEFORE;
-- { id: person:tobie }
```

Note that as a `DELETE` statement returns an empty array by default, and the `ONLY` keyword assumes that a single object will be returned, it will return an error if `RETURN BEFORE` is not included.

```surql
DELETE ONLY person:tobie;
```

Output

```surql
'Expected a single result output when using the ONLY keyword'
```

###  Deleting records based on conditions[](https://surrealdb.com/docs/reference/query-language/statements/delete#deleting-records-based-on-conditions)
The delete statement supports conditional matching of records using a `WHERE` clause. If the expression in the `WHERE` clause evaluates to true, then the respective record will be deleted.

```surql
-- Update all records which match the condition
DELETE city WHERE name = 'London';
```

By default, the delete statement does not return any data, returning only an empty array if the statement succeeds completely. Specify a `RETURN` clause to change the value which is returned for each document that is deleted.

```surql
-- Don't return any result (the default)
DELETE user WHERE age < 18 RETURN NONE;

-- Return the changeset diff
DELETE user WHERE interests CONTAINS 'reading' RETURN DIFF;

-- Return the record before changes were applied
DELETE user WHERE interests CONTAINS 'reading' RETURN BEFORE;

-- Return the record after changes were applied
DELETE user WHERE interests CONTAINS 'reading' RETURN AFTER;
```

An important point to know when using a `WHERE` clause is that it performs a check on the [truthiness](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness) of a value, namely whether a value exists and is not a default value like 0, an empty string, empty array, and so on.
As such, the `DELETE` query below that only specifies `WHERE age` essentially evaluates to "WHERE age exists" and will delete every cat in the database with an `age`.

```surql
CREATE cat:one SET age = 4;
CREATE cat:two;
DELETE cat WHERE age;
SELECT * FROM cat;
```

Output

```surql
[
	{
		id: cat:two
	}
]
```

This pattern is particularly useful when using SurrealDB's [literal types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals). A literal type containing objects that contain a single top-level field can easily be matched on through the field name.

```surql
DEFINE FIELD error_info ON TABLE information TYPE
      { continue: { message: "Continue" } }
    | { retry_with_id: { error: string  } }
    | { deprecated: { message: string   } };

CREATE information SET error_info = { continue: { message: "Continue" }};
CREATE information SET error_info = { continue: { message: "Continue" }};
CREATE information SET error_info = { deprecated: { message: "We don't use this anymore" }};

DELETE information WHERE error_info.continue;
SELECT * FROM information;
```

Output

```surql
[
	{
		error_info: {
			deprecated: {
				message: "We don't use this anymore"
			}
		},
		id: info:o0pmm7zos98iv03xliav
	}
]
```

###  Using TIMEOUT duration records based on conditions[](https://surrealdb.com/docs/reference/query-language/statements/delete#using-timeout-duration-records-based-on-conditions)
When processing a large result set with many interconnected records, it is possible to use the `TIMEOUT` keywords to specify a timeout duration for the statement. If the statement continues beyond this duration, then the transaction will fail, no records will be deleted from the database, and the statement will return an error.

```surql
DELETE person
  WHERE ->knows->person->(knows
  WHERE influencer = false) TIMEOUT 5s;
```

##  Deleting graph edges[](https://surrealdb.com/docs/reference/query-language/statements/delete#deleting-graph-edges)
You can also delete graph edges between two records in the database by using the DELETE statement.
For example the graph edge below:

```surql
RELATE person:tobie->bought->product:iphone;

[
	{
		"id": bought:ctwsll49k37a7rmqz9rr,
		"in": person:tobie,
		"out": product:iphone
	}
]
```

Can be deleted by:

```surql
DELETE person:tobie->bought WHERE out=product:iphone;
```

##  Soft deletions[](https://surrealdb.com/docs/reference/query-language/statements/delete#soft-deletions)
While soft deletions do not exist natively in SurrealDB, they can be simulated by [defining an event](https://surrealdb.com/docs/reference/query-language/statements/define/event) that reacts whenever a deletion occurs.
The following example archives the data of a deleted record in another table. This can be combined with [fewer permissions for the new table](https://surrealdb.com/docs/reference/query-language/statements/define/table#defining-permissions) so that it can be accessed only by [system users](https://surrealdb.com/docs/reference/query-language/statements/define/user) and not [record users](https://surrealdb.com/docs/reference/query-language/statements/define/access/record).

```surql
DEFINE EVENT archive_person ON TABLE person WHEN $event = "DELETE" THEN {
    CREATE deleted_person SET
        data = $before,
        deleted_at = time::now()
};

CREATE |person:1..5|;
DELETE person:1;

-- Only two `person` records left
SELECT * FROM person;
-- But the data of `person:1` is still here
SELECT * FROM deleted_person;
```

Output

```surql
-------- Query --------

[
	{
		id: person:2
	},
	{
		id: person:3
	}
]

-------- Query --------

[
	{
		data: {
			id: person:1
		},
		deleted_at: d'2024-09-12T00:46:59.176Z',
		id: deleted_person:p3fpzhpxuu9jvjn8juyf
	}
]
```

##  The `EXPLAIN` clause[](https://surrealdb.com/docs/reference/query-language/statements/delete#the-explain-clause)
When `EXPLAIN` is used:
  1. 1.
The `DELETE` statement returns an explanation, essentially revealing the execution plan to provide transparency and understanding of the query performance.
  2. 2.
The records are not deleted.

`EXPLAIN` can be followed by `FULL` to see the number of executed rows.
