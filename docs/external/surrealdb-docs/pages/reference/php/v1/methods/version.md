---
title: "https://surrealdb.com/docs/reference/php/v1/methods/version"
url: "https://surrealdb.com/docs/reference/php/v1/methods/version"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/version

Source: https://surrealdb.com/docs/reference/php/v1/methods/version

This method retrieves the current version of a remote database.
Method Syntax

```php
$db->version();
```

###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/version#example-usage)

```php
try {
	$version = $db->version();
	echo "The remote database is running version $version.";
} catch (Exception $e) {
	echo "An error occurred while retrieving the version: " . $e->getMessage();
}

```
