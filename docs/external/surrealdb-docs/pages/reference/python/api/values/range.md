---
title: "https://surrealdb.com/docs/reference/python/api/values/range"
url: "https://surrealdb.com/docs/reference/python/api/values/range"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/range

Source: https://surrealdb.com/docs/reference/python/api/values/range

A `Range` represents a SurrealDB range value with a begin and end bound. Each bound can be inclusive or exclusive. `Range` is a Python dataclass.
Import

```python
from surrealdb import Range
from surrealdb.data.types.range import BoundIncluded, BoundExcluded
```

* * *
##  `Bound` classes[](https://surrealdb.com/docs/reference/python/api/values/range#bounds)
The `Bound` base class has two subclasses that define whether a boundary value is included or excluded.
###  `BoundIncluded`[](https://surrealdb.com/docs/reference/python/api/values/range#boundincluded)
An inclusive bound. The boundary value is part of the range.  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | [Value](https://surrealdb.com/docs/reference/python/api/values/#value)  | The boundary value.  |  
###  `BoundExcluded`[](https://surrealdb.com/docs/reference/python/api/values/range#boundexcluded)
An exclusive bound. The boundary value is not part of the range.  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | [Value](https://surrealdb.com/docs/reference/python/api/values/#value)  | The boundary value.  |  
* * *
##  `Range` dataclass[](https://surrealdb.com/docs/reference/python/api/values/range#range-dataclass)
###  Fields[](https://surrealdb.com/docs/reference/python/api/values/range#fields)  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `begin`  | `Bound`  | The start bound of the range.  |  
| `end`  | `Bound`  | The end bound of the range.  |  
###  Constructor[](https://surrealdb.com/docs/reference/python/api/values/range#constructor)
Syntax

```python
Range(begin, end)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `begin`  | `Bound`  | The start bound (inclusive or exclusive).  |  
| `end`  | `Bound`  | The end bound (inclusive or exclusive).  |  
* * *
##  Examples[](https://surrealdb.com/docs/reference/python/api/values/range#examples)
Inclusive range 1 to 10

```python
from surrealdb import Range
from surrealdb.data.types.range import BoundIncluded

r = Range(
    begin=BoundIncluded(1),
    end=BoundIncluded(10),
)
```

Half-open range 1 to 10

```python
from surrealdb.data.types.range import BoundIncluded, BoundExcluded

r = Range(
    begin=BoundIncluded(1),
    end=BoundExcluded(10),
)
```

Using with queries

```python
from surrealdb import Surreal, Range
from surrealdb.data.types.range import BoundIncluded

db = Surreal("ws://localhost:8000")
db.connect()
db.use("my_ns", "my_db")
db.signin({"username": "root", "password": "root"})

result = db.query(
    "SELECT * FROM events WHERE year IN $range",
    {"range": Range(BoundIncluded(2020), BoundIncluded(2025))},
)
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/range#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values) — All SDK data types
  * •
[RecordID](https://surrealdb.com/docs/reference/python/api/values/record-id) — Record identifier
