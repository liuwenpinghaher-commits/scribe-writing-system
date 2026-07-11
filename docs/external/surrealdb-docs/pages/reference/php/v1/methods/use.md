---
title: "https://surrealdb.com/docs/reference/php/v1/methods/use"
url: "https://surrealdb.com/docs/reference/php/v1/methods/use"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/use

Source: https://surrealdb.com/docs/reference/php/v1/methods/use

Switch to a specific namespace and database. If only the ns or db property is specified, the current connection details will be used to fill the other property.
Method Syntax

```php
$db->use([ "namespace" => "...", "database" => "..." ]);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/use#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `namespace`  | Switches to a specific namespace.  |  
| `database`  | Switches to a specific database.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/use#example-usage)

```php
$db->use([
    "namespace" => "surrealdb",
    "database" => "docs"
]);
```
