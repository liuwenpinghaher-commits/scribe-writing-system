---
title: "https://surrealdb.com/docs/languages/rust"
url: "https://surrealdb.com/docs/languages/rust"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/languages/rust

Source: https://surrealdb.com/docs/languages/rust

The Rust SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries.
##  1. Install the SDK[](https://surrealdb.com/docs/languages/rust#1-install-the-sdk)
Create a new project using `cargo new` and add the [`surrealdb`](https://crates.io/crates/surrealdb) crate along with [`tokio`](https://crates.io/crates/tokio), which lets you use the database inside an `async fn main()`. Enabling the `macros` and `rt-multi-thread` features on `tokio` allows the `#[tokio::main]` attribute to be used on top of `fn main()`.
The two main ways to connect to SurrealDB when getting started are by connecting to a running instance via the `protocol-ws` feature, or by running an embedded instance in memory using the `kv-mem` feature. Each of these can be added via a feature flag in the SDK.

```sh
cargo new my_project
cd my_project
cargo add surrealdb --features kv-mem,protocol-ws
cargo add tokio --features macros,rt-multi-thread
```

Once installed, import the SDK's types into `src/main.rs`.

```rust
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/languages/rust#2-connect-to-surrealdb)
Use [`Surreal::new`](https://surrealdb.com/docs/reference/rust/methods/new) with the `Ws` engine to connect to a running SurrealDB instance, then [`signin`](https://surrealdb.com/docs/reference/rust/methods/signin) to authenticate and [`use_ns`/`use_db`](https://surrealdb.com/docs/reference/rust/methods/use) to select the namespace and database you want to work with. Most operations require both.
Supported connection protocols include:
  * •
**WebSocket** (`ws://`, `wss://`) via the `protocol-ws` feature, for long-lived stateful connections
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections
  * •
**Memory/embedded** (`mem://`) via the `kv-mem` feature, for [embedded instances](https://surrealdb.com/docs/reference/rust/embedding)

```rust
#[tokio::main]
async fn main() -> surrealdb::Result<()> {

    // Connect to the server
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    // Signin as a namespace, database, or root user
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;

    // Select a specific namespace / database
    db.use_ns("main").use_db("main").await?;

    Ok(())
}
```

##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/languages/rust#3-inserting-data-into-surrealdb)
Once connected, you can use [`create`](https://surrealdb.com/docs/reference/rust/methods/create) to create records. The most ergonomic way to pass data to and from the database is to use a struct that derives [`SurrealValue`](https://docs.rs/surrealdb/latest/surrealdb/types/trait.SurrealValue.html), which allows for both serialisation and deserialisation between the Rust code and the database.

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Name {
    first: String,
    last: String,
}

#[derive(Debug, SurrealValue)]
struct Person {
    title: String,
    name: Name,
    marketing: bool,
}

#[derive(Debug, SurrealValue)]
struct Record {
    id: RecordId,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;

    db.use_ns("main").use_db("main").await?;

    // Create a new person with a random id
    let created: Option<Record> = db
        .create("person")
        .content(Person {
            title: "Founder & CEO".to_string(),
            name: Name {
                first: "Tobie".to_string(),
                last: "Morgan Hitchcock".to_string(),
            },
            marketing: true,
        })
        .await?;
    dbg!(created);

    Ok(())
}
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/languages/rust#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/languages/rust#selecting-records)
The [`select`](https://surrealdb.com/docs/reference/rust/methods/select) method retrieves all records from a table. Deserialize the result into a `Vec` of a struct that derives `SurrealValue`.

```rust
// Select all people records
let people: Vec<Record> = db.select("person").await?;
dbg!(people);
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/languages/rust#running-surrealql-queries)
For more advanced use cases, you can use the [`query`](https://surrealdb.com/docs/reference/rust/methods/query) method to run [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements directly. Use [`.bind()`](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters) to safely pass dynamic values, and [`.take()`](https://surrealdb.com/docs/reference/rust/methods/query) to transform a query result into anything that can be deserialized, in this case a `Value`.

```rust
use surrealdb::types::Value;

// Perform a custom advanced query
let mut groups = db
    .query("SELECT marketing, count() FROM type::table($table) GROUP BY marketing")
    .bind(("table", "person"))
    .await?;
dbg!(groups.take::<Value>(0).unwrap());
```

##  5. Closing the connection[](https://surrealdb.com/docs/languages/rust#5-closing-the-connection)
Rust has no explicit close method. The connection is closed automatically when the `Surreal` client is dropped, for example when it goes out of scope at the end of your function.
##  Next steps[](https://surrealdb.com/docs/languages/rust#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Authentication Read more about authentication levels and how to integrate them into your application.](https://surrealdb.com/docs/reference/rust/concepts/authenticating-users)[Live queries Learn how to subscribe to real-time changes in your data with live queries.](https://surrealdb.com/docs/reference/rust/concepts/live)[Embedding SurrealDB Run SurrealDB in memory or on disk directly inside your Rust application.](https://surrealdb.com/docs/reference/rust/embedding)[API Reference Complete reference for all methods, types, and errors.](https://surrealdb.com/docs/reference/rust/methods)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [Rust SDK reference](https://surrealdb.com/docs/reference/rust).
