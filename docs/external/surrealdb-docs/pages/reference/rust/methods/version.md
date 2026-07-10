---
title: "https://surrealdb.com/docs/reference/rust/methods/version"
url: "https://surrealdb.com/docs/reference/rust/methods/version"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/version

Source: https://surrealdb.com/docs/reference/rust/methods/version

Returns the version of the server.
Method Syntax

```rust
db.version()
```

###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/version#example-usage)

```rust
use surrealdb::engine::any::connect;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;

    println!("{:?}", db.version().await?);
    Ok(())
}
```

The function resolves to a [`Version`](https://docs.rs/semver/latest/semver/struct.Version.html) struct as defined in the `semver` crate. Sample output:

```
Version { major: 3, minor: 0, patch: 1 }
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/version#see-also)
  * •
[.version() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.version)
