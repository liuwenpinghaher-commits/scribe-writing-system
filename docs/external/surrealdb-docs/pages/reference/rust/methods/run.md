---
title: "https://surrealdb.com/docs/reference/rust/methods/run"
url: "https://surrealdb.com/docs/reference/rust/methods/run"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/run

Source: https://surrealdb.com/docs/reference/rust/methods/run

3.x2.x
Runs a SurrealQL function.
Method Syntax

```rust
db.run(function)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/run#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `function`  | Specifies the path of the function.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/run#example-usage)
Calling an existing SurrealQL function:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;

    db.signin(Root {
        username: "root".into(),
        password: "secret".into()
    })
    .await?;

    let res: f32 = db.run("rand::float").await?;
    dbg!(res);
    Ok(())
}
```

User-defined functions can be called as well.

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;
    db.signin(Root {
        username: "root".into(),
        password: "secret".into(),
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query("DEFINE FUNCTION fn::return_one() -> int { RETURN 1 };")
        .await?;

    let res: i32 = db.run("fn::return_one").await?;
    dbg!(res);
    Ok(())
}
```

The return value of the `.run()` function can be deserialized in the same way as any other database function.
Deserialize to user-defined struct

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue)]
struct Person {
    first_name: String,
    middle_name: String,
    last_name: String,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query(
        "DEFINE FUNCTION fn::j_jonah_jameson() -> object { RETURN
        {
          first_name: 'J',
          middle_name: 'Jonah',
          last_name: 'Jameson'
        }
    };",
    )
    .await?;

    let res: Person = db.run("fn::j_jonah_jameson").await?;
    dbg!(res);
    Ok(())
}
```

Deserialize as std library type

```rust
use surrealdb::engine::any::connect;

#[tokio::main]
async fn main() {
    let db = connect("memory").await.unwrap();
    db.use_ns("main").use_db("main").await.unwrap();
    db.query("DEFINE FUNCTION fn::array() { [1,2,3] };")
        .await
        .unwrap();

    let res: Vec<i32> = db.run("fn::array").await.unwrap();
    println!("{res:?}");
}
```

Runs a SurrealQL function.
Method Syntax

```rust
db.run(function)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/run#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `function`  | Specifies the path of the function.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/run#example-usage-1)
Calling an existing SurrealQL function:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;

    db.signin(Root {
        username: "root",
        password: "secret"
    })
    .await?;

    let res: f32 = db.run("rand::float").await?;
    dbg!(res);
    Ok(())
}
```

User-defined functions can be called as well.

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query("DEFINE FUNCTION fn::return_one() -> int { RETURN 1 };")
        .await?;

    let res: i32 = db.run("fn::return_one").await?;
    dbg!(res);
    Ok(())
}
```

The return value of the `.run()` function can be deserialized in the same way as any other database function.

```rust
use serde::Deserialize;
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[derive(Debug, Deserialize)]
struct Person {
    first_name: String,
    middle_name: String,
    last_name: String,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query(
        "DEFINE FUNCTION fn::j_jonah_jameson() -> object { RETURN 
        { 
          first_name: 'J',
          middle_name: 'Jonah',
          last_name: 'Jameson'
        } 
    };",
    )
    .await?;

    let res: Person = db.run("fn::j_jonah_jameson").await?;
    dbg!(res);
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/run#see-also)
  * •
[.run() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.run)
