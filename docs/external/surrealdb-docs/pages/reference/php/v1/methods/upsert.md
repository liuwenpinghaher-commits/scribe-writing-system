---
title: "https://surrealdb.com/docs/reference/php/v1/methods/upsert"
url: "https://surrealdb.com/docs/reference/php/v1/methods/upsert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/upsert

Source: https://surrealdb.com/docs/reference/php/v1/methods/upsert

Creates or updates a record in a table.
Method Syntax

```php
$db->upsert($thing, $data);
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/upsert#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `$thing`  | `RecordId`. `StringRecordId` or `string`  | The collection to upsert the record to.  |  
| `$data`  | `mixed`  | The record to upsert.  |  
###  Example[](https://surrealdb.com/docs/reference/php/v1/methods/upsert#example)
Example

```php
$id = new RecordId('users', 'tobie');

// Upsert a record to the "users" collection.
$response = $db->upsert($id, [
	'firstname' => 'Tobie',
	'lastname' => 'Hitchcock',
]);
```
