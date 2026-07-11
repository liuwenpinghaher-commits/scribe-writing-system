---
title: "https://surrealdb.com/docs/reference/mojo/methods/begin-transaction"
url: "https://surrealdb.com/docs/reference/mojo/methods/begin-transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/begin-transaction

Source: https://surrealdb.com/docs/reference/mojo/methods/begin-transaction

Starts a session-scoped transaction and returns a handle. The handle buffers statements and flushes them on `commit()`.
Method Syntax

```python
client.begin_transaction(session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `session`  | An optional session id.  |  
###  Handle methods[](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction#handle-methods)
The returned handle exposes:
  * •
`query(query, bindings_json)` to buffer a statement.
  * •
`create(thing, content_json)` and `select(thing)` convenience wrappers.
  * •
`commit()` to run the buffered statements atomically.
  * •
`cancel()` to discard them.

###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction#example-usage)

```python
var txn = client.begin_transaction()
_ = txn.query("CREATE person:alice SET age = 30;")
_ = txn.query("CREATE person:bob   SET age = 31;")
txn.commit()
```

Note
Session transactions run over a stateful WebSocket session. WebSocket support is rolling out. For atomic transactions over HTTP, use [`transaction_multi()`](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi).
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction#see-also)
  * •
[Transactions](https://surrealdb.com/docs/reference/mojo/concepts/transactions)
  * •
[`transaction_multi()`](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi)
