---
title: "https://surrealdb.com/docs/reference/mojo/concepts/value-types"
url: "https://surrealdb.com/docs/reference/mojo/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/concepts/value-types

Source: https://surrealdb.com/docs/reference/mojo/concepts/value-types

The Mojo SDK ships CBOR encoders and decoders for the SurrealDB tagged value types. These types live in the `surrealdb.value` module and map directly onto the values SurrealDB stores and returns.
##  Record identifiers[](https://surrealdb.com/docs/reference/mojo/concepts/value-types#record-identifiers)
A `RecordId` pairs a table with a record key. Its `to_string()` returns the canonical `table:id` form.

```python
from surrealdb import RecordId, Table

var id = RecordId(Table("person"), "chiru")
print(id.to_string())  # person:chiru
```

`Table` wraps a table name on its own.
##  Scalar types[](https://surrealdb.com/docs/reference/mojo/concepts/value-types#scalar-types)  
| Type  | Fields  | Description  |  
| --- | --- | --- |  
| `Uuid`  | `value`  | A UUID string.  |  
| `DateTime`  |  `seconds`, `nanos`  | A point in time, split into seconds and nanoseconds.  |  
| `Duration`  |  `seconds`, `nanos`  | A length of time.  |  
| `Decimal`  | `value`  | An arbitrary-precision decimal, held as a string.  |  
| `FileRef`  |  `bucket`, `key`  | A reference to a file in a bucket.  |  
| `SurrealSet`  | `items`  | A set of values.  |  
| `FutureValue`  | `body`  | A computed (future) value, held as its expression body.  |  
##  Ranges[](https://surrealdb.com/docs/reference/mojo/concepts/value-types#ranges)
A `RangeValue` describes a bounded range. Its bounds are `BoundIncluded` or `BoundExcluded`, set on the `begin_included`, `begin_excluded`, `end_included`, and `end_excluded` fields.
##  Geometry[](https://surrealdb.com/docs/reference/mojo/concepts/value-types#geometry)
The SDK models the full GeoJSON family:
  * •
`GeometryPoint` with `longitude` and `latitude`.
  * •
`GeometryLine` and `GeometryPolygon`.
  * •
`GeometryMultiPoint`, `GeometryMultiLine`, and `GeometryMultiPolygon`.
  * •
`GeometryCollection`, holding points, lines, and polygons together.

```python
from surrealdb import GeometryPoint

var here = GeometryPoint(-0.118092, 51.509865)
```
