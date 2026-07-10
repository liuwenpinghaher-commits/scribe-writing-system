---
title: "https://surrealdb.com/docs/reference/python/api/core/surreal"
url: "https://surrealdb.com/docs/reference/python/api/core/surreal"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/core/surreal

Source: https://surrealdb.com/docs/reference/python/api/core/surreal

The `Surreal` and `AsyncSurreal` factory functions create a connection to a SurrealDB instance. They inspect the URL scheme and return the appropriate connection class (WebSocket, HTTP, or embedded), so you use the same interface regardless of protocol.
`Surreal(url)` returns a blocking (synchronous) connection. `AsyncSurreal(url)` returns an asynchronous connection. Both expose the same set of methods; the async variants must be awaited.
**Source:** [surrealdb.py](https://github.com/surrealdb/surrealdb.py)
##  Factory functions[](https://surrealdb.com/docs/reference/python/api/core/surreal#factory-functions)
###  `Surreal(url)`[](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal-sync)
Creates a synchronous connection based on the URL scheme.
Syntax

```python
from surrealdb import Surreal

db = Surreal(url)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `str`  | The connection URL. The scheme determines the connection type.  |  
**Returns:** `BlockingWsSurrealConnection | BlockingHttpSurrealConnection | BlockingEmbeddedSurrealConnection`
###  `AsyncSurreal(url)`[](https://surrealdb.com/docs/reference/python/api/core/surreal#surreal-async)
Creates an asynchronous connection based on the URL scheme.
Syntax

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal(url)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `str`  | The connection URL. The scheme determines the connection type.  |  
**Returns:** `AsyncWsSurrealConnection | AsyncHttpSurrealConnection | AsyncEmbeddedSurrealConnection`
###  URL schemes[](https://surrealdb.com/docs/reference/python/api/core/surreal#url-schemes)  
| Scheme  | Connection Type  | Description  |  
| --- | --- | --- |  
|  `ws://`, `wss://`  | WebSocket  | Full-featured stateful connection. Supports live queries, sessions, and transactions.  |  
|  `http://`, `https://`  | HTTP  | Stateless connection. Each request is independent.  |  
|  `mem://`, `memory://`  | Embedded (in-memory)  | In-process database that does not persist data.  |  
|  `file://`, `surrealkv://`  | Embedded (on-disk)  | In-process database backed by SurrealKV storage.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples)
WebSocket

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
```

HTTP

```python
from surrealdb import Surreal

db = Surreal("https://cloud.surrealdb.com")
```

Embedded in-memory

```python
from surrealdb import Surreal

db = Surreal("mem://")
```

Embedded on-disk

```python
from surrealdb import Surreal

db = Surreal("surrealkv://path/to/database")
```

Async WebSocket

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
```

* * *
##  Connection methods[](https://surrealdb.com/docs/reference/python/api/core/surreal#connection-methods)
###  `.connect()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#connect)
Opens the connection to the SurrealDB instance. The URL can optionally be overridden here.
Method Syntax

```python
db.connect(url)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `str | None`  |  An optional URL to override the one provided to the factory function. Defaults to `None`.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-1)
Synchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()
```

Asynchronous

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
await db.connect()
```

Override URL

```python
db = Surreal("ws://localhost:8000")
db.connect("ws://other-host:8000")
```

###  `.close()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#close)
Closes the active connection and releases resources.
Method Syntax

```python
db.close()
```

**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-2)
Synchronous

```python
db.close()
```

Asynchronous

```python
await db.close()
```

###  `.use()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#use)
Switches to a specific namespace and database.
Method Syntax

```python
db.use(namespace, database)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `namespace`  | `str`  | The namespace to use.  |  
| `database`  | `str`  | The database to use.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-3)
Synchronous

```python
db.use("my_namespace", "my_database")
```

Asynchronous

```python
await db.use("my_namespace", "my_database")
```

###  `.version()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#version)
Returns the version string of the connected SurrealDB instance.
Method Syntax

```python
db.version()
```

**Returns:** `str`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-4)
Synchronous

```python
ver = db.version()
print(ver)  # e.g. "surrealdb-2.2.0"
```

Asynchronous

```python
ver = await db.version()
print(ver)
```

* * *
##  Authentication methods[](https://surrealdb.com/docs/reference/python/api/core/surreal#authentication-methods)
###  `.signup()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#signup)
Signs up a user to a specific access method.
Method Syntax

