---
title: "https://surrealdb.com/docs/reference/query-language/clauses/omit"
url: "https://surrealdb.com/docs/reference/query-language/clauses/omit"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/clauses/omit

Source: https://surrealdb.com/docs/reference/query-language/clauses/omit

The `OMIT` clause is used to omit fields from the result set which can be particularly useful when querying large datasets.
##  Syntax[](https://surrealdb.com/docs/reference/query-language/clauses/omit#syntax)
Clause Syntax

```syntax
OMIT @fields FROM @table
```

##  Examples[](https://surrealdb.com/docs/reference/query-language/clauses/omit#examples)

```surql
CREATE person:tobie SET
	name = 'Tobie',
	password = '123456',
	opts.security = 'secure',
	opts.enabled = true;
CREATE person:jaime SET
	name = 'Jaime',
	password = 'asdfgh',
	opts.security = 'secure',
	opts.enabled = false;

SELECT * FROM person;
-- Omit the password field and security field in the options object
SELECT * OMIT password, opts.security FROM person;

-- Using destructuring syntax
SELECT * OMIT password, opts.{ security, enabled } FROM person;
```

```surql
-------- Query 3 (132.138µs) --------

[
	{
		id: person:jaime,
		name: 'Jaime',
		opts: {
			enabled: false,
			security: 'secure'
		},
		password: 'asdfgh'
	},
	{
		id: person:tobie,
		name: 'Tobie',
		opts: {
			enabled: true,
			security: 'secure'
		},
		password: '123456'
	}
]

-------- Query 4 (61.876µs) --------

[
	{
		id: person:jaime,
		name: 'Jaime',
		opts: {
			enabled: false
		}
	},
	{
		id: person:tobie,
		name: 'Tobie',
		opts: {
			enabled: true
		}
	}
]

-------- Query 5 (52.152µs) --------

[
	{
		id: person:jaime,
		name: 'Jaime',
		opts: {}
	},
	{
		id: person:tobie,
		name: 'Tobie',
		opts: {}
	}
]
```
