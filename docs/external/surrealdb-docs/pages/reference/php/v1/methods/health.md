---
title: "https://surrealdb.com/docs/reference/php/v1/methods/health"
url: "https://surrealdb.com/docs/reference/php/v1/methods/health"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/health

Source: https://surrealdb.com/docs/reference/php/v1/methods/health

This method checks wether the database is running and the storage engine is running.
Note
This method is only available on a remote database targeted with the http protocol.
Method Syntax

```php
$db->health();
```

###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/health#example-usage)

```php
$health = $db->health();
echo "The health status is: $health."; // 200 or 500
```

The health function returns `200` if the database is running and is in good shape. `500` if a failure occurred.
