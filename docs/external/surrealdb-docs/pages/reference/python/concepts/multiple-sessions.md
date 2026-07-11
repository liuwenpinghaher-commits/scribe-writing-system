---
title: "https://surrealdb.com/docs/reference/python/concepts/multiple-sessions"
url: "https://surrealdb.com/docs/reference/python/concepts/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/multiple-sessions

Source: https://surrealdb.com/docs/reference/python/concepts/multiple-sessions

The Python SDK supports creating multiple isolated sessions within a single WebSocket connection. Each session maintains its own namespace, database, and authentication state, allowing you to perform independent operations without opening additional connections.
This page covers how to create sessions, isolate their scope, authenticate independently, and close them when no longer needed.
Note
Multiple sessions require a WebSocket connection (`ws://` or `wss://`). HTTP and embedded connections do not support sessions.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.new_session()`](https://surrealdb.com/docs/reference/python/api/core/surreal#new-session)  | Creates a new isolated session on the current connection  |  
| [`session.close_session()`](https://surrealdb.com/docs/reference/python/api/core/surreal-session#close-session)  | Closes the session and detaches it from the connection  |  
| [`session.use(namespace, database)`](https://surrealdb.com/docs/reference/python/api/core/surreal-session#use)  | Switches the session to a specific namespace and database  |  
##  Creating a session[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#creating-a-session)
Call `.new_session()` on an existing connection to create a new session. The async variant returns an `AsyncSurrealSession` and the sync variant returns a `BlockingSurrealSession`. Each session operates independently from the parent connection and other sessions.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})

    session = db.new_session()
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})

    session = await db.new_session()
```

A newly created session does not inherit the namespace, database, or authentication state of the parent connection. You must configure these explicitly on the session.
##  Isolating namespace and database[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#isolating-namespace-and-database)
Each session can target a different namespace and database by calling `.use()`. Changes to one session's scope do not affect the parent connection or any other session.
SynchronousAsynchronous

```python
session_a = db.new_session()
session_a.use("surrealdb", "docs")

session_b = db.new_session()
session_b.use("surrealdb", "staging")

docs_users = session_a.select("users")
staging_users = session_b.select("users")
```

```python
session_a = await db.new_session()
await session_a.use("surrealdb", "docs")

session_b = await db.new_session()
await session_b.use("surrealdb", "staging")

docs_users = await session_a.select("users")
staging_users = await session_b.select("users")
```

In the example above, `session_a` reads from the `docs` database while `session_b` reads from `staging`, both over the same underlying WebSocket connection.
##  Independent authentication[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#independent-authentication)
Each session can authenticate as a different user. This is useful when you need to perform operations on behalf of multiple users without managing separate connections.
SynchronousAsynchronous

```python
session_admin = db.new_session()
session_admin.use("surrealdb", "docs")
session_admin.signin({"username": "root", "password": "root"})

session_user = db.new_session()
session_user.use("surrealdb", "docs")
session_user.signin({
    "namespace": "surrealdb",
    "database": "docs",
    "access": "account",
    "variables": {
        "email": "info@surrealdb.com",
        "password": "123456",
    },
})

all_records = session_admin.select("users")

own_record = session_user.info()
```

```python
session_admin = await db.new_session()
await session_admin.use("surrealdb", "docs")
await session_admin.signin({"username": "root", "password": "root"})

session_user = await db.new_session()
await session_user.use("surrealdb", "docs")
await session_user.signin({
    "namespace": "surrealdb",
    "database": "docs",
    "access": "account",
    "variables": {
        "email": "info@surrealdb.com",
        "password": "123456",
    },
})

all_records = await session_admin.select("users")

own_record = await session_user.info()
```

In the example above, `session_admin` has root-level access while `session_user` is authenticated as a record user. Each session's permissions are enforced independently.
##  Closing a session[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#closing-a-session)
When a session is no longer needed, call `.close_session()` to detach it from the connection and release its resources. The parent connection and other sessions remain active.
SynchronousAsynchronous

```python
session.close_session()
```

```python
await session.close_session()
```

Closing the parent connection automatically closes all sessions associated with it.
##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/multiple-sessions#learn-more)
  * •
[SurrealSession API reference](https://surrealdb.com/docs/reference/python/api/core/surreal-session) for session method signatures
  * •
[Transactions](https://surrealdb.com/docs/reference/python/concepts/transactions) for transaction support within sessions
  * •
[Authentication](https://surrealdb.com/docs/reference/python/concepts/authentication) for signing in within sessions
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb) for WebSocket connection setup
