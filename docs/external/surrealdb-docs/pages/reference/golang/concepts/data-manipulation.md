---
title: "https://surrealdb.com/docs/reference/golang/concepts/data-manipulation"
url: "https://surrealdb.com/docs/reference/golang/concepts/data-manipulation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/data-manipulation

Source: https://surrealdb.com/docs/reference/golang/concepts/data-manipulation

The Go SDK provides generic top-level functions for common CRUD operations on records and tables. These functions work with [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db), [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session), and [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction) through the [`sendable`](https://surrealdb.com/docs/reference/golang/api/types#sendable) constraint, and return typed results through Go generics.
This page covers how to target tables and records, and how to select, create, insert, update, merge, patch, and delete data.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#api-references)  
| Function  | Description  |  
| --- | --- |  
| [`surrealdb.Select[T](ctx, s, what)`](https://surrealdb.com/docs/reference/golang/api/core/db#select)  | Selects all records from a table, or a specific record  |  
| [`surrealdb.Create[T](ctx, s, what, data)`](https://surrealdb.com/docs/reference/golang/api/core/db#create)  | Creates a new record with optional data  |  
| [`surrealdb.Insert[T](ctx, s, table, data)`](https://surrealdb.com/docs/reference/golang/api/core/db#insert)  | Inserts one or multiple records into a table  |  
| [`surrealdb.InsertRelation[T](ctx, s, rel)`](https://surrealdb.com/docs/reference/golang/api/core/db#insertrelation)  | Inserts a relation record between two records  |  
| [`surrealdb.Relate[T](ctx, s, rel)`](https://surrealdb.com/docs/reference/golang/api/core/db#relate)  | Creates a relation with an auto-generated ID  |  
| [`surrealdb.Update[T](ctx, s, what, data)`](https://surrealdb.com/docs/reference/golang/api/core/db#update)  | Replaces the entire content of a record or all records in a table  |  
| [`surrealdb.Upsert[T](ctx, s, what, data)`](https://surrealdb.com/docs/reference/golang/api/core/db#upsert)  | Creates a record if it does not exist, or replaces it entirely  |  
| [`surrealdb.Merge[T](ctx, s, what, data)`](https://surrealdb.com/docs/reference/golang/api/core/db#merge)  | Merges data into a record, preserving unmentioned fields  |  
| [`surrealdb.Patch(ctx, s, what, patches)`](https://surrealdb.com/docs/reference/golang/api/core/db#patch)  | Applies JSON Patch operations to a record or table  |  
| [`surrealdb.Delete[T](ctx, s, what)`](https://surrealdb.com/docs/reference/golang/api/core/db#delete)  | Deletes a specific record or all records from a table  |  
##  Targeting tables and records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#targeting-tables-and-records)
Most data manipulation functions accept a `what` parameter that determines the scope of the operation. You can pass a [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table) to target all records in a table, or a [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) to target a specific record.

```go
import "github.com/surrealdb/surrealdb.go/pkg/models"

all, err := surrealdb.Select[[]Person](ctx, db, models.Table("persons"))

one, err := surrealdb.Select[Person](ctx, db, models.NewRecordID("persons", "tobie"))
```

When a [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table) is passed, operations that return data return a slice. When a [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) is passed, they return a single value. Use the appropriate type parameter to match.
##  Selecting records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#selecting-records)
[`Select`](https://surrealdb.com/docs/reference/golang/api/core/db#select) retrieves records from the database. Pass a [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table) to get all records, or a [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) to get a single record.

```go
persons, err := surrealdb.Select[[]Person](ctx, db, models.Table("persons"))
if err != nil {
	log.Fatal(err)
}

tobie, err := surrealdb.Select[Person](ctx, db, models.NewRecordID("persons", "tobie"))
if err != nil {
	log.Fatal(err)
}
```

##  Creating records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#creating-records)
[`Create`](https://surrealdb.com/docs/reference/golang/api/core/db#create) creates a new record. Pass a [`Table`](https://surrealdb.com/docs/reference/golang/api/values/table) to generate a random ID, or a [`RecordID`](https://surrealdb.com/docs/reference/golang/api/values/record-id) to specify the ID explicitly. The data can be a struct or a map.

```go
person, err := surrealdb.Create[Person](ctx, db, models.Table("persons"), Person{
	Name:    "Tobie",
	Surname: "Morgan Hitchcock",
})

specific, err := surrealdb.Create[Person](ctx, db, models.NewRecordID("persons", "tobie"), map[string]any{
	"name":    "Tobie",
	"surname": "Morgan Hitchcock",
})
```

##  Inserting records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#inserting-records)
[`Insert`](https://surrealdb.com/docs/reference/golang/api/core/db#insert) inserts one or more records into a table. This is useful for bulk operations.

```go
persons, err := surrealdb.Insert[Person](ctx, db, models.Table("persons"), []map[string]any{
	{"name": "Alice", "age": 30},
	{"name": "Bob", "age": 25},
})
```

##  Creating relations[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#creating-relations)
The SDK provides two ways to create graph edges between records.
[`Relate`](https://surrealdb.com/docs/reference/golang/api/core/db#relate) creates a relation with an auto-generated ID. The [`Relationship.ID`](https://surrealdb.com/docs/reference/golang/api/types#relationship) field is ignored.

```go
rel, err := surrealdb.Relate[map[string]any](ctx, db, &surrealdb.Relationship{
	In:       models.NewRecordID("persons", "tobie"),
	Out:      models.NewRecordID("posts", "first"),
	Relation: models.Table("wrote"),
	Data:     map[string]any{"created_at": "2026-01-01T00:00:00Z"},
})
```

[`InsertRelation`](https://surrealdb.com/docs/reference/golang/api/core/db#insertrelation) works like [`Insert`](https://surrealdb.com/docs/reference/golang/api/core/db#insert) but for relation tables. It allows you to specify the ID explicitly via the [`Relationship.ID`](https://surrealdb.com/docs/reference/golang/api/types#relationship) field.

```go
rel, err := surrealdb.InsertRelation[map[string]any](ctx, db, &surrealdb.Relationship{
	In:       models.NewRecordID("persons", "tobie"),
	Out:      models.NewRecordID("posts", "first"),
	Relation: models.Table("wrote"),
})
```

##  Replacing records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#replacing-records)
[`Update`](https://surrealdb.com/docs/reference/golang/api/core/db#update) replaces the entire content of a record or all records in a table. Fields not included in the new data are removed.

```go
updated, err := surrealdb.Update[Person](ctx, db, models.NewRecordID("persons", "tobie"), Person{
	Name:    "Tobie",
	Surname: "Morgan Hitchcock",
})
```

Note
Because [`Update`](https://surrealdb.com/docs/reference/golang/api/core/db#update) performs a full replacement, omitted fields are deleted from the record. Use [`Merge`](https://surrealdb.com/docs/reference/golang/api/core/db#merge) if you want to preserve existing fields.
##  Upserting records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#upserting-records)
[`Upsert`](https://surrealdb.com/docs/reference/golang/api/core/db#upsert) creates a record if it does not already exist, or replaces it entirely if it does.

```go
person, err := surrealdb.Upsert[Person](ctx, db, models.NewRecordID("persons", "tobie"), Person{
	Name:    "Tobie",
	Surname: "Morgan Hitchcock",
})
```

##  Merging data[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#merging-data)
[`Merge`](https://surrealdb.com/docs/reference/golang/api/core/db#merge) deep-merges the provided data into the existing record, preserving fields not mentioned in the merge payload.

```go
merged, err := surrealdb.Merge[Person](ctx, db, models.NewRecordID("persons", "tobie"), map[string]any{
	"age": 35,
})
```

##  Applying patches[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#applying-patches)
[`Patch`](https://surrealdb.com/docs/reference/golang/api/core/db#patch) applies [JSON Patch (RFC 6902)](https://jsonpatch.com/) operations to a record or all records in a table. Each operation is a [`PatchData`](https://surrealdb.com/docs/reference/golang/api/types#patchdata) with `Op`, `Path`, and `Value` fields.

```go
patches, err := surrealdb.Patch(ctx, db, models.NewRecordID("persons", "tobie"), []surrealdb.PatchData{
	{Op: "replace", Path: "/surname", Value: "Hitchcock"},
	{Op: "add", Path: "/verified", Value: true},
})
```

Supported operations include `add`, `remove`, `replace`, `move`, `copy`, and `test`.
##  Deleting records[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#deleting-records)
[`Delete`](https://surrealdb.com/docs/reference/golang/api/core/db#delete) removes a specific record or all records from a table. The function returns the deleted record(s).

```go
deleted, err := surrealdb.Delete[Person](ctx, db, models.NewRecordID("persons", "tobie"))

allDeleted, err := surrealdb.Delete[[]Person](ctx, db, models.Table("persons"))
```

##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation#learn-more)
  * •
[DB API reference](https://surrealdb.com/docs/reference/golang/api/core/db) for complete function signatures and parameters
  * •
[Executing queries](https://surrealdb.com/docs/reference/golang/concepts/executing-queries) for running SurrealQL statements directly
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the types used by data manipulation functions
  * •
[RecordID reference](https://surrealdb.com/docs/reference/golang/api/values/record-id) for constructing record identifiers
  * •
[SurrealQL CRUD statements](https://surrealdb.com/docs/reference/query-language/statements/overview) for the underlying query language
