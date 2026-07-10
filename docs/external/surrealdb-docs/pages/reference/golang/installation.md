---
title: "https://surrealdb.com/docs/reference/golang/installation"
url: "https://surrealdb.com/docs/reference/golang/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/installation

Source: https://surrealdb.com/docs/reference/golang/installation

Install the SDK from [pkg.go.dev](https://pkg.go.dev/github.com/surrealdb/surrealdb.go) using `go get`:

```bash
go get github.com/surrealdb/surrealdb.go
```

Then import the SDK and its models package in your Go files:

```go
import (
	surrealdb "github.com/surrealdb/surrealdb.go"
	"github.com/surrealdb/surrealdb.go/pkg/models"
)
```

The `surrealdb` package contains the client, query functions, and authentication methods. The `models` package contains value types such as [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id), [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table), and [`UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid).
##  Requirements[](https://surrealdb.com/docs/reference/golang/installation#requirements)
  * •
Go `1.23` or later
  * •
SurrealDB `v2.x` or `v3.x`

##  Next steps[](https://surrealdb.com/docs/reference/golang/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/languages/golang) to build your first application
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb) for connection protocols and configuration
