---
title: "https://surrealdb.com/docs/reference/rust/methods/set"
url: "https://surrealdb.com/docs/reference/rust/methods/set"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/set

Source: https://surrealdb.com/docs/reference/rust/methods/set

3.x2.x
Assigns a value as a parameter for this connection.
Method Syntax

```rust
db.set(key, value)
```

This is equivalent to using a [`LET`](https://surrealdb.com/docs/reference/query-language/statements/let) statement in SurrealQL, such as this one.

```surql
LET $name = {
    first: "Tobie",
    last: "Morgan Hitchcock",
};
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/set#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `key`  | Specifies the name of the variable.  |  
| `val`  | Assigns the value to the variable name.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/set#example-usage)

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue)]
struct Name {
    first: String,
    last: String,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;

    db.use_ns("main").use_db("main").await?;

    // Assign the variable on the connection
    db.set(
        "name",
        Name {
            first: "Tobie".to_string(),
            last: "Morgan Hitchcock".to_string(),
        },
    )
    .await?;
    // Use the variable in a subsequent query
    let create = db.query("CREATE person SET name = $name").await?;
    dbg!(create);
    // Use the variable in a subsequent query
    let select = db
        .query("SELECT * FROM person WHERE name.first = $name.first")
        .await?;
    dbg!(select);
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/set#see-also)
  * •
[.set() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.set)

Assigns a value as a parameter for this connection.
Method Syntax

```rust
db.set(key, value)
```

This is equivalent to using a [`LET`](https://surrealdb.com/docs/reference/query-language/statements/let) statement in SurrealQL, such as this one.

```surql
LET $name = {
    first: "Tobie",
    last: "Morgan Hitchcock",
};
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/set#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `key`  | Specifies the name of the variable.  |  
| `val`  | Assigns the value to the variable name.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/set#example-usage-1)

```rust
use serde::Serialize;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;

#[derive(Debug, Serialize)]
struct Name<'a> {
    first: &'a str,
    last: &'a str,
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

    // Assign the variable on the connection
    db.set(
        "name",
        Name {
            first: "Tobie",
            last: "Morgan Hitchcock",
        },
    )
    .await?;
    // Use the variable in a subsequent query
    let create = db.query("CREATE person SET name = $name").await?;
    dbg!(create);
    // Use the variable in a subsequent query
    let select = db
        .query("SELECT * FROM person WHERE name.first = $name.first")
        .await?;
    dbg!(select);
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/set#see-also-1)
  * •
[.set() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.set)
