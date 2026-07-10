---
title: "https://surrealdb.com/docs/reference/python/api/values/geometry"
url: "https://surrealdb.com/docs/reference/python/api/values/geometry"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/geometry

Source: https://surrealdb.com/docs/reference/python/api/values/geometry

The SDK provides GeoJSON-compatible geometry types for working with SurrealDB's spatial data. All geometry classes extend the `Geometry` base class.
Import

```python
from surrealdb import (
    GeometryPoint,
    GeometryLine,
    GeometryPolygon,
    GeometryMultiPoint,
    GeometryMultiLine,
    GeometryMultiPolygon,
    GeometryCollection,
)
```

Individual types can also be imported from `surrealdb.data.types.geometry`.
* * *
##  `GeometryPoint`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrypoint)
A single geographic point defined by longitude and latitude.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#point-constructor)
Syntax

```python
GeometryPoint(longitude, latitude)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `longitude`  | `float`  | The longitude coordinate.  |  
| `latitude`  | `float`  | The latitude coordinate.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples)

```python
point = GeometryPoint(-0.1278, 51.5074)
```

* * *
##  `GeometryLine`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometryline)
A line defined by two or more points.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#line-constructor)
Syntax

```python
GeometryLine(points)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `points`  | `list[GeometryPoint]`  | An ordered list of points that define the line.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-1)

```python
line = GeometryLine([
    GeometryPoint(-0.1278, 51.5074),
    GeometryPoint(-3.1883, 55.9533),
])
```

* * *
##  `GeometryPolygon`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrypolygon)
A polygon defined by one or more linear rings. The first ring is the exterior boundary; any subsequent rings are interior holes. Rings must be closed — the first and last point must be identical, following the GeoJSON specification.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#polygon-constructor)
Syntax

```python
GeometryPolygon(rings)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `rings`  | `list[GeometryLine]`  | A list of linear rings. The first is the exterior ring; others are holes.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-2)

```python
polygon = GeometryPolygon([
    GeometryLine([
        GeometryPoint(0.0, 0.0),
        GeometryPoint(1.0, 0.0),
        GeometryPoint(1.0, 1.0),
        GeometryPoint(0.0, 1.0),
        GeometryPoint(0.0, 0.0),
    ]),
])
```

* * *
##  `GeometryMultiPoint`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrymultipoint)
A collection of points.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#multipoint-constructor)
Syntax

```python
GeometryMultiPoint(points)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `points`  | `list[GeometryPoint]`  | A list of points.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-3)

```python
multi_point = GeometryMultiPoint([
    GeometryPoint(-0.1278, 51.5074),
    GeometryPoint(-3.1883, 55.9533),
    GeometryPoint(-1.8904, 52.4862),
])
```

* * *
##  `GeometryMultiLine`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrymultiline)
A collection of lines.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#multiline-constructor)
Syntax

```python
GeometryMultiLine(lines)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `lines`  | `list[GeometryLine]`  | A list of lines.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-4)

```python
multi_line = GeometryMultiLine([
    GeometryLine([
        GeometryPoint(0.0, 0.0),
        GeometryPoint(1.0, 1.0),
    ]),
    GeometryLine([
        GeometryPoint(2.0, 2.0),
        GeometryPoint(3.0, 3.0),
    ]),
])
```

* * *
##  `GeometryMultiPolygon`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrymultipolygon)
A collection of polygons.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#multipolygon-constructor)
Syntax

```python
GeometryMultiPolygon(polygons)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `polygons`  | `list[GeometryPolygon]`  | A list of polygons.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-5)

```python
multi_polygon = GeometryMultiPolygon([
    GeometryPolygon([
        GeometryLine([
            GeometryPoint(0.0, 0.0),
            GeometryPoint(1.0, 0.0),
            GeometryPoint(1.0, 1.0),
            GeometryPoint(0.0, 1.0),
            GeometryPoint(0.0, 0.0),
        ]),
    ]),
])
```

* * *
##  `GeometryCollection`[](https://surrealdb.com/docs/reference/python/api/values/geometry#geometrycollection)
A heterogeneous collection of geometry objects. Unlike the other multi-types, a `GeometryCollection` can contain a mix of different geometry types.
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/geometry#collection-constructor)
Syntax

```python
GeometryCollection(geometries)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `geometries`  | `list[Geometry]`  | A list of geometry objects of any type.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/geometry#examples-6)

```python
collection = GeometryCollection([
    GeometryPoint(-0.1278, 51.5074),
    GeometryLine([
        GeometryPoint(0.0, 0.0),
        GeometryPoint(1.0, 1.0),
    ]),
])
```

* * *
##  Usage[](https://surrealdb.com/docs/reference/python/api/values/geometry#usage)

```python
from surrealdb import Surreal, GeometryPoint

db = Surreal("ws://localhost:8000")
db.connect()
db.use("my_ns", "my_db")
db.signin({"username": "root", "password": "root"})

db.create("locations", {
    "name": "London",
    "coordinates": GeometryPoint(-0.1278, 51.5074),
})

result = db.query("""
    SELECT * FROM locations
    WHERE geo::distance(coordinates, $point) < 50000
""", {
    "point": GeometryPoint(-0.1180, 51.5099),
})
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/geometry#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values) — All SDK data types
  * •
[RecordID](https://surrealdb.com/docs/reference/python/api/values/record-id) — Record identifier
  * •
[SurrealQL Geometry Functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo) — Geospatial query functions
