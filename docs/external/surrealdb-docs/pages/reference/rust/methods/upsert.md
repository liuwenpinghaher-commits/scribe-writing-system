---
title: "https://surrealdb.com/docs/reference/rust/methods/upsert"
url: "https://surrealdb.com/docs/reference/rust/methods/upsert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/upsert

Source: https://surrealdb.com/docs/reference/rust/methods/upsert

3.x2.x
Upserts all records in a table, or a specific record.
Method Syntax

```rust
db.upsert(resource)
```

The `.upsert()` method is followed by second method that refers to the type of upsert to use: an upsert with `.content()`, `.merge()`, or `.patch()`.
##  `.upsert().content()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertcontent)
Upserts all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).content(data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage)

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Person {
    id: RecordId,
    name: Option<String>,
    company: Option<String>,
    settings: Option<Settings>,
}

#[derive(Debug, SurrealValue)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Debug, SurrealValue)]
struct Company {
    company: String,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;

    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;

    db.use_ns("ns").use_db("db").await?;

    // upsert one record in a table
    let person: Option<Person> = db
        .upsert(("person", "jaime"))
        .content(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query)
This function will run the following query in the database:

```surql
upsert $resource CONTENT $data;
```

###  Restrict records with `.range()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#restrict-records-with-range)
For upserts against a **whole table** , use [`.range(...)`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Upsert.html#method.range-1) together with `.content`, `.merge`, or `.patch` if only keys inside the range should be considered:

```rust
use surrealdb::{
    engine::any::connect,
    opt::Resource,
    types::{SurrealValue, ToSql, Value},
};

#[derive(SurrealValue)]
struct Content {
    second_half_of_alphabet: bool,
}

#[tokio::main]
async fn main() {
    let db = connect("memory").await.unwrap();
    db.use_ns("ns").use_db("db").await.unwrap();

    db.query("CREATE person:alucard, person:plato, person:vlad")
        .await
        .unwrap();

    let res = db
        .upsert::<Value>(Resource::from("person"))
        .range("n"..="z")
        .content(Content {
            second_half_of_alphabet: true,
        })
        .await
        .unwrap()
        .to_sql();
    println!("{res:?}");
}
```

##  `.upsert().merge()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertmerge)
Modifies all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).merge(data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | `resource`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage-1)

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue, Default)]
struct Person {
    name: String,
    company: Option<String>,
    active: Option<bool>,
    marketing: Option<bool>,
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

    // upsert a single record
    let person: Option<Person> = db
        .upsert(("person", "tobie"))
        .merge(Person {
            name: "Tobie".into(),
            ..Default::default()
        })
        .await?;

    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query-1)
This function will run the following query in the database:

```surql
upsert $resource MERGE $data;
```

##  `.upsert().patch()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertpatch)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).patch(patch_op)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments-2)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to modify.  |  
| `data`  | The JSON Patch data with which to modify the records.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage-2)
The `.patch()` method uses a struct called a `PatchOp` that contains the four methods `add()`, `change()`, `remove()`, and `replace()`. Each of these methods takes different arguments depending on the operation. For example, `PathOp::remove()` only takes a single argument (a path), while `PathOp::replace()` takes a second value for the replacement value.

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::PatchOp;
use surrealdb::opt::auth::Root;
use surrealdb::types::{Datetime, SurrealValue};

#[derive(Debug, SurrealValue, Default)]
struct Person {
    name: String,
    company: Option<String>,
    settings: Option<Settings>,
    created_at: Option<Datetime>,
    tags: Option<Vec<String>>,
}

#[derive(Debug, SurrealValue)]
struct Settings {
    active: bool,
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

    // upsert a record with a specific ID
    let person: Option<Person> = db
        .upsert(("person", "tobie"))
        .patch(PatchOp::replace("/name", "Tobie"))
        .patch(PatchOp::replace("/settings/active", false))
        .patch(PatchOp::add("/tags", ["developer", "engineer"]))
        .patch(PatchOp::remove("/company"))
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query-2)
This function will run the following query in the database:

```surql
UPSERT $resource PATCH $data;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/upsert#see-also)
  * •
[.upsert() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.upsert)

Upserts all records in a table, or a specific record.
Method Syntax

```rust
db.upsert(resource)
```

The `.upsert()` method is followed by second method that refers to the type of upsert to use: an upsert with `.content()`, `.merge()`, or `.patch()`.
##  `.upsert().content()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertcontent-1)
Upserts all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).content(data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments-3)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage-3)

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::RecordId;
use surrealdb::Surreal;

#[derive(Debug, Serialize, Deserialize)]
struct Person {
    id: RecordId,
    name: Option<String>,
    company: Option<String>,
    settings: Option<Settings>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Debug, Serialize)]
struct Company {
    company: String,
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

    // upsert one record in a table
    let person: Option<Person> = db
        .upsert(("person", "jaime"))
        .content(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query-3)
This function will run the following query in the database:

```surql
upsert $resource CONTENT $data;
```

##  `.upsert().merge()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertmerge-1)
Modifies all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).merge(data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments-4)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | `resource`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage-4)

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;

#[derive(Debug, Serialize, Deserialize, Default)]
struct Person {
    name: String,
    company: Option<String>,
    active: Option<bool>,
    marketing: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
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

    // upsert a single record
    let person: Option<Person> = db
        .upsert(("person", "tobie"))
        .merge(Person {
            name: "Tobie".into(),
            ..Default::default()
        })
        .await?;

    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query-4)
This function will run the following query in the database:

```surql
upsert $resource MERGE $data;
```

##  `.upsert().patch()`[](https://surrealdb.com/docs/reference/rust/methods/upsert#upsertpatch-1)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```rust
db.upsert(resource).patch(patch_op)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/upsert#arguments-5)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to modify.  |  
| `data`  | The JSON Patch data with which to modify the records.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/upsert#example-usage-5)
The `.patch()` method uses a struct called a `PatchOp` that contains the four methods `add()`, `change()`, `remove()`, and `replace()`. Each of these methods takes different arguments depending on the operation. For example, `PathOp::remove()` only takes a single argument (a path), while `PathOp::replace()` takes a second value for the replacement value.

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::opt::PatchOp;
use surrealdb::sql::Datetime;
use surrealdb::Surreal;

#[derive(Debug, Serialize, Deserialize, Default)]
struct Person {
    name: String,
    company: Option<String>,
    settings: Option<Settings>,
    created_at: Option<Datetime>,
    tags: Option<Vec<String>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
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

    // upsert a record with a specific ID
    let person: Option<Person> = db
        .upsert(("person", "tobie"))
        .patch(PatchOp::replace("/settings/active", false))
        .patch(PatchOp::add("/tags", &["developer", "engineer"]))
        .patch(PatchOp::remove("/company"))
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/upsert#translated-query-5)
This function will run the following query in the database:

```surql
UPSERT $resource PATCH $data;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/upsert#see-also-1)
  * •
[.upsert() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.upsert)
