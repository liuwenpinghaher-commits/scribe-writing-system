---
title: "https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb

The Python SDK supports connecting to SurrealDB over WebSocket, HTTP, or as an embedded in-process database. Connections can be synchronous or asynchronous, and the SDK automatically selects the correct connection class based on the URL scheme you provide.
This page covers how to create, configure, and manage connections to a SurrealDB instance.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`Surreal(url)`](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal)  | Creates a synchronous connection based on the URL scheme  |  
| [`AsyncSurreal(url)`](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal)  | Creates an asynchronous connection based on the URL scheme  |  
| [`db.connect(url?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#connect)  | Opens the connection to the SurrealDB instance  |  
| [`db.close()`](https://surrealdb.com/docs/reference/python/api/core/surreal#close)  | Closes the active connection and releases resources  |  
| [`db.use(namespace, database)`](https://surrealdb.com/docs/reference/python/api/core/surreal#use)  | Switches to a specific namespace and database  |  
| [`db.version()`](https://surrealdb.com/docs/reference/python/api/core/surreal#version)  | Returns the version of the connected SurrealDB instance  |  
##  Choosing between synchronous and asynchronous[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#choosing-between-synchronous-and-asynchronous)
The SDK provides two factory functions: `Surreal` for synchronous (blocking) connections and `AsyncSurreal` for asynchronous connections. Both return a connection object with the same set of methods, the async variants must be awaited.
Use `Surreal` when your application is synchronous or when you are writing scripts, CLI tools, or other non-async code. Use `AsyncSurreal` when working with async frameworks such as FastAPI, aiohttp, or any `asyncio`-based application.
SynchronousAsynchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()
```

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
await db.connect()
```

##  Opening a connection[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#opening-a-connection)
The `Surreal` and `AsyncSurreal` factory functions accept a URL and return the appropriate connection class. The SDK inspects the URL scheme to determine whether to use a WebSocket, HTTP, or embedded connection.
You can connect to a remote SurrealDB instance over WebSocket or HTTP.
SynchronousAsynchronous

```python
from surrealdb import Surreal

ws_db = Surreal("ws://localhost:8000")
ws_db.connect()

http_db = Surreal("https://cloud.surrealdb.com")
http_db.connect()
```

```python
from surrealdb import AsyncSurreal

ws_db = AsyncSurreal("ws://localhost:8000")
await ws_db.connect()

http_db = AsyncSurreal("https://cloud.surrealdb.com")
await http_db.connect()
```

You can also run SurrealDB as an embedded in-process database, which is useful for testing or standalone applications.

```python
from surrealdb import Surreal

mem_db = Surreal("mem://")
mem_db.connect()

disk_db = Surreal("surrealkv://path/to/database")
disk_db.connect()
```

The `.connect()` method optionally accepts a URL to override the one provided to the factory. See the [API reference](https://surrealdb.com/docs/reference/python/api/core/surreal#connect) for parameter details.
##  Connection string protocols[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#connection-string-protocols)
The URL scheme determines the connection type and its capabilities.  
| Scheme  | Connection type  | Description  |  
| --- | --- | --- |  
| `ws://`  | WebSocket  | Unencrypted stateful connection  |  
| `wss://`  | WebSocket  | TLS-encrypted stateful connection  |  
| `http://`  | HTTP  | Unencrypted stateless connection  |  
| `https://`  | HTTP  | TLS-encrypted stateless connection  |  
| `mem://`  | Embedded (in-memory)  | In-process database that does not persist data  |  
| `file://`  | Embedded (on-disk)  | In-process database backed by SurrealKV storage  |  
| `surrealkv://`  | Embedded (on-disk)  | In-process database backed by SurrealKV storage  |  
WebSocket and HTTP are used to connect to remote SurrealDB instances, while the embedded protocols run the database engine directly in your Python process. See [Embedded databases](https://surrealdb.com/docs/reference/python/concepts/embedded-databases) for more on in-process connections.
##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
After connecting, use `.use()` to select the namespace and database you want to work with. Most operations require a namespace and database to be selected first.
SynchronousAsynchronous

```python
db.use("surrealdb", "docs")
```

```python
await db.use("surrealdb", "docs")
```

You can call `.use()` multiple times to switch between namespaces and databases on the same connection.
##  Using context managers[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#using-context-managers)
Python's context manager protocol (`with` / `async with`) provides a convenient way to manage connection lifecycle. The connection is automatically opened when entering the context and closed when exiting, even if an exception occurs.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})
    results = db.select("users")
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})
    results = await db.select("users")
```

Using context managers is the recommended approach, as it guarantees resources are released even when errors occur.
##  Effect of connection protocol on token and session duration[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#effect-of-connection-protocol-on-token-and-session-duration)
The connection protocol affects how authentication tokens and sessions behave.
WebSocket connections (`ws://`, `wss://`) are long-lived and stateful. After the initial authentication, the session persists for the lifetime of the connection. The session duration defaults to `NONE`, meaning it never expires unless configured otherwise.
HTTP connections (`http://`, `https://`) are short-lived and stateless. Each request is independent and requires its own authentication token. The token duration defaults to 1 hour.
You can configure token and session durations using the `DURATION` clause in the [`DEFINE ACCESS METHOD`](https://surrealdb.com/docs/reference/query-language/statements/define/access) or [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) statements.
Note
Learn more about token and session duration in the [security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#expiration) documentation.
##  Closing a connection[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#closing-a-connection)
When you are done with a connection, call `.close()` to release the underlying resources. If you use a context manager, this happens automatically.
SynchronousAsynchronous

```python
db.close()
```

```python
await db.close()
```

##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for complete method signatures and parameters
  * •
[Authentication](https://surrealdb.com/docs/reference/python/concepts/authentication) for signing in and managing user sessions
  * •
[Embedded databases](https://surrealdb.com/docs/reference/python/concepts/embedded-databases) for running SurrealDB in-process
  * •
[Error handling](https://surrealdb.com/docs/reference/python/concepts/error-handling) for handling connection and authentication errors
