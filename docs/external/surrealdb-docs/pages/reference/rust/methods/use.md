---
title: "https://surrealdb.com/docs/reference/rust/methods/use"
url: "https://surrealdb.com/docs/reference/rust/methods/use"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/use

Source: https://surrealdb.com/docs/reference/rust/methods/use

Switch to a specific namespace and database.
Method Syntax

```rust
db.use_ns(ns).use_db(db)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/use#arguments)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `ns`  | Switches to a specific namespace.  |  
| `db`  | Switches to a specific database.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/use#example-usage)

```rust
use surrealdb::engine::remote::ws::Ws;
use surrealdb::Surreal;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;
    db.use_ns("main").use_db("main").await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/use#see-also)
  * •
[.use_db() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.use_db)
  * •
[.use_ns() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.use_ns)
