---
title: "https://surrealdb.com/docs/reference/python/api/core/surreal-transaction"
url: "https://surrealdb.com/docs/reference/python/api/core/surreal-transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/core/surreal-transaction

Source: https://surrealdb.com/docs/reference/python/api/core/surreal-transaction

A transaction wraps a connection with both a session ID and a transaction ID, scoping all operations to a single atomic unit. Changes are applied only when the transaction is committed, and can be rolled back with cancel.
Transactions are created by calling [`.begin_transaction()`](https://surrealdb.com/docs/reference/python/api/core/surreal-session#begin-transaction) on a session. They are **not** available on HTTP or embedded connections.
Note
Transactions require a WebSocket connection (`ws://` or `wss://`). They must be created from a session via `.begin_transaction()`.
**Source:** [`async_ws.py`](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/connections/async_ws.py) · [`blocking_ws.py`](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/connections/blocking_ws.py)
* * *
##  Creating a transaction[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#creating)
Method Syntax

```python
txn = session.begin_transaction()
```

**Returns (sync):** `BlockingSurrealTransaction`  
**Returns (async):** `AsyncSurrealTransaction`
###  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#examples)
Synchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()
db.signin({"username": "root", "password": "root"})
db.use("my_namespace", "my_database")

session = db.new_session()
session.use("my_namespace", "my_database")

txn = session.begin_transaction()
txn.create("users", {"name": "Alice"})
txn.commit()
```

Asynchronous

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
await db.connect()
await db.signin({"username": "root", "password": "root"})
await db.use("my_namespace", "my_database")

session = await db.new_session()
await session.use("my_namespace", "my_database")

txn = await session.begin_transaction()
await txn.create("users", {"name": "Alice"})
await txn.commit()
```

* * *
##  Inherited methods[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#inherited-methods)
A transaction exposes query and CRUD methods that mirror the parent connection's interface. All operations are scoped to this transaction and are not visible outside it until committed. For full parameter tables and examples, see the [Surreal](https://surrealdb.com/docs/reference/python/api/core/surreal) reference.  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| [`.query(query, vars)`](https://surrealdb.com/docs/reference/python/api/core/surreal#query)  | Awaitable / lazy `Value` or `tuple[Value, ...]` builder  | Execute one or more SurrealQL statements within the transaction.  |  
| [`.select(record)`](https://surrealdb.com/docs/reference/python/api/core/surreal#select)  | [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)  | Select records.  |  
| [`.create(record, data)`](https://surrealdb.com/docs/reference/python/api/core/surreal#create)  | CRUD builder -> `dict[str, Value]`  | Create a record (chain `.content/.replace/.merge/.patch`).  |  
| [`.update(record, data)`](https://surrealdb.com/docs/reference/python/api/core/surreal#update)  | CRUD builder -> `dict` or `list`  | Update records (chain `.content/.replace/.merge/.patch`).  |  
| [`.upsert(record, data)`](https://surrealdb.com/docs/reference/python/api/core/surreal#upsert)  | CRUD builder -> `dict` or `list`  | Upsert a record (chain `.content/.replace/.merge/.patch`).  |  
| [`.delete(record)`](https://surrealdb.com/docs/reference/python/api/core/surreal#delete)  | CRUD builder -> `dict` or `list`  | Delete records.  |  
| [`.insert(table, data, relation=False)`](https://surrealdb.com/docs/reference/python/api/core/surreal#insert)  | Insert builder -> `list[Value]`  | Insert records. Pass `relation=True` or chain `.relation()` for `INSERT RELATION`.  |  
| [`.run(name, args, version)`](https://surrealdb.com/docs/reference/python/api/core/surreal#run)  | [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)  | Call a SurrealDB function within the transaction.  |  
| [`.let(key, value)`](https://surrealdb.com/docs/reference/python/api/core/surreal#let)  | `None`  | Set a transaction-scoped variable.  |  
| [`.unset(key)`](https://surrealdb.com/docs/reference/python/api/core/surreal#unset)  | `None`  | Unset a transaction-scoped variable.  |  
* * *
##  Transaction-specific methods[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#transaction-specific-methods)
###  `.commit()`[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#commit)
Commits the transaction, applying all changes made within it to the database. After committing, the transaction object should not be used.
Method Syntax

```python
txn.commit()
```

**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#examples-1)
Synchronous

```python
txn = session.begin_transaction()
txn.create("users", {"name": "Alice", "email": "alice@example.com"})
txn.create("users", {"name": "Bob", "email": "bob@example.com"})
txn.commit()
```

Asynchronous

```python
txn = await session.begin_transaction()
await txn.create("users", {"name": "Alice", "email": "alice@example.com"})
await txn.create("users", {"name": "Bob", "email": "bob@example.com"})
await txn.commit()
```

###  `.cancel()`[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#cancel)
Cancels the transaction, discarding all changes made within it. No data is written to the database. After cancelling, the transaction object should not be used.
Method Syntax

```python
txn.cancel()
```

**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#examples-2)
Synchronous

```python
txn = session.begin_transaction()
txn.delete("users")
txn.cancel()
```

Asynchronous

```python
txn = await session.begin_transaction()
await txn.delete("users")
await txn.cancel()
```

Rollback on error

```python
txn = session.begin_transaction()
try:
    txn.create("orders", {"product": "Laptop", "qty": 1})
    txn.update(RecordID("inventory", "laptop"), {"stock": -1})
    txn.commit()
except Exception:
    txn.cancel()
```

* * *
##  Complete example[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#complete-example)
Atomic transfer (sync)

```python
from surrealdb import Surreal, RecordID

with Surreal("ws://localhost:8000") as db:
    db.use("bank", "ledger")
    db.signin({"username": "root", "password": "root"})

    session = db.new_session()
    session.use("bank", "ledger")

    session.create(RecordID("accounts", "alice"), {"balance": 1000})
    session.create(RecordID("accounts", "bob"), {"balance": 500})

    txn = session.begin_transaction()
    try:
        txn.query(
            "UPDATE accounts:alice SET balance = balance - $amount",
            {"amount": 200},
        )
        txn.query(
            "UPDATE accounts:bob SET balance = balance + $amount",
            {"amount": 200},
        )
        txn.commit()
        print("Transfer committed")
    except Exception:
        txn.cancel()
        print("Transfer rolled back")

    accounts = session.select("accounts")
    print("Accounts:", accounts)

    session.close_session()
```

Atomic transfer (async)

```python
import asyncio
from surrealdb import AsyncSurreal, RecordID

async def main():
    async with AsyncSurreal("ws://localhost:8000") as db:
        await db.use("bank", "ledger")
        await db.signin({"username": "root", "password": "root"})

        session = await db.new_session()
        await session.use("bank", "ledger")

        await session.create(RecordID("accounts", "alice"), {"balance": 1000})
        await session.create(RecordID("accounts", "bob"), {"balance": 500})

        txn = await session.begin_transaction()
        try:
            await txn.query(
                "UPDATE accounts:alice SET balance = balance - $amount",
                {"amount": 200},
            )
            await txn.query(
                "UPDATE accounts:bob SET balance = balance + $amount",
                {"amount": 200},
            )
            await txn.commit()
            print("Transfer committed")
        except Exception:
            await txn.cancel()
            print("Transfer rolled back")

        accounts = await session.select("accounts")
        print("Accounts:", accounts)

        await session.close_session()

asyncio.run(main())
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#see-also)
  * •
[SurrealSession](https://surrealdb.com/docs/reference/python/api/core/surreal-session) — Session management reference
  * •
[Surreal](https://surrealdb.com/docs/reference/python/api/core/surreal) — Connection reference with full method documentation
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/types) — Type aliases and value types
  * •
[Errors](https://surrealdb.com/docs/reference/python/api/errors) — Error classes reference
