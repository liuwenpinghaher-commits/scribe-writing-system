---
title: "https://surrealdb.com/docs/reference/php/v1/methods/insert-relation"
url: "https://surrealdb.com/docs/reference/php/v1/methods/insert-relation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/insert-relation

Source: https://surrealdb.com/docs/reference/php/v1/methods/insert-relation

Inserts one or multiple relations in the database.
Method Syntax

```php
$db->insertRelation($thing, $data)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/insert-relation#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  | `string` or `Table`  | Target table to insert the relation to.  |  
| `data`  | `array`  | An array of relations to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/insert-relation#example-usage)

```php
// Insert a single relation
$relation = $db->insertRelation('person', [
	"id" => new RecordId('person', 'tobie'),
	"in" => new RecordId('company', 'surreal'),
	"out" => new RecordId('role', 'founder'),
]);

// Insert multiple relations
$relations = $db->insertRelation('person', [
	[
		"id" => new RecordId('person', 'tobie'),
		"in" => new RecordId('company', 'surreal'),
		"out" => new RecordId('role', 'founder'),
	],
	[
		"id" => new RecordId('person', 'jaime'),
		"in" => new RecordId('company', 'surreal'),
		"out" => new RecordId('role', 'cofounder'),
	],
]);
```
