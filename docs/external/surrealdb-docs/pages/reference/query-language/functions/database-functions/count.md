---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/count"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/count"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/count

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/count

This function can be used when counting field values and expressions.  
| Function  | Description  |  
| --- | --- |  
| [`count()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count#count)  | Counts a row, or whether a given value is truthy  |  
##  `count`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count#count)
The count function counts the number of times that the function is called. This is useful for returning the total number of records in a SELECT statement with a `GROUP BY` clause.
API DEFINITION

```surql
count() -> 1
```

If a value is given as the first argument, then this function checks whether a given value is [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness). This is useful for returning the total number of rows, which match a certain condition, in a [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select) statement, with a GROUP BY clause.
API DEFINITION

```surql
count(any) -> number
```

If an array is given, this function counts the number of items in the array which are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness). If, instead, you want to count the total number of items in the given array, then use the [`array::len()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylen) function.
API DEFINITION

```surql
count(array) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN count();

-- 1
```

```surql
RETURN count(true);

-- 1
```

```surql
RETURN count(10 > 15);

-- 0
```

```surql
RETURN count([ 1, 2, 3, null, 0, false, (15 > 10), rand::uuid() ]);

5
```

The following examples show this function being used in a [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select) statement with a GROUP clause: 

```surql
SELECT 
	count() 
FROM [
	{ age: 33 }, 
	{ age: 45 }, 
	{ age: 39 }
] 
GROUP ALL;
```

Response

```surql
[
	{ count: 3 }
]
```

```surql
SELECT 
	count(age > 35) 
FROM [
	{ age: 33 }, 
	{ age: 45 }, 
	{ age: 39 }
] 
GROUP ALL;
```

Response

```surql
[
	{ count: 2 }
]
```

An advanced example of the count function can be seen below:

```surql
SELECT
	country,
	count(age > 30) AS total
FROM [
	{ age: 33, country: 'GBR' },
	{ age: 45, country: 'GBR' },
	{ age: 39, country: 'USA' },
	{ age: 29, country: 'GBR' },
	{ age: 43, country: 'USA' }
]
GROUP BY country;
```

Response

```surql
[
	{
		country: 'GBR',
		total: 2
	},
	{
		country: 'USA',
		total: 2
	}
]
```

  
  

##  Using a `COUNT` index with `count()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count#using-a-count-index-with-count)
Available since: v3.0.0
A `COUNT` index can be defined to speed up `count()` when used with a `GROUP ALL` clause. This allows `count()` to access a single stored value when it is called instead of iterating over the entire table.

```surql
CREATE user;
-- One record in table, very fast
SELECT count() FROM user GROUP ALL;

-- 10,000 new records,
-- count() takes a bit longer than before
CREATE |user:10000| RETURN NONE;
SELECT count() FROM user GROUP ALL;

-- Add index, wait a moment for it to build
DEFINE INDEX user_count ON user COUNT;
-- count() very performant again
SELECT count() FROM user GROUP ALL;
```
