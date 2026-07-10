---
title: "https://surrealdb.com/docs/reference/php/v1/methods/connect"
url: "https://surrealdb.com/docs/reference/php/v1/methods/connect"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/connect

Source: https://surrealdb.com/docs/reference/php/v1/methods/connect

Connects to a local or remote database endpoint.
Method Syntax

```php
$db->connect($host, $options)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/connect#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `host`  | `string`  | The url of the database endpoint to connect to.  |  
| `options`  | `associative array`  | An object with options to initiate the connection to SurrealDB.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/connect#example-usage)
There are several ways to connect to a database endpoint. You can connect to a local or remote endpoint, specify a namespace and database pair to use, authenticate with an existing token, authenticate using a pair of credentials, or use advanced custom logic to prepare the connection to the database.

```php
// Connect to a local endpoint
$db->connect('http://127.0.0.1:8000/rpc');

// Connect to a remote endpoint
$db->connect('https://cloud.surrealdb.com/rpc');

// Specify a namespace and database pair to use
$db->connect('https://cloud.surrealdb.com/rpc', [
	"namespace" => "surrealdb",
	"database" => "docs",
]);
```
