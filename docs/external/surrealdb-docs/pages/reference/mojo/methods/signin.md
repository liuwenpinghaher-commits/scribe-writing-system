---
title: "https://surrealdb.com/docs/reference/mojo/methods/signin"
url: "https://surrealdb.com/docs/reference/mojo/methods/signin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/signin

Source: https://surrealdb.com/docs/reference/mojo/methods/signin

Signs in to the database with CBOR-encoded credentials. On success, the returned token is stored on the client for subsequent requests.
Method Syntax

```python
client.signin(credentials_cbor, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/signin#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `credentials_cbor`  |  The credentials, CBOR-encoded as a map, as a `List[UInt8]`.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/signin#example-usage)

```python
from surrealdb import CborCodec
from std.collections import List

var codec = CborCodec()
var pairs = List[Tuple[String, List[UInt8]]]()
pairs.append(Tuple(String("user"), codec.encode_text("root")))
pairs.append(Tuple(String("pass"), codec.encode_text("root")))

var resp = client.signin(codec.encode_map(pairs))
```

Note
`signin` operates on a stateful session, which is provided by the WebSocket transport. WebSocket support is rolling out. Over HTTP, supply credentials with the `access_token` field on `ConnectOptions`.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/signin#see-also)
  * •
[Authentication](https://surrealdb.com/docs/reference/mojo/concepts/authentication)
  * •
[`signup()`](https://surrealdb.com/docs/reference/mojo/methods/signup)
