---
title: "https://surrealdb.com/docs/reference/php/v1/methods/import"
url: "https://surrealdb.com/docs/reference/php/v1/methods/import"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/import

Source: https://surrealdb.com/docs/reference/php/v1/methods/import

Imports data into a table.
Note
This method is only available on a remote database targeted with the http protocol.
Method Syntax

```php
$db->import($content, $username, $password);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/import#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `content`  | `string`  | The content to import.  |  
| `username`  | `string`  | The username to authenticate with.  |  
| `password`  | `string`  | The password to authenticate with.  |  
###  Example[](https://surrealdb.com/docs/reference/php/v1/methods/import#example)
Example

```php
// connect and select the namespace + database that the import function will use to import the data
$db->connect('http://localhost:8080', [
	'namespace' => 'example',
	'database' => 'example',
]);

// grab file contents and import the data
$import = file_get_contents('data.surql');
$db->import($import, 'admin', 'password');
```
