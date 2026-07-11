---
title: "https://surrealdb.com/docs/reference/java/api/values/record-id"
url: "https://surrealdb.com/docs/reference/java/api/values/record-id"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/record-id

Source: https://surrealdb.com/docs/reference/java/api/values/record-id

A `RecordId` uniquely identifies a record in SurrealDB. It consists of a table name and an ID value. The ID can be a `long`, `String`, `UUID`, or a composite key using `Array` or `Object`. See the [SurrealQL record ID documentation](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) for details on how record identifiers work in SurrealDB.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Constructors[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructors)
###  `RecordId(String table, long id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor-long)
Creates a record ID with a numeric identifier.
Method Syntax

```java
new RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `long`  | The numeric record identifier.  |  
Example

```java
RecordId id = new RecordId("person", 1);
```

###  `RecordId(String table, String id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor-string)
Creates a record ID with a string identifier.
Method Syntax

```java
new RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `String`  | The string record identifier.  |  
Example

```java
RecordId id = new RecordId("person", "tobie");
```

###  `RecordId(String table, UUID id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor-uuid)
Creates a record ID with a UUID identifier.
Method Syntax

```java
new RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `UUID`  | The UUID record identifier.  |  
Example

```java
RecordId id = new RecordId("person", UUID.randomUUID());
```

###  `RecordId(String table, Array id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor-array)
Creates a record ID with a composite key using an array.
Method Syntax

```java
new RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `Array`  | The composite key as an array.  |  
###  `RecordId(String table, Object id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor-object)
Creates a record ID with a composite key using an object.
Method Syntax

```java
new RecordId(table, id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `id`  | `Object`  | The composite key as an object.  |  
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/values/record-id#methods)
###  `.getTable()`[](https://surrealdb.com/docs/reference/java/api/values/record-id#get-table)
Returns the table name of this record ID.
Method Syntax

```java
recordId.getTable()
```

**Returns:** `String`
Example

```java
RecordId id = new RecordId("person", "tobie");
String table = id.getTable();
```

###  `.getId()`[](https://surrealdb.com/docs/reference/java/api/values/record-id#get-id)
Returns the identifier part of this record ID.
Method Syntax

```java
recordId.getId()
```

**Returns:** [`Id`](https://surrealdb.com/docs/reference/java/api/values/record-id#id)
Example

```java
RecordId id = new RecordId("person", "tobie");
Id identifier = id.getId();
```

* * *
##  `Id`[](https://surrealdb.com/docs/reference/java/api/values/record-id#id)
The `Id` class represents the identifier part of a `RecordId`. It wraps the underlying value and provides type checking and extraction methods.
###  Static factory methods[](https://surrealdb.com/docs/reference/java/api/values/record-id#static-factory-methods)
####  `Id.from(long id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#from-long)
Creates an `Id` from a numeric value.
Method Syntax

```java
Id.from(id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `long`  | The numeric identifier.  |  
**Returns:** `Id`
####  `Id.from(String id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#from-string)
Creates an `Id` from a string value.
Method Syntax

```java
Id.from(id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `String`  | The string identifier.  |  
**Returns:** `Id`
####  `Id.from(UUID id)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#from-uuid)
Creates an `Id` from a UUID value.
Method Syntax

```java
Id.from(id)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `UUID`  | The UUID identifier.  |  
**Returns:** `Id`
###  Type checking methods[](https://surrealdb.com/docs/reference/java/api/values/record-id#type-checking-methods)  
| Method  | Returns `true` when  |  
| --- | --- |  
| `isLong()`  | The ID is a numeric value  |  
| `isString()`  | The ID is a string value  |  
| `isUuid()`  | The ID is a UUID value  |  
| `isArray()`  | The ID is a composite array key  |  
| `isObject()`  | The ID is a composite object key  |  
###  Getter methods[](https://surrealdb.com/docs/reference/java/api/values/record-id#getter-methods)  
| Method  | Return Type  | Description  |  
| --- | --- | --- |  
| `getLong()`  | `long`  | Returns the numeric ID value  |  
| `getString()`  | `String`  | Returns the string ID value  |  
| `getUuid()`  | `UUID`  | Returns the UUID ID value  |  
| `getArray()`  | `Array`  | Returns the composite array key  |  
| `getObject()`  | `Object`  | Returns the composite object key  |  
* * *
##  `RecordIdRange`[](https://surrealdb.com/docs/reference/java/api/values/record-id#record-id-range)
The `RecordIdRange` class represents a range of record IDs within a table. It can be used with methods like `select` to retrieve a subset of records.
###  Constructor[](https://surrealdb.com/docs/reference/java/api/values/record-id#constructor)
####  `RecordIdRange(String table, Id start, Id end)`[](https://surrealdb.com/docs/reference/java/api/values/record-id#range-constructor)
Creates a range of record IDs. Pass `null` for `start` or `end` to leave that bound open.
Method Syntax

```java
new RecordIdRange(table, start, end)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table name.  |  
| `start`  | `Id`  |  The start of the range. Pass `null`for an unbounded start.  |  
| `end`  | `Id`  |  The end of the range. Pass `null`for an unbounded end.  |  
###  Methods[](https://surrealdb.com/docs/reference/java/api/values/record-id#methods-1)
####  `.getTable()`[](https://surrealdb.com/docs/reference/java/api/values/record-id#range-get-table)
Returns the table name of this range.
Method Syntax

```java
range.getTable()
```

**Returns:** `String`
####  `.getStart()`[](https://surrealdb.com/docs/reference/java/api/values/record-id#range-get-start)
Returns the start bound of the range, or `null` if unbounded.
Method Syntax

```java
range.getStart()
```

**Returns:** `Id` (nullable)
####  `.getEnd()`[](https://surrealdb.com/docs/reference/java/api/values/record-id#range-get-end)
Returns the end bound of the range, or `null` if unbounded.
Method Syntax

```java
range.getEnd()
```

**Returns:** `Id` (nullable)
###  Example[](https://surrealdb.com/docs/reference/java/api/values/record-id#example)
Selecting a range of records

```java
RecordIdRange range = new RecordIdRange("users", Id.from(1), Id.from(100));
List<Value> results = db.select(range);
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/record-id#see-also)
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal) — Connection and method reference
  * •
[Data manipulation](https://surrealdb.com/docs/reference/java/concepts/data-manipulation) — Working with records
  * •
[SurrealQL record IDs](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) — Record identifier formats and types
