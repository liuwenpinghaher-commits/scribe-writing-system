---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans

A boolean (`bool`) is a primitive type that can be either `true` or `false`.

```surql
CREATE person SET newsletter = false, interested = true;
```

Many SurrealDB operators and functions return booleans.

```surql
SELECT
    name,
    id,
    name = "Billy" AS name_is_billy,
    name.len() > 20 AS name_is_long
FROM
    CREATE person SET name = "Billy";
```

Response

```surql
[
	{
		id: person:7j4t4higwb141v1v2xum,
		name: 'Billy',
		name_is_billy: true,
		name_is_long: false
	}
]
```

Boolean values can be written in anycase.

```surql
CREATE person SET 
    newsletter = FALSE,
    interested = True,
    very_interested = trUE;
```

##  Booleans in `WHERE` clauses[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans#booleans-in-where-clauses)
When performing a query on the database, accessing a record's ID directly or using a [record range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges) allows performance to be significantly sped up by avoiding the table scan which is used when a `WHERE` clause is included.
However, if a `WHERE` clause is unavoidable, performance can still be improved by simplifying the portion after the clause as much as possible. As a boolean is the simplest possible datatype, having a boolean field that can be used in a `WHERE` clause can significantly improve performance compared to a more complex operation.

```surql
DEFINE FIELD data_length ON person VALUE random_data.len();
DEFINE FIELD is_short ON person VALUE random_data.len() < 10;

-- Fill up the database a bit with 10,000 records
CREATE |person:10000|
  SET random_data = rand::string(1000) RETURN NONE;
-- Add one outlier with short random_data
CREATE person:one SET random_data = "HI!" RETURN NONE;

-- Function call + compare operation: slowest
SELECT * FROM person WHERE random_data.len() < 10;
-- Compare operation: much faster
SELECT * FROM person WHERE data_length < 10;
-- Boolean check: even faster
SELECT * FROM person WHERE is_short;
-- Direct record access: almost instantaneous
SELECT * FROM person:one;
```

##  Boolean values vs. truthy values[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans#boolean-values-vs-truthy-values)
All SurrealQL values are either truthy or not. While seemingly similar to booleans in that `true` is a truthy value and `false` is not, the truthiness of a value extends to all value types and is based on the existence of a concrete value as opposed to empty values, `NONE`, `NULL`, and so on. For more information and examples, see [this page](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
