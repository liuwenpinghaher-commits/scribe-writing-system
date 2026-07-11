---
title: "https://surrealdb.com/docs/reference/mojo/methods/create"
url: "https://surrealdb.com/docs/reference/mojo/methods/create"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/create

Source: https://surrealdb.com/docs/reference/mojo/methods/create

Creates a record in the database. This is a convenience wrapper that runs `CREATE  CONTENT ;`.
Method Syntax

```python
client.create(thing, content_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/create#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to create.  |  
| `content_json`  | The record content as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/create#example-usage)

```python
var resp = client.create("person", '{ "name": "Chiru", "age": 30 }')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/create#translated-query)

```surql
CREATE $thing CONTENT $content_json;
```
