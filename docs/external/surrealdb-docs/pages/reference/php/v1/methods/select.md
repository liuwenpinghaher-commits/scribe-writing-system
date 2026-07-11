---
title: "https://surrealdb.com/docs/reference/php/v1/methods/select"
url: "https://surrealdb.com/docs/reference/php/v1/methods/select"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/select

Source: https://surrealdb.com/docs/reference/php/v1/methods/select

Selects all records in a table, or a specific record, from the database.
Method Syntax

```php
$db->select($thing)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/select#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to select.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/select#example-usage)

```php
// Select all records from a table
$people = $db->select('person');

// Select a specific record from a table
$person = $db->select(new RecordId('person', 'h5wxrf2ewk8xjxosxtyc'));
$person = $db->select(new StringRecordId('person:h5wxrf2ewk8xjxosxtyc'));
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/select#translated-query)
This function will run the following query in the database.

```surql
SELECT * FROM $thing;
```
