---
title: "https://surrealdb.com/docs/reference/rust/methods/wait-for"
url: "https://surrealdb.com/docs/reference/rust/methods/wait-for"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/wait-for

Source: https://surrealdb.com/docs/reference/rust/methods/wait-for

Wait for the selected event to happen before proceeding.
Method Syntax

```rust
db.wait_for(event)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/wait-for#arguments)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `event`  | `WaitFor`  | The event to wait for before proceeding.  |  
`WaitFor` is a simple enum with two variants representing the event to wait for.

```rust
pub enum WaitFor {
    Connection,
    Database,
}
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/wait-for#example-usage)
The following test from the source code demonstrates the behaviour of the `.wait_for_()` method in a variety of situations.

```rust
use std::task::Poll;

use surrealdb::engine::remote::ws::{Client, Ws};
use surrealdb::opt::auth::Root;
use surrealdb::opt::WaitFor::{Connection, Database};
use surrealdb::Surreal;

use futures::poll;
use std::pin::pin;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {

    // Create an unconnected client
    // At this point wait_for should continue to wait for both the connection and database selection.
    let db: Surreal<Client> = Surreal::init();
    assert_eq!(poll!(pin!(db.wait_for(Connection))), Poll::Pending);
    assert_eq!(poll!(pin!(db.wait_for(Database))), Poll::Pending);

    // Connect to the server
    // The connection event should fire and allow wait_for to return immediately when waiting for a connection.
    // When waiting for a database to be selected, it should continue waiting.
    db.connect::<Ws>("127.0.0.1:8000").await.unwrap();
    assert_eq!(poll!(pin!(db.wait_for(Connection))), Poll::Ready(()));
    assert_eq!(poll!(pin!(db.wait_for(Database))), Poll::Pending);

    // Sign into the server
    // At this point the connection has already been established but the database hasn't been selected yet.
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await
    .unwrap();
    assert_eq!(poll!(pin!(db.wait_for(Connection))), Poll::Ready(()));
    assert_eq!(poll!(pin!(db.wait_for(Database))), Poll::Pending);

    // Selecting a namespace shouldn't fire the database selection event.
    db.use_ns("namespace").await.unwrap();
    assert_eq!(poll!(pin!(db.wait_for(Connection))), Poll::Ready(()));
    assert_eq!(poll!(pin!(db.wait_for(Database))), Poll::Pending);

    // Select the database to use
    // Both the connection and database events have fired, wait_for should return immediately for both.
    db.use_db("database").await.unwrap();
    assert_eq!(poll!(pin!(db.wait_for(Connection))), Poll::Ready(()));
    assert_eq!(poll!(pin!(db.wait_for(Database))), Poll::Ready(()));
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/wait-for#see-also)
  * •
[.wait_for() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.wait_for)
