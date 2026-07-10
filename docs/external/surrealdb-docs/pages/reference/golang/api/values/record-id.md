---
title: "https://surrealdb.com/docs/reference/golang/api/values/record-id"
url: "https://surrealdb.com/docs/reference/golang/api/values/record-id"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/api/values/record-id

Source: https://surrealdb.com/docs/reference/golang/api/values/record-id

The `RecordID` struct represents a SurrealDB record identifier. A record ID consists of a table name and an identifier value, providing a typed way to reference records without ambiguity from string parsing.
**Package:** `github.com/surrealdb/surrealdb.go/pkg/models`
**Source:** [pkg/models/record_id.go](https://github.com/surrealdb/surrealdb.go/blob/main/pkg/models/record_id.go)
* * *
##  Definition[](https://surrealdb.com/docs/reference/golang/api/values/record-id#definition)

```go
type RecordID struct {
    Table string
    ID    any
}
```

The `ID` field can be any CBOR-serializable value: a string, integer, array, or map.
* * *
##  Constructors[](https://surrealdb.com/docs/reference/golang/api/values/record-id#constructors)
###  `NewRecordID`[](https://surrealdb.com/docs/reference/golang/api/values/record-id#newrecordid)
Creates a new `RecordID` with the given table name and ID.
Syntax

```go
id := models.NewRecordID(tableName, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `tableName`  | `string`  | The table name.  |  
| `id`  | `any`  | The record identifier value.  |  
**Returns:** `RecordID`
####  Examples[](https://surrealdb.com/docs/reference/golang/api/values/record-id#examples)

```go
id := models.NewRecordID("persons", "tobie")

numericID := models.NewRecordID("events", 42)

compositeID := models.NewRecordID("access", []any{"us", 2026})
```

###  `ParseRecordID`[](https://surrealdb.com/docs/reference/golang/api/values/record-id#parserecordid)
Parses a string of the form `"table:id"` into a `RecordID`. Only works for simple IDs without colons.
Syntax

```go
id, err := models.ParseRecordID(idStr)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `idStr`  | `string`  |  A string in the form `"table:id"`.  |  
**Returns:** `(*RecordID, error)`
Returns `ErrBadRecordID` if the string does not contain exactly one colon.
* * *
##  Methods[](https://surrealdb.com/docs/reference/golang/api/values/record-id#methods)
###  `.String()`[](https://surrealdb.com/docs/reference/golang/api/values/record-id#string)
Returns the string representation of the record ID in the form `"table:id"`.
Syntax

```go
s := id.String()
```

**Returns:** `string`
###  `.SurrealString()`[](https://surrealdb.com/docs/reference/golang/api/values/record-id#surrealstring)
Returns the SurrealQL representation of the record ID in the form `r'table:id'`.
Syntax

```go
s := id.SurrealString()
```

**Returns:** `string`
* * *
##  CBOR encoding[](https://surrealdb.com/docs/reference/golang/api/values/record-id#cbor-encoding)
`RecordID` is encoded as CBOR tag 8 containing a two-element array `[table, id]`. The SDK handles marshaling and unmarshaling automatically when you use `RecordID` in structs.

```go
type Person struct {
    ID      *models.RecordID `json:"id,omitempty"`
    Name    string           `json:"name"`
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/golang/api/values/record-id#see-also)
  * •
[Table](https://surrealdb.com/docs/reference/golang/api/values/table) for the table name type
  * •
[Value types](https://surrealdb.com/docs/reference/golang/concepts/value-types) for the full type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/golang/concepts/data-manipulation) for using record IDs in CRUD operations
  * •
[SurrealQL record IDs](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) for the underlying data model
