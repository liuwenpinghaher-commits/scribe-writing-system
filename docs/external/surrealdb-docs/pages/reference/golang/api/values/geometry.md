---
title: "https://surrealdb.com/docs/reference/golang/api/values/geometry"
url: "https://surrealdb.com/docs/reference/golang/api/values/geometry"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/geometry

Source: https://surrealdb.com/docs/reference/golang/api/values/geometry

The SDK provides typed geometry structs that map to SurrealDB's GeoJSON-based geometry types. Each type handles CBOR encoding with the appropriate tag number.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/geometry.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/geometry.go)
* * *
##  Types[](https://surrealdb.com/docs/reference/golang/api/values/geometry#types)
###  `GeometryPoint`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrypoint)
A geographic point with longitude and latitude coordinates.

```go
type GeometryPoint struct {
    Longitude float64
    Latitude  float64
}
```

CBOR tag: 88
####  Methods[](https://surrealdb.com/docs/reference/golang/api/values/geometry#methods)
  * •
`.GetCoordinates()` — returns `[2]float64{Longitude, Latitude}`

####  Examples[](https://surrealdb.com/docs/reference/golang/api/values/geometry#examples)

```go
point := models.GeometryPoint{Longitude: -0.118, Latitude: 51.509}
```

###  `GeometryLine`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometryline)
A line consisting of two or more points.

```go
type GeometryLine []GeometryPoint
```

CBOR tag: 89
###  `GeometryPolygon`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrypolygon)
A polygon consisting of one or more closed line rings.

```go
type GeometryPolygon []GeometryLine
```

CBOR tag: 90
###  `GeometryMultiPoint`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrymultipoint)
A collection of points.

```go
type GeometryMultiPoint []GeometryPoint
```

CBOR tag: 91
###  `GeometryMultiLine`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrymultiline)
A collection of lines.

```go
type GeometryMultiLine []GeometryLine
```

CBOR tag: 92
###  `GeometryMultiPolygon`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrymultipolygon)
A collection of polygons.

```go
type GeometryMultiPolygon []GeometryPolygon
```

CBOR tag: 93
###  `GeometryCollection`[](https://surrealdb.com/docs/reference/golang/api/values/geometry#geometrycollection)
A heterogeneous collection of geometry objects.

```go
type GeometryCollection []any
```

CBOR tag: 94
* * *
##  Usage[](https://surrealdb.com/docs/reference/golang/api/values/geometry#usage)

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

type Location struct {
    ID       *models.RecordID      `json:"id,omitempty"`
    Name     string                `json:"name"`
    Position models.GeometryPoint  `json:"position"`
    Boundary models.GeometryPolygon `json:"boundary"`
}

line := models.GeometryLine{
    {Longitude: -0.118, Latitude: 51.509},
    {Longitude: -0.076, Latitude: 51.508},
}

polygon := models.GeometryPolygon{
    models.GeometryLine{
        {Longitude: -0.12, Latitude: 51.50},
        {Longitude: -0.08, Latitude: 51.50},
        {Longitude: -0.08, Latitude: 51.52},
        {Longitude: -0.12, Latitude: 51.52},
        {Longitude: -0.12, Latitude: 51.50},
    },
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/geometry#see-also)
  * •
[RecordID](https://surrealdb.com/docs/reference/golang/api/values/record-id) for the record identifier type
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using geometry values in CRUD operations
  * •
[SurrealQL geometry types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries) for the underlying data model
