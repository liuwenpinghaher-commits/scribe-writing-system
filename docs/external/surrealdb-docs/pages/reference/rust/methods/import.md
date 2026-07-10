---
title: "https://surrealdb.com/docs/reference/rust/methods/import"
url: "https://surrealdb.com/docs/reference/rust/methods/import"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/import

Source: https://surrealdb.com/docs/reference/rust/methods/import

3.x2.x
Restores the database from a file.
Note
WebSocket connections currently do not support exports and imports. Be sure to use an HTTP endpoint and the `protocol-http` feature when using this method.
Method Syntax

```rust
db.import(source)
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/import#example-usage)
The following example assumes the presence of a file called `backup.surql` in the same directory as the current project. To quickly create it, copy and paste [the example for the .export() method](https://surrealdb.com/docs/reference/rust/methods/export).

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("main").use_db("main").await?;
    db.import("backup.surql").await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/import#see-also)
  * •
[.import() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.import)

Restores the database from a file.
Note
WebSocket connections currently do not support exports and imports. Be sure to use an HTTP endpoint when using this method.
Method Syntax

```rust
db.import(source)
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/import#example-usage-1)

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("main").use_db("main").await?;
    db.import("backup.surql").await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/import#see-also-1)
  * •
[.import() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.import)
