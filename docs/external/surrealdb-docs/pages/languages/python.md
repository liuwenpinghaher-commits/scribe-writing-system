---
title: "https://surrealdb.com/docs/languages/python"
url: "https://surrealdb.com/docs/languages/python"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/python

Source: https://surrealdb.com/docs/languages/python

The Python SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/python#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/python/installation) to install the SDK as a dependency in your project. Once installed, import the SDK to start using it.
SynchronousAsynchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
```

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
```

The `Surreal` and `AsyncSurreal` factory functions accept a connection URL and return the appropriate connection class based on the protocol.
##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/python#2-connect-to-surrealdb)
You can use the `.connect()` method to open the connection, then `.use()` to select a namespace and database, and `.signin()` to authenticate.
Supported connection protocols include:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived stateful connections
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections
  * •
**Embedded** (`mem://`, `file://`, `surrealkv://`) for in-process databases

SynchronousAsynchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()
db.use("company_name", "project_name")
db.signin({"username": "root", "password": "root"})
```

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
await db.connect()
await db.use("company_name", "project_name")
await db.signin({"username": "root", "password": "root"})
```

You can also use a context manager to automatically close the connection when you are done.
SynchronousAsynchronous

```python
with Surreal("ws://localhost:8000") as db:
    db.use("company_name", "project_name")
    db.signin({"username": "root", "password": "root"})
```

```python
async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("company_name", "project_name")
    await db.signin({"username": "root", "password": "root"})
```

##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/python#3-inserting-data-into-surrealdb)
Once connected, you can use the `.create()` method to create records. Pass a table name or a `RecordID` as the first argument and the record data as the second.
SynchronousAsynchronous

```python
from surrealdb import RecordID

user = db.create("users", {
    "name": "John",
    "email": "john@example.com",
    "age": 32,
})

product = db.create(RecordID("products", "apple"), {
    "name": "Apple",
    "price": 1.50,
    "category": "fruit",
})
```

```python
from surrealdb import RecordID

user = await db.create("users", {
    "name": "John",
    "email": "john@example.com",
    "age": 32,
})

product = await db.create(RecordID("products", "apple"), {
    "name": "Apple",
    "price": 1.50,
    "category": "fruit",
})
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/python#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/python#selecting-records)
The `.select()` method retrieves all records from a table, or a single record by its `RecordID`.
SynchronousAsynchronous

```python
users = db.select("users")

apple = db.select(RecordID("products", "apple"))
```

```python
users = await db.select("users")

apple = await db.select(RecordID("products", "apple"))
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/python#running-surrealql-queries)
For more advanced use cases, you can use the `.query()` method to run [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements directly. Use the `vars` parameter to safely pass dynamic values.
SynchronousAsynchronous

```python
result = db.query(
    "SELECT name, price FROM products WHERE price < $max_price ORDER BY price",
    {"max_price": 5.00},
)
```

```python
result = await db.query(
    "SELECT name, price FROM products WHERE price < $max_price ORDER BY price",
    {"max_price": 5.00},
)
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/python#5-closing-the-connection)
Always close the connection when you are done to release resources. If you use a context manager, this happens automatically.
SynchronousAsynchronous

```python
db.close()
```

```python
await db.close()
```

##  Next steps[](https://surrealdb.com/docs/languages/python#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connection management Learn how to manage your database connections, including protocols and context managers.](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb)[Authentication Read more about authentication and how to integrate it into your application.](https://surrealdb.com/docs/reference/python/concepts/authentication)[Data manipulation Learn how to create, read, update, and delete records using the SDK.](https://surrealdb.com/docs/reference/python/concepts/data-manipulation)[API Reference Complete reference for all classes, methods, types, and errors.](https://surrealdb.com/docs/reference/python/api/core/surreal)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Python SDK reference](https://surrealdb.com/docs/reference/python).
