---
title: "https://surrealdb.com/docs/reference/mojo/methods/merge"
url: "https://surrealdb.com/docs/reference/mojo/methods/merge"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/merge

Source: https://surrealdb.com/docs/reference/mojo/methods/merge

Merges data into all records in a table, or a specific record, leaving unspecified fields untouched. This is a convenience wrapper that runs `UPDATE  MERGE ;`.
Method Syntax

```python
client.merge(thing, data_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/merge#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to merge into.  |  
| `data_json`  | The data to merge, as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/merge#example-usage)

```python
var resp = client.merge("person:chiru", '{ "age": 31 }')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/merge#translated-query)

```surql
UPDATE $thing MERGE $data_json;
```
