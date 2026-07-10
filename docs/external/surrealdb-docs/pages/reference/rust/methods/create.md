---
title: "https://surrealdb.com/docs/reference/rust/methods/create"
url: "https://surrealdb.com/docs/reference/rust/methods/create"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/create

Source: https://surrealdb.com/docs/reference/rust/methods/create

3.x2.x
Creates one or more records in the database.
Method Syntax

```rust
db.create(resource).content(data)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/create#arguments)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/create#example-usage)

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Person {
    name: Option<String>,
    marketing: Option<bool>,
}

#[derive(Debug, SurrealValue)]
struct Record {
    id: RecordId,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("ws://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("main").use_db("main").await?;

    // Create a record with a random ID
    let person: Option<Person> = db.create("person").await?;
    dbg!(person);
    // Create a record with a specific ID
    let record: Option<Record> = db
        .create(("person", "tobie"))
        .content(Person {
            name: Some("Tobie".into()),
            marketing: Some(true),
        })
        .await?;
    dbg!(record);
    Ok(())
}
```

Creates one or more records in the database.
Method Syntax

```rust
db.create(resource).content(data)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/create#arguments-1)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/create#example-usage-1)

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::RecordId;

#[derive(Debug, Serialize, Deserialize)]
struct Person {
    name: Option<String>,
    marketing: Option<bool>
}

#[derive(Debug, Deserialize)]
struct Record {
    id: RecordId,
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

    // Create a record with a random ID
    let person: Option<Person> = db.create("person").await?;
    dbg!(person);
    // Create a record with a specific ID
    let record: Option<Record> = db
        .create(("person", "tobie"))
        .content(Person {
            name: Some("Tobie".into()),
            marketing: Some(true),
        })
        .await?;
    dbg!(record);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/create#translated-query)
This function will run the following query in the database:

```surql
CREATE $resource CONTENT $data;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/create#see-also)
  * •
[.create() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.create)
