---
title: "https://surrealdb.com/docs/reference/python/api/values/record-id"
url: "https://surrealdb.com/docs/reference/python/api/values/record-id"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/api/values/record-id

Source: https://surrealdb.com/docs/reference/python/api/values/record-id

A `RecordID` represents a unique record identifier in SurrealDB, combining a table name with an ID value. It is the Python equivalent of SurrealDB's `record` type.
Import

```python
from surrealdb import RecordID
```

**Source:** [record_id.py](https://github.com/surrealdb/surrealdb.py/blob/main/src/surrealdb/data/types/record_id.py)
* * *
##  Constructor[](https://surrealdb.com/docs/reference/python/api/values/record-id#constructor)
Syntax

```python
RecordID(table_name, identifier)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table_name`  | `str`  | The name of the table this record belongs to.  |  
| `identifier`  | `Any`  | The unique identifier for the record within the table.  |  
###  Examples[](https://surrealdb.com/docs/reference/python/api/values/record-id#examples)
String ID

```python
record = RecordID("users", "john")
```

Numeric ID

```python
record = RecordID("products", 42)
```

List ID

```python
record = RecordID("events", ["2025", "01", "01"])
```

* * *
##  Static methods[](https://surrealdb.com/docs/reference/python/api/values/record-id#static-methods)
###  `RecordID.parse()`[](https://surrealdb.com/docs/reference/python/api/values/record-id#parse)
Parses a record ID from its string representation.
Syntax

```python
RecordID.parse(record_str)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `record_str`  | `str`  |  A record ID string in `table_name:id`format.  |  
**Returns:** `RecordID`

```python
record = RecordID.parse("users:john")
print(record.table_name)  # "users"
print(record.id)          # "john"
```

* * *
##  Properties[](https://surrealdb.com/docs/reference/python/api/values/record-id#properties)  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `table_name`  | `str`  | The table name component of the record ID.  |  
| `id`  | [`Value`](https://surrealdb.com/docs/reference/python/api/values/#value)  | The identifier component of the record ID.  |  

```python
record = RecordID("users", "john")
print(record.table_name)  # "users"
print(record.id)          # "john"
```

* * *
##  Methods[](https://surrealdb.com/docs/reference/python/api/values/record-id#methods)
###  `__str__()`[](https://surrealdb.com/docs/reference/python/api/values/record-id#str)
Returns the string representation in `table_name:id` format.

```python
record = RecordID("users", "john")
print(str(record))  # "users:john"
```

###  `__eq__()`[](https://surrealdb.com/docs/reference/python/api/values/record-id#eq)
Compares two `RecordID` instances for equality based on both `table_name` and `id`.

```python
a = RecordID("users", "john")
b = RecordID("users", "john")
print(a == b)  # True
```

* * *
##  Pydantic support[](https://surrealdb.com/docs/reference/python/api/values/record-id#pydantic)
When the `pydantic` extra is installed (`pip install surrealdb[pydantic]`), `RecordID` can be used as a field type in Pydantic models with automatic validation and serialization.

```python
from pydantic import BaseModel
from surrealdb import RecordID

class User(BaseModel):
    id: RecordID
    name: str

user = User(id=RecordID("users", "john"), name="John")
```

* * *
##  `RecordIdType`[](https://surrealdb.com/docs/reference/python/api/values/record-id#recordidtype)
Methods that accept a record or table reference use the `RecordIdType` alias, which accepts a plain string, a [`Table`](https://surrealdb.com/docs/reference/python/api/values/table), or a `RecordID`.
Type Definition

```python
RecordIdType = str | Table | RecordID
```

See the [Data types overview](https://surrealdb.com/docs/reference/python/api/values/#recordidtype) for details.
* * *
##  See also[](https://surrealdb.com/docs/reference/python/api/values/record-id#see-also)
  * •
[Data types](https://surrealdb.com/docs/reference/python/api/values) — All SDK data types
  * •
[Table](https://surrealdb.com/docs/reference/python/api/values/table) — Table name wrapper
  * •
[Surreal](https://surrealdb.com/docs/reference/python/api/core/surreal) — Connection and query methods
