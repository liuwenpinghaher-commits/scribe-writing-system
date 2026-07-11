---
title: "https://surrealdb.com/docs/reference/python/api/types"
url: "https://surrealdb.com/docs/reference/python/api/types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/types

Source: https://surrealdb.com/docs/reference/python/api/types

The SDK provides type definitions and dataclasses for type-safe development. This page documents the key types used throughout the SDK.
**Source:** [types.py](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/types.py), [models.py](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/data/models.py), [url.py](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/connections/url.py)
##  Value types[](https://surrealdb.com/docs/reference/python/api/types#value-types)
###  `Value`[](https://surrealdb.com/docs/reference/python/api/types#value)
Union type representing all possible values that can be sent to or returned from SurrealDB.

```python
Value = (
    str | int | float | bool | None | bytes | UUID | Decimal
    | Table | Range | RecordID | Duration | Datetime
    | GeometryPoint | GeometryLine | GeometryPolygon
    | GeometryMultiPoint | GeometryMultiLine | GeometryMultiPolygon
    | GeometryCollection
    | dict[str, "Value"] | list["Value"]
)
```

This type is recursive: dictionaries and lists can contain nested `Value` types. See the [Data types overview](https://surrealdb.com/docs/reference/python/api/values/) for details on each SurrealDB-specific type.
* * *
###  `RecordIdType`[](https://surrealdb.com/docs/reference/python/api/types#recordidtype)
Type alias for values accepted as record or table references by CRUD methods.

```python
RecordIdType = str | Table | RecordID
```

When a `str` is passed, it is treated as a table name. Pass a [`RecordID`](https://surrealdb.com/docs/reference/python/api/values/record-id) for specific record targeting, or a [`Table`](https://surrealdb.com/docs/reference/python/api/values/table) for explicit table references.
##  Authentication types[](https://surrealdb.com/docs/reference/python/api/types#authentication-types)
###  `Tokens`[](https://surrealdb.com/docs/reference/python/api/types#tokens)
Frozen dataclass returned by `.signin()` and `.signup()`. Contains the access token and an optional refresh token.

```python
@dataclass(frozen=True)
class Tokens:
    access: str | None = None
    refresh: str | None = None
```

**Properties:**  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `access`  | `str \| None`  | The JWT access token  |  
| `refresh`  | `str \| None`  | The refresh token, if the access method was defined with `WITH REFRESH`  |  
**Example:**

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()
db.use("main", "main")

tokens = db.signin({"username": "root", "password": "root"})
print(tokens.access)
print(tokens.refresh)
```

##  Data model types[](https://surrealdb.com/docs/reference/python/api/types#data-model-types)
###  `Patch`[](https://surrealdb.com/docs/reference/python/api/types#patch)
Dataclass representing a JSON Patch operation per the [JSON Patch specification](https://jsonpatch.com/).

```python
@dataclass
class Patch:
    op: str
    path: str
    value: Any
```

**Properties:**  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `op`  | `str`  | The patch operation: `"add"`, `"remove"`, `"replace"`, `"move"`, `"copy"`, or `"test"`  |  
| `path`  | `str`  | The JSON pointer path  |  
| `value`  | `Any`  | The value for the operation  |  
* * *
###  `QueryResponse`[](https://surrealdb.com/docs/reference/python/api/types#queryresponse)
Frozen dataclass representing an HTTP query response.

```python
@dataclass(frozen=True)
class QueryResponse:
    time: str
    status: str
    result: list[dict[str, Any]]
```

**Properties:**  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `time`  | `str`  | The time the request was processed  |  
| `status`  | `str`  | The status of the request  |  
| `result`  | `list[dict[str, Any]]`  | The query results  |  
##  Connection types[](https://surrealdb.com/docs/reference/python/api/types#connection-types)
###  `UrlScheme`[](https://surrealdb.com/docs/reference/python/api/types#urlscheme)
Enum of supported connection URL schemes. The SDK uses this internally to select the appropriate connection class.

```python
class UrlScheme(Enum):
    HTTP = "http"
    HTTPS = "https"
    WS = "ws"
    WSS = "wss"
    MEM = "mem"
    FILE = "file"
    MEMORY = "memory"
    SURREALKV = "surrealkv"
```
  
| Scheme  | Connection type  | Description  |  
| --- | --- | --- |  
|  `HTTP`, `HTTPS`  | HTTP  | Short-lived stateless connections  |  
|  `WS`, `WSS`  | WebSocket  | Long-lived stateful connections with full feature support  |  
|  `MEM`, `MEMORY`  | Embedded  | In-memory database  |  
| `FILE`  | Embedded  | File-based persistent database  |  
| `SURREALKV`  | Embedded  | SurrealKV persistent database  |  
##  See also[](https://surrealdb.com/docs/reference/python/api/types#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values/) for the SurrealDB-specific type classes
  * •
[Errors](https://surrealdb.com/docs/reference/python/api/errors/) for error classes and constants
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for methods using these types