```python
db.signup(vars)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `vars`  |  dict[str, [Value](https://surrealdb.com/docs/reference/python/api/types/#value)]  |  Variables used for signup, including `namespace`, `database`, `access`, and any additional fields required by the access method.  |  
**Returns:** [`Tokens`](https://surrealdb.com/docs/reference/python/api/types/#tokens)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-5)
Synchronous

```python
token = db.signup({
    "namespace": "my_namespace",
    "database": "my_database",
    "access": "user_access",
    "email": "user@example.com",
    "password": "s3cret",
})
```

Asynchronous

```python
token = await db.signup({
    "namespace": "my_namespace",
    "database": "my_database",
    "access": "user_access",
    "email": "user@example.com",
    "password": "s3cret",
})
```

###  `.signin()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#signin)
Signs in to the database with the given credentials.
Method Syntax

```python
db.signin(vars)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `vars`  |  dict[str, [Value](https://surrealdb.com/docs/reference/python/api/types/#value)]  |  Credentials for authentication. For root access, provide `username`and `password`. For scoped access, also include `namespace`, `database`, and `access`.  |  
**Returns:** [`Tokens`](https://surrealdb.com/docs/reference/python/api/types/#tokens)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-6)
Root signin (sync)

```python
token = db.signin({
    "username": "root",
    "password": "root",
})
```

Root signin (async)

```python
token = await db.signin({
    "username": "root",
    "password": "root",
})
```

Scoped signin

```python
token = db.signin({
    "namespace": "my_namespace",
    "database": "my_database",
    "access": "user_access",
    "email": "user@example.com",
    "password": "s3cret",
})
```

###  `.authenticate()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#authenticate)
Authenticates the current connection with a JWT token.
Method Syntax

```python
db.authenticate(token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `token`  | `str`  | The JWT token to authenticate with.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-7)
Synchronous

```python
db.authenticate("eyJhbGciOiJIUzI1NiIs...")
```

Asynchronous

```python
await db.authenticate("eyJhbGciOiJIUzI1NiIs...")
```

###  `.invalidate()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#invalidate)
Invalidates the authentication for the current connection, removing the associated JWT token.
Method Syntax

```python
db.invalidate()
```

**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-8)
Synchronous

```python
db.invalidate()
```

Asynchronous

```python
await db.invalidate()
```

###  `.info()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#info)
Returns the record of the currently authenticated user.
Method Syntax

```python
db.info()
```

**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-9)
Synchronous

```python
user = db.info()
print(user)  # e.g. {"id": "users:john", "email": "john@example.com"}
```

Asynchronous

```python
user = await db.info()
```

* * *
##  Variables[](https://surrealdb.com/docs/reference/python/api/core/surreal#variables)
###  `.let()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#let)
Defines a variable on the current connection that can be used in subsequent queries.
Method Syntax

```python
db.let(key, value)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `key`  | `str`  |  The name of the variable (without the `$`prefix).  |  
| `value`  | [Value](https://surrealdb.com/docs/reference/python/api/types/#value)  | The value to assign to the variable.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-10)
Synchronous

```python
db.let("user_id", RecordID("users", "john"))
result = db.query("SELECT * FROM users WHERE id = $user_id")
```

Asynchronous

```python
await db.let("user_id", RecordID("users", "john"))
result = await db.query("SELECT * FROM users WHERE id = $user_id")
```

###  `.unset()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#unset)
Removes a previously defined variable from the current connection.
Method Syntax

