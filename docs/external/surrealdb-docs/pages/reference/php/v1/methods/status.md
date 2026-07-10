---
title: "https://surrealdb.com/docs/reference/php/v1/methods/status"
url: "https://surrealdb.com/docs/reference/php/v1/methods/status"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/status

Source: https://surrealdb.com/docs/reference/php/v1/methods/status

This method retrieves the current status of a remote database.
Method Syntax

```php
$db->status();
```

###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/status#example-usage)

```php
$status = $db->status();
echo "The status code is: $status."; // 200 or 500
```

The status function returns `200` if the database is running and `500` if the database is down or cannot be reached.
