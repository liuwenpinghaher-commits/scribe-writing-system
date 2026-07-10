---
title: "https://surrealdb.com/docs/reference/golang/api/values/datetime"
url: "https://surrealdb.com/docs/reference/golang/api/values/datetime"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/datetime

Source: https://surrealdb.com/docs/reference/golang/api/values/datetime

The `CustomDateTime` struct wraps Go's `time.Time` and handles CBOR encoding with tag 12 as specified by SurrealDB. It preserves nanosecond precision and stores datetimes as a `[seconds, nanoseconds]` pair.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/datetime.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/datetime.go)
* * *
##  Definition[](https://surrealdb.com/docs/reference/golang/api/values/datetime#definition)

```go
type CustomDateTime struct {
    time.Time
}
```

`CustomDateTime` embeds `time.Time`, so all standard `time.Time` methods are available directly.
* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/values/datetime#methods)
###  `.String()`[](https://surrealdb.com/docs/reference/golang/api/values/datetime#string)
Returns the datetime formatted as `"2006-01-02T15:04:05Z"` in UTC.
Syntax

```go
s := dt.String()
```

**Returns:** `string`
###  `.SurrealString()`[](https://surrealdb.com/docs/reference/golang/api/values/datetime#surrealstring)
Returns the SurrealQL representation: ` '2006-01-02T15:04:05Z'`.
Syntax

```go
s := dt.SurrealString()
```

**Returns:** `string`
###  `.IsZero()`[](https://surrealdb.com/docs/reference/golang/api/values/datetime#iszero)
Returns `true` if the datetime is nil or the zero time.
Syntax

```go
zero := dt.IsZero()
```

**Returns:** `bool`
* * *
##  Usage[](https://surrealdb.com/docs/reference/golang/api/values/datetime#usage)

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

now := models.CustomDateTime{Time: time.Now()}

type Event struct {
    ID        *models.RecordID     `json:"id,omitempty"`
    CreatedAt models.CustomDateTime `json:"created_at"`
}
```

Zero-valued `CustomDateTime` is encoded as CBOR tag 6 (`NONE`).
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/datetime#see-also)
  * •
[RecordID](https://surrealdb.com/docs/reference/golang/api/values/record-id) for the record identifier type
  * •
[Duration](https://surrealdb.com/docs/reference/golang/api/values/duration) for the duration type
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using datetime values in CRUD operations
  * •
[SurrealQL datetime type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) for the underlying data model
