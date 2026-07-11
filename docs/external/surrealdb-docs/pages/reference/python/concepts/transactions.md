---
title: "https://surrealdb.com/docs/reference/python/concepts/transactions"
url: "https://surrealdb.com/docs/reference/python/concepts/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/transactions

Source: https://surrealdb.com/docs/reference/python/concepts/transactions

The Python SDK supports client-side transactions that group multiple operations into a single atomic unit. All operations within a transaction either succeed together when committed or are rolled back entirely when cancelled. Transactions are scoped to a session and execute over a WebSocket connection.
This page covers how to create, execute, commit, cancel, and handle errors within transactions.
Note
Transactions require a WebSocket connection (`ws://` or `wss://`) and must be created from a session. HTTP and embedded connections do not support transactions.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/transactions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`session.begin_transaction()`](https://surrealdb.com/docs/reference/python/api/core/surreal-session#begin-transaction)  | Begins a new transaction within the session  |  
| [`txn.commit()`](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#commit)  | Commits all operations in the transaction, making changes permanent  |  
| [`txn.cancel()`](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction#cancel)  | Cancels the transaction and rolls back all changes  |  
##  Creating a transaction[](https://surrealdb.com/docs/reference/python/concepts/transactions#creating-a-transaction)
To create a transaction, first open a session with `.new_session()` on the connection, then call `.begin_transaction()` on the session. The returned transaction object provides the same data manipulation methods as the main connection, but all operations are held until the transaction is committed or cancelled.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})

    session = db.new_session()
    session.use("surrealdb", "docs")

    txn = session.begin_transaction()
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})

    session = await db.new_session()
    await session.use("surrealdb", "docs")

    txn = await session.begin_transaction()
```

##  Executing operations within a transaction[](https://surrealdb.com/docs/reference/python/concepts/transactions#executing-operations-within-a-transaction)
Once a transaction is created, use its methods — such as `.query()`, `.create()`, `.select()`, `.update()`, and `.delete()` — to perform operations. These operations are buffered within the transaction scope and are not visible to other connections or sessions until the transaction is committed.
SynchronousAsynchronous

```python
txn.create("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})

txn.create("users", {
    "name": "Bob",
    "email": "bob@example.com",
    "age": 25,
})

result = txn.query("SELECT * FROM users")
```

```python
await txn.create("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})

await txn.create("users", {
    "name": "Bob",
    "email": "bob@example.com",
    "age": 25,
})

result = await txn.query("SELECT * FROM users")
```

Refer to the [SurrealTransaction API reference](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction) for the full list of methods available on the transaction object.
##  Committing a transaction[](https://surrealdb.com/docs/reference/python/concepts/transactions#committing-a-transaction)
Calling `.commit()` makes all operations in the transaction permanent. After committing, the changes become visible to other connections and sessions.
SynchronousAsynchronous

```python
txn.commit()
```

```python
await txn.commit()
```

A transaction can only be committed once. After committing, the transaction object should not be reused.
##  Cancelling a transaction[](https://surrealdb.com/docs/reference/python/concepts/transactions#cancelling-a-transaction)
Calling `.cancel()` discards all operations in the transaction and rolls back any changes. The database state is restored to what it was before the transaction began.
SynchronousAsynchronous

```python
txn.cancel()
```

```python
await txn.cancel()
```

##  Handling errors in transactions[](https://surrealdb.com/docs/reference/python/concepts/transactions#handling-errors-in-transactions)
Use a `try`/`except` block to ensure that a transaction is cancelled if any operation fails. This prevents partial changes from being committed to the database.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})

    session = db.new_session()
    session.use("surrealdb", "docs")

    txn = session.begin_transaction()

    try:
        txn.create("users", {"name": "Alice", "age": 30})
        txn.create("users", {"name": "Bob", "age": 25})
        txn.commit()
    except Exception:
        txn.cancel()
        raise
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})

    session = await db.new_session()
    await session.use("surrealdb", "docs")

    txn = await session.begin_transaction()

    try:
        await txn.create("users", {"name": "Alice", "age": 30})
        await txn.create("users", {"name": "Bob", "age": 25})
        await txn.commit()
    except Exception:
        await txn.cancel()
        raise
```

The `raise` at the end re-raises the original exception after cancelling the transaction, so the error is still visible to the caller.
##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/transactions#learn-more)
  * •
[SurrealTransaction API reference](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction) for transaction method signatures
  * •
[SurrealSession API reference](https://surrealdb.com/docs/reference/python/api/core/surreal-session) for session management
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions) for session setup
  * •
[Error handling](https://surrealdb.com/docs/reference/python/concepts/error-handling) for error recovery patterns
