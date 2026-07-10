---
title: "https://surrealdb.com/docs/reference/java/concepts/data-manipulation"
url: "https://surrealdb.com/docs/reference/java/concepts/data-manipulation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/data-manipulation

Source: https://surrealdb.com/docs/reference/java/concepts/data-manipulation

The Java SDK provides dedicated methods for common CRUD operations on records and tables. These methods offer a structured alternative to writing raw [SurrealQL](https://surrealdb.com/docs/reference/query-language), with built-in type safety through Java generics and POJO deserialization.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.create(target, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#create)  | Creates one or more records  |  
| [`db.select(target)`](https://surrealdb.com/docs/reference/java/api/core/surreal#select)  | Selects records from a table or by ID  |  
| [`db.insert(target, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert)  | Inserts one or more records  |  
| [`db.update(target, upType, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#update)  | Updates records  |  
| [`db.upsert(target, upType, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert)  | Updates or creates records  |  
| [`db.delete(target)`](https://surrealdb.com/docs/reference/java/api/core/surreal#delete)  | Deletes records  |  
| [`db.relate(from, table, to)`](https://surrealdb.com/docs/reference/java/api/core/surreal#relate)  | Creates a graph relation  |  
| [`db.insertRelation(target, content)`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation)  | Inserts a relation record  |  
##  Defining model classes[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#defining-model-classes)
Data manipulation methods can work with POJOs (Plain Old Java Objects) for type-safe access. Model classes need a public no-argument constructor and fields that map to SurrealDB object keys. Use a [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id) field named `id` to hold the record identifier.

```java
public class Person {
    public RecordId id;
    public String name;
    public int age;

    public Person() {}
}
```

##  Creating records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#creating-records)
The [`.create()`](https://surrealdb.com/docs/reference/java/api/core/surreal#create) method creates new records. When called with a table name, SurrealDB generates a random ID and returns a list. When called with a [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id), the record is created with that specific ID and a single result is returned.

```java
Person alice = new Person();
alice.name = "Alice";
alice.age = 30;

// Create with a generated ID — returns List<Value>
List<Value> created = db.create("person", alice);

// Create with a specific ID — returns Value
Value tobie = db.create(new RecordId("person", "tobie"), alice);

// Typed variant — returns List<Person>
List<Person> typed = db.create(Person.class, "person", alice);
```

##  Selecting records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#selecting-records)
The [`.select()`](https://surrealdb.com/docs/reference/java/api/core/surreal#select) method reads records from the database. When called with a table name, it returns an `Iterator`. When called with a `RecordId`, it returns an `Optional`.

```java
// Select all records from a table
Iterator<Value> all = db.select("person");

// Select a specific record
Optional<Value> one = db.select(new RecordId("person", "tobie"));

// Typed variants
Iterator<Person> allTyped = db.select(Person.class, "person");
Optional<Person> oneTyped = db.select(Person.class, new RecordId("person", "tobie"));
```

Use `selectSync()` instead of `select()` when you need thread-safe iteration over the results.
##  Inserting records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#inserting-records)
The [`.insert()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert) method inserts one or more records into a table using varargs. This is more efficient than calling `.create()` in a loop for bulk operations.

```java
Person alice = new Person();
alice.name = "Alice";
alice.age = 30;

Person bob = new Person();
bob.name = "Bob";
bob.age = 25;

List<Value> inserted = db.insert("person", alice, bob);
```

Use [`.insertRelation()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation) to insert graph edge records. See [Creating graph relations](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#creating-graph-relations) for details.
##  Updating records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#updating-records)
The [`.update()`](https://surrealdb.com/docs/reference/java/api/core/surreal#update) method modifies existing records. You specify the update strategy using the [`UpType`](https://surrealdb.com/docs/reference/java/api/types#up-type) enum:  
| UpType  | Behavior  |  
| --- | --- |  
| `UpType.CONTENT`  | Replaces the entire record with the new content  |  
| `UpType.MERGE`  | Merges new fields into the existing record  |  
| `UpType.PATCH`  | Applies a JSON Patch to the record  |  

```java
Person updated = new Person();
updated.name = "Alice Smith";
updated.age = 31;

// Replace the entire record
db.update(new RecordId("person", "alice"), UpType.CONTENT, updated);

// Merge fields into the existing record
db.update(new RecordId("person", "alice"), UpType.MERGE, Map.of("age", 31));

// Update all records in a table
db.update("person", UpType.MERGE, Map.of("active", true));

// Typed variant
Person result = db.update(
    Person.class, new RecordId("person", "alice"), UpType.CONTENT, updated
);
```

##  Upserting records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#upserting-records)
The [`.upsert()`](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert) method works like `.update()` but creates the record if it does not already exist. It accepts the same [`UpType`](https://surrealdb.com/docs/reference/java/api/types#up-type) strategies.

```java
Person person = new Person();
person.name = "Charlie";
person.age = 28;

db.upsert(new RecordId("person", "charlie"), UpType.CONTENT, person);
```

##  Deleting records[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#deleting-records)
The [`.delete()`](https://surrealdb.com/docs/reference/java/api/core/surreal#delete) method removes records from the database. You can delete a single record by [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id), multiple records by passing several `RecordId` values, a range of records with [`RecordIdRange`](https://surrealdb.com/docs/reference/java/api/values/record-id#record-id-range), or all records in a table by passing the table name.

```java
// Delete a single record
db.delete(new RecordId("person", "tobie"));

// Delete multiple specific records
db.delete(new RecordId("person", "alice"), new RecordId("person", "bob"));

// Delete a range of records
db.delete(new RecordIdRange("person", Id.from("a"), Id.from("f")));

// Delete all records in a table
db.delete("person");
```

##  Creating graph relations[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#creating-graph-relations)
The [`.relate()`](https://surrealdb.com/docs/reference/java/api/core/surreal#relate) method creates edges between records in SurrealDB's [graph model](https://surrealdb.com/docs/reference/query-language/statements/relate). You specify the source record, the edge table, and the target record. Optionally, you can attach content to the edge.

```java
db.relate(
    new RecordId("person", "tobie"),
    "likes",
    new RecordId("post", 1)
);

// With content on the edge
db.relate(
    new RecordId("person", "tobie"),
    "likes",
    new RecordId("post", 1),
    Map.of("timestamp", "2026-02-27T12:00:00Z")
);
```

You can also use [`.insertRelation()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation) to insert relation records with `in` and `out` fields, similar to how `.insert()` works for regular records.

```java
public class Likes extends InsertRelation {
    public String timestamp;

    public Likes() {}
}

Likes like = new Likes();
like.in = new RecordId("person", "tobie");
like.out = new RecordId("post", 1);
like.timestamp = "2026-02-27T12:00:00Z";

db.insertRelation(Likes.class, "likes", like);
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/data-manipulation#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal) for complete method signatures
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) for type mappings and the Value class
  * •
[Executing queries](https://surrealdb.com/docs/reference/java/concepts/executing-queries) for custom SurrealQL queries
  * •
[RecordId reference](https://surrealdb.com/docs/reference/java/api/values/record-id) for record identifier details
  * •
[SurrealQL SELECT](https://surrealdb.com/docs/reference/query-language/statements/select), [CREATE](https://surrealdb.com/docs/reference/query-language/statements/create), [UPDATE](https://surrealdb.com/docs/reference/query-language/statements/update), [DELETE](https://surrealdb.com/docs/reference/query-language/statements/delete) for the underlying query statements
  * •
[SurrealQL RELATE](https://surrealdb.com/docs/reference/query-language/statements/relate) for graph relation syntax
  * •
[Record IDs](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) for SurrealDB record identifier formats
