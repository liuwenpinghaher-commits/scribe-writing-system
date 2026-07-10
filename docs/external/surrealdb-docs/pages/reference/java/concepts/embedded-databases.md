---
title: "https://surrealdb.com/docs/reference/java/concepts/embedded-databases"
url: "https://surrealdb.com/docs/reference/java/concepts/embedded-databases"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/embedded-databases

Source: https://surrealdb.com/docs/reference/java/concepts/embedded-databases

The Java SDK can run SurrealDB as an embedded in-process database, eliminating the need for a separate server. Embedded databases use JNI to run the SurrealDB engine directly within your application, which removes network overhead and simplifies deployment for testing, prototyping, and standalone applications.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.connect(url)`](https://surrealdb.com/docs/reference/java/api/core/surreal#connect)  | Connects using an embedded protocol  |  
| [`db.exportSql(path)`](https://surrealdb.com/docs/reference/java/api/core/surreal#export-sql)  | Exports the database to a file  |  
| [`db.importSql(path)`](https://surrealdb.com/docs/reference/java/api/core/surreal#import-sql)  | Imports data from a file  |  
##  Running an in-memory database[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#running-an-in-memory-database)
Use the `memory://` scheme to start an in-memory embedded database. All data is stored in memory and is lost when the connection closes. This is ideal for unit tests and rapid prototyping where persistence is not required.

```java
try (Surreal db = new Surreal()) {
    db.connect("memory://");
    db.useNs("main").useDb("main");
}
```

##  Running a disk-based database[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#running-a-disk-based-database)
Use the `surrealkv://` scheme with a file path to start a disk-based embedded database. Data is persisted to the specified directory and survives application restarts.

```java
try (Surreal db = new Surreal()) {
    db.connect("surrealkv://path/to/database");
    db.useNs("app").useDb("main");
}
```

##  Exporting and importing data[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#exporting-and-importing-data)
The [`.exportSql()`](https://surrealdb.com/docs/reference/java/api/core/surreal#export-sql) method writes the current database contents to a SurrealQL file. The [`.importSql()`](https://surrealdb.com/docs/reference/java/api/core/surreal#import-sql) method reads a SurrealQL file and applies it to the database.

```java
try (Surreal db = new Surreal()) {
    db.connect("surrealkv://path/to/database");
    db.useNs("app").useDb("main");

    db.exportSql("backup.surql");
    db.importSql("backup.surql");
}
```

##  When to use embedded databases[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#when-to-use-embedded-databases)
Embedded databases are well suited for scenarios where running a separate SurrealDB server is unnecessary or impractical:
  * •
**Testing** — use `memory://` for fast, isolated tests that start with a clean database on every run.
  * •
**Desktop and mobile applications** — use `surrealkv://` to bundle a persistent database directly within the application.
  * •
**CLI tools** — embed a database to store local state or configuration without requiring users to install SurrealDB.
  * •
**Prototyping** — iterate quickly without managing a server process.

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/embedded-databases#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal) for complete method signatures
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for all connection protocols
  * •
[SurrealDB deployment](https://surrealdb.com/docs/build/deployment) for production server deployment
  * •
[SurrealDB CLI start](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) for server configuration and storage backends
  * •
[SurrealDB CLI import](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) and [export](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export) for command-line data management
