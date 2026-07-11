---
title: "https://surrealdb.com/docs/reference/php/v1/methods/patch"
url: "https://surrealdb.com/docs/reference/php/v1/methods/patch"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/patch

Source: https://surrealdb.com/docs/reference/php/v1/methods/patch

Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```php
$db->patch($thing, $data, $diff)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/patch#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to patch.  |  
| `data`  | `associative array`  | The JSON Patch data with which to patch the records.  |  
| `diff`  | `boolean`  | Whether to return the diff of the patched record.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/patch#example-usage)

```php
// Update all records in a table
$people = $db->patch('person', [
		[ "op" => 'replace', "path" => '/created_at',
	    "value" => new Date() ],
]);

// Update a record with a specific ID
$person = $db->patch(new RecordId('person', 'tobie'), [
		[ "op" => 'replace', "path" => '/settings/active',
	    "value" => false ],
		[ "op" => 'add', "path" => '/tags', "value" => ['developer',
	    'engineer'] ],
	[ "op" => 'remove', "path" => '/temp' ],
]);
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/patch#translated-query)
This function will run the following query in the database.

```surql
UPDATE $thing PATCH $data;
```
