---
title: "https://surrealdb.com/docs/reference/php/v1/methods/export"
url: "https://surrealdb.com/docs/reference/php/v1/methods/export"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/export

Source: https://surrealdb.com/docs/reference/php/v1/methods/export

Exports data from a table.
Note
This method is only available on a remote database targeted with the http protocol.
Method Syntax

```php
$db->export($username, $password);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/export#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `username`  | `string`  | The username to authenticate with.  |  
| `password`  | `string`  | The password to authenticate with.  |  
###  Example[](https://surrealdb.com/docs/reference/php/v1/methods/export#example)
Example

```php
// connect to the remote database. For the export to work, the database must exists with also existing data.
$db->connect('http://localhost:8080', [
	'namespace' => 'example',
	'database' => 'example',
]);

// Export data
$response = $db->export('admin', 'password');

// Create a file and write the response to it
$fp = fopen('exported_data.json', 'w');

// Write the response to the file
fwrite($fp, $response);

// Close the file
fclose($fp);
```
