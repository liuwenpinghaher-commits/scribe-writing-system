---
title: "https://surrealdb.com/docs/reference/python/api/values/duration"
url: "https://surrealdb.com/docs/reference/python/api/values/duration"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/duration

Source: https://surrealdb.com/docs/reference/python/api/values/duration

A `Duration` stores a time duration with nanosecond precision. It supports parsing from human-readable strings (including compound formats like `"1h30m"`) and provides properties for converting to common time units.
`Duration` is a Python dataclass.
Import

```python
from surrealdb import Duration
```

* * *
##  Fields[](https://surrealdb.com/docs/reference/python/api/values/duration#fields)  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `elapsed`  | `int`  | The duration in nanoseconds.  |  
* * *
##  Constructor[](https://surrealdb.com/docs/reference/python/api/values/duration#constructor)
Syntax

```python
Duration(elapsed)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `elapsed`  | `int`  | The duration in nanoseconds.  |  

```python
d = Duration(5_000_000_000)
print(d.seconds)  # 5.0
```

* * *
##  Static methods[](https://surrealdb.com/docs/reference/python/api/values/duration#static-methods)
###  `Duration.parse()`[](https://surrealdb.com/docs/reference/python/api/values/duration#parse)
Parses a duration from a string or integer value. String values support SurrealDB duration syntax, including compound durations.
Syntax

```python
Duration.parse(value, nanoseconds=0)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | `str | int`  |  A duration string (e.g. `"1h30m"`, `"500ms"`) or an integer in nanoseconds.  |  
| `nanoseconds`  | `int`  |  Additional nanoseconds to add. Defaults to `0`.  |  
**Returns:** `Duration`
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/duration#examples)

```python
d = Duration.parse("1h30m")
print(d.minutes)  # 90.0

d = Duration.parse("500ms")
print(d.milliseconds)  # 500.0

d = Duration.parse("2d12h")
print(d.hours)  # 60.0

d = Duration.parse(1_000_000_000)
print(d.seconds)  # 1.0
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/python/api/values/duration#properties)
All unit properties return a `float`.  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `nanoseconds`  | `float`  | Duration in nanoseconds.  |  
| `microseconds`  | `float`  | Duration in microseconds.  |  
| `milliseconds`  | `float`  | Duration in milliseconds.  |  
| `seconds`  | `float`  | Duration in seconds.  |  
| `minutes`  | `float`  | Duration in minutes.  |  
| `hours`  | `float`  | Duration in hours.  |  
| `days`  | `float`  | Duration in days.  |  
| `weeks`  | `float`  | Duration in weeks.  |  
| `years`  | `float`  | Duration in years (365-day).  |  

```python
d = Duration.parse("2h30m")
print(d.hours)    # 2.5
print(d.minutes)  # 150.0
print(d.seconds)  # 9000.0
```

* * *
##  Methods[](https://surrealdb.com/docs/reference/python/api/values/duration#methods)
###  `to_string()`[](https://surrealdb.com/docs/reference/python/api/values/duration#to-string)
Returns the duration as a human-readable string.
Syntax

```python
duration.to_string()
```

**Returns:** `str`

```python
d = Duration.parse("1h30m")
print(d.to_string())  # "1h30m"
```

###  `to_compact()`[](https://surrealdb.com/docs/reference/python/api/values/duration#to-compact)
Returns the duration as a compact list of integer values.
Syntax

```python
duration.to_compact()
```

**Returns:** `list[int]`

```python
d = Duration.parse("1h30m")
print(d.to_compact())
```

* * *
##  Usage[](https://surrealdb.com/docs/reference/python/api/values/duration#usage)

```python
from surrealdb import Surreal, Duration

db = Surreal("ws://localhost:8000")
db.connect()
db.use("my_ns", "my_db")
db.signin({"username": "root", "password": "root"})

db.create("tasks", {
    "title": "Backup",
    "interval": Duration.parse("6h"),
})
```

* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/duration#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values) — All SDK data types
  * •
[Datetime](https://surrealdb.com/docs/reference/python/api/values/datetime) — Datetime wrapper
