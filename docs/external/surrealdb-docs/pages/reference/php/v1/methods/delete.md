---
title: "https://surrealdb.com/docs/reference/php/v1/methods/delete"
url: "https://surrealdb.com/docs/reference/php/v1/methods/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods/delete

Source: https://surrealdb.com/docs/reference/php/v1/methods/delete

Deletes all records in a table, or a specific record, from the database.
Method Syntax

```php
$db->delete($thing)
```

###  Arguments[](https://surrealdb.com/docs/reference/php/v1/methods/delete#arguments)  
| Arguments  | Type  | Description  |  
| --- | --- | --- |  
| `thing`  |  `string`, `RecordId`or `StringRecordId`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid) to delete.  |  
###  Example usage[](https://surrealdb.com/docs/reference/php/v1/methods/delete#example-usage)

```php
// Delete all records from a table
$db->delete('person');

// Delete a specific record from a table
$db->delete(new RecordId('person', 'h5wxrf2ewk8xjxosxtyc'));
```

###  Translated query[](https://surrealdb.com/docs/reference/php/v1/methods/delete#translated-query)
This function will run the following query in the database.

```surql
DELETE $thing;
```
