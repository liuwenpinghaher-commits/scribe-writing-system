---
title: "https://surrealdb.com/docs/reference/rust/methods/connect"
url: "https://surrealdb.com/docs/reference/rust/methods/connect"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/connect

Source: https://surrealdb.com/docs/reference/rust/methods/connect

Connects to a local or remote database endpoint.
Method Syntax

```rust
db.connect(address)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/connect#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `endpoint`  | The database endpoint to connect to.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/connect#example-usage)
The `.connect()` method will usually take a `String` or a type that implements `Into`. Note that the final `.connect()` with a `Config` is possible because of the implementation `impl IntoEndpoint for (T, Config)  
where T: Into`.

```rust
use std::sync::LazyLock;
use std::time::Duration;
use surrealdb::engine::remote::ws::{Client, Ws, Wss};
use surrealdb::opt::Config;
use surrealdb::Surreal;

static DB: LazyLock<Surreal<Client>> = LazyLock::new(Surreal::init);

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Connect to a local endpoint
    DB.connect::<Ws>("127.0.0.1:8000").await?;
    // Connect to a remote endpoint
    DB.connect::<Wss>("cloud.surrealdb.com").await?;
    // A tuple with a Config struct can also be passed in for fine tuning of the connection
    let config = Config::default().query_timeout(Duration::from_millis(1500));
    DB.connect::<Ws>(("127.0.0.1:8000", config)).await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/connect#see-also)
  * •
[.connect() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/engine/any/fn.connect.html)
