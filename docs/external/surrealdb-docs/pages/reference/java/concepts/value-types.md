---
title: "https://surrealdb.com/docs/reference/java/concepts/value-types"
url: "https://surrealdb.com/docs/reference/java/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/value-types

Source: https://surrealdb.com/docs/reference/java/concepts/value-types

The Java SDK maps SurrealDB data types to native Java types where possible and provides custom classes for types that have no direct Java equivalent. You can work with results as untyped [`Value`](/docs/reference/java/api/values/value) objects or pass a `Class` to SDK methods for automatic deserialization into POJOs.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/value-types#api-references)  
| Class  | Description  |  
| --- | --- |  
| [`Value`](https://surrealdb.com/docs/reference/java/api/values/value)  | Represents any SurrealDB value  |  
| [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id)  | Represents a record identifier  |  
| [`Geometry`](https://surrealdb.com/docs/reference/java/api/values/geometry)  | Represents geometric data  |  
| [`FileRef`](https://surrealdb.com/docs/reference/java/api/values/file-ref)  | Represents a file reference  |  
| [`Datetime`](https://surrealdb.com/docs/reference/java/api/values/datetime)  |  Maps to `java.time.ZonedDateTime`  |  
| [`Duration`](https://surrealdb.com/docs/reference/java/api/values/duration)  |  Maps to `java.time.Duration`  |  
| [`Table`](https://surrealdb.com/docs/reference/java/api/values/table)  |  Table name value, maps to `String`  |  
| [`Range`](https://surrealdb.com/docs/reference/java/api/values/range)  | Range value with start and end bounds  |  
##  Type mapping[](https://surrealdb.com/docs/reference/java/concepts/value-types#type-mapping)
SurrealDB types map to Java types as follows:  
| SurrealDB Type  | Java Type  | Notes  |  
| --- | --- | --- |  
| `string`  | `String`  |   |  
| `int`  | `long`  |   |  
| `float`  | `double`  |   |  
| `bool`  | `boolean`  |   |  
| `null`  | `null`  |   |  
| `none`  | `Value.isNone()`  | Check via [`Value`](https://surrealdb.com/docs/reference/java/api/values/value)  |  
| [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `ZonedDateTime`  | `java.time`  |  
| [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes)  | `Duration`  | `java.time`  |  
| `decimal`  | `BigDecimal`  | `java.math`  |  
| `uuid`  | `UUID`  | `java.util`  |  
| `bytes`  | `byte[]`  |   |  
| `array`  | [`Array`](https://surrealdb.com/docs/reference/java/api/values/value#array)  | SDK custom class  |  
| `object`  | [`Object`](https://surrealdb.com/docs/reference/java/api/values/value#object)  | SDK custom class  |  
| [`record`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids)  | [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id)  | SDK custom class  |  
| [`geometry`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries)  | [`Geometry`](https://surrealdb.com/docs/reference/java/api/values/geometry)  | SDK custom class  |  
| [`file`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files)  | [`FileRef`](https://surrealdb.com/docs/reference/java/api/values/file-ref)  | SDK custom class  |  
| `table`  | `String`  | Via `Value.getTable()`  |  
| `range`  | [`Value`](https://surrealdb.com/docs/reference/java/api/values/value)  | Via `Value.getRangeStart()` / `Value.getRangeEnd()`  |  
##  Working with the Value class[](https://surrealdb.com/docs/reference/java/concepts/value-types#working-with-the-value-class)
[`Value`](https://surrealdb.com/docs/reference/java/api/values/value) is the untyped representation of any SurrealDB value. It provides type-checking methods and getters for extracting the underlying Java value.

```java
Value value = response.take(0);

if (value.isLong()) {
    long count = value.getLong();
}

if (value.isString()) {
    String name = value.getString();
}

if (value.isArray()) {
    Array items = value.getArray();
}
```

To convert a `Value` directly into a POJO, use `.get(Class)`.

```java
Person person = value.get(Person.class);
```

##  Using POJOs for type-safe access[](https://surrealdb.com/docs/reference/java/concepts/value-types#using-pojos-for-type-safe-access)
Instead of working with raw [`Value`](/docs/reference/java/api/values/value) objects, you can pass a `Class` to most SDK methods to get automatic deserialization. POJOs need a public no-argument constructor, and their fields map directly to SurrealDB object keys.

```java
public class Person {
    public RecordId id;
    public String name;
    public int age;

    public Person() {}
}

List<Person> people = db.create(Person.class, "person", newPerson);
Optional<Person> tobie = db.select(Person.class, new RecordId("person", "tobie"));
```

##  Constructing record identifiers[](https://surrealdb.com/docs/reference/java/concepts/value-types#constructing-record-identifiers)
[`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id) represents a SurrealDB record identifier consisting of a table name and an ID value. The ID can be a `long`, `String`, `UUID`, `Array`, or `Object`.

```java
RecordId numericId = new RecordId("person", 1L);
RecordId stringId = new RecordId("person", "tobie");
RecordId uuidId = new RecordId("person", UUID.randomUUID());

Array compositeKey = new Array(2026, "Q1");
RecordId arrayId = new RecordId("report", compositeKey);

Object objectKey = new Object();
objectKey.put("region", "eu");
objectKey.put("year", 2026);
RecordId objectId = new RecordId("report", objectKey);
```

##  Iterating arrays and objects[](https://surrealdb.com/docs/reference/java/concepts/value-types#iterating-arrays-and-objects)
The SDK's `Array` class implements `Iterable`, and the `Object` class implements `Iterable`. You can iterate over them using standard Java for-each loops.

```java
Array items = value.getArray();
for (Value item : items) {
    System.out.println(item.getString());
}

Object obj = value.getObject();
for (Entry entry : obj) {
    System.out.println(entry.getKey() + ": " + entry.getValue());
}
```

When iterating from multiple threads, use `synchronizedIterator()` to get a thread-safe iterator.

```java
Iterator<Value> safeIterator = items.synchronizedIterator();
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/value-types#learn-more)
  * •
[Value API reference](https://surrealdb.com/docs/reference/java/api/values/value) for complete Value class documentation
  * •
[RecordId API reference](https://surrealdb.com/docs/reference/java/api/values/record-id) for record identifier details
  * •
[Geometry API reference](https://surrealdb.com/docs/reference/java/api/values/geometry) for geometric data types
  * •
[FileRef API reference](https://surrealdb.com/docs/reference/java/api/values/file-ref) for file references
  * •
[Datetime API reference](https://surrealdb.com/docs/reference/java/api/values/datetime) for datetime handling
  * •
[Duration API reference](https://surrealdb.com/docs/reference/java/api/values/duration) for duration handling
  * •
[Table API reference](https://surrealdb.com/docs/reference/java/api/values/table) for table name values
  * •
[Range API reference](https://surrealdb.com/docs/reference/java/api/values/range) for range values
  * •
[Data manipulation](https://surrealdb.com/docs/reference/java/concepts/data-manipulation) for using types with CRUD operations
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) for the full list of SurrealDB data types
