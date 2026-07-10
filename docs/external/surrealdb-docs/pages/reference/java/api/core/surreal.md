---
title: "https://surrealdb.com/docs/reference/java/api/core/surreal"
url: "https://surrealdb.com/docs/reference/java/api/core/surreal"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/core/surreal

Source: https://surrealdb.com/docs/reference/java/api/core/surreal

The `Surreal` class is the main entry point for the Java SDK. It provides methods for connecting to a SurrealDB instance, authenticating, querying, and managing data. The class implements `AutoCloseable`, so it can be used in a try-with-resources block to ensure the connection is closed automatically.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Connection methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#connection-methods)
###  `Surreal()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#constructor)
Creates a new `Surreal` instance. The instance is not connected to any server until `.connect()` is called.
Method Syntax

```java
Surreal db = new Surreal();
```

**Returns:** `Surreal`
Example

```java
Surreal db = new Surreal();
```

###  `.connect(url)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#connect)
Connects the instance to a SurrealDB server using the specified URL. The URL scheme determines the connection protocol. See the [start command](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) documentation for server configuration options.
Method Syntax

```java
db.connect(url)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `String`  |  The connection URL. Supported schemes: `ws://`, `wss://`, `http://`, `https://`, `memory://`, `surrealkv://`.  |  
**Returns:** `Surreal` (for method chaining)
Example

```java
db.connect("ws://localhost:8000");
```

###  `.close()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#close)
Closes the active connection and releases all associated resources. This is called automatically when using try-with-resources.
Method Syntax

```java
db.close()
```

**Returns:** `void`
Example

```java
db.close();
```

###  `.useNs(namespace)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#use-ns)
Switches the connection to a specific namespace.
Method Syntax

```java
db.useNs(ns)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ns`  | `String`  | The namespace to switch to.  |  
**Returns:** `Surreal` (for method chaining)
Example

```java
db.useNs("surrealdb").useDb("docs");
```

###  `.useDb(database)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#use-db)
Switches the connection to a specific database.
Method Syntax

```java
db.useDb(database)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `db`  | `String`  | The database to switch to.  |  
**Returns:** `Surreal` (for method chaining)
Example

```java
db.useDb("docs");
```

###  `.useDefaults()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#use-defaults)
Resets the namespace and database to the server defaults.
Method Syntax

```java
db.useDefaults()
```

**Returns:** `Surreal` (for method chaining)
Example

```java
db.useDefaults();
```

###  `.getNamespace()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#get-namespace)
Returns the namespace currently in use on this connection.
Method Syntax

```java
db.getNamespace()
```

**Returns:** `String`
Example

```java
String ns = db.getNamespace();
```

###  `.getDatabase()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#get-database)
Returns the database currently in use on this connection.
Method Syntax

```java
db.getDatabase()
```

**Returns:** `String`
Example

```java
String database = db.getDatabase();
```

###  `.newSession()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#new-session)
Creates a new isolated session that shares the underlying connection but maintains its own namespace, database, authentication state, and variables.
Method Syntax

```java
db.newSession()
```

**Returns:** `Surreal`
Example

```java
Surreal session = db.newSession();
session.useNs("other_ns").useDb("other_db");
```

* * *
##  Authentication methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#authentication-methods)
###  `.signin(credential)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#signin)
Signs in to the database with the provided credentials. The credential type determines the authentication level: root, namespace, database, or record access.
Method Syntax

```java
db.signin(credential)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `credential`  | `Credential`  |  The credentials to sign in with. Use `RootCredential`, `NamespaceCredential`, `DatabaseCredential`, or `RecordCredential`.  |  
**Returns:** `Token`
Example

```java
Token token = db.signin(new RootCredential("root", "root"));
```

###  `.signup(credential)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#signup)
Signs up a new record user using a record access method defined with [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access).
Method Syntax

```java
db.signup(credential)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `credential`  | `RecordCredential`  | The record access credentials including namespace, database, access method, and any additional fields required by the access definition.  |  
**Returns:** `Token`
Example

```java
Token token = db.signup(new RecordCredential(
    "surrealdb", "docs", "user_access",
    Map.of("email", "user@example.com", "password", "s3cret")
));
```

###  `.authenticate(token)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#authenticate)
Authenticates the current connection using an existing JWT token.
Method Syntax

```java
db.authenticate(token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `token`  | `String`  | A valid JWT token string.  |  
**Returns:** `Surreal` (for method chaining)
Example

```java
db.authenticate("eyJhbGciOiJIUzI1NiIs...");
```

###  `.invalidate()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#invalidate)
Invalidates the current authentication, removing the associated session token.
Method Syntax

```java
db.invalidate()
```

