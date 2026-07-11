---
title: "https://surrealdb.com/docs/reference/python/api/values/table"
url: "https://surrealdb.com/docs/reference/python/api/values/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/table

Source: https://surrealdb.com/docs/reference/python/api/values/table

A `Table` wraps a table name string, providing a type-safe way to reference SurrealDB tables. It can be used anywhere a [`RecordIdType`](https://surrealdb.com/docs/reference/python/api/values/#recordidtype) is accepted.
Import

```python
from surrealdb import Table
```

* * *
##  Constructor[](https://surrealdb.com/docs/reference/python/api/values/table#constructor)
Syntax

```python
Table(table_name)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table_name`  | `str`  | The name of the table.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/table#examples)

```python
table = Table("users")
print(table.table_name)  # "users"
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/python/api/values/table#properties)  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `table_name`  | `str`  | The table name string.  |  
* * *
##  Usage[](https://surrealdb.com/docs/reference/python/api/values/table#usage)
`Table` is interchangeable with a plain `str` in most SDK methods. It is useful when you want to distinguish table references from arbitrary strings at the type level.

```python
from surrealdb import Surreal, Table

db = Surreal("ws://localhost:8000")
db.connect()
db.use("my_ns", "my_db")
db.signin({"username": "root", "password": "root"})

users = db.select(Table("users"))
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/table#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values) — All SDK data types
  * •
[RecordID](https://surrealdb.com/docs/reference/python/api/values/record-id) — Record identifier with table and ID components
