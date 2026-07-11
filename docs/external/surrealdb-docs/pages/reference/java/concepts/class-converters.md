---
title: "https://surrealdb.com/docs/reference/java/concepts/class-converters"
url: "https://surrealdb.com/docs/reference/java/concepts/class-converters"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/class-converters

Source: https://surrealdb.com/docs/reference/java/concepts/class-converters

The Java SDK includes a built-in class conversion system that automatically maps between Java classes and SurrealDB values. When you pass a `Class` to SDK methods, the converter serializes Java objects into SurrealDB-compatible data on the way in and deserializes SurrealDB responses back into typed Java objects on the way out. This removes the need to manually extract fields from raw [`Value`](/docs/reference/java/api/values/value) objects and gives you compile-time type safety across your data layer.
##  How conversion works[](https://surrealdb.com/docs/reference/java/concepts/class-converters#how-conversion-works)
Class conversion happens in two directions:
  * •
**Serialization** — When you pass a Java object to a method like [`.create()`](https://surrealdb.com/docs/reference/java/api/core/surreal#create), [`.insert()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert), or [`.update()`](https://surrealdb.com/docs/reference/java/api/core/surreal#update), the SDK reads the object's public fields and converts them into a SurrealDB object. Field names become object keys, and field values are converted to the corresponding SurrealDB types.
  * •
**Deserialization** — When you call a typed method like `db.select(Person.class, ...)` or use `Value.get(Person.class)`, the SDK creates a new instance of your class and populates its public fields from the SurrealDB object, matching by field name.

```java
public class Person {
    public RecordId id;
    public String name;
    public int age;

    public Person() {}
}

Person person = new Person();
person.name = "Tobie";
person.age = 33;

// Serialization: Person → SurrealDB object
db.create(new RecordId("person", "tobie"), person);

// Deserialization: SurrealDB object → Person
Optional<Person> result = db.select(Person.class,
    new RecordId("person", "tobie"));
```

##  POJO requirements[](https://surrealdb.com/docs/reference/java/concepts/class-converters#pojo-requirements)
For a Java class to work with the converter, it must satisfy two rules:
  1. 1.
**Public no-argument constructor** — The SDK needs to instantiate the class during deserialization.
  2. 2.
**Public fields** — Fields are matched by name to SurrealDB object keys. Private fields, getters, and setters are not used by the converter.

```java
public class Product {
    public RecordId id;
    public String name;
    public double price;
    public boolean active;

    public Product() {}
}
```

Fields that exist in the Java class but not in the SurrealDB object are left at their Java default value (`null` for objects, `0` for numbers, `false` for booleans). Fields in the SurrealDB object that have no matching Java field are silently ignored.
##  Field type mapping[](https://surrealdb.com/docs/reference/java/concepts/class-converters#field-type-mapping)
POJO fields and bound values are mapped to SurrealDB types based on their declared Java type:  
| Java Field/Value Type  | SurrealDB Type  | Notes  |  
| --- | --- | --- |  
| `String`  | `string`  |   |  
|  `long` / `Long`  | `int`  |   |  
|  `int` / `Integer`  | `int`  | Narrowed from SurrealDB's 64-bit integer  |  
|  `double` / `Double`  | `float`  |   |  
|  `float` / `Float`  | `float`  | Narrowed from SurrealDB's 64-bit float  |  
|  `boolean` / `Boolean`  | `bool`  |   |  
| `BigDecimal`  | `decimal`  | `java.math`  |  
| `UUID`  | `uuid`  | `java.util`  |  
| `byte[]`  | `bytes`  |   |  
| `Instant`  | [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `java.time`  |  
| `ZonedDateTime`  | [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `java.time`  |  
| `OffsetDateTime`  | [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `java.time`  |  
| `LocalDateTime`  | [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `java.time`  |  
| `java.util.Date`  | [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | `java.time`  |  
| `Duration`  | [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes)  | `java.time`  |  
| [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id)  | [`record`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids)  | SDK class  |  
| [`Geometry`](https://surrealdb.com/docs/reference/java/api/values/geometry)  | [`geometry`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries)  | SDK class  |  
| [`FileRef`](https://surrealdb.com/docs/reference/java/api/values/file-ref)  | [`file`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files)  | SDK class  |  
See [Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) for the complete type mapping reference.
##  Nested objects[](https://surrealdb.com/docs/reference/java/concepts/class-converters#nested-objects)
When a POJO field is itself a class with public fields and a no-argument constructor, the converter recurses into it. This lets you model nested SurrealDB objects with nested Java classes.

```java
public class Address {
    public String street;
    public String city;
    public String country;

    public Address() {}
}

public class Person {
    public RecordId id;
    public String name;
    public Address address;

    public Person() {}
}

Person person = new Person();
person.name = "Tobie";
person.address = new Address();
person.address.street = "123 Main St";
person.address.city = "London";
person.address.country = "UK";

db.create(new RecordId("person", "tobie"), person);
```

The resulting SurrealDB record contains a nested object:

```surql
{
    id: person:tobie,
    name: "Tobie",
    address: {
        street: "123 Main St",
        city: "London",
        country: "UK"
    }
}
```

##  Temporal types[](https://surrealdb.com/docs/reference/java/concepts/class-converters#temporal-types)
SurrealDB [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) values represent an absolute point in time. When serializing Java objects, the SDK accepts `Instant`, `ZonedDateTime`, `OffsetDateTime`, `LocalDateTime`, and `java.util.Date` fields. When deserializing SurrealDB `datetime` values back into POJOs, the same types are supported; `ZonedDateTime` is the usual choice when you need the stored instant with its offset.
> Note: `LocalDateTime` does not contain a time zone or offset. The SDK interprets `LocalDateTime` values as UTC during serialization. If the value represents a user's local wall-clock time in a specific region, prefer `ZonedDateTime` or `OffsetDateTime` so the intended instant is explicit.
[`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) fields map to `java.time.Duration` in your POJOs.

```java
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.Duration;
import java.util.Date;

public class TaskWrite {
    public RecordId id;
    public String title;
    public Instant scheduledAt;
    public OffsetDateTime reviewedAt;
    public LocalDateTime localDeadline;
    public Date legacyCreatedAt;
    public Duration timeout;

    public TaskWrite() {}
}

TaskWrite task = new TaskWrite();
task.scheduledAt = Instant.parse("2026-06-06T08:00:00Z");
task.reviewedAt = OffsetDateTime.parse("2026-06-06T10:00:00+02:00");
task.localDeadline = LocalDateTime.parse("2026-06-06T10:00:00");
task.legacyCreatedAt = Date.from(task.scheduledAt);
task.timeout = Duration.ofMinutes(30);

db.create(new RecordId("task", "build"), task);
```

Use `ZonedDateTime` fields when you want the full stored instant (recommended for most read paths). `Instant`, `OffsetDateTime`, and `LocalDateTime` also work on deserialization:

```java
import java.time.ZonedDateTime;
import java.time.Duration;

public class TaskRead {
    public RecordId id;
    public String title;
    public ZonedDateTime scheduledAt;
    public ZonedDateTime reviewedAt;
    public ZonedDateTime localDeadline;
    public ZonedDateTime legacyCreatedAt;
    public Duration timeout;

    public TaskRead() {}
}

Optional<TaskRead> task = db.select(TaskRead.class,
    new RecordId("task", "build"));
ZonedDateTime when = task.get().scheduledAt;
Duration howLong = task.get().timeout;
```

##  Relation classes[](https://surrealdb.com/docs/reference/java/concepts/class-converters#relation-classes)
Graph edges created with [`.relate()`](https://surrealdb.com/docs/reference/java/api/core/surreal#relate) or [`.insertRelation()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation) use specialized base classes that include the standard relation fields (`id`, `in`, `out`).
###  Using `Relation`[](https://surrealdb.com/docs/reference/java/concepts/class-converters#using-relation)
Extend [`Relation`](https://surrealdb.com/docs/reference/java/api/types#relation) when reading or creating edges with `.relate()`. The base class provides `id`, `in`, and `out` as `RecordId` fields.

```java
public class Likes extends Relation {
    public String createdAt;
}

Likes like = db.relate(
    Likes.class,
    new RecordId("person", "alice"),
    "likes",
    new RecordId("post", "post1")
);
```

###  Using `InsertRelation`[](https://surrealdb.com/docs/reference/java/concepts/class-converters#using-insertrelation)
Extend [`InsertRelation`](https://surrealdb.com/docs/reference/java/api/types#insert-relation) when inserting edges with `.insertRelation()`. The base class provides `id` as an [`Id`](https://surrealdb.com/docs/reference/java/api/values/record-id#id) and `in` / `out` as `RecordId` fields.

```java
public class Follows extends InsertRelation {
    public ZonedDateTime since;

    public Follows() {}
}

Follows follow = new Follows();
follow.in = new RecordId("person", "alice");
follow.out = new RecordId("person", "bob");
follow.since = ZonedDateTime.now();

db.insertRelation(Follows.class, "follows", follow);
```

##  Where conversion is available[](https://surrealdb.com/docs/reference/java/concepts/class-converters#where-conversion-is-available)
Typed conversion is available across most SDK methods. Any method that accepts a `Class` parameter uses the converter:  
| Method  | Typed variant  |  
| --- | --- |  
| [`db.select(target)`](https://surrealdb.com/docs/reference/java/api/core/surreal#select)  | `db.select(Class, target)`  |  
| [`db.create(target, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#create)  | `db.create(Class, target, content)`  |  
| [`db.insert(target, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert)  | `db.insert(Class, target, content)`  |  
| [`db.update(target, upType, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#update)  | `db.update(Class, target, upType, content)`  |  
| [`db.upsert(target, upType, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert)  | `db.upsert(Class, target, upType, content)`  |  
| [`db.relate(from, table, to)`](https://surrealdb.com/docs/reference/java/api/core/surreal#relate)  | `db.relate(Class, from, table, to)`  |  
| [`response.take(index)`](https://surrealdb.com/docs/reference/java/api/core/response#take)  | `response.take(Class, index)`  |  
| [`value.get(Class)`](https://surrealdb.com/docs/reference/java/api/values/value#get)  |  Direct POJO conversion from a `Value`  |  
| [`array.iterator(Class)`](https://surrealdb.com/docs/reference/java/api/values/value#array-typed-iterator)  | Typed iteration over array elements  |  
##  Handling conversion errors[](https://surrealdb.com/docs/reference/java/concepts/class-converters#handling-conversion-errors)
When the SDK cannot convert a value to the target class — for example, because a field type is incompatible or the class is missing a no-argument constructor — it throws a [`SerializationException`](https://surrealdb.com/docs/reference/java/api/errors#serialization-exception). You can catch this specifically or handle it as part of the general [`SurrealException`](https://surrealdb.com/docs/reference/java/api/errors) hierarchy.

```java
try {
        Optional<Person> person = db.select(Person.class,
        new RecordId("person", "tobie"));
} catch (SerializationException e) {
    System.err.println("Conversion failed: " + e.getMessage());
}
```

See [Error handling](https://surrealdb.com/docs/reference/java/concepts/error-handling) for more on the exception hierarchy.
##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/class-converters#learn-more)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) for the complete SurrealDB-to-Java type mapping
  * •
[Data manipulation](https://surrealdb.com/docs/reference/java/concepts/data-manipulation) for using converted types with CRUD operations
  * •
[Value API reference](https://surrealdb.com/docs/reference/java/api/values/value) for the `Value.get(Class)` method
  * •
[Response API reference](https://surrealdb.com/docs/reference/java/api/core/response) for typed response extraction
  * •
[Java Types reference](https://surrealdb.com/docs/reference/java/api/types) for `Relation`, `InsertRelation`, and other SDK types
  * •
[Error handling](https://surrealdb.com/docs/reference/java/concepts/error-handling) for serialization error details
