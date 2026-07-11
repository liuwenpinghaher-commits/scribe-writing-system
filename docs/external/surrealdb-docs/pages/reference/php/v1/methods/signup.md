---
title: "https://surrealdb.com/docs/reference/php/v1/methods/signup"
url: "https://surrealdb.com/docs/reference/php/v1/methods/signup"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/signup

Source: https://surrealdb.com/docs/reference/php/v1/methods/signup

Signs up to a specific authentication access method.
Method Syntax

```php
$db->signup([
    "namespace" => "main",
    "database" => "db",
    "access" => "account",
    // ... other variables
]);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/signup#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `namespace`  | The namespace to sign up to  |  
| `database`  | The database to sign up to  |  
| `access`  | The access method to sign up to. Also pass any variables used in the access definition.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/signup#example-usage)

```php
$token = $db->signup([
	"namespace" => "surrealdb",
	"database" => "docs",
	"access" => "user",

	// Also pass any properties required by the access definition
	"email" => "info@surrealdb.com",
	"pass" => "123456",
]);
```

You can invalidate the authentication for the current connection using the [`invalidate()` method](https://surrealdb.com/docs/reference/php/v1/methods/invalidate).
