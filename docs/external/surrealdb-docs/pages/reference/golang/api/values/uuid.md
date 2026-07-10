---
title: "https://surrealdb.com/docs/reference/golang/api/values/uuid"
url: "https://surrealdb.com/docs/reference/golang/api/values/uuid"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/uuid

Source: https://surrealdb.com/docs/reference/golang/api/values/uuid

The `UUID` struct wraps the `github.com/gofrs/uuid` package and handles CBOR encoding with tag 37 as specified by SurrealDB. It supports both UUID v4 and v7 values.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/uuid.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/uuid.go)
* * *
##  Definition[](https://surrealdb.com/docs/reference/golang/api/values/uuid#definition)

```go
type UUID struct {
    uuid.UUID
}
```

`UUID` embeds `github.com/gofrs/uuid.UUID`, so all methods from that package are available directly.
* * *
##  Related types[](https://surrealdb.com/docs/reference/golang/api/values/uuid#related-types)
###  `UUIDString`[](https://surrealdb.com/docs/reference/golang/api/values/uuid#uuidstring)
A string type for UUID values that prefer string representation. Encoded with CBOR tag 9.

```go
type UUIDString string
```

* * *
##  CBOR encoding[](https://surrealdb.com/docs/reference/golang/api/values/uuid#cbor-encoding)
`UUID` is encoded as CBOR tag 37 containing the 16-byte binary representation. `UUIDString` is encoded as CBOR tag 9 containing the string representation.
* * *
##  Usage[](https://surrealdb.com/docs/reference/golang/api/values/uuid#usage)
`UUID` is returned by live query functions and session/transaction creation. You typically receive it from the SDK rather than constructing it manually.

```go
liveID, err := surrealdb.Live(ctx, db, models.Table("persons"), false)
fmt.Println(liveID.String())
```

* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/uuid#see-also)
  * •
[Live queries](https://surrealdb.com/docs/reference/golang/concepts/live-queries) for live query UUIDs
  * •
[Session](https://surrealdb.com/docs/reference/golang/api/core/session#id) for session UUIDs
  * •
[Transaction](https://surrealdb.com/docs/reference/golang/api/core/transaction#id) for transaction UUIDs
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[SurrealQL UUID type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) for the underlying data model
