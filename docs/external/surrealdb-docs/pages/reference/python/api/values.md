---
title: "https://surrealdb.com/docs/reference/python/api/values"
url: "https://surrealdb.com/docs/reference/python/api/values"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values

Source: https://surrealdb.com/docs/reference/python/api/values

The Python SDK provides custom classes that map SurrealDB types to Python. These classes are used throughout the SDK for parameters and return values. Standard Python types like `str`, `int`, `float`, `bool`, `None`, `bytes`, `dict`, and `list` are also used directly where they map naturally to SurrealDB types.
##  `Value` type[](https://surrealdb.com/docs/reference/python/api/values#value)
The `Value` union type represents any value that can be sent to or received from SurrealDB.
Type Definition

```python
Value = (
    str | int | float | bool | None | bytes | UUID | Decimal
    | Table | Range | RecordID | Duration | Datetime
    | GeometryPoint | GeometryLine | GeometryPolygon
    | GeometryMultiPoint | GeometryMultiLine | GeometryMultiPolygon
    | GeometryCollection | dict[str, "Value"] | list["Value"]
)
```

##  Type mapping[](https://surrealdb.com/docs/reference/python/api/values#type-mapping)  
| Python Type  | SurrealDB Type  | Notes  |  
| --- | --- | --- |  
| `str`  | `string`  |   |  
| `int`  | `int`  |   |  
| `float`  | `float`  |   |  
| `bool`  | `bool`  |   |  
| `None`  |  `NONE` / `NULL`  |   |  
| `bytes`  | `bytes`  |   |  
| `UUID`  | `uuid`  | From `uuid` standard library  |  
| `Decimal`  | `decimal`  | From `decimal` standard library  |  
| `dict`  | `object`  | Keys must be strings  |  
| `list`  | `array`  |   |  
| [`RecordID`](https://surrealdb.com/docs/reference/python/api/values/record-id)  | `record`  | Table name + identifier  |  
| [`Table`](https://surrealdb.com/docs/reference/python/api/values/table)  | table reference  | Table name wrapper  |  
| [`Duration`](https://surrealdb.com/docs/reference/python/api/values/duration)  | `duration`  | Nanosecond precision  |  
| [`Datetime`](https://surrealdb.com/docs/reference/python/api/values/datetime)  | `datetime`  | ISO 8601 string  |  
| [`Range`](https://surrealdb.com/docs/reference/python/api/values/range)  | `range`  | Inclusive/exclusive bounds  |  
| [`Geometry*`](https://surrealdb.com/docs/reference/python/api/values/geometry)  | `geometry`  | GeoJSON-compatible types  |  
##  `RecordIdType` type[](https://surrealdb.com/docs/reference/python/api/values#recordidtype)
Many SDK methods accept a `RecordIdType`, which allows passing a table name, a `Table` object, or a `RecordID`.
Type Definition

```python
RecordIdType = str | Table | RecordID
```

##  `Tokens` type[](https://surrealdb.com/docs/reference/python/api/values#tokens)
Authentication methods return a `Tokens` string alias.
Type Definition

```python
Tokens = str
```

##  Custom types[](https://surrealdb.com/docs/reference/python/api/values#custom-types)
  * •
[`RecordID`](https://surrealdb.com/docs/reference/python/api/values/record-id) — Record identifier with table name and ID components
  * •
[`Table`](https://surrealdb.com/docs/reference/python/api/values/table) — Table name wrapper for type-safe references
  * •
[`Datetime`](https://surrealdb.com/docs/reference/python/api/values/datetime) — Datetime wrapper for SurrealDB datetime values
  * •
[`Duration`](https://surrealdb.com/docs/reference/python/api/values/duration) — Duration with nanosecond precision and unit conversion
  * •
[`Range`](https://surrealdb.com/docs/reference/python/api/values/range) — Range type with inclusive and exclusive bounds
  * •
[`Geometry`](https://surrealdb.com/docs/reference/python/api/values/geometry) — GeoJSON-compatible geometry types for spatial data

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/python/api/core/surreal) — Connection and query methods
  * •
[Errors](https://surrealdb.com/docs/reference/python/api/errors) — Error classes reference
