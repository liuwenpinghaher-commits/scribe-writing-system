---
title: "https://surrealdb.com/docs/reference/golang/api/values/duration"
url: "https://surrealdb.com/docs/reference/golang/api/values/duration"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/duration

Source: https://surrealdb.com/docs/reference/golang/api/values/duration

The `CustomDuration` struct wraps Go's `time.Duration` and handles CBOR encoding with tag 14 as specified by SurrealDB. It stores durations as a `[seconds, nanoseconds]` pair and formats them using SurrealDB's human-readable syntax (e.g., `1d2h30m`).
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/duration.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/duration.go)
* * *
##  Definition[](https://surrealdb.com/docs/reference/golang/api/values/duration#definition)

```go
type CustomDuration struct {
    time.Duration
}
```

`CustomDuration` embeds `time.Duration`, so all standard `time.Duration` methods are available directly.
* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/values/duration#methods)
###  `.String()`[](https://surrealdb.com/docs/reference/golang/api/values/duration#string)
Returns the duration formatted in SurrealDB syntax (e.g., `2h30m`, `1d12h`, `500ms`).
Syntax

```go
s := dur.String()
```

**Returns:** `string`
###  `.ToCustomDurationString()`[](https://surrealdb.com/docs/reference/golang/api/values/duration#tocustomdurationstring)
Converts to a `CustomDurationString` value.
Syntax

```go
ds := dur.ToCustomDurationString()
```

**Returns:** `CustomDurationString`
* * *
##  Related types[](https://surrealdb.com/docs/reference/golang/api/values/duration#related-types)
###  `CustomDurationString`[](https://surrealdb.com/docs/reference/golang/api/values/duration#customdurationstring)
A string type for durations in SurrealDB format (e.g., `"1d2h30m"`). Encoded with CBOR tag 13.

```go
type CustomDurationString string
```

####  Methods[](https://surrealdb.com/docs/reference/golang/api/values/duration#methods-1)
  * •
`.String()` — returns the string value
  * •
`.ToDuration()` — parses into `time.Duration`
  * •
`.ToCustomDuration()` — converts to `CustomDuration`

* * *
##  Helper functions[](https://surrealdb.com/docs/reference/golang/api/values/duration#helper-functions)
###  `FormatDuration`[](https://surrealdb.com/docs/reference/golang/api/values/duration#formatduration)
Formats nanoseconds into SurrealDB duration syntax.
Syntax

```go
s := models.FormatDuration(ns)
```

**Returns:** `string`
###  `ParseDuration`[](https://surrealdb.com/docs/reference/golang/api/values/duration#parseduration)
Parses a SurrealDB duration string into nanoseconds.
Syntax

```go
ns, err := models.ParseDuration("1d2h30m")
```

**Returns:** `(int64, error)`
Supported units: `y`, `w`, `d`, `h`, `m`, `s`, `ms`, `us`/`µs`, `ns`.
* * *
##  Usage[](https://surrealdb.com/docs/reference/golang/api/values/duration#usage)

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

dur := models.CustomDuration{Duration: 2*time.Hour + 30*time.Minute}
fmt.Println(dur.String()) // "2h30m"

type Session struct {
    ID      *models.RecordID      `json:"id,omitempty"`
    Timeout models.CustomDuration  `json:"timeout"`
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/duration#see-also)
  * •
[RecordID](https://surrealdb.com/docs/reference/golang/api/values/record-id) for the record identifier type
  * •
[CustomDateTime](https://surrealdb.com/docs/reference/golang/api/values/datetime) for the datetime type
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using duration values in CRUD operations
  * •
[SurrealQL duration type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations) for the underlying data model
