---
title: "https://surrealdb.com/docs/reference/php/v1/methods/let"
url: "https://surrealdb.com/docs/reference/php/v1/methods/let"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/let

Source: https://surrealdb.com/docs/reference/php/v1/methods/let

Assigns a value as a parameter for this connection.
Method Syntax

```php
$db->let($name, $value)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/let#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | Specifies the name of the variable.  |  
| `value`  | `mixed`  | Assigns the value to the variable name.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/let#example-usage)

```php
// Assign the variable on the connection
$db->let('name', [
	"first" => "Tobie",
	"last" => "Morgan Hitchcock",
]);

// Use the variable in a subsequent query
$db->query('CREATE person SET name = $name');

// Use the variable in a subsequent query
$db->query('SELECT * FROM person WHERE name.first = $name.first');
```

You can remove the variable from the connection using the [`unset()` method](https://surrealdb.com/docs/reference/php/v1/methods/unset).
