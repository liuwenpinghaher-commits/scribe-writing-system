---
title: "https://surrealdb.com/docs/reference/php/v1/methods/unset"
url: "https://surrealdb.com/docs/reference/php/v1/methods/unset"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/unset

Source: https://surrealdb.com/docs/reference/php/v1/methods/unset

Removes a parameter for this connection.
Method Syntax

```php
$db->unset($key)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/unset#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `key`  | `string`  | Specifies the name of the variable.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/unset#example-usage)

```php
// Remove the variable from the connection
$db->unset('name');
```
