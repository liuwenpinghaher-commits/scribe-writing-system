---
title: "https://surrealdb.com/docs/reference/python/concepts/data-manipulation"
url: "https://surrealdb.com/docs/reference/python/concepts/data-manipulation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/data-manipulation

Source: https://surrealdb.com/docs/reference/python/concepts/data-manipulation

The Python SDK provides dedicated methods for common CRUD operations on records and tables. These methods offer a structured alternative to writing raw SurrealQL, with built-in parameter handling and type safety.
This page covers how to target tables and records, and how to select, create, insert, update, merge, patch, and delete data.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.select(record)`](https://surrealdb.com/docs/reference/python/api/core/surreal#select)  | Selects all records from a table, or a specific record  |  
| [`db.create(record, data?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#create)  | Creates a new record with an optional data payload  |  
| [`db.insert(table, data)`](https://surrealdb.com/docs/reference/python/api/core/surreal#insert)  | Inserts one or multiple records into a table  |  
| [`db.insert_relation(table, data)`](https://surrealdb.com/docs/reference/python/api/core/surreal#insert-relation)  | Inserts one or multiple relation records  |  
| [`db.update(record, data?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#update)  | Replaces the entire content of a record or all records in a table  |  
| [`db.upsert(record, data?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#upsert)  | Creates a record if it does not exist, or replaces it entirely  |  
| [`db.merge(record, data?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#merge)  | Merges data into an existing record, preserving unmentioned fields  |  
| [`db.patch(record, data?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#patch)  | Applies JSON Patch operations to a record or all records in a table  |  
| [`db.delete(record)`](https://surrealdb.com/docs/reference/python/api/core/surreal#delete)  | Deletes a specific record or all records from a table  |  
##  Targeting tables and records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#targeting-tables-and-records)
Most data manipulation methods accept a `record` parameter that determines the scope of the operation. You can pass a table name as a string to target all records in that table, or a [RecordID](https://surrealdb.com/docs/reference/python/api/values/record-id) to target a specific record.

```python
from surrealdb import RecordID

db.select("users")

db.select(RecordID("users", "tobie"))
```

When a string is passed, the operation applies to the entire table. When a `RecordID` is passed, it applies to the single record identified by that ID. See the [RecordID reference](https://surrealdb.com/docs/reference/python/api/values/record-id) for more on constructing record identifiers.
##  Selecting records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#selecting-records)
The `.select()` method retrieves records from the database. Pass a table name to get all records, or a `RecordID` to get a single record.
SynchronousAsynchronous

```python
from surrealdb import Surreal, RecordID

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})

    all_users = db.select("users")

    tobie = db.select(RecordID("users", "tobie"))
```

```python
from surrealdb import AsyncSurreal, RecordID

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})

    all_users = await db.select("users")

    tobie = await db.select(RecordID("users", "tobie"))
```

When selecting a table, the method returns a list. When selecting a specific record, it returns a single value or `None` if the record does not exist.
##  Creating records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#creating-records)
The `.create()` method creates a new record. Pass a table name to generate a random ID, or a `RecordID` to specify the ID explicitly.
SynchronousAsynchronous

```python
from surrealdb import RecordID

user = db.create("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})

specific = db.create(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "age": 35,
})
```

```python
from surrealdb import RecordID

user = await db.create("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 30,
})

specific = await db.create(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "age": 35,
})
```

The method returns the created record, including any server-generated fields such as the `id`.
##  Inserting records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#inserting-records)
The `.insert()` method inserts one or more records into a table. This is useful for bulk operations where you need to add multiple records at once.
SynchronousAsynchronous

```python
db.insert("users", {"name": "Alice", "age": 30})

db.insert("users", [
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 40},
])
```

```python
await db.insert("users", {"name": "Alice", "age": 30})

await db.insert("users", [
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 40},
])
```

The `.insert_relation()` method works the same way but is designed for creating graph edges between records. Each record must include `in` and `out` fields pointing to the connected records.
SynchronousAsynchronous

```python
from surrealdb import RecordID

db.insert_relation("likes", {
    "in": RecordID("users", "tobie"),
    "out": RecordID("posts", 123),
})

db.insert_relation("likes", [
    {"in": RecordID("users", "tobie"), "out": RecordID("posts", 123)},
    {"in": RecordID("users", "jaime"), "out": RecordID("posts", 456)},
])
```

```python
from surrealdb import RecordID

await db.insert_relation("likes", {
    "in": RecordID("users", "tobie"),
    "out": RecordID("posts", 123),
})

await db.insert_relation("likes", [
    {"in": RecordID("users", "tobie"), "out": RecordID("posts", 123)},
    {"in": RecordID("users", "jaime"), "out": RecordID("posts", 456)},
])
```

##  Replacing records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#replacing-records)
The `.update()` method replaces the entire content of a record or all records in a table. Any fields not included in the new data are removed.
SynchronousAsynchronous

```python
from surrealdb import RecordID

db.update(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "active": True,
})

db.update("users", {"active": False})
```

```python
from surrealdb import RecordID

await db.update(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "active": True,
})

await db.update("users", {"active": False})
```

Note
Because `.update()` performs a full replacement, omitted fields are deleted from the record. Use `.merge()` if you want to preserve existing fields.
##  Upserting records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#upserting-records)
The `.upsert()` method creates a record if it does not already exist, or replaces it entirely if it does. This combines the behavior of `.create()` and `.update()` in a single operation.
SynchronousAsynchronous

```python
from surrealdb import RecordID

db.upsert(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "active": True,
})
```

```python
from surrealdb import RecordID

await db.upsert(RecordID("users", "tobie"), {
    "name": "Tobie",
    "email": "tobie@surrealdb.com",
    "active": True,
})
```

##  Merging data[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#merging-data)
The `.merge()` method deep-merges the provided data into the existing record, preserving any fields that are not mentioned in the merge payload. This is useful for partial updates.
SynchronousAsynchronous

```python
from surrealdb import RecordID

db.merge(RecordID("users", "tobie"), {
    "settings": {"active": True},
})

db.merge("users", {
    "updated_at": "2026-02-25T12:00:00Z",
})
```

```python
from surrealdb import RecordID

await db.merge(RecordID("users", "tobie"), {
    "settings": {"active": True},
})

await db.merge("users", {
    "updated_at": "2026-02-25T12:00:00Z",
})
```

In the example above, only the `settings.active` field is changed on the specific record. All other fields on the record remain untouched.
##  Applying patches[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#applying-patches)
The `.patch()` method applies [JSON Patch (RFC 6902)](https://jsonpatch.com/) operations to a record or all records in a table. Each operation is a dictionary with `op`, `path`, and optionally `value` fields.
SynchronousAsynchronous

```python
from surrealdb import RecordID

db.patch(RecordID("users", "tobie"), [
    {"op": "replace", "path": "/settings/active", "value": False},
    {"op": "add", "path": "/tags", "value": ["developer", "admin"]},
    {"op": "remove", "path": "/temp"},
])
```

```python
from surrealdb import RecordID

await db.patch(RecordID("users", "tobie"), [
    {"op": "replace", "path": "/settings/active", "value": False},
    {"op": "add", "path": "/tags", "value": ["developer", "admin"]},
    {"op": "remove", "path": "/temp"},
])
```

Supported operations include `add`, `remove`, `replace`, `move`, `copy`, and `test`.
##  Deleting records[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#deleting-records)
The `.delete()` method removes a specific record or all records from a table. The method returns the deleted record(s).
SynchronousAsynchronous

```python
from surrealdb import RecordID

deleted = db.delete(RecordID("users", "tobie"))

all_deleted = db.delete("users")
```

```python
from surrealdb import RecordID

deleted = await db.delete(RecordID("users", "tobie"))

all_deleted = await db.delete("users")
```

##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/data-manipulation#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for complete method signatures and parameters
  * •
[Executing queries](https://surrealdb.com/docs/reference/python/concepts/executing-queries) for running SurrealQL statements directly
  * •
[Value types](https://surrealdb.com/docs/reference/python/api/types) for the types used by data manipulation methods
  * •
[RecordID reference](https://surrealdb.com/docs/reference/python/api/values/record-id) for constructing record identifiers
  * •
[SurrealQL CRUD statements](https://surrealdb.com/docs/reference/query-language/statements/overview) for the underlying query language
