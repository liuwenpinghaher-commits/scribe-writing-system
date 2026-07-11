---
title: "https://surrealdb.com/docs/reference/mojo/methods/call"
url: "https://surrealdb.com/docs/reference/mojo/methods/call"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/call

Source: https://surrealdb.com/docs/reference/mojo/methods/call

Runs a SurrealQL function, built-in or custom, and returns its result.
Method Syntax

```python
client.call(fn_name, args, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/call#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `fn_name`  |  The function name, for example `fn::greet`or `time::now`.  |  
| `args`  |  The function arguments, each CBOR-encoded, as a `List[List[UInt8]]`.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/call#example-usage)

```python
from surrealdb import CborCodec
from std.collections import List

var codec = CborCodec()
var args = List[List[UInt8]]()
args.append(codec.encode_text("Chiru"))

var resp = client.call("fn::greet", args)
```
