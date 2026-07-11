---
title: "https://surrealdb.com/docs/reference/mojo/methods/set"
url: "https://surrealdb.com/docs/reference/mojo/methods/set"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/set

Source: https://surrealdb.com/docs/reference/mojo/methods/set

Assigns a value to a parameter for the connection, so you can reference it as `$name` in subsequent queries.
Method Syntax

```python
client.set(name, value_cbor, session)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/set#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `name`  |  The parameter name, without the leading `$`.  |  
| `value_cbor`  |  The value, CBOR-encoded as a `List[UInt8]`.  |  
| `session`  | An optional session id.  |  
###  Convenience wrappers[](https://surrealdb.com/docs/reference/mojo/methods/set#convenience-wrappers)
For common scalar types, the SDK provides wrappers that encode the value for you:
  * •
`set_string(name, value, session)`
  * •
`set_int(name, value, session)`
  * •
`set_bool(name, value, session)`

###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/set#example-usage)

```python
client.set_string("name", "Chiru")
client.set_int("age", 30)

var resp = client.query("SELECT * FROM person WHERE name = $name AND age >= $age;")
```

To encode a value by hand, use `CborCodec`:

```python
from surrealdb import CborCodec

var codec = CborCodec()
client.set("name", codec.encode_text("Chiru"))
```

###  See also[](https://surrealdb.com/docs/reference/mojo/methods/set#see-also)
  * •
[`unset()`](https://surrealdb.com/docs/reference/mojo/methods/unset)
