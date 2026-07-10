---
title: "https://surrealdb.com/docs/reference/mojo/methods/select"
url: "https://surrealdb.com/docs/reference/mojo/methods/select"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/select

Source: https://surrealdb.com/docs/reference/mojo/methods/select

Selects all records in a table, or a specific record. This is a convenience wrapper that runs `SELECT * FROM ;`.
Method Syntax

```python
client.select(thing, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/select#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to select.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/select#example-usage)

```python
# Select every record in a table
var people = client.select("person")

# Select a specific record
var chiru = client.select("person:chiru")
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/select#translated-query)

```surql
SELECT * FROM $thing;
```
