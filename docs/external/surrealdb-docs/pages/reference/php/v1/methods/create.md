---
title: "https://surrealdb.com/docs/reference/php/v1/methods/create"
url: "https://surrealdb.com/docs/reference/php/v1/methods/create"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/create

Source: https://surrealdb.com/docs/reference/php/v1/methods/create

Creates a record in the database.
Method Syntax

```php
$db->create($thing, $data)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/create#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to create.  |  
| `data`  | `mixed`  | The document / record data to create.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/create#example-usage)

```php
// Create a record with a random ID
[$person] = $db->create('person');

// Create a record with a specific ID
$person = $db->create(new RecordId('person', 'tobie'), [
	"name" => 'Tobie',
	"settings" => [
		"active" => true,
		"marketing" => true,
	],
]);

// The content you are creating the record with might differ from the return type
[$record] = $db->create(
    new RecordId('person', 'tobie'),
    ["name" => "Tobie"]
);
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/create#translated-query)
This function will run the following query in the database.

```surql
CREATE $thing CONTENT $data;
```
