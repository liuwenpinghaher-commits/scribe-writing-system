---
title: "https://surrealdb.com/docs/reference/mojo/methods/update"
url: "https://surrealdb.com/docs/reference/mojo/methods/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/update

Source: https://surrealdb.com/docs/reference/mojo/methods/update

Updates all records in a table, or a specific record, replacing their content. This is a convenience wrapper that runs `UPDATE  CONTENT ;`.
Method Syntax

```python
client.update(thing, content_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/update#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to update.  |  
| `content_json`  | The replacement content as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/update#example-usage)

```python
var resp = client.update("person:chiru", '{ "age": 31 }')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/update#translated-query)

```surql
UPDATE $thing CONTENT $content_json;
```