**Returns:** `Surreal` (for method chaining)
Example

```java
db.invalidate();
```

* * *
##  Query methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#query-methods)
###  `.query(sql)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#query)
Executes one or more SurrealQL statements and returns a `Response` containing the results of each statement.
Method Syntax

```java
db.query(sql)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `sql`  | `String`  | The SurrealQL query string to execute.  |  
**Returns:** [`Response`](https://surrealdb.com/docs/reference/java/api/core/response)
Example

```java
Response response = db.query("SELECT * FROM users");
List<User> users = response.take(User.class, 0);
```

###  `.queryBind(sql, params)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#query-bind)
Executes a parameterised SurrealQL query. Parameters are safely injected into the query, preventing SurrealQL injection.
Method Syntax

```java
db.queryBind(sql, params)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `sql`  | `String`  | The SurrealQL query string with parameter placeholders.  |  
| `params`  | `Map<String, ?>`  | A map of parameter names to values.  |  
**Returns:** [`Response`](https://surrealdb.com/docs/reference/java/api/core/response)
Example

```java
Response response = db.queryBind(
    "SELECT * FROM users WHERE age > $min_age",
    Map.of("min_age", 18)
);
```

###  `.run(name, args)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#run)
Runs a server-side SurrealDB function defined with [`DEFINE FUNCTION`](https://surrealdb.com/docs/reference/query-language/statements/define/function).
Method Syntax

```java
db.run(name, args)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `String`  |  The function name (e.g. `"fn::calculate_total"`).  |  
| `args`  | `Object...`  | Arguments to pass to the function.  |  
**Returns:** `Value`
Example

```java
Value result = db.run("fn::calculate_total", 100, 0.2);
```

* * *
##  Data methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#data-methods)
Note
Most data methods have multiple overloads. The typed variants accepting `Class<T>` are shown below. Untyped variants returning `Value` or `Iterator<Value>` are also available.
###  `.create(type, target, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#create)
Creates one or more records. When called with a table name, SurrealDB generates random IDs. When called with a `RecordId`, the record is created with that specific ID.
Method Syntax

```java
<T> List<T> create(Class<T> type, String target, T... contents)
<T> T create(Class<T> type, RecordId recordId, T content)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  |  `String`or `RecordId`  | The table name or specific record ID.  |  
| `contents`  |  `T`or `T...`  | The record content(s) to create.  |  
**Returns:** `List` (table target) or `T` (record ID target)
Example

```java
Person alice = new Person();
alice.name = "Alice";
alice.age = 30;

List<Person> created = db.create(Person.class, "person", alice);

Person specific = db.create(Person.class, new RecordId("person", "tobie"), alice);
```

###  `.select(type, target)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#select)
Selects records from a table or retrieves specific records by ID.
Method Syntax

```java
<T> Iterator<T> select(Class<T> type, String target)
<T> Optional<T> select(Class<T> type, RecordId recordId)
<T> List<T> select(Class<T> type, RecordId... recordIds)
<T> List<T> select(Class<T> type, RecordIdRange range)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  |  `String`, `RecordId`, `RecordId...`, or `RecordIdRange`  | The table name, a single record ID, multiple record IDs, or a record ID range.  |  
**Returns:** `Iterator` (table), `Optional` (single ID), `List` (multiple IDs or range)
Example

```java
Iterator<Person> all = db.select(Person.class, "person");

Optional<Person> one = db.select(Person.class, new RecordId("person", "tobie"));

List<Person> range = db.select(Person.class,
    new RecordIdRange("person", Id.from("a"), Id.from("m")));
```

###  `.selectSync(type, target)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#select-sync)
Thread-safe variant of [`.select()`](https://surrealdb.com/docs/reference/java/api/core/surreal#select) for table-level queries. Returns a synchronized iterator safe for use across multiple threads.
Method Syntax

```java
<T> Iterator<T> selectSync(Class<T> type, String target)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  | `String`  | The table name to select from.  |  
**Returns:** `Iterator` (synchronized)
Example

```java
Iterator<Person> all = db.selectSync(Person.class, "person");
```

###  `.insert(type, target, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#insert)
Inserts one or more records into a table.
Method Syntax

```java
<T> List<T> insert(Class<T> type, String target, T... contents)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  | `String`  | The table to insert into.  |  
| `contents`  | `T...`  | The record content(s) to insert.  |  
**Returns:** `List`
Example

```java
Person alice = new Person();
alice.name = "Alice";

List<Person> inserted = db.insert(Person.class, "person", alice);
```

###  `.update(type, target, upType, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#update)
Updates existing records. Use `UpType.CONTENT` to replace the entire record, `UpType.MERGE` to merge fields into the existing record, or `UpType.PATCH` to apply a JSON Patch.
Method Syntax

```java
<T> T update(Class<T> type, RecordId recordId, UpType upType, T content)
<T> Iterator<T> update(Class<T> type, String target, UpType upType, T content)
<T> Value update(RecordIdRange range, UpType upType, T content)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  |  `RecordId`, `RecordIdRange`, or `String`  | The record ID, record ID range, or table name to update.  |  
| `upType`  | `UpType`  |  The update strategy: `UpType.CONTENT`(replace), `UpType.MERGE`(merge), or `UpType.PATCH`(JSON Patch).  |  
| `content`  | `T`  | The update content.  |  
**Returns:** `T` (single record) or `Iterator` (table)
Example

```java
Person updated = new Person();
updated.name = "Alice Smith";
updated.age = 31;

Person result = db.update(Person.class, new RecordId("person", "alice"), UpType.CONTENT, updated);
```

###  `.updateSync(type, target, upType, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#update-sync)
Thread-safe variant of [`.update()`](https://surrealdb.com/docs/reference/java/api/core/surreal#update) for table-level updates. Returns a synchronized iterator safe for use across multiple threads.
Method Syntax

```java
<T> Iterator<T> updateSync(Class<T> type, String target, UpType upType, T content)
```

**Returns:** `Iterator` (synchronized)
Example

```java
Iterator<Person> results = db.updateSync(Person.class, "person", UpType.MERGE, updates);
```

###  `.upsert(type, target, upType, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert)
Updates an existing record or creates a new one if it does not exist. Accepts the same parameters as [`.update()`](https://surrealdb.com/docs/reference/java/api/core/surreal#update).
Method Syntax

```java
<T> T upsert(Class<T> type, RecordId recordId, UpType upType, T content)
<T> Iterator<T> upsert(Class<T> type, String target, UpType upType, T content)
<T> Value upsert(RecordIdRange range, UpType upType, T content)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The class to deserialize results into.  |  
| `target`  |  `RecordId`, `RecordIdRange`, or `String`  | The record ID, record ID range, or table name to upsert.  |  
| `upType`  | `UpType`  |  The update strategy: `UpType.CONTENT`(replace), `UpType.MERGE`(merge), or `UpType.PATCH`(JSON Patch).  |  
| `content`  | `T`  | The record content.  |  
**Returns:** `T` (single record) or `Iterator` (table)
Example

```java
Person person = new Person();
person.name = "Alice";
person.age = 30;

Person result = db.upsert(Person.class, new RecordId("person", "alice"), UpType.CONTENT, person);
```

###  `.upsertSync(type, target, upType, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert-sync)
Thread-safe variant of [`.upsert()`](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert) for table-level upserts. Returns a synchronized iterator safe for use across multiple threads.
Method Syntax

```java
<T> Iterator<T> upsertSync(Class<T> type, String target, UpType upType, T content)
```

**Returns:** `Iterator` (synchronized)
Example

```java
Iterator<Person> results = db.upsertSync(Person.class, "person", UpType.CONTENT, person);
```

###  `.delete(target)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#delete)
Deletes records from the database. Supports deleting a single record, multiple records by ID, a range of records, or all records in a table.
Method Syntax

```java
void delete(RecordId recordId)
void delete(RecordId... recordIds)
void delete(RecordIdRange range)
void delete(String target)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `target`  |  `RecordId`, `RecordId...`, `RecordIdRange`, or `String`  | A single record ID, multiple record IDs, a record ID range, or a table name.  |  
**Returns:** `void`
Example

```java
db.delete(new RecordId("person", "tobie"));

db.delete(new RecordId("person", "alice"), new RecordId("person", "bob"));

db.delete(new RecordIdRange("person", Id.from("a"), Id.from("f")));

db.delete("temp_data");
```

###  `.relate(from, table, to)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#relate)
Creates a graph relation between two records.
Method Syntax

```java
Value relate(RecordId from, String table, RecordId to)
<T extends Relation> T relate(Class<T> type, RecordId from, String table, RecordId to)
<T> Value relate(RecordId from, String table, RecordId to, T content)
<R extends Relation, T> R relate(Class<R> type, RecordId from, String table, RecordId to, T content)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T extends Relation>`  |  The class to deserialize the relation into. Omit for untyped `Value`return.  |  
| `from`  | `RecordId`  | The source record.  |  
| `table`  | `String`  | The relation table name.  |  
| `to`  | `RecordId`  | The target record.  |  
| `content`  | `T`  | Additional data to attach to the edge record.  |  
**Returns:** `Value` or `T`
Example

```java
Value relation = db.relate(
    new RecordId("person", "alice"),
    "likes",
    new RecordId("post", "post1")
);

Value withContent = db.relate(
    new RecordId("person", "alice"),
    "likes",
    new RecordId("post", "post1"),
    Map.of("timestamp", "2026-01-01T00:00:00Z")
);
```

###  `.insertRelation(target, content)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation)
Inserts a relation record into a relation table with additional data.
Method Syntax

```java
<T extends InsertRelation> T insertRelation(Class<T> type, String target, T content)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T extends InsertRelation>`  | The relation class to deserialize into.  |  
| `target`  | `String`  | The relation table name.  |  
| `content`  | `T`  |  The relation content, including `in`and `out`fields.  |  
**Returns:** `T`
Example

```java
Likes like = new Likes();
like.in = new RecordId("person", "alice");
like.out = new RecordId("post", "post1");
like.createdAt = "2025-01-01T00:00:00Z";

Likes result = db.insertRelation(Likes.class, "likes", like);
```

###  `.insertRelations(target, contents)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relations)
Inserts multiple relation records into a relation table using varargs.
Method Syntax

```java
<T extends InsertRelation> List<T> insertRelations(Class<T> type, String target, T... contents)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T extends InsertRelation>`  | The relation class to deserialize into.  |  
| `target`  | `String`  | The relation table name.  |  
| `contents`  | `T...`  |  The relation records to insert, each including `in`and `out`fields.  |  
**Returns:** `List`
Example

```java
Likes like1 = new Likes();
like1.in = new RecordId("person", "alice");
like1.out = new RecordId("post", "post1");

Likes like2 = new Likes();
like2.in = new RecordId("person", "alice");
like2.out = new RecordId("post", "post2");

List<Likes> results = db.insertRelations(Likes.class, "likes", like1, like2);
```

* * *
##  Live query methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#live-query-methods)
Note
Live queries require a WebSocket connection (`ws://` or `wss://`).
###  `.selectLive(table)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#select-live)
Starts a live query that receives real-time notifications when records in the specified table are created, updated, or deleted.
Method Syntax

```java
db.selectLive(table)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `String`  | The table to watch for changes.  |  
**Returns:** [`LiveStream`](https://surrealdb.com/docs/reference/java/api/core/live-stream)
Example

```java
LiveStream stream = db.selectLive("person");
```

* * *
##  Transaction methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#transaction-methods)
###  `.beginTransaction()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#begin-transaction)
Starts a new atomic transaction. All operations performed on the returned `Transaction` are grouped and only applied when committed.
Method Syntax

```java
db.beginTransaction()
```

**Returns:** [`Transaction`](https://surrealdb.com/docs/reference/java/api/core/transaction)
Example

```java
Transaction tx = db.beginTransaction();
```

* * *
##  Utility methods[](https://surrealdb.com/docs/reference/java/api/core/surreal#utility-methods)
###  `.version()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#version)
Returns the version string of the connected SurrealDB server.
Method Syntax

```java
db.version()
```

**Returns:** `String`
Example

```java
String version = db.version();
```

###  `.health()`[](https://surrealdb.com/docs/reference/java/api/core/surreal#health)
Checks the health of the connected SurrealDB server.
Method Syntax

```java
db.health()
```

**Returns:** `boolean`
Example

```java
boolean healthy = db.health();
```

###  `.exportSql(path)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#export-sql)
Exports the current database to a file at the specified path.
Method Syntax

```java
db.exportSql(path)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `String`  | The file path to export the database to.  |  
**Returns:** `boolean`
Example

```java
boolean success = db.exportSql("/tmp/backup.surql");
```

###  `.importSql(path)`[](https://surrealdb.com/docs/reference/java/api/core/surreal#import-sql)
Imports a database from a file at the specified path.
Method Syntax

```java
db.importSql(path)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `String`  | The file path to import the database from.  |  
**Returns:** `boolean`
Example

```java
boolean success = db.importSql("/tmp/backup.surql");
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/core/surreal#see-also)
  * •
[Transaction](https://surrealdb.com/docs/reference/java/api/core/transaction) — Transaction reference
  * •
[Response](https://surrealdb.com/docs/reference/java/api/core/response) — Query response reference
  * •
[LiveStream](https://surrealdb.com/docs/reference/java/api/core/live-stream) — Live query reference
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) — Connection protocols and patterns
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) — Authentication concepts
  * •
[SurrealQL](https://surrealdb.com/docs/reference/query-language) — Query language reference
  * •
[DEFINE USER](https://surrealdb.com/docs/reference/query-language/statements/define/user) — System user configuration
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) — Record access method configuration
