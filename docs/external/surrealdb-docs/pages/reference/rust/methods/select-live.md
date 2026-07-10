---
title: "https://surrealdb.com/docs/reference/rust/methods/select-live"
url: "https://surrealdb.com/docs/reference/rust/methods/select-live"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/select-live

Source: https://surrealdb.com/docs/reference/rust/methods/select-live

3.x2.x
Initiate live queries for a live stream of notifications.
You can achieve the same live subscription by running `LIVE SELECT` inside [`query()`](https://surrealdb.com/docs/reference/rust/methods/query#live-select-stream) and consuming results with [`IndexedResults::stream`](https://docs.rs/surrealdb/latest/surrealdb/method/query/struct.IndexedResults.html#method.stream). This can be useful when one or more live statements are part of a larger batch or if you prefer to use raw SurrealQL.
Method Syntax

```rust
db.select(resource).live()
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/select-live#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage: Listen for live updates[](https://surrealdb.com/docs/reference/rust/methods/select-live#example-usage-listen-for-live-updates)
The following example requires adding the `futures` crate with `cargo add futures` in order to work with the results of the async stream. Once run, the program will continue to wait and listen for events for the `person` table to happen.

```rust
use futures::StreamExt;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::{Notification, Surreal};
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Person {
    id: RecordId,
}

// Handle the result of the live query notification
fn handle(result: Result<Notification<Person>, surrealdb::Error>) {
    println!("Received notification: {:?}", result);
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    db.signin(Root {
        username: "root".into(),
        password: "secret".into(),
    })
    .await?;

    db.use_ns("main").use_db("main").await?;

    db.query("DEFINE TABLE person").await?;

    // Select the "person" table and listen for live updates.
    let mut stream = db.select("person").live().await?;

    // Process updates as they come in.
    while let Some(result) = stream.next().await {
        // Do something with the notification
        handle(result);
    }
    Ok(())
}
```

Then connect to it using Surrealist or open a new terminal window with the following command.

```
surreal sql --user root --pass secret --pretty
```

You can then use queries like the following to work with some `person` records.

```surql
CREATE person;
UPDATE person SET is_nice_person = true;
DELETE person;
```

The following output will then show up in the terminal window running the Rust example.

```
Received notification: Ok(Notification { query_id: Uuid(ab57b7f9-00b1-47e8-8f29-9d11d0572264), action: Create, data: Person { id: RecordId { table: Table("person"), key: String("pbpm2xhmaofyne383455") } } })
Received notification: Ok(Notification { query_id: Uuid(ab57b7f9-00b1-47e8-8f29-9d11d0572264), action: Update, data: Person { id: RecordId { table: Table("person"), key: String("pbpm2xhmaofyne383455") } } })
Received notification: Ok(Notification { query_id: Uuid(ab57b7f9-00b1-47e8-8f29-9d11d0572264), action: Delete, data: Person { id: RecordId { table: Table("person"), key: String("pbpm2xhmaofyne383455") } } })
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/select-live#see-also)
  * •
[.live() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Select.html#method.live)
  * •
[`query()` with streaming `LIVE SELECT`](https://surrealdb.com/docs/reference/rust/methods/query#live-select-stream)

Initiate live queries for a live stream of notifications.
Method Syntax

```rust
db.select(resource).live()
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/select-live#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage: Listen for live updates[](https://surrealdb.com/docs/reference/rust/methods/select-live#example-usage-listen-for-live-updates-1)
The following example requires adding the `futures` crate with `cargo add futures` in order to work with the results of the async stream. Once run, the program will continue to wait and listen for events for the `person` table to happen.

```rust
use futures::StreamExt;
use serde::Deserialize;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::{Notification, Surreal};
use surrealdb::RecordId;

#[derive(Debug, Deserialize)]
struct Person {
    id: RecordId,
}

// Handle the result of the live query notification
fn handle(result: Result<Notification<Person>, surrealdb::Error>) {
    println!("Received notification: {:?}", result);
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;

    db.use_ns("ns").use_db("db").await?;

    // Select the "person" table and listen for live updates.
    let mut stream = db.select("person").live().await?;

    // Process updates as they come in.
    while let Some(result) = stream.next().await {
        // Do something with the notification
        handle(result);
    }
    Ok(())
}
```

Then connect to it using Surrealist or open a new terminal window with the following command.

```
surreal sql --namespace ns --database db --user root --pass secret --pretty
```

You can then use queries like the following to work with some `person` records.

```surql
CREATE person;
UPDATE person SET is_nice_person = true;
DELETE person;
```

The following output will then show up in the terminal window running the Rust example.

```
Received notification: Ok(Notification { query_id: b55d31dc-e657-4a6b-a32b-f5abed4ef459, action: Create, data: Person { id: RecordId { table: "person", key: String("334mabva9ibitsypabm5") } } })
Received notification: Ok(Notification { query_id: b55d31dc-e657-4a6b-a32b-f5abed4ef459, action: Update, data: Person { id: RecordId { table: "person", key: String("334mabva9ibitsypabm5") } } })
Received notification: Ok(Notification { query_id: b55d31dc-e657-4a6b-a32b-f5abed4ef459, action: Delete, data: Person { id: RecordId { table: "person", key: String("334mabva9ibitsypabm5") } } })
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/select-live#see-also-1)
  * •
[.live() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Select.html#method.live)
