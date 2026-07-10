---
title: "https://surrealdb.com/docs/reference/query-language/statements/show"
url: "https://surrealdb.com/docs/reference/query-language/statements/show"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/show

Source: https://surrealdb.com/docs/reference/query-language/statements/show

Changefeeds allow you to retrieve and sync changes from SurrealDB to external systems and platforms using the `SHOW` statement.
For updates to existing records, the shape of each mutation depends on how the changefeed was defined on the table. When you use `INCLUDE ORIGINAL` with `CHANGEFEED`, stored differences are **reverse diffs** : they describe the changes required to go from the record’s state after the write **back** to the state immediately before it.
For updates to existing records, the shape of each mutation depends on how the changefeed was defined on the table. When you use [`INCLUDE ORIGINAL`](https://surrealdb.com/docs/reference/query-language/statements/define/table#example-usage) with `CHANGEFEED`, stored differences are **reverse diffs** : they describe the changes required to go from the record’s state after the write **back** to the state immediately before it. See the [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table#example-usage) examples for sample responses with and without `INCLUDE ORIGINAL`.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/show#requirements)
  * •
You must first [`DEFINE`](https://surrealdb.com/docs/reference/query-language/statements/define/table#example-usage) a changefeed on either a table or a database.

###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/show#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
SHOW CHANGES FOR TABLE @tablename
	SINCE @timestamp | @versionstamp
	[ LIMIT @number ]
```

SHOWCHANGESFORTABLE@tablenameSINCE@timestamp@versionstampLIMIT@number
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/show#example-usage)
###  Basic usage[](https://surrealdb.com/docs/reference/query-language/statements/show#basic-usage)
The following expression shows usage of the SHOW statement.

```surql
-- Define the changefeed and its duration
DEFINE TABLE reading CHANGEFEED 3d;

-- Create some records in the reading table
CREATE reading SET story += ["Once upon a time"];
UPDATE reading SET story += ["there was a database"];

-- Replay changes to the reading table since a date
SHOW CHANGES FOR TABLE reading SINCE d"2023-09-07T01:23:52Z" LIMIT 10;
-- Replay changes to the reading table since a versionstamp
SHOW CHANGES FOR TABLE reading SINCE 1 LIMIT 10;
```

Assuming the datetime above matches with the one when the changefeed was established, the response for both queries will be as follows.
Response

```surql
[
	{
		changes: [
			{
				define_table: {
					changefeed: {
						expiry: 3d,
						original: false
					},
					drop: false,
					id: 0,
					kind: {
						kind: 'ANY'
					},
					name: 'reading',
					permissions: {
						create: false,
						delete: false,
						select: false,
						update: false
					},
					schemafull: false
				}
			}
		],
		versionstamp: 116395873313095680
	},
	{
		changes: [
			{
				update: {
					id: reading:kpqxnt8h4me84zed9fgf,
					story: [
						'Once upon a time'
					]
				}
			}
		],
		versionstamp: 116395873313161216
	},
	{
		changes: [
			{
				update: {
					id: reading:kpqxnt8h4me84zed9fgf,
					story: [
						'Once upon a time',
						'there was a database'
					]
				}
			}
		],
		versionstamp: 116395873313161217
	}
]
```

Response if INCLUDE ORIGINAL set on changefeed

```surql
[
	{
		changes: [
			{
				define_table: {
					changefeed: {
						expiry: 3d,
						original: true
					},
					drop: false,
					id: 0,
					kind: {
						kind: 'ANY'
					},
					name: 'reading',
					permissions: {
						create: false,
						delete: false,
						select: false,
						update: false
					},
					schemafull: false
				}
			}
		],
		versionstamp: 116395871166398464
	},
	{
		changes: [
			{
				update: {
					id: reading:q0lovlass9zgq19l1kfb,
					story: [
						'Once upon a time, '
					]
				}
			}
		],
		versionstamp: 116395871166464000
	},
	{
		changes: [
			{
				current: {
					id: reading:q0lovlass9zgq19l1kfb,
					story: [
						'Once upon a time, ',
						'there was a database'
					]
				},
				update: [
					{
						op: 'remove',
						path: '/story/1'
					}
				]
			}
		],
		versionstamp: 116395871166529536
	}
]
```

###  Deletes with `INCLUDE ORIGINAL`[](https://surrealdb.com/docs/reference/query-language/statements/show#deletes-with-include-original)
Available since: v3.2.0
When a table changefeed is defined with `INCLUDE ORIGINAL`, delete events surface the record's pre-image under `delete.original`. Plain changefeeds (without `INCLUDE ORIGINAL`) still emit `{ delete: { id } }` only.

```surql
DEFINE TABLE original_tb CHANGEFEED 1h INCLUDE ORIGINAL;
CREATE original_tb:1 SET name = 'Tobie';
DELETE original_tb:1;
SHOW CHANGES FOR TABLE original_tb SINCE 0;
```

Response

```surql
[
	{
		changes: [
			{
				delete: {
					id: original_tb:1,
					original: {
						id: original_tb:1,
						name: 'Tobie'
					}
				}
			}
		],
		versionstamp: /* … */
	}
]
```

Note the following when working with the versionstamps of a changefeed:
  * •
Changefeeds defined on tables are implemented via a single `CHANGEFEED` on the database level. As such, `SHOW CHANGES FOR TABLE sometable` will only show versionstamps in sequential order if `sometable` is the database's only table.
  * •
The `versionstamp` output above is due to an extra two bytes needed for more detailed ordering needed in the FoundationDB distributed [SurrealDB backend](https://surrealdb.com/docs/architecture). To turn these versionstamps into a normal sequence of numbers, a right shift of sixteen bits (`>> 16`) can be used.
  * •
A `SINCE <number` greater than the current sequential number will return an empty array.
  * •
`SINCE ` needs to be a datetime after which the `CHANGEFEED` was defined.

Versionstamps carry the following two guarantees:
  * •
Versionstamps monotonically increase.
  * •
Versionstamp format is universal across various backends.
