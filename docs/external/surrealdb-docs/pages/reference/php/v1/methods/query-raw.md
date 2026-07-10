---
title: "https://surrealdb.com/docs/reference/php/v1/methods/query-raw"
url: "https://surrealdb.com/docs/reference/php/v1/methods/query-raw"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/query-raw

Source: https://surrealdb.com/docs/reference/php/v1/methods/query-raw

With queryRaw, you will get back the raw RPC response.   
This contrast to the .query() method, this will not throw for errors that occur in individual queries,   
but will rather give those back as a string, and this will include the time it took to execute the individual queries.
Method Syntax

```php
$db->queryRaw($query, $params);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/query-raw#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `$query`  | `string`  | The query to execute  |  
| `$params`  | `associative array`  | An associative array of parameters to bind to the query.  |  
###  Example[](https://surrealdb.com/docs/reference/php/v1/methods/query-raw#example)
Example

```php
// Query the database for all users with the firstname "Tobie" with parameters.
$response = $db->queryRaw(
	'SELECT * FROM users WHERE firstname = $firstname',
	['firstname' => 'Tobie']
);

// Query the database for all users with the firstname "Tobie" without parameters.
$response = $db->queryRaw('SELECT * FROM users WHERE firstname = "Tobie"');
```
