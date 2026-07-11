---
title: "https://surrealdb.com/docs/reference/mojo/methods/delete"
url: "https://surrealdb.com/docs/reference/mojo/methods/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/delete

Source: https://surrealdb.com/docs/reference/mojo/methods/delete

Deletes all records in a table, or a specific record. This is a convenience wrapper that runs `DELETE ;`.
Method Syntax

```python
client.delete(thing, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/delete#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to delete.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/delete#example-usage)

```python
# Delete a specific record
var resp = client.delete("person:chiru")

# Delete every record in a table
var cleared = client.delete("person")
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/delete#translated-query)

```surql
DELETE $thing;
```
