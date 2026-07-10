---
title: "https://surrealdb.com/docs/reference/rest-api/cbor-protocol"
url: "https://surrealdb.com/docs/reference/rest-api/cbor-protocol"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rest-api/cbor-protocol

Source: https://surrealdb.com/docs/reference/rest-api/cbor-protocol

SurrealDB extends the [CBOR](https://www.rfc-editor.org/rfc/rfc8949.html) protocol with a number of custom tags to support the full range of data types available in SurrealDB. This document provides an overview of the custom tags and their respective values.
##  References:[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#references)
  * •
CBOR Protocol - [RFC 8949](https://www.rfc-editor.org/rfc/rfc8949.html)
  * •
CBOR Official Tags - [Iana](https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml)

##  Custom tags[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#custom-tags)  
| Tag  | Value  |  
| --- | --- |  
| [Tag 0](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-0)  | [Datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) ([RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) string)  |  
| [Tag 6](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-6)  | [`NONE`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/none-and-null#none-values)  |  
| [Tag 7](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-7)  | Table name  |  
| [Tag 8](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-8)  | [Record ID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids)  |  
| [Tag 9](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-9)  | [UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) (string)  |  
| [Tag 10](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-10)  | [Decimal](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#decimal-numbers) (string)  |  
| [Tag 12](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-12)  | [Datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) (compact)  |  
| [Tag 13](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-13)  | [Duration](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) (string)  |  
| [Tag 14](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-14)  | [Duration](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) (compact)  |  
| [Tag 15](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-15)  | [Future](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures) (compact)  |  
| [Tag 37](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-37)  | [UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) (binary)  |  
| [Tag 49](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-49)  | [Range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges)  |  
| [Tag 50](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-50)  | [Included Bound](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges)  |  
| [Tag 51](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-51)  | [Excluded Bound](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges)  |  
| [Tag 88](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-88)  | [Geometry Point](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#point)  |  
| [Tag 89](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-89)  | [Geometry Line](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#linestring)  |  
| [Tag 90](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-90)  | [Geometry Polygon](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#polygon)  |  
| [Tag 91](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-91)  | [Geometry MultiPoint](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipoint)  |  
| [Tag 92](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-92)  | [Geometry MultiLine](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multilinestring)  |  
| [Tag 93](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-93)  | [Geometry MultiPolygon](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipolygon)  |  
| [Tag 94](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-94)  | [Geometry Collection](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries)  |  
###  Tag 0[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-0)
A [datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) represented in an [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) string.
Adopted from the [Iana Specification](https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml).
**Note:** [Tag 12](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-12) is preferred and always sent back by SurrealDB.
###  Tag 6[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-6)
Represents a [`NONE`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/none-and-null#none-values) value. The value passed to the tagged value is `null`, as it cannot be empty.
###  Tag 7[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-7)
A table name, represented as a string.
###  Tag 8[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-8)
A [Record ID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids), represented as an two-value array, containing a table part (string) and an id part (string, number, object or array).
Instead of an two-value array, SurrealDB also accepts a string with a string-formatted Record ID. A string Record ID will never be sent back from SurrealDB, however.
###  Tag 9[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-9)
A [UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) represented in a string format.
**Note:** [Tag 37](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-37) is preferred and always sent back by SurrealDB.
###  Tag 10[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-10)
A [Decimal](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#decimal-numbers) represented in a string format.
###  Tag 12[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-12)
A [Datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) represented in a two-value array, containing seconds (number) and optionally nanoseconds (number).
###  Tag 13[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-13)
A [Duration](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) represented in a string format.
**Note:** [Tag 14](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-14) is preferred and always sent back by SurrealDB.
###  Tag 14[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-14)
A [Duration](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) represented in a two-value array, containing optionally seconds (number) and optionally nanoseconds (number). An empty array will be considered a duration of 0.
###  Tag 15[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-15)
A [Future](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures) represented as a string containing the uncomputed SurrealQL query or expression. The value transported needs to be returned in an `Object` in a `{}`, this will also be the format you receive it in from SurrealDB this will allow for it to be computed when accessed or used within a query.
###  Tag 37[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-37)
A [UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) represented in a binary format. Please reference (<https://docs.rs/uuid/latest/uuid/struct.Uuid.html#method.as_bytes>).
Adopted from the [Iana Specification](https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml).
###  Tag 49[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-49)
A [Range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges) represented as a two-value array containing optional bounds. Each bound can be either null (for unbounded), or a tagged value using either Tag 50 (included bound) or Tag 51 (excluded bound). 
The bounds follow SurrealQL's range syntax where `..` represents a range, `>..` represents an excluded lower bound, and `..=` represents an included upper bound.
###  Tag 50[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-50)
An included bound value used within [Range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges) bounds. The tagged value represents an inclusive boundary (equivalent to `..=` for upper bounds in SurrealQL range syntax).
###  Tag 51[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-51)
An excluded bound value used within [Range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges) bounds. The tagged value represents an exclusive boundary (equivalent to `>..` for lower bounds in SurrealQL range syntax).
###  Tag 88[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-88)
A [Geometry Point](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#point) represented by a two-value array containing a longitude (float) and latitude (float). 
###  Tag 89[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-89)
A [Geometry Line](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#linestring) represented by an array with two or more points ([Tag 88](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-88)).
###  Tag 90[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-90)
A [Geometry Polygon](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#polygon) represented by an array with one or more closed lines ([Tag 89](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-89)).
If the lines are not closed, meaning that the first and last point are equal, then SurrealDB will automatically suffix the line with it's first point.
###  Tag 91[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-91)
A [Geometry MultiPoint](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipoint) represented by an array with one or more points ([Tag 88](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-88)).
###  Tag 92[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-92)
A [Geometry MultiLine](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multilinestring) represented by an array with one or more lines ([Tag 89](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-89)).
###  Tag 93[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-93)
A [Geometry MultiPolygon](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipolygon) represented by an array with one or more polygons ([Tag 90](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-90)).
###  Tag 94[](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-94)
A [Geometry Collection](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries) represented by an array with one or more geometry values ([Tag 88](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-88), [Tag 89](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-89), [Tag 90](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-90), [Tag 91](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-91), [Tag 92](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-92), [Tag 93](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-93) or [Tag 94](https://surrealdb.com/docs/reference/rest-api/cbor-protocol#tag-94)).
