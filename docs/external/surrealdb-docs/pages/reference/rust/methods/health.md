---
title: "https://surrealdb.com/docs/reference/rust/methods/health"
url: "https://surrealdb.com/docs/reference/rust/methods/health"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/health

Source: https://surrealdb.com/docs/reference/rust/methods/health

Runs a lightweight health check on the current session/connection. On success, the future resolves to `Ok(())`; otherwise you get a [`surrealdb::Error`](https://docs.rs/surrealdb/latest/surrealdb/enum.Error.html).
Method Syntax

```rust
db.health().await?
```

This is a simple way to assert the database is reachable and accepting commands after `connect` (or periodically in long-lived processes) without sending a full SurrealQL query.
###  See also[](https://surrealdb.com/docs/reference/rust/methods/health#see-also)
  * •
[`.health()` on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.health)
