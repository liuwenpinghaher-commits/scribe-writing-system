---
title: "https://surrealdb.com/docs/reference/python/api/values/datetime"
url: "https://surrealdb.com/docs/reference/python/api/values/datetime"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/datetime

Source: https://surrealdb.com/docs/reference/python/api/values/datetime

A `Datetime` wraps an ISO 8601 datetime string for use with SurrealDB's `datetime` type. It preserves the original string representation through serialization and deserialization.
Import

```python
from surrealdb import Datetime
```

* * *
##  Constructor[](https://surrealdb.com/docs/reference/python/api/values/datetime#constructor)
Syntax

```python
Datetime(dt)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `dt`  | `str`  | An ISO 8601 datetime string.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/datetime#examples)

```python
dt = Datetime("2025-01-15T10:30:00Z")
```

```python
dt = Datetime("2025-06-01T14:00:00.000+02:00")
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/python/api/values/datetime#properties)  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `dt`  | `str`  | The ISO 8601 datetime string.  |  

```python
dt = Datetime("2025-01-15T10:30:00Z")
print(dt.dt)  # "2025-01-15T10:30:00Z"
```

* * *
##  Usage[](https://surrealdb.com/docs/reference/python/api/values/datetime#usage)

```python
from surrealdb import Surreal, RecordID, Datetime

db = Surreal("ws://localhost:8000")
db.connect()
db.use("my_ns", "my_db")
db.signin({"username": "root", "password": "root"})

db.create("events", {
    "title": "Launch",
    "scheduled_at": Datetime("2025-06-01T09:00:00Z"),
})
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/datetime#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values), All SDK data types
  * •
[Duration](https://surrealdb.com/docs/reference/python/api/values/duration), Duration type with unit conversion
