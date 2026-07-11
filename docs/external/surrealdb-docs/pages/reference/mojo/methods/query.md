---
title: "https://surrealdb.com/docs/reference/mojo/methods/query"
url: "https://surrealdb.com/docs/reference/mojo/methods/query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/query

Source: https://surrealdb.com/docs/reference/mojo/methods/query

Runs one or more SurrealQL statements against the database and returns an `RpcResponse`.
Method Syntax

```python
client.query(query, bindings_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/query#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `query`  | The SurrealQL statements to run.  |  
| `bindings_json`  |  Optional bindings as a JSON string. Defaults to `"{}"`.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/query#example-usage)

```python
var resp = client.query("SELECT * FROM person WHERE age > 18;")

if resp.is_ok():
    if resp.result:
        print(resp.result.value())
else:
    print("error:", resp.error_message().value())
```

Note
A dedicated API for passing arbitrary CBOR bindings is on the roadmap. Today, CBOR connections support the default `"{}"`, while JSON-RPC connections accept raw JSON strings via `bindings_json`.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/query#see-also)
  * •
[Executing queries](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries)
