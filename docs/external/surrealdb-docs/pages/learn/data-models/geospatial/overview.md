---
title: "https://surrealdb.com/docs/learn/data-models/geospatial/overview"
url: "https://surrealdb.com/docs/learn/data-models/geospatial/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/geospatial/overview

Source: https://surrealdb.com/docs/learn/data-models/geospatial/overview

A geospatial database is specifically designed (or extended) to store and query data related to the Earth’s surface. Rather than just focusing on numeric or textual data, these systems handle coordinates, polygons, linestrings, and other spatial objects that define locations and shapes. Queries typically revolve around spatial relationships, like finding points within a boundary, measuring distances, or detecting intersections between shapes.
Historically, geospatial capabilities were mostly the domain of specialised systems such as PostGIS (an extension of PostgreSQL) or dedicated GIS software. SurrealDB offers geospatial features to unify location-related data with other data models (relational, document, graph, vector, and so on) under one roof with no extensions required.
In this section, you’ll learn how to think like a geospatial database user: represent location with geometry or geography types, index and query with spatial predicates, and combine SurrealDB’s [geo functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo) with the rest of your data.
##  Core concepts of geospatial data[](https://surrealdb.com/docs/learn/data-models/geospatial/overview#core-concepts-of-geospatial-data)
  * •
Coordinate reference systems (CRS): Coordinates can be stored in different projections. A common choice is WGS84 for latitude and longitude (EPSG:4326), used by GPS. Other systems exist for local or projected coordinates.
  * •
Geometry types: Including points, linestrings, polygons, and multi-variants—see [Geometry types](https://surrealdb.com/docs/learn/data-models/geospatial/geometry-types).
  * •
Spatial relationships: Operations such as contains, intersects, within, touches, or disjoint—see [Spatial queries](https://surrealdb.com/docs/learn/data-models/geospatial/spatial-queries).
  * •
Distance and proximity: Measuring distance between geometries, buffers, and geohash-style encodings—see [Distance and proximity](https://surrealdb.com/docs/learn/data-models/geospatial/distance-and-proximity).

For reference types and function signatures, see [Geometries](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries) and [Geo functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo).