```python
db.unset(key)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `key`  | `str`  | The name of the variable to remove.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-11)
Synchronous

```python
db.unset("user_id")
```

Asynchronous

```python
await db.unset("user_id")
```

* * *
##  Query methods[](https://surrealdb.com/docs/reference/python/api/core/surreal#query-methods)
###  `.query()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#query)
Runs a set of [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements against the database. Returns an awaitable (async) or lazy (sync) builder.
Method Syntax

```python
db.query(query, vars)
```

Important
**Behaviour change in v3.0.** `.query()` now surfaces every statement result. When the server returns a single statement result it returns the result directly; when it returns multiple results it returns a `tuple[Value, ...]`. This fixes the silent-discard behaviour reported in [issue #232](https://github.com/surrealdb/surrealdb.py/issues/232).  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query`  | `str`  | The SurrealQL query string to execute.  |  
| `vars`  |  dict[str, [Value](https://surrealdb.com/docs/reference/python/api/types/#value)] | None  |  Variables to bind into the query. Defaults to `None`.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value) for a single-statement query, otherwise `tuple[Value, ...]` of statement results.
The returned object also exposes `.into(cls)` which maps the N statement results positionally onto the fields of a dataclass (or any class accepting keyword arguments).
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-12)
Single statement (async)

```python
result = await db.query(
    "SELECT * FROM users WHERE age > $min_age",
    {"min_age": 18},
)
```

Multi-statement returns tuple

```python
people, count = await db.query(
    "SELECT * FROM person; SELECT count() FROM person GROUP ALL"
)
```

Map results onto a dataclass

```python
from dataclasses import dataclass

@dataclass
class Stats:
    people: list
    count: list

stats = await db.query(
    "SELECT * FROM person; SELECT count() FROM person GROUP ALL"
).into(Stats)
```

Synchronous lazy builder

```python
# The sync builder auto-executes when consumed (indexed, iterated, compared, etc.).
# For fire-and-forget statements call .execute() explicitly.
people = db.query("SELECT * FROM users")
print(len(people))
db.query("DELETE temp_data;").execute()
```

###  `.query_raw()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#query-raw)
Runs a set of SurrealQL statements and returns the raw RPC response, including per-statement results, statuses, and execution times. Unlike `.query()`, errors in individual statements are returned in the response rather than raised as exceptions.
Method Syntax

```python
db.query_raw(query, params)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query`  | `str`  | The SurrealQL query string to execute.  |  
| `params`  |  dict[str, [Value](https://surrealdb.com/docs/reference/python/api/types/#value)] | None  |  Variables to bind into the query. Defaults to `None`.  |  
**Returns:** `dict[str, Any]`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-13)
Synchronous

```python
raw = db.query_raw(
    "CREATE users SET name = $name; SELECT * FROM users;",
    {"name": "John"},
)

for statement in raw["result"]:
    print(statement["status"], statement["time"])
```

Asynchronous

```python
raw = await db.query_raw(
    "CREATE users SET name = $name; SELECT * FROM users;",
    {"name": "John"},
)
```

* * *
##  CRUD methods[](https://surrealdb.com/docs/reference/python/api/core/surreal#crud-methods)
Important
**v3.0 builder pattern.** `.create()`, `.update()`, `.upsert()`, `.delete()`, and `.insert()` return an awaitable (async) or lazy (sync) builder. The builder exposes chainable clause methods that map directly to SurrealQL clauses:
Calling `.create(record, data)` is sugar for `.create(record).content(data)`. The standalone `.merge()`, `.patch()`, and `.insert_relation()` methods from v2.x have been removed.
###  `.select()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#select)
Selects all records in a table, or a specific record by its ID.
Method Syntax

```python
db.select(record)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record`  | [RecordIdType](https://surrealdb.com/docs/reference/python/api/types/#recordidtype)  |  A table name ( `str`) or a `RecordID`to select.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-14)
Synchronous

```python
users = db.select("users")

user = db.select(RecordID("users", "john"))
```

Asynchronous

```python
users = await db.select("users")

user = await db.select(RecordID("users", "john"))
```

###  `.create()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#create)
Creates a record in a table. If a `RecordID` is passed, the record is created with that specific ID. If a table name is passed, a random ID is generated.
Method Syntax

```python
db.create(record, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record`  | [RecordIdType](https://surrealdb.com/docs/reference/python/api/types/#recordidtype)  |  The table name or `RecordID`to create.  |  
| `data`  |  [Value](https://surrealdb.com/docs/reference/python/api/types/#value)| None  |  The record data. Defaults to `None`.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-15)
Synchronous

```python
user = db.create("users", {
    "name": "John",
    "email": "john@example.com",
})

product = db.create(RecordID("products", "apple"), {
    "name": "Apple",
    "price": 1.50,
})
```

Asynchronous

```python
user = await db.create("users", {
    "name": "John",
    "email": "john@example.com",
})
```

###  `.update()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#update)
Replaces the entire record with the given data. Fields not present in `data` are removed.
Method Syntax

```python
db.update(record, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record`  | [RecordIdType](https://surrealdb.com/docs/reference/python/api/types/#recordidtype)  |  The table name or `RecordID`to update.  |  
| `data`  |  [Value](https://surrealdb.com/docs/reference/python/api/types/#value)| None  |  The new record data. Defaults to `None`.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-16)
Synchronous

```python
db.update(RecordID("users", "john"), {
    "name": "John Doe",
    "email": "john.doe@example.com",
})
```

Asynchronous

```python
await db.update(RecordID("users", "john"), {
    "name": "John Doe",
    "email": "john.doe@example.com",
})
```

###  `.upsert()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#upsert)
Updates an existing record or creates a new one if it does not exist. Replaces the entire record content.
Method Syntax

```python
db.upsert(record, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record`  | [RecordIdType](https://surrealdb.com/docs/reference/python/api/types/#recordidtype)  |  The table name or `RecordID`to upsert.  |  
| `data`  |  [Value](https://surrealdb.com/docs/reference/python/api/types/#value)| None  |  The record data. Defaults to `None`.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-17)
Synchronous

```python
db.upsert(RecordID("users", "john"), {
    "name": "John",
    "email": "john@example.com",
})
```

Asynchronous

```python
await db.upsert(RecordID("users", "john"), {
    "name": "John",
    "email": "john@example.com",
})
```

###  `.merge` clause[](https://surrealdb.com/docs/reference/python/api/core/surreal#merge)
`.merge(data)` is a builder clause method - chain it on `.update()`, `.upsert()`, or `.create()`. It compiles to `... MERGE $data` and preserves any existing fields not present in `data`.
Synchronous

```python
db.update(RecordID("users", "john")).merge({"age": 32})
```

Asynchronous

```python
await db.update(RecordID("users", "john")).merge({"age": 32})
```

###  `.patch` clause[](https://surrealdb.com/docs/reference/python/api/core/surreal#patch)
`.patch(data)` is a builder clause method - chain it on `.update()`, `.upsert()`, or `.create()`. It compiles to `... PATCH $data` and applies JSON Patch operations.
Synchronous

```python
db.update(RecordID("users", "john")).patch([
    {"op": "replace", "path": "/email", "value": "new@example.com"},
    {"op": "add", "path": "/verified", "value": True},
])
```

Asynchronous

```python
await db.update(RecordID("users", "john")).patch([
    {"op": "replace", "path": "/email", "value": "new@example.com"},
])
```

###  `.delete()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#delete)
Deletes all records in a table, or a specific record by its ID.
Method Syntax

```python
db.delete(record)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record`  | [RecordIdType](https://surrealdb.com/docs/reference/python/api/types/#recordidtype)  |  The table name or `RecordID`to delete.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-18)
Synchronous

```python
db.delete(RecordID("users", "john"))

db.delete("temp_data")
```

Asynchronous

```python
await db.delete(RecordID("users", "john"))
```

* * *
##  Insert methods[](https://surrealdb.com/docs/reference/python/api/core/surreal#insert-methods)
###  `.insert()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#insert)
Inserts one or more records into a table.
Method Syntax

```python
db.insert(table, data)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `str | Table`  | The table to insert into.  |  
| `data`  | [Value](https://surrealdb.com/docs/reference/python/api/types/#value)  | A single record dict or a list of record dicts to insert.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-19)
Synchronous

```python
db.insert("users", {"name": "Alice", "email": "alice@example.com"})

db.insert("users", [
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"},
])
```

Asynchronous

```python
await db.insert("users", {"name": "Alice", "email": "alice@example.com"})
```

###  Inserting relations[](https://surrealdb.com/docs/reference/python/api/core/surreal#insert-relation)
The standalone `.insert_relation()` method from v2.x has been removed. Use `.insert(table, data, relation=True)` or chain `.relation()` on the insert builder to issue an `INSERT RELATION INTO` statement.
Synchronous

```python
db.insert("likes", {
    "in": RecordID("users", "alice"),
    "out": RecordID("posts", "post1"),
}, relation=True)

# Or via the builder:
db.insert("likes").relation().content({
    "in": RecordID("users", "alice"),
    "out": RecordID("posts", "post1"),
})
```

Asynchronous

```python
await db.insert("likes", {
    "in": RecordID("users", "alice"),
    "out": RecordID("posts", "post1"),
}, relation=True)
```

* * *
##  Calling functions[](https://surrealdb.com/docs/reference/python/api/core/surreal#calling-functions)
###  `.run()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#run)
Calls a SurrealDB function and returns its result. The function name typically uses the `fn::` prefix for user-defined functions or namespace prefixes for built-ins.
Method Syntax

```python
db.run(name, args, version)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `str`  |  The fully-qualified function name, e.g. `"fn::increment"`.  |  
| `args`  |  list[ [Value](https://surrealdb.com/docs/reference/python/api/types/#value)] | None  | Positional arguments forwarded to the function.  |  
| `version`  | `str | None`  | Optional function version selector.  |  
**Returns:** [`Value`](https://surrealdb.com/docs/reference/python/api/types/#value)
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-20)
Synchronous

```python
result = db.run("fn::increment", [1])
```

Asynchronous

```python
greeting = await db.run("fn::greet", ["world"])
```

* * *
##  Live queries[](https://surrealdb.com/docs/reference/python/api/core/surreal#live-queries)
Note
Live queries require a WebSocket connection (`ws://` or `wss://`). HTTP and embedded connections raise `UnsupportedFeatureError`.
###  `.live()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#live)
Initiates a live query for a table. Returns a UUID that identifies the live query and can be passed to `.subscribe_live()` and `.kill()`.
Method Syntax

```python
db.live(table, diff)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `str | Table`  | The table to watch for changes.  |  
| `diff`  | `bool`  |  If `True`, notifications include JSON Patch diffs instead of full records. Defaults to `False`.  |  
**Returns:** `UUID`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-21)
Synchronous

```python
query_uuid = db.live("users")

query_uuid = db.live("users", diff=True)
```

Asynchronous

```python
query_uuid = await db.live("users")
```

###  `.subscribe_live()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#subscribe-live)
Returns a generator that yields live query notifications for the given query UUID. Each notification is a dict containing the action (`"CREATE"`, `"UPDATE"`, `"DELETE"`), the record data, and the record ID.
Method Syntax

```python
db.subscribe_live(query_uuid)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query_uuid`  | `str | UUID`  |  The UUID of the live query returned by [`.live()`](https://surrealdb.com/docs/reference/python/api/core/surreal#live).  |  
**Returns (sync):** `Generator[dict[str, Value], None, None]`  
**Returns (async):** `AsyncGenerator[dict[str, Value], None]`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-22)
Synchronous

```python
query_uuid = db.live("users")

for notification in db.subscribe_live(query_uuid):
    print(notification["action"], notification["result"])
```

Asynchronous

```python
query_uuid = await db.live("users")

async for notification in db.subscribe_live(query_uuid):
    print(notification["action"], notification["result"])
```

###  `.kill()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#kill)
Terminates a running live query by its UUID.
Method Syntax

```python
db.kill(query_uuid)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query_uuid`  | `str | UUID`  | The UUID of the live query to kill.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-23)
Synchronous

```python
db.kill(query_uuid)
```

Asynchronous

```python
await db.kill(query_uuid)
```

* * *
##  Sessions[](https://surrealdb.com/docs/reference/python/api/core/surreal#sessions)
Note
Sessions require a WebSocket connection (`ws://` or `wss://`). HTTP and embedded connections raise `UnsupportedFeatureError`.
Sessions allow you to create isolated contexts on a single connection, each with its own namespace, database, variables, and authentication state.
###  `.new_session()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#new-session)
Creates a new isolated session on the current connection.
Method Syntax

```python
db.new_session()
```

**Returns (sync):** `BlockingSurrealSession`  
**Returns (async):** `AsyncSurrealSession`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-24)
Synchronous

```python
session = db.new_session()
session.use("other_ns", "other_db")
result = session.select("users")
```

Asynchronous

```python
session = await db.new_session()
await session.use("other_ns", "other_db")
result = await session.select("users")
```

###  `.attach()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#attach)
Attaches to the server-side session associated with this connection and returns its session ID.
Method Syntax

```python
db.attach()
```

**Returns:** `UUID`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-25)
Synchronous

```python
session_id = db.attach()
```

Asynchronous

```python
session_id = await db.attach()
```

###  `.detach()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#detach)
Detaches from a server-side session.
Method Syntax

```python
db.detach(session_id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `session_id`  | `UUID`  | The session ID to detach from.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-26)
Synchronous

```python
db.detach(session_id)
```

Asynchronous

```python
await db.detach(session_id)
```

* * *
##  Transactions[](https://surrealdb.com/docs/reference/python/api/core/surreal#transactions)
Note
Transactions require a WebSocket connection (`ws://` or `wss://`). HTTP and embedded connections raise `UnsupportedFeatureError`.
Transactions let you group multiple operations into an atomic unit. Changes are only applied when the transaction is committed, and can be rolled back with cancel.
###  `.begin()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#begin)
Begins a new transaction, optionally within a specific session.
Method Syntax

```python
db.begin(session_id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `session_id`  | `UUID | None`  |  The session to start the transaction in. If `None`, uses the default session. Defaults to `None`.  |  
**Returns:** `UUID` — the transaction ID
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-27)
Synchronous

```python
txn_id = db.begin()
```

Asynchronous

```python
txn_id = await db.begin()
```

Within a session

```python
session_id = db.attach()
txn_id = db.begin(session_id)
```

###  `.commit()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#commit)
Commits a transaction, applying all changes made within it.
Method Syntax

```python
db.commit(txn_id, session_id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `txn_id`  | `UUID`  |  The transaction ID returned by [`.begin()`](https://surrealdb.com/docs/reference/python/api/core/surreal#begin).  |  
| `session_id`  | `UUID | None`  |  The session the transaction belongs to. Defaults to `None`.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-28)
Synchronous

```python
txn_id = db.begin()
db.query("CREATE users SET name = 'Alice'")
db.commit(txn_id)
```

Asynchronous

```python
txn_id = await db.begin()
await db.query("CREATE users SET name = 'Alice'")
await db.commit(txn_id)
```

###  `.cancel()`[](https://surrealdb.com/docs/reference/python/api/core/surreal#cancel)
Cancels a transaction, discarding all changes made within it.
Method Syntax

```python
db.cancel(txn_id, session_id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `txn_id`  | `UUID`  |  The transaction ID returned by [`.begin()`](https://surrealdb.com/docs/reference/python/api/core/surreal#begin).  |  
| `session_id`  | `UUID | None`  |  The session the transaction belongs to. Defaults to `None`.  |  
**Returns:** `None`
####  Examples[](https://surrealdb.com/docs/reference/python/api/core/surreal#examples-29)
Synchronous

```python
txn_id = db.begin()
db.query("DELETE users")
db.cancel(txn_id)
```

Asynchronous

```python
txn_id = await db.begin()
await db.query("DELETE users")
await db.cancel(txn_id)
```

* * *
##  Context manager[](https://surrealdb.com/docs/reference/python/api/core/surreal#context-manager)
Both `Surreal` and `AsyncSurreal` support the context manager protocol. The connection is automatically opened on entry and closed on exit.
###  Synchronous[](https://surrealdb.com/docs/reference/python/api/core/surreal#synchronous)
Synchronous context manager

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("my_namespace", "my_database")
    db.signin({"username": "root", "password": "root"})
    users = db.select("users")
```

###  Asynchronous[](https://surrealdb.com/docs/reference/python/api/core/surreal#asynchronous)
Asynchronous context manager

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("my_namespace", "my_database")
    await db.signin({"username": "root", "password": "root"})
    users = await db.select("users")
```

* * *
##  Complete example[](https://surrealdb.com/docs/reference/python/api/core/surreal#complete-example)
Full workflow (sync)

```python
from surrealdb import Surreal, RecordID

with Surreal("ws://localhost:8000") as db:
    db.use("shop", "inventory")
    db.signin({"username": "root", "password": "root"})

    db.create("products", {"name": "Laptop", "price": 999.99})
    db.create("products", {"name": "Mouse", "price": 29.99})

    products = db.select("products")
    print("All products:", products)

    cheap = db.query(
        "SELECT * FROM products WHERE price < $max",
        {"max": 100},
    )
    print("Affordable:", cheap)

    db.update(RecordID("products", products[0]["id"].id)).merge({"stock": 50})

    db.delete(RecordID("products", products[1]["id"].id))
```

Full workflow (async)

```python
import asyncio
from surrealdb import AsyncSurreal, RecordID

async def main():
    async with AsyncSurreal("ws://localhost:8000") as db:
        await db.use("shop", "inventory")
        await db.signin({"username": "root", "password": "root"})

        await db.create("products", {"name": "Laptop", "price": 999.99})

        products = await db.select("products")
        print("Products:", products)

asyncio.run(main())
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/core/surreal#see-also)
  * •
[SurrealSession](https://surrealdb.com/docs/reference/python/api/core/surreal-session) — Session management reference
  * •
[SurrealTransaction](https://surrealdb.com/docs/reference/python/api/core/surreal-transaction) — Transaction reference
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/types) — Type aliases and value types
  * •
[Errors](https://surrealdb.com/docs/reference/python/api/errors) — Error classes reference
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb) — Connection protocols and patterns
