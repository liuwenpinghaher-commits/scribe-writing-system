---
title: "https://surrealdb.com/docs/reference/mojo"
url: "https://surrealdb.com/docs/reference/mojo"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo

Source: https://surrealdb.com/docs/reference/mojo

The SurrealDB SDK for Mojo lets you connect to a SurrealDB instance from your Mojo applications and run queries, manage data, call database functions, authenticate, and subscribe to changes with live queries. It speaks both CBOR-RPC and JSON-RPC over the same `/rpc` endpoint, and ships transports for `http://`, `https://`, `ws://`, and `wss://`.
The SDK has no third-party Mojo dependencies. The transport sits on a small libc-socket layer, and TLS is backed by a thin OpenSSL FFI with certificate verification against the system root store.
Important
The SDK requires Mojo `>= 0.26.1.0, < 0.26.2.0`, and is managed with [pixi](https://pixi.sh/). The current SDK version is `0.2.0`.
Note
The SDK works with SurrealDB `3.x`, ensuring compatibility with the latest version, `v3.2.0`.
##  Getting started[](https://surrealdb.com/docs/reference/mojo#getting-started)
[Installation Install the SDK and add it to your project.](https://surrealdb.com/docs/reference/mojo/installation)[Getting started guide Connect to SurrealDB and run your first queries.](https://surrealdb.com/docs/languages/mojo)
##  Learn[](https://surrealdb.com/docs/reference/mojo#learn)
[Concepts Guides for connecting, authenticating, querying, and working with data.](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb)[API Reference Complete reference for the SDK's methods, types, and errors.](https://surrealdb.com/docs/reference/mojo/methods)
##  Choosing a client[](https://surrealdb.com/docs/reference/mojo#choosing-a-client)
The SDK provides two clients with the same surface:
  * •
`AsyncSurrealClient` for asynchronous applications.
  * •
`SurrealClient`, a thin blocking wrapper around the async client.

Async client

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
            access_token=Optional(String("Basic cm9vdDpyb290")),  # root:secret
        ),
    )

    var resp = client.query("RETURN 1 + 1;")
    if resp.is_ok():
        print("result:", resp.result.value() if resp.result else "null")
    else:
        print("error:", resp.error_message().value())
```

##  Transports[](https://surrealdb.com/docs/reference/mojo#transports)
HTTP and HTTPS are the recommended transports for everyday querying, and are the most thoroughly tested path. WebSocket (`ws://` and `wss://`) unlocks SurrealDB's stateful features: authenticated sessions, server-side transactions that span multiple requests, and live-query notifications delivered out of band.
Note
WebSocket support is rolling out. For request and response querying, including atomic multi-statement transactions, use the HTTP or HTTPS transport.
The wire format is configurable. CBOR is the default and the most compact on the wire; JSON is useful when you want to inspect traffic or proxy through a JSON-only gateway. See [Connecting to SurrealDB](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb) for the full set of options.
##  Contributing[](https://surrealdb.com/docs/reference/mojo#contributing)
To contribute to the SDK code, submit an Issue or Pull Request in the [surrealdb.mojo](https://github.com/surrealdb/surrealdb.mojo) repository. To contribute to this documentation, submit an Issue or Pull Request in the [docs.surrealdb.com](https://github.com/surrealdb/docs.surrealdb.com) repository.
##  Sources[](https://surrealdb.com/docs/reference/mojo#sources)
  * •
[GitHub repository](https://github.com/surrealdb/surrealdb.mojo)
