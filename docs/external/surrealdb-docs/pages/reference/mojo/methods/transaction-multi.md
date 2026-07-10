---
title: "https://surrealdb.com/docs/reference/mojo/methods/transaction-multi"
url: "https://surrealdb.com/docs/reference/mojo/methods/transaction-multi"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/transaction-multi

Source: https://surrealdb.com/docs/reference/mojo/methods/transaction-multi

Wraps a list of statements in `BEGIN TRANSACTION;` and `COMMIT TRANSACTION;` and sends them as a single atomic query. This works on any transport and is the recommended way to run a transaction over HTTP.
Method Syntax

```python
client.transaction_multi(statements, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `statements`  |  The statements to run, as a `List[String]`. A trailing semicolon is added to each if missing.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi#example-usage)

```python
from std.collections import List

var stmts = List[String]()
stmts.append("CREATE car:a SET wheels = 4;")
stmts.append("CREATE car:b SET wheels = 4;")
var resp = client.transaction_multi(stmts)
```

If any statement fails, the whole transaction is rolled back.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi#see-also)
  * •
[Transactions](https://surrealdb.com/docs/reference/mojo/concepts/transactions)
  * •
[`begin_transaction()`](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction)
