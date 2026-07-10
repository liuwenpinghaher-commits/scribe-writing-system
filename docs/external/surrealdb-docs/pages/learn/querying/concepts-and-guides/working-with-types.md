---
title: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types"
url: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types

Source: https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types

This page contains a number of examples and tips for working with various data types that go beyond the general API documentation for each type.
For general information on these data types, see the [data types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/index) page in the query language documentation.
##  Arrays[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types#arrays)
Working with arrays is one of the most important skills when working with SurrealDB, as [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select) statements return an array of values by default unless the `ONLY` keyword is used on an array that contains a single item.

```surql
-- Even this returns an array
SELECT * FROM 9;
-- Use the `ONLY` clause to return a single item
SELECT * FROM ONLY 9;
-- Error: array has more than one item
SELECT * FROM ONLY [1,9];
```

Output

```surql
-------- Query 1  --------

[
	9
]

-------- Query 2 --------

9

-------- Query 3 --------

'Expected a single result output when using the ONLY keyword'
```

This also means that a `SELECT` statement used to fetch records from a datastore can be used unchanged for any other array of values.

```surql
LET $ten_items = [8,5,3,2,6,4,76,9,8,5];
SELECT * FROM $ten_items START 5 LIMIT 5;
```

Output

```surql
[
	4,
	76,
	9,
	8,
	5
]
```

Other syntax can be used to achieve the same result, such as pulling from a range of indexes.

```surql
LET $ten_items = [8,5,3,2,6,4,76,9,8,5];
$ten_items[5..10];
```

##  Type safety and type conversion[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types#type-safety-and-type-conversion)
###  Using typed `LET` statements[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types#using-typed-let-statements)
Using typed `LET` statements is a good practice when prototyping code or when getting used to SurrealQL for the first time. Take the following example that attempts to count the number of `true` values in a field by filtering out values that are not `true`, without noticing that the field actually contains strings instead of booleans. The query output ends up being 0, rather than the expected 2.

```surql
CREATE some:record SET vals = ["true", "false", "true"];
some:record.vals.filter(|$val| $val = true).len();
```

Output

```surql
0
```

Breaking this into multiple typed `LET` statements shows the error right away.

```surql
LET $vals: array<bool> = some:record.vals;
LET $len: number = $vals.filter(|$val| $val = true).len();
$len;
```

Output

```surql
-------- Query 1 --------

"Tried to set `$vals`, but couldn't coerce value: Expected `bool`
but found `'true'` when coercing an element of `array<bool>`"

-------- Query 2 --------

'There was a problem running the filter() function.
no such method found for the none type'

-------- Query 3 --------

NONE
```

With the location of the error in clear sight, a fix is that much easier to implement.

```surql
LET $vals: array<bool> = some:record.vals.map(|$val| <bool>$val);
LET $len: number = $vals.filter(|$val| $val = true).len();
$len;
```

Output

```surql
2
```

###  Mapping items in an array[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/working-with-types#mapping-items-in-an-array)
The [`array::map()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymap) function provides access to each item in an array, allowing an operation to be performed on it before being passed on. Other similar functions can also be used, such as [`array::filter()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfilter) which passes on an array that only contains the items that return `true` to an expression of your choice.
The following example shows how to chain these functions to validate and modify data in a single statement. The example below removes any items with a `NONE`, checks to see if the location data is a valid geometric point, and then returns the remaining items as objects with a different structure.

```surql
[
	NONE,
	{
		at: (98, 65.7),
		name: "Some city"
	},
	{
		at: (-190.7, 0),
		name: NONE
	},
    {
        name: "Other city",
        at: (0.0, 0.1)
    },
	{
        name: "Nonexistent city",
        at: (200.0, 66.5)
    }
]
    .filter(|$v| $v != NONE AND $v.name != NONE)
    .filter(|$v| $v.at.is_valid())
    .map(|$v, $i| {
        item: $i,
        name: $v.name,
        coordinates: $v.at
    });
```

Output

```surql
[
	{
		coordinates: (98, 65.7),
		item: 0,
		name: 'Some city'
	},
	{
		coordinates: (0, 0.1),
		item: 1,
		name: 'Other city'
	}
]
```

While refining pipelines like this, [`.expect()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valueexpect) (
Available since: v3.1.0
) on the result of `.filter()` or `.map()` can confirm the shape you expect before the query continues. For example, `.expect(|$records| $records.len() = 2, "Expected exactly two valid cities")`.
