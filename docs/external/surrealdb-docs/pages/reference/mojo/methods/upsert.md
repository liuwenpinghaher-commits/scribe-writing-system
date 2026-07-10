---
title: "https://surrealdb.com/docs/reference/mojo/methods/upsert"
url: "https://surrealdb.com/docs/reference/mojo/methods/upsert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/upsert

Source: https://surrealdb.com/docs/reference/mojo/methods/upsert

Creates a record if it does not exist, or updates it if it does. This is a convenience wrapper that runs `UPSERT  CONTENT ;`.
Method Syntax

```python
client.upsert(thing, content_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/upsert#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to upsert.  |  
| `content_json`  | The record content as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/upsert#example-usage)

```python
var resp = client.upsert("person:chiru", '{ "name": "Chiru", "age": 31 }')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/upsert#translated-query)

```surql
UPSERT $thing CONTENT $content_json;
```
