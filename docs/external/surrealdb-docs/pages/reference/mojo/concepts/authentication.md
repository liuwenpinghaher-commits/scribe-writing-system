---
title: "https://surrealdb.com/docs/reference/mojo/concepts/authentication"
url: "https://surrealdb.com/docs/reference/mojo/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/authentication

Source: https://surrealdb.com/docs/reference/mojo/concepts/authentication

The Mojo SDK authenticates in one of two ways: with an access token supplied on the connection, or with the `signin` RPC over a stateful WebSocket session.
##  Access tokens[](https://surrealdb.com/docs/reference/mojo/concepts/authentication#access-tokens)
The `access_token` field on `ConnectOptions` is placed in the `Authorization` header. If the value already starts with `Bearer `, `Basic `, or `Digest `, it is passed through verbatim. Otherwise the SDK treats it as a raw JWT and prepends `Bearer `.

```python
# Basic auth (root user, dev fixtures)
ConnectOptions(access_token=Optional(String("Basic cm9vdDpyb290")))

# JWT from a previous signin
ConnectOptions(access_token=Optional(String("Bearer eyJhbGciOi...")))

# Raw JWT (the SDK prepends "Bearer ")
ConnectOptions(access_token=Optional(String("eyJhbGciOi...")))
```

This is the recommended approach for the HTTP and HTTPS transports.
##  Signing in with credentials[](https://surrealdb.com/docs/reference/mojo/concepts/authentication#signing-in-with-credentials)
Over a WebSocket session, you can authenticate with the `signin` RPC. Credentials are encoded as a CBOR map with `CborCodec`. On success, `signin()` stores the returned token on the client for subsequent requests.

```python
from surrealdb import AsyncSurrealClient, CborCodec, ConnectOptions
from std.collections import Optional, List

def main():
    var client = AsyncSurrealClient()
    _ = client.connect(
        "ws://localhost:8000/rpc",
        ConnectOptions(
            namespace=Optional(String("test")),
            database=Optional(String("test")),
        ),
    )

    # Encode the credentials map {"user": "root", "pass": "root"}.
    var codec = CborCodec()
    var pairs = List[Tuple[String, List[UInt8]]]()
    pairs.append(Tuple(String("user"), codec.encode_text("root")))
    pairs.append(Tuple(String("pass"), codec.encode_text("root")))
    _ = client.signin(codec.encode_map(pairs))
    client.use("test", "test")
```

Note
`signin`, `signup`, `authenticate`, and `invalidate` operate on a stateful session, which is provided by the WebSocket transport. WebSocket support is rolling out.
##  Other auth methods[](https://surrealdb.com/docs/reference/mojo/concepts/authentication#other-auth-methods)
  * •
`signup(credentials_cbor)` creates a new record-access account and signs in.
  * •
`authenticate(token)` authenticates the current connection with a token, and stores it on the client.
  * •
`invalidate()` clears the current token and invalidates the session.

```python
client.authenticate("eyJhbGciOi...")
client.invalidate()
```

See the method reference for [`signin`](https://surrealdb.com/docs/reference/mojo/methods/signin), [`signup`](https://surrealdb.com/docs/reference/mojo/methods/signup), [`authenticate`](https://surrealdb.com/docs/reference/mojo/methods/authenticate), and [`invalidate`](https://surrealdb.com/docs/reference/mojo/methods/invalidate).
