---
title: "https://surrealdb.com/docs/reference/php/v1/methods/run"
url: "https://surrealdb.com/docs/reference/php/v1/methods/run"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/run

Source: https://surrealdb.com/docs/reference/php/v1/methods/run

Runs a defined SurrealQL function on the remote database.
Method Syntax

```php
$db->run($function, $version, $params);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/run#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `$function`  | `string`  | The name of the function to run.  |  
| `$version`  | `string` or `null`  | The version of the function to run.  |  
| `$params`  | `array` or `null`  | An array of parameters to pass to the function.  |  
###  Example[](https://surrealdb.com/docs/reference/php/v1/methods/run#example)
Example

```php
$functionA = $db->run("fn::hello_world", null, ["Tobie"]);
$functionB = $db->run("fn::hello_world", "v1", ["Tobie"]);

// or with named arguments
$functionA = $db->run("fn::hello_world", params: ["Tobie"]);
$functionB = $db->run("fn::hello_world", version: "v1", params: ["Tobie"]);
```
