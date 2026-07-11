---
title: "https://surrealdb.com/docs/reference/rust/embedding"
url: "https://surrealdb.com/docs/reference/rust/embedding"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/embedding

Source: https://surrealdb.com/docs/reference/rust/embedding

SurrealDB is designed to be run in many different ways and in many environments. Due to the [separation of the storage and API layers](https://surrealdb.com/docs/architecture), SurrealDB can be run in embedded mode, from within a number of different language environments. In Rust, SurrealDB can be run as an in-memory database, it can persist data using a file-based storage engine, or on a distributed cluster.
##  Install the SDK[](https://surrealdb.com/docs/reference/rust/embedding#install-the-sdk)
First, create a new project using `cargo new` and add the SurrealDB crate to your dependencies, enabling the key-value store you need:

```sh
# For an in memory database
cargo add surrealdb --features kv-mem

# For a RocksDB file
cargo add surrealdb --features kv-rocksdb
```

You will need to add the following additional dependencies:

```bash
cargo add serde --features derive
cargo add tokio --features macros,rt-multi-thread
```

  

##  Connect to SurrealDB[](https://surrealdb.com/docs/reference/rust/embedding#connect-to-surrealdb)
Open `src/main.rs` and replace everything in there with the following code to try out some basic operations using the SurrealDB SDK with an embedded database. Look at [integrations to connect to a database](https://surrealdb.com/docs/reference/rust/overview).

```rust
use serde::{Deserialize, Serialize};
use surrealdb::types::RecordId;
use surrealdb::Surreal;

// For an in memory database
use surrealdb::engine::local::Mem;

// For a RocksDB file
// use surrealdb::engine::local::RocksDb;

#[derive(Debug, Serialize)]
struct Name<'a> {
    first: &'a str,
    last: &'a str,
}

#[derive(Debug, Serialize)]
struct Person<'a> {
    title: &'a str,
    name: Name<'a>,
    marketing: bool,
}

#[derive(Debug, Serialize)]
struct Responsibility {
    marketing: bool,
}

#[derive(Debug, Deserialize)]
struct Record {
    #[allow(dead_code)]
    id: RecordId,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Create database connection in memory
    let db = Surreal::new::<Mem>(()).await?;
    
    // Create database connection using RocksDB
    // let db = Surreal::new::<RocksDb>("path/to/database-folder").await?;

    // Select a specific namespace / database
    db.use_ns("main").use_db("main").await?;

    // Create a new person with a random id
    let created: Option<Record> = db
        .create("person")
        .content(Person {
            title: "Founder & CEO",
            name: Name {
                first: "Tobie",
                last: "Morgan Hitchcock",
            },
            marketing: true,
        })
        .await?;
    dbg!(created);

    // Update a person record with a specific id
    let updated: Option<Record> = db
        .update(("person", "jaime"))
        .merge(Responsibility { marketing: true })
        .await?;
    dbg!(updated);

    // Select all people records
    let people: Vec<Record> = db.select("person").await?;
    dbg!(people);

    // Perform a custom advanced query
    let groups = db
        .query("SELECT marketing, count() FROM type::table($table) GROUP BY marketing")
        .bind(("table", "person"))
        .await?;
    dbg!(groups);

    Ok(())
}
```

Run your program from the command line with:

```sh
cargo run
```

  

##  SDK methods[](https://surrealdb.com/docs/reference/rust/embedding#sdk-methods)
The Rust SDK comes with a number of built-in functions.  
| Function  | Description  |  
| --- | --- |  
| [`Surreal::init()`](https://surrealdb.com/docs/reference/rust/embedding#init)  | Initialises a static database engine  |  
| [`db.connect(endpoint)`](https://surrealdb.com/docs/reference/rust/embedding#connect)  | Connects to a specific database endpoint, saving the connection on the static client  |  
| [{"Surreal:: (endpoint)"}](https://surrealdb.com/docs/reference/rust/embedding#new)  | Connects to a local or remote database endpoint  |  
| [`db.use_ns(namespace).use_db(database)`](https://surrealdb.com/docs/reference/rust/embedding#use-ns-db)  | Switch to a specific namespace and database  |  
| [`db.signup(credentials)`](https://surrealdb.com/docs/reference/rust/embedding#signup)  | Signs up a user using a specific record access method  |  
| [`db.signin(credentials)`](https://surrealdb.com/docs/reference/rust/embedding#signin)  | Signs this connection in using a specific access method or system user  |  
| [`db.invalidate()`](https://surrealdb.com/docs/reference/rust/embedding#invalidate)  | Invalidates the authentication for the current connection  |  
| [`db.authenticate(token)`](https://surrealdb.com/docs/reference/rust/embedding#authenticate)  | Authenticates the current connection with a JSON Web Token  |  
| [`db.set(key, val)`](https://surrealdb.com/docs/reference/rust/embedding#set)  | Assigns a value as a parameter for this connection  |  
| [`db.query(sql)`](https://surrealdb.com/docs/reference/rust/embedding#query)  | Runs a set of SurrealQL statements against the database  |  
| [`db.select(resource)`](https://surrealdb.com/docs/reference/rust/embedding#select)  | Selects all records in a table, or a specific record  |  
| [`db.create(resource).content(data)`](https://surrealdb.com/docs/reference/rust/embedding#create)  | Creates a record in the database  |  
| [`db.update(resource).content(data)`](https://surrealdb.com/docs/reference/rust/embedding#update-content)  | Updates all records in a table, or a specific record  |  
| [`db.update(resource).merge(data)`](https://surrealdb.com/docs/reference/rust/embedding#update-merge)  | Modifies all records in a table, or a specific record  |  
| [`db.update(resource).patch(data)`](https://surrealdb.com/docs/reference/rust/embedding#update-patch)  | Applies JSON Patch changes to all records in a table, or a specific record  |  
| [`db.delete(resource)`](https://surrealdb.com/docs/reference/rust/embedding#delete)  | Deletes all records, or a specific record  |  
  

##  `.init()`[](https://surrealdb.com/docs/reference/rust/embedding#init)
The DB static singleton ensures that a single database instance is available across very large or complicated applications. With the singleton, only one connection to the database is instantiated, and the database connection does not have to be shared across components or controllers.
Method Syntax

```rust
Surreal::init()
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage)

```rust
static DB: LazyLock<Surreal<Client>> = LazyLock::new(Surreal::init);

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Connect to the database
    DB.connect::<Wss>("cloud.surrealdb.com").await?;
    // Select a namespace + database
    DB.use_ns("main").use_db("main").await?;
    // Create or update a specific record
    let tobie: Option<Record> = DB
        .update(("person", "tobie"))
        .content(Person { name: "Tobie" })
        .await?;
    Ok(())
}
```

  

##  `.connect()`[](https://surrealdb.com/docs/reference/rust/embedding#connect)
Connects to a local or remote database endpoint.
Method Syntax

```rust
db.connect(endpoint)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `endpoint`  | The database endpoint to connect to.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-1)

```rust
// Connect to a local endpoint
DB.connect::<Ws>("127.0.0.1:8000").await?;
// Connect to a remote endpoint
DB.connect::<Wss>("cloud.surrealdb.com").await?;
```

  

##  `.new()`[](https://surrealdb.com/docs/reference/rust/embedding#new)
Connects to a local or remote database endpoint.
Method Syntax

```rust
Surreal::new::<T>(endpoint)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `endpoint`  | The database endpoint to connect to.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-2)

```rust
let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;
```

  

##  `.use_ns()` and `.use_db()`[](https://surrealdb.com/docs/reference/rust/embedding#use-ns-db)
Switch to a specific namespace and database.
Method Syntax

```rust
db.use_ns(ns).use_db(db)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `ns`  | Switches to a specific namespace.  |  
| `db`  | Switches to a specific database.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-3)

```rust
db.use_ns("main").use_db("main").await?;
```

  

##  `.signup()`[](https://surrealdb.com/docs/reference/rust/embedding#signup)
Signs up using a specific record access method.
Method Syntax

```rust
db.signup(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-3)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signup query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-4)

```rust
use serde::Serialize;
use surrealdb::opt::auth::Scope;

#[derive(Serialize)]
struct Credentials<'a> {
    email: &'a str,
    pass: &'a str,
}

let jwt = db.signup(Scope {
    namespace: "main",
    database: "main",
    access: "user",
    params: Credentials {
        email: "info@surrealdb.com",
        pass: "123456",
    },
}).await?;

// ⚠️: It is important to note that the token should be handled securely and protected from unauthorized access.
let token = jwt.as_insecure_token();
```

  

##  `.signin()`[](https://surrealdb.com/docs/reference/rust/embedding#signin)
Signs in using a specific access method or system user.
Method Syntax

```rust
db.signin(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-4)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signin query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-5)

```rust
use serde::Serialize;
use surrealdb::opt::auth::Scope;

#[derive(Serialize)]
struct Credentials<'a> {
    email: &'a str,
    pass: &'a str,
}

let jwt = db.signin(Scope {
    namespace: "main",
    database: "main",
    access: "user",
    params: Credentials {
        email: "info@surrealdb.com",
        pass: "123456",
    },
}).await?;

// ⚠️: It is important to note that the token should be handled securely and protected from unauthorized access.
let token = jwt.as_insecure_token();
```

  

##  `.invalidate()`[](https://surrealdb.com/docs/reference/rust/embedding#invalidate)
Invalidates the authentication for the current connection.
Method Syntax

```rust
db.invalidate(credentials)
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-6)

```surql
db.invalidate().await?;
```

  

##  `.authenticate()`[](https://surrealdb.com/docs/reference/rust/embedding#authenticate)
Authenticates the current connection with a JWT token.
Method Syntax

```rust
db.authenticate(token)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-5)  
| Arguments  | Description  |  
| --- | --- |  
| `token`  | The JWT authentication token.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-7)

```rust
db.authenticate(jwt).await?;
```

  

##  `.set()`[](https://surrealdb.com/docs/reference/rust/embedding#set)
Assigns a value as a parameter for this connection.
Method Syntax

```rust
db.set(key, val)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-6)  
| Arguments  | Description  |  
| --- | --- |  
| `key`  | Specifies the name of the variable.  |  
| `val`  | Assigns the value to the variable name.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-8)

```rust
// Assign the variable on the connection
db.set("name", Name {
    first: "Tobie",
    last: "Morgan Hitchcock",
}).await?;
// Use the variable in a subsequent query
db.query("CREATE person SET name = $name").await?;
// Use the variable in a subsequent query
db.query("SELECT * FROM person WHERE name.first = $name.first").await?;
```

  

##  `.query()`[](https://surrealdb.com/docs/reference/rust/embedding#query)
Runs a set of SurrealQL statements against the database.
Method Syntax

```rust
db.query(sql).bind(vars)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-7)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `vars`  | Assigns variables which can be used in the query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-9)

```rust
// Run some queries
let sql = "
    CREATE person;
    SELECT * FROM type::table($table);
";
let mut result = db
    .query(sql)
    .bind(("table", "person"))
    .await?;
// Get the first result from the first query
let created: Option<Person> = result.take(0)?;
// Get all of the results from the second query
let people: Vec<Person> = result.take(1)?;
```

  

##  `.select()`[](https://surrealdb.com/docs/reference/rust/embedding#select)
Selects all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.select(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-8)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-10)

```rust
// Select all records from a table
let people: Vec<Person> = db.select("person").await?;
// Select a specific record from a table
let person: Option<Person> = db.select(("person", "h5wxrf2ewk8xjxosxtyc")).await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query)
This function will run the following query in the database:

```surql
SELECT * FROM $resource;
```

  

##  `.create()`[](https://surrealdb.com/docs/reference/rust/embedding#create)
Creates a record in the database.
Method Syntax

```rust
db.create(resource).content(data)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-9)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-11)

```rust
// Create a record with a random ID
let person: Option<Person> = db.create("person").await?;
// Create a record with a specific ID
let record: Record = db
    .create(("person", "tobie"))
    .content(Person {
        name: "Tobie",
        settings: {
            active: true,
            marketing: true,
       },
    }).await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query-1)
This function will run the following query in the database:

```surql
CREATE $resource CONTENT $data;
```

  

##  `.update().content()`[](https://surrealdb.com/docs/reference/rust/embedding#update-content)
Updates all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).content(data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-10)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-12)

```rust
// Update all records in a table
let people: Vec<Person> = db.update("person").await?;
// Update a record with a specific ID
let person: Option<Person> = db
    .update(("person", "tobie"))
    .content(Person {
        name: "Tobie",
        settings: {
            active: true,
            marketing: true,
        },
    }).await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query-2)
This function will run the following query in the database:

```surql
UPDATE $resource CONTENT $data;
```

  

##  `.update().merge()`[](https://surrealdb.com/docs/reference/rust/embedding#update-merge)
Modifies all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).merge(data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-11)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-13)

```rust
// Update all records in a table
let people: Vec<Person> = db.update("person")
    .merge(Document {
        updated_at: Datetime::default(),
    })
    .await?;
// Update a record with a specific ID
let person: Option<Person> = db.update(("person", "tobie"))
    .merge(Document {
        updated_at: Datetime::default(),
        settings: Settings {
            active: true,
        },
    })
    .await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query-3)
This function will run the following query in the database:

```surql
UPDATE $resource MERGE $data;
```

  

##  `.update().patch()`[](https://surrealdb.com/docs/reference/rust/embedding#update-patch)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).patch(data)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-12)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to modify.  |  
| `data`  | The JSON Patch data with which to modify the records.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-14)

```rust
// Update all records in a table
let people: Vec<Person> = db.update("person")
    .patch(PatchOp::replace("/created_at", Datetime::default()))
    .await?;

// Update a record with a specific ID
let person: Option<Person> = db.update(("person", "tobie"))
    .patch(PatchOp::replace("/settings/active", false))
    .patch(PatchOp::add("/tags", &["developer", "engineer"]))
    .patch(PatchOp::remove("/temp"))
    .await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query-4)
This function will run the following query in the database:

```surql
UPDATE $resource PATCH $data;
```

  

##  `.delete()`[](https://surrealdb.com/docs/reference/rust/embedding#delete)
Deletes all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.delete(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/embedding#arguments-13)  
| Arguments  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/embedding#example-usage-15)

```rust
// Delete all records from a table
let people: Vec<Person> = db.delete("person").await?;
// Delete a specific record from a table
let person: Option<Person> = db.delete(("person", "h5wxrf2ewk8xjxosxtyc")).await?;
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/embedding#translated-query-5)
This function will run the following query in the database:

```surql
DELETE FROM $resource RETURN BEFORE;
```
