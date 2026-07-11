---
title: "https://surrealdb.com/docs/reference/php/v1/methods/update"
url: "https://surrealdb.com/docs/reference/php/v1/methods/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/update

Source: https://surrealdb.com/docs/reference/php/v1/methods/update

Updates all records in a table, or a specific record, in the database.
Method Syntax

```php
$db->update($thing, $data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/update#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to update.  |  
| `data`  | `mixed`  | The document / record data to update.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/update#example-usage)

```php
// Update all records in a table
$people = $db->update('person');

// Update a record with a specific ID
$person = $db->update(new RecordId('person', 'tobie'), [
	"name" => 'Tobie',
	"settings" => [
		"active" => true,
		"marketing" => true,
	],
]);

// The content you are updating the record with might differ from the return type
$record = $db->update(new RecordId('person', 'tobie'), [
	"name" => 'Tobie',
]);
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/update#translated-query)
This function will run the following query in the database.

```surql
UPDATE $thing CONTENT $data;
```
