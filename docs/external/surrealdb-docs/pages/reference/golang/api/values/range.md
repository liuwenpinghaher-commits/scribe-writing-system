---
title: "https://surrealdb.com/docs/reference/golang/api/values/range"
url: "https://surrealdb.com/docs/reference/golang/api/values/range"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/range

Source: https://surrealdb.com/docs/reference/golang/api/values/range

The `Range` generic struct represents a SurrealDB range value with configurable bound types. Ranges can have inclusive or exclusive bounds on either end.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/range.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/range.go)
* * *
##  Definitions[](https://surrealdb.com/docs/reference/golang/api/values/range#definitions)
###  `Range`[](https://surrealdb.com/docs/reference/golang/api/values/range#range-struct)

```go
type Range[T any, TBeg Bound[T], TEnd Bound[T]] struct {
    Begin *TBeg
    End   *TEnd
}
```

CBOR tag: 49
###  `BoundIncluded`[](https://surrealdb.com/docs/reference/golang/api/values/range#boundincluded)
An inclusive bound (the value is included in the range).

```go
type BoundIncluded[T any] struct {
    Value T
}
```

CBOR tag: 50
###  `BoundExcluded`[](https://surrealdb.com/docs/reference/golang/api/values/range#boundexcluded)
An exclusive bound (the value is excluded from the range).

```go
type BoundExcluded[T any] struct {
    Value T
}
```

CBOR tag: 51
###  `Bound`[](https://surrealdb.com/docs/reference/golang/api/values/range#bound)
The constraint interface for bound types.

```go
type Bound[T any] interface {
    BoundIncluded[T] | BoundExcluded[T]
}
```

* * *
##  Related types[](https://surrealdb.com/docs/reference/golang/api/values/range#related-types)
###  `RecordRangeID`[](https://surrealdb.com/docs/reference/golang/api/values/range#recordrangeid)
A range scoped to a specific table, used for range-based record selection.

```go
type RecordRangeID[T any, TBeg Bound[T], TEnd Bound[T]] struct {
    Range[T, TBeg, TEnd]
    Table Table
}
```

* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/values/range#methods)
###  `.String()`[](https://surrealdb.com/docs/reference/golang/api/values/range#string)
Returns the string representation of the range (e.g., `1..10`, `1>..=10`).
**Returns:** `string`
###  `.GetJoinString()`[](https://surrealdb.com/docs/reference/golang/api/values/range#getjoinstring)
Returns the range operator string (e.g., `..`, `>..`, `..=`, `>..=`).
**Returns:** `string`
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/range#see-also)
  * •
[Table](https://surrealdb.com/docs/reference/golang/api/values/table) for the table name type used in `RecordRangeID`
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using ranges in queries
  * •
[SurrealQL ranges](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges) for the underlying data model
