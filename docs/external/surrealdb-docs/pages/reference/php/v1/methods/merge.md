---
title: "https://surrealdb.com/docs/reference/php/v1/methods/merge"
url: "https://surrealdb.com/docs/reference/php/v1/methods/merge"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/merge

Source: https://surrealdb.com/docs/reference/php/v1/methods/merge

Modifies all records in a table, or a specific record, in the database.
Method Syntax

```php
$db->merge($thing, $data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/merge#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to merge.  |  
| `data`  | `mixed`  | The document / record data to merge.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/merge#example-usage)

```php
// Update all records in a table
$people = $db->merge('person', [
	"updated_at" => new Date(),
]);

// Update a record with a specific ID
$person = $db->merge(new RecordId('person', 'tobie'), [
	"updated_at" => new Date(),
	"settings" => [
		"active" => true,
	],
]);

// The content you are merging the record with might differ from the return type
$record = $db->merge(new RecordId('person', 'tobie'), [
	"name" => 'Tobie',
]);
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/merge#translated-query)
This function will run the following query in the database.

```surql
UPDATE $thing MERGE $data;
```
