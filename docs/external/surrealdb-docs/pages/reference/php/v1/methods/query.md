---
title: "https://surrealdb.com/docs/reference/php/v1/methods/query"
url: "https://surrealdb.com/docs/reference/php/v1/methods/query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/query

Source: https://surrealdb.com/docs/reference/php/v1/methods/query

Runs a set of [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database.
Method Syntax

```php
$db->query($query, $vars)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/query#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `$query`  | `string`  | Specifies the SurrealQL statements.  |  
| `$vars`  | `associative array`  | Assigns variables which can be used in the query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/query#example-usage)

```php
// Assign the variable on the connection
$result = db->query(
	'CREATE person SET name = "John"; SELECT * FROM type::table($tb);',
	[ "tb" => "person" ]
);

// Get the first result from the first query
$created = $result[0]->result[0];

// Get all of the results from the second query
$people = $result[1]->result;
```
