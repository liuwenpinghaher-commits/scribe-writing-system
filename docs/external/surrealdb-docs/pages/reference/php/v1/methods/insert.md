---
title: "https://surrealdb.com/docs/reference/php/v1/methods/insert"
url: "https://surrealdb.com/docs/reference/php/v1/methods/insert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/insert

Source: https://surrealdb.com/docs/reference/php/v1/methods/insert

Inserts one or multiple records in the database.
Method Syntax

```php
$db->insert($thing, $data)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/insert#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  | `string`  | The table name or [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to insert to.  |  
| `data`  | `associative array`  | Either a single document/record or an array of documents/records to insert  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/insert#example-usage)

```php
// Insert a single record
[$person] = $db->insert('person', [
	"name" => 'Tobie',
	"settings" => [
		"active" => true,
		"marketing" => true,
	],
]);

$person = $db->insert(new RecordId('person', 'tobie'), [
	"name" => 'Tobie',
	"settings" => [
		"active" => true,
		"marketing" => true,
	],
]);

// Insert multiple records
$people = $db->insert('person', [
	[
		"name" => 'Tobie',
		"settings" => [
			"active" => true,
			"marketing" => true,
		],
	],
	[
		"name" => 'Jaime',
		"settings" => [
			"active" => true,
			"marketing" => true,
		],
	],
]);

// The content you are creating the record with might differ from the return type
$people = $db->insert('person', [
	[ "name" => 'Tobie' ],
	[ "name" => 'Jaime' ],
]);
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/insert#translated-query)
This function will run the following query in the database.

```surql
INSERT INTO $thing $data;
```
