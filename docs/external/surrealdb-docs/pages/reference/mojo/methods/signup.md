---
title: "https://surrealdb.com/docs/reference/mojo/methods/signup"
url: "https://surrealdb.com/docs/reference/mojo/methods/signup"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/signup

Source: https://surrealdb.com/docs/reference/mojo/methods/signup

Creates a new record-access account from CBOR-encoded credentials and signs in.
Method Syntax

```python
client.signup(credentials_cbor, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/signup#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `credentials_cbor`  |  The signup payload, CBOR-encoded as a map, as a `List[UInt8]`. It names the access method along with the namespace, database, and any variables it expects.  |  
| `session`  | An optional session id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/signup#example-usage)

```python
from surrealdb import CborCodec
from std.collections import List

var codec = CborCodec()
var pairs = List[Tuple[String, List[UInt8]]]()
pairs.append(Tuple(String("namespace"), codec.encode_text("test")))
pairs.append(Tuple(String("database"), codec.encode_text("test")))
pairs.append(Tuple(String("access"), codec.encode_text("user")))
pairs.append(Tuple(String("email"), codec.encode_text("chiru@example.com")))
pairs.append(Tuple(String("pass"), codec.encode_text("changeme")))

var resp = client.signup(codec.encode_map(pairs))
```

Note
`signup` operates on a stateful session, which is provided by the WebSocket transport. WebSocket support is rolling out.
###  See also[](https://surrealdb.com/docs/reference/mojo/methods/signup#see-also)
  * •
[Authentication](https://surrealdb.com/docs/reference/mojo/concepts/authentication)
  * •
[`signin()`](https://surrealdb.com/docs/reference/mojo/methods/signin)
