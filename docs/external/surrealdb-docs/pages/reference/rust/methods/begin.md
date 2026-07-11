---
title: "https://surrealdb.com/docs/reference/rust/methods/begin"
url: "https://surrealdb.com/docs/reference/rust/methods/begin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/begin

Source: https://surrealdb.com/docs/reference/rust/methods/begin

Starts a transaction. The connection is taken into a [`Transaction`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html) that exposes the same query and CRUD entry points as `Surreal` (scoped to the transaction) plus [`commit()`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html#method.commit) and [`cancel()`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html#method.cancel).
Note that this method takes by value (taking a `self`), which is then passed on to the `Transaction`. The `.commit()` and `.cancel()` methods are used to finalise the transaction and return the `Surreal` client for reuse.
Method Syntax

```rust
let tx = db.begin().await?;
// tx.query(...), .select(), .create(), .insert(), .upsert(), .update(), .delete()
```

##  `.commit()`[](https://surrealdb.com/docs/reference/rust/methods/begin#commit)
[`tx.commit().await?`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html#method.commit) applies every statement run on the handle and returns ownership of the underlying `Surreal` client so the connection can run further work outside the transaction.

```rust
// let db = tx.commit().await?;
```

##  `.cancel()`[](https://surrealdb.com/docs/reference/rust/methods/begin#cancel)
[`tx.cancel().await?`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html#method.cancel) rolls back the transaction and **also** returns the `Surreal` client for reuse.

```rust
// let db = tx.cancel().await?;
```

For a broader discussion and more detailed examples, see the concept page on [Manual transactions](https://surrealdb.com/docs/reference/rust/concepts/transaction).
###  See also[](https://surrealdb.com/docs/reference/rust/methods/begin#see-also)
  * •
[`.begin()` on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.begin)
  * •
[`Transaction` in the Rust API](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Transaction.html)
