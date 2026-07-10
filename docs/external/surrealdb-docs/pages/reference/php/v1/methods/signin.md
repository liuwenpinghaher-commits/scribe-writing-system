---
title: "https://surrealdb.com/docs/reference/php/v1/methods/signin"
url: "https://surrealdb.com/docs/reference/php/v1/methods/signin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/signin

Source: https://surrealdb.com/docs/reference/php/v1/methods/signin

Signs in to a root, namespace, database or record user.
Method Syntax

```php
$db->signin([
    "namespace" => "main",
    "database" => "db",
    "access" => "account",
    // ... other variables
]);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/signin#arguments)  
| Properties  | Description  |  
| --- | --- |  
| `username`  | The username of the database user  |  
| `password`  | The password of the database user  |  
| `namespace`  | The namespace to sign in to  |  
| `database`  | The database to sign in to  |  
| `access`  | The access method to sign in to. Also pass any variables used in the access definition.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/signin#example-usage)

```php
// Authenticate with a root user
$token = $db->signin([
	"username" => "root",
	"password" => "surrealdb",
]);

// Authenticate with a Namespace user
$token = $db->signin([
	"namespace" => "surrealdb",
	"username" => "tobie",
	"password" => "surrealdb",
]);

// Authenticate with a Database user
$token = $db->signin([
	"namespace" => "surrealdb",
	"database" => "docs",
	"username" => "tobie",
	"password" => "surrealdb",
]);

// Authenticate with a record access user
$token = $db->signin([
	"namespace" => "surrealdb",
	"database" => "docs",
	"access" => "user",

	// Also pass any properties required by the access definition
	"email" => "info@surrealdb.com",
	"pass" => "123456",
]);
```

You can invalidate the authentication for the current connection using the [`invalidate()` method](https://surrealdb.com/docs/reference/php/v1/methods/invalidate).
