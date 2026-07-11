---
title: "https://surrealdb.com/docs/reference/python/concepts/value-types"
url: "https://surrealdb.com/docs/reference/python/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/value-types

Source: https://surrealdb.com/docs/reference/python/concepts/value-types

The Python SDK maps SurrealDB data types to Python types automatically. Standard Python types like `str`, `int`, `float`, `bool`, `None`, `dict`, and `list` map directly to their SurrealDB equivalents. For SurrealDB-specific types such as record identifiers, durations, and geometry, the SDK provides dedicated Python classes.
See the [Data types reference](https://surrealdb.com/docs/reference/python/api/values/) for the full API details of each type.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/value-types#api-references)  
| Class |  
| --- |  
| [`RecordID(table_name, identifier)`](https://surrealdb.com/docs/reference/python/api/values/record-id) |  
| [`Table(table_name)`](https://surrealdb.com/docs/reference/python/api/values/table) |  
| [`Duration(elapsed)`](https://surrealdb.com/docs/reference/python/api/values/duration) |  
| [`Datetime(dt)`](https://surrealdb.com/docs/reference/python/api/values/datetime) |  
| [`Range(begin, end)`](https://surrealdb.com/docs/reference/python/api/values/range) |  
| [`GeometryPoint(...)`](https://surrealdb.com/docs/reference/python/api/values/geometry) |  
##  Type mapping between Python and SurrealDB[](https://surrealdb.com/docs/reference/python/concepts/value-types#type-mapping-between-python-and-surrealdb)
The following table shows how Python types correspond to SurrealDB types. Standard library types are used directly, while SurrealDB-specific types use the custom classes listed above.  
| Python Type  | SurrealDB Type  |  
| --- | --- |  
| `str`  | `string`  |  
| `int`  | `int`  |  
| `float`  | `float`  |  
| `bool`  | `bool`  |  
| `None`  |  `NONE` / `NULL`  |  
| `bytes`  | `bytes`  |  
| `UUID`  | `uuid`  |  
| `Decimal`  | `decimal`  |  
| `dict`  | `object`  |  
| `list`  | `array`  |  
| [`RecordID`](https://surrealdb.com/docs/reference/python/api/values/record-id)  | `record`  |  
| [`Table`](https://surrealdb.com/docs/reference/python/api/values/table)  | `table`  |  
| [`Duration`](https://surrealdb.com/docs/reference/python/api/values/duration)  | `duration`  |  
| [`Datetime`](https://surrealdb.com/docs/reference/python/api/values/datetime)  | `datetime`  |  
| [`Range`](https://surrealdb.com/docs/reference/python/api/values/range)  | `range`  |  
| [`Geometry*`](https://surrealdb.com/docs/reference/python/api/values/geometry)  | `geometry`  |  
##  Working with record identifiers[](https://surrealdb.com/docs/reference/python/concepts/value-types#working-with-record-identifiers)
A [`RecordID`](https://surrealdb.com/docs/reference/python/api/values/record-id) uniquely identifies a single record in a table by combining a table name with an identifier value. You can construct one directly or parse it from a string.

```python
from surrealdb import RecordID

record = RecordID("users", "tobie")
print(record.table_name)  # "users"
print(record.id)          # "tobie"

parsed = RecordID.parse("users:tobie")
print(parsed.table_name)  # "users"
```

The identifier can be a string, integer, list, or any other supported value type. Use `RecordID` wherever the SDK expects a record reference, such as in `.select()`, `.create()`, or `.delete()`.

```python
from surrealdb import Surreal, RecordID

with Surreal("ws://localhost:8000") as db:
    db.use("my_ns", "my_db")
    db.signin({"username": "root", "password": "root"})

    db.create(RecordID("users", "tobie"), {
        "name": "Tobie",
        "email": "tobie@surrealdb.com",
    })

    user = db.select(RecordID("users", "tobie"))
```

See the [RecordID reference](https://surrealdb.com/docs/reference/python/api/values/record-id) for the complete API, including equality checks and Pydantic support.
##  Working with durations[](https://surrealdb.com/docs/reference/python/concepts/value-types#working-with-durations)
A [`Duration`](https://surrealdb.com/docs/reference/python/api/values/duration) represents a time span with nanosecond precision. The most common way to create one is by parsing a human-readable string using SurrealDB's duration syntax.

```python
from surrealdb import Duration

d = Duration.parse("1h30m")
print(d.hours)    # 1.5
print(d.minutes)  # 90.0

d2 = Duration.parse("500ms")
print(d2.milliseconds)  # 500.0
```

You can also construct a `Duration` directly from nanoseconds and convert it back to a string.

```python
d = Duration(5_000_000_000)
print(d.seconds)      # 5.0
print(d.to_string())  # "5s"
```

Durations are useful for setting intervals, timeouts, and TTLs in your data.

```python
from surrealdb import Surreal, Duration

with Surreal("ws://localhost:8000") as db:
    db.use("my_ns", "my_db")
    db.signin({"username": "root", "password": "root"})

    db.create("tasks", {
        "title": "Backup",
        "interval": Duration.parse("6h"),
    })
```

See the [Duration reference](https://surrealdb.com/docs/reference/python/api/values/duration) for all unit properties and methods.
##  Working with datetime values[](https://surrealdb.com/docs/reference/python/concepts/value-types#working-with-datetime-values)
A [`Datetime`](https://surrealdb.com/docs/reference/python/api/values/datetime) wraps an ISO 8601 datetime string for use with SurrealDB's `datetime` type. It preserves the original string representation through serialization and deserialization.

```python
from surrealdb import Datetime

dt = Datetime("2025-06-01T09:00:00Z")
print(dt.dt)  # "2025-06-01T09:00:00Z"
```

Use `Datetime` when creating records that contain date or time fields.

```python
from surrealdb import Surreal, Datetime

with Surreal("ws://localhost:8000") as db:
    db.use("my_ns", "my_db")
    db.signin({"username": "root", "password": "root"})

    db.create("events", {
        "title": "Launch",
        "scheduled_at": Datetime("2025-06-01T09:00:00Z"),
    })
```

See the [Datetime reference](https://surrealdb.com/docs/reference/python/api/values/datetime) for the full API.
##  Working with ranges[](https://surrealdb.com/docs/reference/python/concepts/value-types#working-with-ranges)
A [`Range`](https://surrealdb.com/docs/reference/python/api/values/range) represents a bounded interval with inclusive or exclusive endpoints. Each bound is wrapped in a `BoundIncluded` or `BoundExcluded` to specify whether the boundary value is part of the range.

```python
from surrealdb import Range
from surrealdb.data.types.range import BoundIncluded, BoundExcluded

inclusive = Range(
    begin=BoundIncluded(1),
    end=BoundIncluded(10),
)

half_open = Range(
    begin=BoundIncluded(1),
    end=BoundExcluded(10),
)
```

Ranges are commonly used in query parameters to filter results within a specific interval.

```python
from surrealdb import Surreal, Range
from surrealdb.data.types.range import BoundIncluded

with Surreal("ws://localhost:8000") as db:
    db.use("my_ns", "my_db")
    db.signin({"username": "root", "password": "root"})

    result = db.query(
        "SELECT * FROM events WHERE year IN $range",
        {"range": Range(BoundIncluded(2020), BoundIncluded(2025))},
    )
```

See the [Range reference](https://surrealdb.com/docs/reference/python/api/values/range) for the full API and bound types.
##  Working with geometry types[](https://surrealdb.com/docs/reference/python/concepts/value-types#working-with-geometry-types)
The SDK provides seven GeoJSON-compatible geometry types for working with SurrealDB's spatial data: `GeometryPoint`, `GeometryLine`, `GeometryPolygon`, `GeometryMultiPoint`, `GeometryMultiLine`, `GeometryMultiPolygon`, and `GeometryCollection`.
The most common type is `GeometryPoint`, which represents a single geographic coordinate.

```python
from surrealdb import Surreal, GeometryPoint

with Surreal("ws://localhost:8000") as db:
    db.use("my_ns", "my_db")
    db.signin({"username": "root", "password": "root"})

    db.create("locations", {
        "name": "London",
        "coordinates": GeometryPoint(-0.1278, 51.5074),
    })
```

More complex types compose from simpler ones — a `GeometryLine` is built from a list of points, a `GeometryPolygon` from a list of lines, and so on. See the [Geometry reference](https://surrealdb.com/docs/reference/python/api/values/geometry) for constructors and examples of all seven types.
##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/value-types#learn-more)
  * •
[Data types reference](https://surrealdb.com/docs/reference/python/api/values/) for complete API details
  * •
[RecordID reference](https://surrealdb.com/docs/reference/python/api/values/record-id) for record identifier API
  * •
[Duration reference](https://surrealdb.com/docs/reference/python/api/values/duration) for duration API
  * •
[Python types](https://surrealdb.com/docs/reference/python/api/types/) for Value and RecordIdType definitions
  * •
[Data manipulation](https://surrealdb.com/docs/reference/python/concepts/data-manipulation) for using types in queries
