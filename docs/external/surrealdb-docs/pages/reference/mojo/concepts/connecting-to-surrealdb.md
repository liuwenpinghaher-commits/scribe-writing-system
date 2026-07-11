---
title: "https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb

The Mojo SDK connects to a SurrealDB instance with `connect()`, which takes an endpoint URL and an optional `ConnectOptions`. The URL scheme selects the transport.

```python
from surrealdb import AsyncSurrealClient, ConnectOptions
from std.collections import Optional

def main():
    var client = AsyncSurrealClient()
    _ = client.connect(
        "http://localhost:8000/rpc",
        ConnectOptions(
            namespace=Optional(String("test")),
            database=Optional(String("test")),
            access_token=Optional(String("Basic cm9vdDpyb290")),
        ),
    )
```

`connect()` returns a `Bool`. The endpoint path is `/rpc`.
##  Transports[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#transports)
The SDK ships transports for four schemes:  
| Scheme  | Transport  | Notes  |  
| --- | --- | --- |  
| `http://`  | HTTP/1.1  | Request and response querying. The most thoroughly tested path.  |  
| `https://`  | HTTP/1.1 over TLS  | Build with `-D HTTPS=1`. See [TLS](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#tls).  |  
| `ws://`  | WebSocket  | Stateful sessions, server-side transactions, and live queries.  |  
| `wss://`  | WebSocket over TLS  | Build with `-D HTTPS=1`.  |  
Note
WebSocket support is rolling out. For request and response querying, including atomic multi-statement transactions, use the HTTP or HTTPS transport.
##  Connection options[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#connection-options)
`ConnectOptions` carries the namespace, database, credentials, and wire format for the connection.  
| Field  | Description  |  
| --- | --- |  
| `namespace`  |  The namespace to use. Sent as the `Surreal-NS`header.  |  
| `database`  |  The database to use. Sent as the `Surreal-DB`header.  |  
| `access_token`  |  The credential placed in the `Authorization`header. See [Authentication](https://surrealdb.com/docs/reference/mojo/concepts/authentication).  |  
| `tls_insecure`  |  Disables TLS certificate verification. Dev fixtures only. Defaults to `False`.  |  
| `format`  |  `RpcFormat.CBOR`(default) or `RpcFormat.JSON`.  |  
The `Surreal-NS` and `Surreal-DB` headers are sent automatically when `namespace` and `database` are set.
##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
You can also switch the namespace and database on an open connection with `use()`:

```python
client.use("test", "test")
```

##  Wire format: CBOR or JSON[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#wire-format-cbor-or-json)
Both protocols use the same `/rpc` endpoint and the same RPC methods. Pick the wire format with `ConnectOptions.format`:

```python
from surrealdb import AsyncSurrealClient, ConnectOptions, RpcFormat
from std.collections import Optional

def main():
    var client = AsyncSurrealClient()
    _ = client.connect(
        "http://localhost:8000/rpc",
        ConnectOptions(
            namespace=Optional(String("test")),
            database=Optional(String("test")),
            access_token=Optional(String("Basic cm9vdDpyb290")),
            format=RpcFormat.JSON,  # or RpcFormat.CBOR (default)
        ),
    )
    var resp = client.query("RETURN 1 + 1;")
```

Switching `format` swaps the `Content-Type` and `Accept` headers (`application/json` versus `application/cbor`) and the codec used to encode and decode the RPC envelope. Everything else stays the same.
CBOR is the default because it is what the SurrealDB server uses internally and the most compact on the wire. JSON is useful when you want to inspect traffic in DevTools, match the SurrealDB JavaScript SDK behaviour, or proxy through a JSON-only gateway.
##  TLS[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#tls)
Certificates are validated against the system root store by default. For self-signed dev fixtures, set `tls_insecure=True`:

```python
ConnectOptions(
    namespace=Optional(String("test")),
    access_token=Optional(String("Basic cm9vdDpyb290")),
    tls_insecure=True,  # never use in production
)
```

For the build flags required to connect over `https://` or `wss://`, see [Build with HTTPS](https://surrealdb.com/docs/reference/mojo/installation#build-with-https).
##  Connection state[](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb#connection-state)
Two helpers report the state of the connection and the features the active transport supports:

```python
if client.is_connected():
    var caps = client.capabilities()
```

`capabilities()` returns an `EngineCapabilities` describing which RPC features the active transport supports (live queries, sessions, server-side transactions, and the API endpoint). The client checks these flags before issuing a request, and raises an `UnsupportedFeatureError` rather than sending a request the server would reject.
Close the connection when you are done:

```python
client.close()
```
