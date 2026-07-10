---
title: "https://surrealdb.com/docs/reference/rust/methods/use-defaults"
url: "https://surrealdb.com/docs/reference/rust/methods/use-defaults"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/use-defaults

Source: https://surrealdb.com/docs/reference/rust/methods/use-defaults

Clears the explicit `USE` state for namespace and database and **uses the default** values associated with the connection. The outcome depends on your endpoint and `DEFINE` configuration.
Method Syntax

```rust
db.use_defaults().await?
```

This complements [`use_ns()` and `use_db()`](https://surrealdb.com/docs/reference/rust/methods/use) when you want to reset to defaults instead of a specific pair.
###  See also[](https://surrealdb.com/docs/reference/rust/methods/use-defaults#see-also)
  * •
[`.use_defaults()` on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.use_defaults)
