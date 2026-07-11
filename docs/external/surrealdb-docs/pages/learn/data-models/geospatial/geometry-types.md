---
title: "https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types"
url: "https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types

Source: https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types

SurrealDB’s `geometry` type follows the [GeoJSON](https://en.wikipedia.org/wiki/GeoJSON) model in which both (and only) a `type` and `coordinates` field must be specified. A tuple shorthand (e.g. `(50.0, 75.7)`) is also accepted when creating a `point`.
##  Coordinate order[](https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types#coordinate-order)
Points are defined with **longitude before latitude** , as required by the GeoJSON spec. Many map services display latitude first, so be sure to confirm the order when ingesting external data.

```surql
-- Tuple shorthand for a point (lon, lat)
CREATE city:london SET centre = (-0.118092, 51.509865);

-- Full GeoJSON object form
CREATE city:london SET centre = {
    type: "Point",
    coordinates: [-0.118092, 51.509865],
};
```

See the [Geometries](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries) reference for `LineString`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon`, and `Collection`, including examples for each type.
##  Why geometry types matter[](https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types#why-geometry-types-matter)
  * •
**Points** capture a single location (venues, vehicles, users).
  * •
**Line strings** represent paths (routes, boundaries along a corridor).
  * •
**Polygons** represent regions (service areas, countries, floor plans projected to the globe).

Choosing the right type makes spatial predicates (`INTERSECTS`, `CONTAINS`, and so on) accurate and keeps indexes meaningful when you add spatial indexing in your schema.
