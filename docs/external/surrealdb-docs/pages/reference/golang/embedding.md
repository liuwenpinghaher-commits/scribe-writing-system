---
title: "https://surrealdb.com/docs/reference/golang/embedding"
url: "https://surrealdb.com/docs/reference/golang/embedding"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/embedding

Source: https://surrealdb.com/docs/reference/golang/embedding

##  Setup[](https://surrealdb.com/docs/reference/golang/embedding#setup)
  1. 1.
Build surrealdb.c and set up CGO
  2. 2.
Run the command `go get github.com/surrealdb/surrealdb.c.go`
  3. 3.
Write code to connect to an embedded instance of SurrealDB.

Note
New to CGO? This module links against a C static library (libsurrealdb_c.a) at compile time. You must build surrealdb.c and set CGO_LDFLAGS to its location before go build or go test will work. Without this, the Go linker cannot find the SurrealDB symbols and the build will fail. See docs/build.md for step-by-step instructions — or use the provided Makefile which handles everything automatically (make build).
The following code shows a simple example that opens up an embedded instance in memory, defines a table and then creates and selects a `person` record that matches the `Person` struct that the output deserializes into.

```go
package main

import (
    "context"
    "fmt"
    "log"

    surrealdb "github.com/surrealdb/surrealdb.c.go"
)

type Person struct {
    ID   surrealdb.RecordID[string] `cbor:"id,omitempty"`
    Name string                     `cbor:"name"`
    Age  int64                      `cbor:"age"`
}

func main() {
    ctx := context.Background()

    db, err := surrealdb.Open(ctx, "mem://")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    db.Use(ctx, "main", "main")
    db.Query(ctx, "DEFINE TABLE person SCHEMALESS", nil)
    db.Query(ctx, "CREATE $rid CONTENT $content", map[string]any{
        "rid":     surrealdb.NewRecordID("person", "alice"),
        "content": Person{Name: "Alice", Age: 30},
    })

    results, _ := surrealdb.Query[Person](ctx, db, "SELECT * FROM person", nil)
    for _, p := range results[0].Values() {
        fmt.Printf("%s: %s (age %d)\n", p.ID, p.Name, p.Age)
    }
}
```

##  More information[](https://surrealdb.com/docs/reference/golang/embedding#more-information)
For more information on the Go bindings used for an embedded SurrealDB instance, see [this page](https://github.com/surrealdb/surrealdb.c.go/tree/main/docs) for the surrealdb.c.go repo.
Pages of particular note are:
  * •
[Storage backends](https://github.com/surrealdb/surrealdb.c.go/blob/main/docs/rocksdb.md): how to use other endpoints like `rocksdb://`.
  * •
[Linking strategy](https://github.com/surrealdb/surrealdb.c.go/blob/main/docs/internals.md)
