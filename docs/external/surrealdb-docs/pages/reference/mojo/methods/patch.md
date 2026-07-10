---
title: "https://surrealdb.com/docs/reference/mojo/methods/patch"
url: "https://surrealdb.com/docs/reference/mojo/methods/patch"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/patch

Source: https://surrealdb.com/docs/reference/mojo/methods/patch

Applies a JSON Patch to all records in a table, or a specific record. This is a convenience wrapper that runs `UPDATE  PATCH ;`.
Method Syntax

```python
client.patch(thing, patch_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/patch#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `thing`  | The table or specific record to patch.  |  
| `patch_json`  | A JSON Patch array as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/patch#example-usage)

```python
var resp = client.patch("person:chiru", '[{ "op": "replace", "path": "/age", "value": 31 }]')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/patch#translated-query)

```surql
UPDATE $thing PATCH $patch_json;
```
