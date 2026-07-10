---
title: "https://surrealdb.com/docs/languages/mojo"
url: "https://surrealdb.com/docs/languages/mojo"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/mojo

Source: https://surrealdb.com/docs/languages/mojo

The Mojo SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/mojo#1-install-the-sdk)
Install the SDK, then import `AsyncSurrealClient` and `ConnectOptions` into your Mojo program.

```python
from surrealdb import AsyncSurrealClient, ConnectOptions
from std.collections import Optional
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/mojo#2-connect-to-surrealdb)
Create a client and connect over HTTP, passing your namespace, database, and access token through `ConnectOptions`.

```python
def main():
    var client = AsyncSurrealClient()
    _ = client.connect(
        "http://localhost:8000/rpc",
        ConnectOptions(
            namespace=Optional(String("test")),
            database=Optional(String("test")),
            access_token=Optional(String("Basic cm9vdDpyb290")),  # root:secret
        ),
    )
```

Supported connection protocols include:
  * •
HTTP

The `access_token` here is the base64 encoding of `root:secret`, sent as HTTP Basic auth.
##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/mojo#3-inserting-data-into-surrealdb)
The client exposes convenience methods that wrap common SurrealQL statements. Each takes the table or record to act on and a JSON document. Use `create` to insert a new record.

```python
client.create("person", '{ "name": "Chiru", "age": 30 }')
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/mojo#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/mojo#selecting-records)
Use `select` to retrieve a record or all records in a table.

```python
client.select("person:chiru")
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/mojo#running-surrealql-queries)
Use `query` to run any SurrealQL statement.

```python
var resp = client.query("SELECT * FROM person WHERE age > 18;")
```

Every call returns an `RpcResponse`. Check `is_ok()` before reading the result, and inspect the error fields otherwise.

```python
if resp.is_ok():
    if resp.result:
        print(resp.result.value())
else:
    print("code:", resp.error_code().value())
    print("message:", resp.error_message().value())
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/mojo#5-closing-the-connection)
When you are finished, close the connection to release its resources.

```python
client.close()
```

##  Next steps[](https://surrealdb.com/docs/languages/mojo#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connecting to SurrealDB Learn about transports, wire formats, and TLS.](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb)[Executing queries Work with responses and convenience methods.](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries)[Authentication Sign in and manage credentials.](https://surrealdb.com/docs/reference/mojo/concepts/authentication)[API Reference Complete reference for all methods available in the Mojo SDK.](https://surrealdb.com/docs/reference/mojo/methods)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Mojo SDK reference](https://surrealdb.com/docs/reference/mojo).
