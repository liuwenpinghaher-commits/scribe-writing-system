---
title: "https://surrealdb.com/docs/reference/golang/concepts/value-types"
url: "https://surrealdb.com/docs/reference/golang/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/value-types

Source: https://surrealdb.com/docs/reference/golang/concepts/value-types

The Go SDK communicates with SurrealDB using CBOR (Concise Binary Object Representation) rather than JSON. The SDK provides Go types that map to SurrealDB's data model and handle CBOR serialization transparently when used in structs or maps.
This page covers the mapping between SurrealDB types and Go types, and how to work with the most common value types.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/value-types#api-references)  
| Type  | Description  |  
| --- | --- |  
| [`models.RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id)  | A unique record identifier with table name and ID  |  
| [`models.Table`](https://surrealdb.com/docs/reference/golang/api/values/table)  | A table name  |  
| [`models.UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid)  | A UUID v4 or v7 value  |  
| [`models.CustomDateTime`](https://surrealdb.com/docs/reference/golang/api/values/datetime)  | A datetime value wrapping time.Time  |  
| [`models.CustomDuration`](https://surrealdb.com/docs/reference/golang/api/values/duration)  | A duration value wrapping time.Duration  |  
| [`models.GeometryPoint`](https://surrealdb.com/docs/reference/golang/api/values/geometry)  | A geographic point with longitude and latitude  |  
| [`models.Range`](https://surrealdb.com/docs/reference/golang/api/values/range)  | A range with inclusive or exclusive bounds  |  
##  Type mapping[](https://surrealdb.com/docs/reference/golang/concepts/value-types#type-mapping)
The following table shows how SurrealDB types map to Go types when using the SDK.  
| SurrealQL type  | Go type  | CBOR tag  |  
| --- | --- | --- |  
| `null`  | `nil`  | -  |  
| `none`  |  `models.CustomNil` / `models.None`  | 6  |  
| `bool`  | `bool`  | -  |  
| `int`  |  `int`, `int64`, etc.  | -  |  
| `float`  | `float64`  | -  |  
| `decimal`  | `models.DecimalString`  | 10  |  
| `string`  | `string`  | -  |  
| `bytes`  | `[]byte`  | -  |  
| `datetime`  | `models.CustomDateTime`  | 12  |  
| `duration`  | `models.CustomDuration`  | 14  |  
| `uuid`  | `models.UUID`  | 37  |  
| `record`  | `models.RecordID`  | 8  |  
| `array`  |  `[]any` or typed slice  | -  |  
| `object`  |  `map[string]any` or struct  | -  |  
| `geometry<point>`  | `models.GeometryPoint`  | 88  |  
| `geometry<line>`  | `models.GeometryLine`  | 89  |  
| `geometry<polygon>`  | `models.GeometryPolygon`  | 90  |  
| `geometry<multipoint>`  | `models.GeometryMultiPoint`  | 91  |  
| `geometry<multiline>`  | `models.GeometryMultiLine`  | 92  |  
| `geometry<multipolygon>`  | `models.GeometryMultiPolygon`  | 93  |  
| `geometry<collection>`  | `models.GeometryCollection`  | 94  |  
##  Working with record IDs[](https://surrealdb.com/docs/reference/golang/concepts/value-types#working-with-record-ids)
Use [`models.NewRecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) to construct a `RecordID`, or receive them from query results. The ID can be any CBOR-serializable value (string, integer, array, etc.).

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

id := models.NewRecordID("persons", "tobie")

numericID := models.NewRecordID("events", 42)
```

To parse a record ID from a string like `"persons:tobie"`, use `ParseRecordID`:

```go
id, err := models.ParseRecordID("persons:tobie")
```

When defining structs for database records, use `*models.RecordID` for the ID field:

```go
type Person struct {
	ID      *models.RecordID `json:"id,omitempty"`
	Name    string           `json:"name"`
	Surname string           `json:"surname"`
}
```

##  Working with datetimes[](https://surrealdb.com/docs/reference/golang/concepts/value-types#working-with-datetimes)
[`CustomDateTime`](https://surrealdb.com/docs/reference/golang/api/values/datetime) wraps Go's `time.Time` and handles CBOR encoding with nanosecond precision.

```go
now := models.CustomDateTime{Time: time.Now()}
```

You can use all standard `time.Time` methods directly on a `CustomDateTime` value, since it embeds `time.Time`.
##  Working with durations[](https://surrealdb.com/docs/reference/golang/concepts/value-types#working-with-durations)
[`CustomDuration`](https://surrealdb.com/docs/reference/golang/api/values/duration) wraps Go's `time.Duration` with SurrealDB-compatible formatting (e.g., `1d2h30m`).

```go
dur := models.CustomDuration{Duration: 2*time.Hour + 30*time.Minute}
fmt.Println(dur.String()) // "2h30m"
```

Use `CustomDurationString` when you need the string representation directly, and call `.ToCustomDuration()` to convert back.
##  Working with geometry types[](https://surrealdb.com/docs/reference/golang/concepts/value-types#working-with-geometry-types)
The SDK provides types for all SurrealDB geometry values. [`GeometryPoint`](https://surrealdb.com/docs/reference/golang/api/values/geometry) is the most common:

```go
point := models.GeometryPoint{Longitude: -0.118, Latitude: 51.509}
```

Other geometry types compose `GeometryPoint`:

```go
line := models.GeometryLine{
	{Longitude: -0.118, Latitude: 51.509},
	{Longitude: -0.076, Latitude: 51.508},
}

polygon := models.GeometryPolygon{line}
```

##  Using None[](https://surrealdb.com/docs/reference/golang/concepts/value-types#using-none)
SurrealDB distinguishes between `null` (SQL NULL) and `none` (absence of a value). Use `models.None` to represent the absence of a value:

```go
surrealdb.Create[any](ctx, db, models.Table("test"), map[string]any{
	"field": models.None,
})
```

##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/value-types#learn-more)
  * •
[RecordID reference](https://surrealdb.com/docs/reference/golang/api/values/record-id) for detailed constructors and methods
  * •
[UUID reference](https://surrealdb.com/docs/reference/golang/api/values/uuid) for UUID types
  * •
[DateTime reference](https://surrealdb.com/docs/reference/golang/api/values/datetime) for datetime handling
  * •
[Duration reference](https://surrealdb.com/docs/reference/golang/api/values/duration) for duration types and parsing
  * •
[Geometry reference](https://surrealdb.com/docs/reference/golang/api/values/geometry) for all geometry types
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) for the underlying type system
