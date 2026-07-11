---
title: "https://surrealdb.com/docs/reference/javascript/api/values"
url: "https://surrealdb.com/docs/reference/javascript/api/values"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values

Source: https://surrealdb.com/docs/reference/javascript/api/values

The JavaScript SDK provides custom classes for SurrealDB-specific data types, ensuring type safety and data integrity when working with the database. For a conceptual overview with usage examples and best practices, see the [Value types concept page](https://surrealdb.com/docs/reference/javascript/concepts/value-types).
##  Custom data type classes[](https://surrealdb.com/docs/reference/javascript/api/values#custom-data-type-classes)
  * •
[**RecordId**](https://surrealdb.com/docs/reference/javascript/api/values/record-id) - Type-safe record identifiers with table and ID components
    * ◦
`new RecordId(table, id)` - Create record ID
    * ◦
Also includes `RecordIdRange` for querying ranges
  * •
[**Table**](https://surrealdb.com/docs/reference/javascript/api/values/table) - Type-safe table references
    * ◦
`new Table(name)` - Create typed table reference
    * ◦
Used in SELECT, CREATE, UPDATE, DELETE operations
  * •
[**DateTime**](https://surrealdb.com/docs/reference/javascript/api/values/datetime) - Datetime values with nanosecond precision
    * ◦
`DateTime.now()` - Current datetime
    * ◦
`new DateTime(string)` - Parse from ISO string
    * ◦
`.toDate()` - Convert to JavaScript Date
  * •
[**Duration**](https://surrealdb.com/docs/reference/javascript/api/values/duration) - Time duration with support for multiple units
    * ◦
`new Duration('5h30m')` - Parse from string
    * ◦
`.milliseconds` - Get duration in milliseconds
  * •
[**Decimal**](https://surrealdb.com/docs/reference/javascript/api/values/decimal) - Arbitrary precision decimal numbers
    * ◦
`new Decimal('19.99')` - Create precise decimal
    * ◦
Preserves precision during operations
  * •
[**Uuid**](https://surrealdb.com/docs/reference/javascript/api/values/uuid) - Universally unique identifiers
    * ◦
`Uuid.v4()` - Generate random UUID
    * ◦
`Uuid.v7()` - Generate time-ordered UUID
  * •
[**Range**](https://surrealdb.com/docs/reference/javascript/api/values/range) - Generic range values for numeric and date ranges
  * •
[**FileRef**](https://surrealdb.com/docs/reference/javascript/api/values/file-ref) - References to files stored in SurrealDB
    * ◦
`.bucket` - Storage bucket name
    * ◦
`.key` - File key within the bucket

##  Geometric types[](https://surrealdb.com/docs/reference/javascript/api/values#geometric-types)
  * •
[**Geometry**](https://surrealdb.com/docs/reference/javascript/api/values/geometry) - Spatial/geometric data types
    * ◦
`GeometryPoint` - Single point
    * ◦
`GeometryLine` - Line between points
    * ◦
`GeometryPolygon` - Polygon shape
    * ◦
`GeometryMultiPoint`, `GeometryMultiLine`, `GeometryMultiPolygon`
    * ◦
`GeometryCollection` - Mixed geometry collection

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values#see-also)
  * •
[Value types concept page](https://surrealdb.com/docs/reference/javascript/concepts/value-types) - Usage guide with type mapping, examples, and best practices
  * •
[SurrealQL data types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types) - Database data model
  * •
[Utilities](https://surrealdb.com/docs/reference/javascript/concepts/utilities) - Comparing and converting values
