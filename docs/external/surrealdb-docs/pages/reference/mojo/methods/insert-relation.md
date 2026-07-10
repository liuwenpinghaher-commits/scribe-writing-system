---
title: "https://surrealdb.com/docs/reference/mojo/methods/insert-relation"
url: "https://surrealdb.com/docs/reference/mojo/methods/insert-relation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/insert-relation

Source: https://surrealdb.com/docs/reference/mojo/methods/insert-relation

Inserts one or more relation records into a table. This is a convenience wrapper that runs `INSERT RELATION INTO   
;`.
Method Syntax

```python
client.insert_relation(table, data_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/insert-relation#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `table`  | The relation table to insert into.  |  
| `data_json`  |  A single relation or an array of relations, as a JSON string. Each carries an `in`and an `out`record.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/insert-relation#example-usage)

```python
var resp = client.insert_relation(
    "likes",
    '[{ "in": "person:alice", "out": "person:bob" }]',
)
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/insert-relation#translated-query)

```surql
INSERT RELATION INTO $table $data_json;
```
