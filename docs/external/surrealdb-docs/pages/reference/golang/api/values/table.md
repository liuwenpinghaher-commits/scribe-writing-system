---
title: "https://surrealdb.com/docs/reference/golang/api/values/table"
url: "https://surrealdb.com/docs/reference/golang/api/values/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/table

Source: https://surrealdb.com/docs/reference/golang/api/values/table

The `Table` type is a named string type representing a SurrealDB table name. It is used with data manipulation functions like `Select`, `Create`, `Insert`, and `Delete` to target all records in a table.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/table.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/table.go)
* * *
##  Definition[](https://surrealdb.com/docs/reference/golang/api/values/table#definition)

```go
type Table string
```

* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/values/table#methods)
###  `.String()`[](https://surrealdb.com/docs/reference/golang/api/values/table#string)
Returns the table name as a plain string.
Syntax

```go
s := table.String()
```

**Returns:** `string`
* * *
##  Usage[](https://surrealdb.com/docs/reference/golang/api/values/table#usage)

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

persons, err := surrealdb.Select[[]Person](ctx, db, models.Table("persons"))

_, err = surrealdb.Insert[Person](ctx, db, models.Table("persons"), data)
```

`Table` is encoded as CBOR tag 7 when sent over the wire.
* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/table#see-also)
  * •
[RecordID](https://surrealdb.com/docs/reference/golang/api/values/record-id) for targeting specific records
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using tables in CRUD operations
