---
title: "https://surrealdb.com/docs/reference/query-language/statements/update"
url: "https://surrealdb.com/docs/reference/query-language/statements/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/update

Source: https://surrealdb.com/docs/reference/query-language/statements/update

The `UPDATE` statement can be used to update existing records in the database. If the record does not exist, the statement will succeed but no records will be updated.
Note
This statement can not be used to create graph relationships. For that, use the [`RELATE`](https://surrealdb.com/docs/reference/query-language/statements/relate) or [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) statement.
Note
`UPDATE` does not create records that do not exist. To update a record and create it if it does not exist, use the [`UPSERT`](https://surrealdb.com/docs/reference/query-language/statements/upsert) statement.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/update#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
UPDATE [ ONLY ] @targets
	[ CONTENT @value
	  | MERGE @value
	  | PATCH @value
	  | REPLACE @value
	  | [ SET @field = @value, ... | UNSET @field, ... ]
	]
	[ WHERE @condition ]
	[ RETURN NONE | RETURN BEFORE | RETURN AFTER | RETURN DIFF | RETURN @statement_param, ... | RETURN VALUE @statement_param ]
	[ TIMEOUT @duration ]
	[ EXPLAIN [ FULL ]]
;
```

UPDATEONLY@targetsCONTENT@valueMERGE@valuePATCH@valueREPLACE@valueSETUNSET@field (=|,) @value ...WHERE@conditionRETURNNONEBEFOREAFTERDIFF@statement_param, ...VALUE@statement_paramTIMEOUT@durationEXPLAINFULL;
Note
`@target` refers to either record output including an `id` field, or a [record ID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) on its own.
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/update#example-usage)
Let's look at some examples of how to use the `UPDATE` statement. First we'll create two `person` records with the [`CREATE`](https://surrealdb.com/docs/reference/query-language/statements/create) statement so that the examples will produce a meaningful output.

```surql
-- Create a Schemaless person table with a random id
CREATE person CONTENT {
    name: 'John',
    company: 'Surrealist',
    skills: ['JavaScript', 'Go' , 'SurrealQL']
};

-- Create another person with a specific id
CREATE person:tobie CONTENT {
    name: 'Tobie',
    company: 'SurrealDB',
    skills: ['JavaScript', 'Go' , 'SurrealQL']
};
```

Let's say we wanted to update the `person` table with a new field `enjoys` (an array), a new skill `breathing` to the existing `skills` field (another array), add a new numeric field called `dollars`, and a `last_name` field that relies on the existing `name` field to set its value.
To do this we would use the following query.

```surql
-- Update all records in a table
-- The `enjoys` field will also be an array.
-- The += operator alone is enough to infer the type
UPDATE person SET 
	dollars = 50,
	skills += 'breathing',
	enjoys += 'reading',
	full_name = name + ' Mc' + name + 'erson';
```

Output

```surql
[
	{
		company: 'Surrealist',
		dollars: 50,
		enjoys: [
			'reading'
		],
		full_name: 'John McJohnerson',
		id: person:j1qov2pxey3p8s6hqlev,
		name: 'John',
		skills: [
			'JavaScript',
			'Go',
			'SurrealQL',
			'breathing'
		]
	},
	{
		company: 'SurrealDB',
		dollars: 50,
		enjoys: [
			'reading'
		],
		full_name: 'Tobie McTobieerson',
		id: person:tobie,
		name: 'Tobie',
		skills: [
			'JavaScript',
			'Go',
			'SurrealQL',
			'breathing'
		]
	}
]
```

For more specific updates, you can specify a record ID to update a single record. The following query will update the record with the ID `person:tobie` to add "Rust" as a skill.

```surql
-- Update a record with a specific string id to add a new skill: 'Rust'
UPDATE person:tobie SET skills += 'Rust';
```

Output

```surql
[
	{
		company: 'SurrealDB',
		dollars: 50,
		enjoys: [
			'reading'
		],
		full_name: 'Tobie McTobieerson',
		id: person:tobie,
		name: 'Tobie',
		skills: [
			'JavaScript',
			'Go',
			'SurrealQL',
			'breathing',
			'Rust'
		]
	}
]
```

The `-=` operator can be used to remove an item from an array or reduce a numeric value by a certain value.

```surql
UPDATE person:tobie SET 
	skills -= 'Go', 
	dollars -= 1;
```

Output

```surql
[
	{
		company: 'SurrealDB',
		dollars: 49,
		enjoys: [
			'reading'
		],
		full_name: 'Tobie McTobieerson',
		id: person:tobie,
		name: 'Tobie',
		skills: [
			'JavaScript',
			'SurrealQL',
			'breathing',
			'Rust'
		]
	}
]
```

You can also remove a field from a record using the `UNSET` keyword or by setting the field to `NONE`.

```surql
-- Remove the company field by setting it to NONE or using the UNSET keyword
UPDATE person:tobie SET company = NONE;

UPDATE person:tobie UNSET company;
```

Output

```surql
[
	{
		dollars: 49,
		enjoys: [
			'reading'
		],
		full_name: 'Tobie McTobieerson',
		id: person:tobie,
		name: 'Tobie',
		skills: [
			'JavaScript',
			'SurrealQL',
			'breathing',
			'Rust'
		]
	}
]
```

##  Conditional update with `WHERE` clause[](https://surrealdb.com/docs/reference/query-language/statements/update#conditional-update-with-where-clause)
The `UPDATE` statement supports conditional matching of records using a `WHERE` clause. If the expression in the `WHERE` clause evaluates to `true`, then the respective record will be updated.

```surql
-- Update all records which match the condition that `company` is not equal to "SurrealDB"
UPDATE person SET skills += "System design"
  WHERE company != "SurrealDB";
```

Output

```surql
[
	{
		company: 'Surrealist',
		dollars: 50,
		enjoys: [
			'reading'
		],
		full_name: 'John McJohnerson',
		id: person:i5z3i64cpqpo8jtr6jww,
		name: 'John',
		skills: [
			'JavaScript',
			'Go',
			'SurrealQL',
			'breathing',
			'System design'
		]
	},
	{
		dollars: 49,
		enjoys: [
			'reading'
		],
		full_name: 'Tobie McTobieerson',
		id: person:tobie,
		name: 'Tobie',
		skills: [
			'JavaScript',
			'SurrealQL',
			'breathing',
			'Rust',
			'System design'
		]
	}
]
```

##  CONTENT clause[](https://surrealdb.com/docs/reference/query-language/statements/update#content-clause)
Instead of specifying record data using the `SET` clause, it is also possible to use the `CONTENT` keyword to specify the record data using a SurrealQL object.

```surql
-- Update all records with the same content
UPDATE person CONTENT {
	name: 'John',
	company: 'SurrealDB',
	skills: ['Rust', 'Go', 'JavaScript'],
};

-- Oops, now they are both named John.
-- Update a specific record with some content
UPDATE person:tobie CONTENT {
	name: 'Tobie',
	company: 'SurrealDB',
	skills: ['Rust', 'Go', 'JavaScript'],
};
```

A statement with a `CONTENT` clause bypasses `READONLY` fields instead of generating an error.

```surql
DEFINE FIELD created
  ON person TYPE datetime DEFAULT d'2024-01-01T00:00:00Z' READONLY;
CREATE person:gladys SET age = 90;
-- Does not try to modify `created` field, no error
UPDATE person:gladys CONTENT { age: 70 };
```

Output before 2.1.0Output after 2.1.0

```surql
-------- Query --------
[
	{
		age: 90,
		created: d'2024-01-01T00:00:00Z',
		id: person:gladys
	}
]

-------- Query --------
'Found changed value for field `created`,
  with record `person:gladys`,
  but field is readonly'
```

```surql
-------- Query --------
[
	{
		age: 90,
		created: d'2024-01-01T00:00:00Z',
		id: person:gladys
	}
]

-------- Query --------
[
	{
		age: 70,
		created: d'2024-01-01T00:00:00Z',
		id: person:gladys
	}
]
```

##  REPLACE clause[](https://surrealdb.com/docs/reference/query-language/statements/update#replace-clause)
Originally an alias for `CONTENT`, the `REPLACE` clause maintains the previous behaviour regarding `READONLY` fields. If the content following `REPLACE` does not match a record's `READONLY` fields, an error will be generated.

```surql
DEFINE FIELD created
  ON person TYPE datetime DEFAULT d'2024-01-01T00:00:00Z' READONLY;
CREATE person:gladys SET age = 90;
-- Attempts to change `created` field, error
UPDATE person:gladys REPLACE { age: 70 };
-- `created` equals current value, query works
UPDATE person:gladys REPLACE { age: 70,
  created: d'2024-01-01T00:00:00Z' };
```

Output

```surql
-------- Query --------
[
	{
		age: 90,
		created: d'2024-01-01T00:00:00Z',
		id: person:gladys
	}
]

-------- Query --------
'Found changed value for field `created`,
  with record `person:gladys`,
  but field is readonly'

-------- Query --------
[
	{
		age: 70,
		created: d'2024-01-01T00:00:00Z',
		id: person:gladys
	}
]
```

##  MERGE clause[](https://surrealdb.com/docs/reference/query-language/statements/update#merge-clause)
Instead of specifying the full record data using `CONTENT` or one field at a time using `SET`, it is also possible to merge-update only specific fields by using the `MERGE` keyword followed by on object containing the fields which are to be upserted.

```surql
-- Update certain fields on all records
UPDATE person MERGE {
	settings: {
		marketing: true,
	},
};

-- Update certain fields on a specific record
UPDATE person:tobie MERGE {
	settings: {
		marketing: true,
	},
};
```

Output

```surql
[
	{
		company: 'SurrealDB',
		id: person:i5z3i64cpqpo8jtr6jww,
		name: 'John',
		settings: {
			marketing: true
		},
		skills: [
			'Rust',
			'Go',
			'JavaScript'
		]
	},
	{
		company: 'SurrealDB',
		id: person:tobie,
		name: 'Tobie',
		settings: {
			marketing: true
		},
		skills: [
			'Rust',
			'Go',
			'JavaScript'
		]
	}
]
```

##  PATCH clause[](https://surrealdb.com/docs/reference/query-language/statements/update#patch-clause)
You can also specify changes to be applied to your query response, using the PATCH command which works similar to the [JSON Patch specification](https://jsonpatch.com/)

```surql
-- Patch the JSON response
UPDATE person:tobie PATCH [
	{
		"op": "add",
		"path": "Engineering",
		"value": "true"
	}
]
```

Output

```surql
[
	{
		Engineering: 'true',
		company: 'SurrealDB',
		id: person:tobie,
		name: 'Tobie',
		settings: {
			marketing: true
		},
		skills: [
			'Rust',
			'Go',
			'JavaScript'
		]
	}
]
```

##  Alter the `RETURN` value[](https://surrealdb.com/docs/reference/query-language/statements/update#alter-the-return-value)
By default, the update statement returns the record value once the changes have been made. To change the return value of each record, use the `RETURN` clause, specifying `NONE`, `BEFORE`, `AFTER`, `DIFF`, a comma-separated list of specific fields or ad-hoc fields, or `VALUE` for a single field without its key name.

```surql
-- Don't return any result
UPDATE person SET skills += 'reading' RETURN NONE;

-- Return the changeset diff
UPDATE person SET skills += 'reading' RETURN DIFF;

-- Return the record before changes were applied
UPDATE person SET skills += 'reading' RETURN BEFORE;

-- Return the record after changes were applied (the default)
UPDATE person SET skills += 'reading' RETURN AFTER;

-- Return the value of the 'skills' field without the field name
UPDATE person SET skills += 'reading' RETURN VALUE skills;

-- Return a specific field only from the updated records
UPDATE person:tobie SET skills = ['skiing',
  'music'] RETURN name,
  interests;
```

##  Using a timeout[](https://surrealdb.com/docs/reference/query-language/statements/update#using-a-timeout)
When processing a large result set with many interconnected records, it is possible to use the `TIMEOUT` keyword to specify a timeout duration for the statement. If the statement continues beyond this duration, then the transaction will fail, no records will be updated in the database, and the statement will return an error.

```surql
UPDATE person 
	SET important = true 
	WHERE ->knows->person->(knows WHERE influencer = true) 
	TIMEOUT 5s;
```

##  UPDATE inside database exports[](https://surrealdb.com/docs/reference/query-language/statements/update#update-inside-database-exports)
As `UPDATE` before version 2.0.0 used to create a specified record ID if it did not exist, it was used in the `.surql` files generated by the [`surreal export`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export) command to export existing records in a database. As of version 2.0.0, the [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) statement is used instead.
##  The `EXPLAIN` clause[](https://surrealdb.com/docs/reference/query-language/statements/update#the-explain-clause)
When `EXPLAIN` is used:
  1. 1.
The `UPDATE` statement returns an explanation, essentially revealing the execution plan to provide transparency and understanding of the query performance.
  2. 2.
The records are not updated.

`EXPLAIN` can be followed by `FULL` to see the number of executed rows.
