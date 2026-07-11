---
title: "https://surrealdb.com/docs/reference/rust/methods/init"
url: "https://surrealdb.com/docs/reference/rust/methods/init"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/init

Source: https://surrealdb.com/docs/reference/rust/methods/init

The .init() method initializes a new unconnected instance of the client.  
This is typically used to create a global, static instance of the client.
Method Syntax

```rust
Surreal::init()
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/init#example-usage)

```rust
use std::sync::LazyLock;
use surrealdb::engine::remote::ws::{Client, Ws};
use surrealdb::Surreal;

static DB: LazyLock<Surreal<Client>> = LazyLock::new(Surreal::init);

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Connect to the database
    DB.connect::<Ws>("127.0.0.1:8000").await?;
    Ok(())
}
```

`Surreal::init()` can also be used to create an instance of `Surreal`, allowing you to choose at runtime which way to connect.

```rust
use std::env;
use std::sync::LazyLock;
use surrealdb::engine::any::Any;
use surrealdb::Surreal;

static DB: LazyLock<Surreal<Any>> = LazyLock::new(Surreal::init);

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Choose an endpoint at runtime using the `DB_ENDPOINT` environment variable
    // or fallback to the memory engine.
    let endpoint = env::var("DB_ENDPOINT").unwrap_or_else(|_| "mem://".to_owned());
    DB.connect(endpoint).await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/init#see-also)
  * •
[.init() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.init)
