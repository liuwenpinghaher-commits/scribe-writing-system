---
title: "https://surrealdb.com/docs/reference/rust/methods/update"
url: "https://surrealdb.com/docs/reference/rust/methods/update"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/update

Source: https://surrealdb.com/docs/reference/rust/methods/update

3.x2.x
Update all or specific records in the database.
Method Syntax

```rust
db.update(resource)
```

The `.update()` method is followed by second method that refers to the type of update to use: an update with `.content()`, `.merge()`, or `.patch()`.
##  `.update().content()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatecontent)
Updates all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).content(data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage)

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue, Default)]
struct Person {
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

    db.use_ns("main").use_db("main").await?;

    db.query("CREATE person:tobie, person:jaime").await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .content(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(people);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query)
This function will run the following query in the database:

```surql
UPDATE $resource CONTENT $data;
```

###  Restrict records with `.range()`[](https://surrealdb.com/docs/reference/rust/methods/update#restrict-records-with-range)
Table-scoped updates accept [`.range(...)`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Update.html#method.range-1) before `.content`, `.merge`, or `.patch`, limiting which record IDs are affected:

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
        .update::<Value>(Resource::from("person"))
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

##  `.update().merge()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatemerge)
Modifies all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).merge(data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | `resource`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage-1)

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

    db.query("CREATE person:tobie SET name = 'Tobie'; CREATE person:jaime SET name = 'jaime';")
        .await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .merge(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(people);

    // Update a single record
    let person: Option<Person> = db
        .update(("person", "jaime"))
        .merge(Settings {
            active: true,
            marketing: true,
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query-1)
This function will run the following query in the database:

```surql
UPDATE $resource MERGE $data;
```

##  `.update().patch()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatepatch)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).patch(patch_op)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments-2)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to modify.  |  
| `data`  | The JSON Patch data with which to modify the records.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage-2)
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

    db.query(
        "
        CREATE person:tobie SET name = 'Tobie', company = 'SurrealDB'; 
        CREATE person:jaime SET name = 'jaime', company = 'SurrealDB';",
    )
    .await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .patch(PatchOp::replace("/created_at", Datetime::default()))
        .await?;
    dbg!(people);

    // Update a record with a specific ID
    let person: Option<Person> = db
        .update(("person", "tobie"))
        .patch(PatchOp::replace("/settings/active", false))
        .patch(PatchOp::add("/tags", ["developer", "engineer"]))
        .patch(PatchOp::remove("/company"))
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query-2)
This function will run the following query in the database:

```surql
UPDATE $resource PATCH $data;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/update#see-also)
  * •
[.update() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.update)

Update all or specific records in the database.
Method Syntax

```rust
db.update(resource)
```

The `.update()` method is followed by second method that refers to the type of update to use: an update with `.content()`, `.merge()`, or `.patch()`.
##  `.update().content()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatecontent-1)
Updates all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).content(data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments-3)  
| Argument  | Type  | Description  |  
| --- | --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage-3)

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::Surreal;

#[derive(Debug, Serialize, Deserialize, Default)]
struct Person {
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

    db.query("CREATE person:tobie, person:jaime").await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .content(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(people);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query-3)
This function will run the following query in the database:

```surql
UPDATE $resource CONTENT $data;
```

##  `.update().merge()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatemerge-1)
Modifies all records in a table, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).merge(data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments-4)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | `resource`  | The document / record data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage-4)

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

    db.query("CREATE person:tobie SET name = 'Tobie'; CREATE person:jaime SET name = 'jaime';")
        .await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .merge(Company {
            company: "SurrealDB".into(),
        })
        .await?;
    dbg!(people);

    // Update a single record
    let person: Option<Person> = db
        .update(("person", "jaime"))
        .merge(Settings {
            active: true,
            marketing: true,
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query-4)
This function will run the following query in the database:

```surql
UPDATE $resource MERGE $data;
```

##  `.update().patch()`[](https://surrealdb.com/docs/reference/rust/methods/update#updatepatch-1)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```rust
db.update(resource).patch(patch_op)
```

Note
This function patches the current document / record data with the specified JSON Patch data.
###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/update#arguments-5)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to modify.  |  
| `data`  | The JSON Patch data with which to modify the records.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/update#example-usage-5)
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

    db.query(
        "
        CREATE person:tobie SET name = 'Tobie', company = 'SurrealDB'; 
        CREATE person:jaime SET name = 'jaime', company = 'SurrealDB';",
    )
    .await?;

    // Update all records in a table
    let people: Vec<Person> = db
        .update("person")
        .patch(PatchOp::replace("/created_at", Datetime::default()))
        .await?;
    dbg!(people);

    // Update a record with a specific ID
    let person: Option<Person> = db
        .update(("person", "tobie"))
        .patch(PatchOp::replace("/settings/active", false))
        .patch(PatchOp::add("/tags", &["developer", "engineer"]))
        .patch(PatchOp::remove("/company"))
        .await?;
    dbg!(person);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/update#translated-query-5)
This function will run the following query in the database:

```surql
UPDATE $resource PATCH $data;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/update#see-also-1)
  * •
[.update() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.update)
