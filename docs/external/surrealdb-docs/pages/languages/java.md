---
title: "https://surrealdb.com/docs/languages/java"
url: "https://surrealdb.com/docs/languages/java"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/java

Source: https://surrealdb.com/docs/languages/java

The Java SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/java#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/java/installation) to install the SDK as a dependency in your project. Once installed, import the SDK to start using it.

```java
import com.surrealdb.Surreal;
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/java#2-connect-to-surrealdb)
Use a try-with-resources block to create a connection, then call [`.useNs()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-ns) and [`.useDb()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-db) to select a namespace and database, and [`.signin()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signin) to authenticate.
Supported connection protocols include:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived stateful connections
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections
  * •
**Embedded** (`memory`, `surrealkv://`) for in-process databases

```java
import com.surrealdb.Surreal;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("company_name").useDb("project_name");
    db.signin(new RootCredential("root", "root"));
}
```

The [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) class implements `AutoCloseable`, so the connection is automatically closed at the end of the try-with-resources block.
##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/java#3-inserting-data-into-surrealdb)
To represent database records in your application, define [POJO](https://wikipedia.org/wiki/Plain_old_Java_object) classes that match your table structure. A public no-argument constructor is required. Use a [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id) field named `id` to hold the record identifier.

```java
import com.surrealdb.RecordId;

public class Person {
    public RecordId id;
    public String name;
    public int age;

    public Person() {
    }

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
```

Use [`.create()`](https://surrealdb.com/docs/reference/java/api/core/surreal#create) to insert records into a table. When passing a table name, the method returns a list of created records with generated IDs.

```java
Person person = new Person("John", 32);
List<Person> created = db.create(Person.class, "persons", person);
```

To create a record with a specific ID, pass a [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id) instead. This returns the created record directly.

```java
Person created = db.create(Person.class, new RecordId("persons", "john"), person);
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/java#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/java#selecting-records)
The [`.select()`](https://surrealdb.com/docs/reference/java/api/core/surreal#select) method retrieves all records from a table, or a single record by its `RecordId`.

```java
Iterator<Person> persons = db.select(Person.class, "persons");

Optional<Person> john = db.select(Person.class, new RecordId("persons", "john"));
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/java#running-surrealql-queries)
For more advanced use cases, use the [`.queryBind()`](https://surrealdb.com/docs/reference/java/api/core/surreal#query-bind) method to execute [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements with bound [parameters](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters).

```java
Response response = db.queryBind(
    "SELECT * FROM persons WHERE age > $min_age",
    Map.of("min_age", 25)
);

Value result = response.take(0);
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/java#5-closing-the-connection)
If you use a try-with-resources block as shown above, the connection is closed automatically. Otherwise, call [`.close()`](https://surrealdb.com/docs/reference/java/api/core/surreal#close) manually to release resources.

```java
db.close();
```

##  Next steps[](https://surrealdb.com/docs/languages/java#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connection management Learn how to manage your database connections, including protocols and embedded mode.](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb)[Authentication Read more about authentication and how to integrate it into your application.](https://surrealdb.com/docs/reference/java/concepts/authentication)[Data manipulation Learn how to create, read, update, and delete records using the SDK.](https://surrealdb.com/docs/reference/java/concepts/data-manipulation)[API Reference Complete reference for all classes, methods, types, and errors.](https://surrealdb.com/docs/reference/java/api/core/surreal)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Java SDK reference](https://surrealdb.com/docs/reference/java).
