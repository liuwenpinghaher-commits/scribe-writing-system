---
title: "https://surrealdb.com/docs/reference/mojo/concepts/executing-queries"
url: "https://surrealdb.com/docs/reference/mojo/concepts/executing-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/executing-queries

Source: https://surrealdb.com/docs/reference/mojo/concepts/executing-queries

The primary way to run SurrealQL with the Mojo SDK is `query()`, which sends one or more statements and returns an `RpcResponse`.

```python
var resp = client.query("SELECT * FROM person WHERE age > 18;")
```

##  Reading the response[](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries#reading-the-response)
Every call returns an `RpcResponse`. Check `is_ok()` before reading the result. The decoded text representation is available on `result`, and the raw bytes on `result_raw`.

```python
if resp.is_ok():
    # CBOR-decoded text representation for convenience
    if resp.result:
        print(resp.result.value())
    # Raw CBOR bytes if you need them
    print("bytes:", len(resp.result_raw))
else:
    print("code:", resp.error_code().value())
    print("message:", resp.error_message().value())
```

`RpcResponse` exposes the following:  
| Member  | Description  |  
| --- | --- |  
| `is_ok()`  |  Returns `True`when there is no error.  |  
| `is_error()`  |  Returns `True`when the response carries an error.  |  
| `has_result()`  |  Returns `True`when a result is present.  |  
| `result`  |  The decoded text representation, as `Optional[String]`.  |  
| `result_raw`  |  The raw CBOR or JSON bytes, as `List[UInt8]`.  |  
| `error_message()`  |  The error message, as `Optional[String]`.  |  
| `error_code()`  |  The error code, as `Optional[Int]`.  |  
##  Convenience methods[](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries#convenience-methods)
The SDK wraps the most common statements so you do not have to write the SurrealQL by hand. Each takes the table or record to act on and a JSON document.

```python
client.create("person", '{ "name": "Chiru", "age": 30 }')
client.select("person:chiru")
client.update("person:chiru", '{ "age": 31 }')
client.delete("person:chiru")
client.insert("person", '[{ "name": "Alice" }, { "name": "Bob" }]')
```

These build a SurrealQL statement under the hood. For example, `create("person", data)` runs `CREATE person CONTENT ;`. See the method reference for the full list, including [`upsert`](/docs/reference/mojo/methods/upsert), [`merge`](/docs/reference/mojo/methods/merge), [`patch`](/docs/reference/mojo/methods/patch), and [`insert_relation`](/docs/reference/mojo/methods/insert-relation).
##  Bindings[](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries#bindings)
`query()` accepts a `bindings_json` argument.

```python
var resp = client.query("SELECT * FROM person;", "{}")
```

Note
A dedicated API for passing arbitrary CBOR bindings is on the roadmap. Today, CBOR connections support the default `"{}"`, while JSON-RPC connections accept raw JSON strings via `bindings_json`.
##  Sessions and transactions[](https://surrealdb.com/docs/reference/mojo/concepts/executing-queries#sessions-and-transactions)
Each `query` is wrapped in its own implicit transaction by the server. To run several statements atomically, use [`transaction_multi`](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi), or the [transactions](https://surrealdb.com/docs/reference/mojo/concepts/transactions) concept page for the full picture.
