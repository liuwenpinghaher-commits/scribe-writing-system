---
title: "https://surrealdb.com/docs/reference/rust/methods/insert"
url: "https://surrealdb.com/docs/reference/rust/methods/insert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/insert

Source: https://surrealdb.com/docs/reference/rust/methods/insert

3.x2.x
Method Syntax

```rust
db.insert(resource).content(data);
db.insert(resource).relation(data);
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/insert#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
| `data`  | The relation table data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/insert#example-usage)
Inserting a record with a specific ID:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(SurrealValue)]
struct Data {
    name: String,
    settings: Settings,
}

#[derive(Debug, SurrealValue)]
struct Person {
    name: String,
    settings: Settings,
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

    let person: Option<Person> = db
        .insert(("person", "tobie"))
        .content(Data {
            name: "Tobie".to_string(),
            settings: Settings {
                active: true,
                marketing: true,
            },
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

Inserting multiple records into a table:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::types::SurrealValue;

#[derive(Debug, SurrealValue)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(SurrealValue)]
struct Data {
    name: String,
    settings: Settings,
}

#[derive(Debug, SurrealValue)]
struct Person {
    name: String,
    settings: Settings,
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

    let people: Vec<Person> = db
        .insert("person")
        .content(vec![
            Data {
                name: "Tobie".to_string(),
                settings: Settings {
                    active: true,
                    marketing: false,
                },
            },
            Data {
                name: "Jaime".to_string(),
                settings: Settings {
                    active: true,
                    marketing: true,
                },
            },
        ])
        .await?;
    dbg!(people);
    Ok(())
}
```

An example of two `person` records and one `company` record, followed by `.insert().relation()` to create a relation between them. Note the usage of the `#[surreal(rename)]` attribute to interface between the Rust struct `Founded` and the original relation table, which must have [an `in` and an `out` field](https://surrealdb.com/docs/reference/query-language/statements/relate).

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(SurrealValue)]
struct Data {
    id: RecordId,
    name: String,
}

#[derive(Debug, SurrealValue)]
struct Record {
    name: String,
    id: RecordId,
}

#[derive(Debug, SurrealValue)]
struct Founded {
    #[surreal(rename = "in")]
    founder: RecordId,
    #[surreal(rename = "out")]
    company: RecordId,
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

    let records: Vec<Record> = db
        .insert("person")
        .content(vec![
            Data {
                id: RecordId::new("person", "tobie"),
                name: "Tobie".to_string(),
            },
            Data {
                id: RecordId::new("person", "jaime"),
                name: "Jaime".to_string(),
            },
            Data {
                id: RecordId::new("company", "surrealdb"),
                name: "SurrealDB".to_string(),
            },
        ])
        .await?;
    dbg!(records);

    let founded: Vec<Founded> = db
        .insert("founded")
        .relation(vec![
            Founded {
                founder: RecordId::new("person", "tobie"),
                company: RecordId::new("company", "surrealdb"),
            },
            Founded {
                founder: RecordId::new("person", "jaime"),
                company: RecordId::new("company", "surrealdb"),
            },
        ])
        .await?;
    dbg!(founded);
    Ok(())
}
```

The equivalent SurrealQL statements to create and query the relations are:

```surql
RELATE [person:jaime, person:tobie]->founded->company:surrealdb;
SELECT ->founded->company FROM person;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/insert#see-also)
  * •
[.insert() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.insert)

Method Syntax

```rust
db.insert(resource).content(data);
db.insert(resource).relation(data);
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/insert#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or the specific record ID to create.  |  
| `data`  | The document / record data to insert.  |  
| `data`  | The relation table data to insert.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/insert#example-usage-1)
Inserting a record with a specific ID:

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Serialize)]
struct Data<'a> {
    name: &'a str,
    settings: Settings,
}

#[derive(Debug, Deserialize)]
struct Person {
    name: String,
    settings: Settings,
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

    let person: Option<Person> = db
        .insert(("person", "tobie"))
        .content(Data {
            name: "Tobie",
            settings: Settings {
                active: true,
                marketing: true,
            },
        })
        .await?;
    dbg!(person);
    Ok(())
}
```

Inserting multiple records into a table:

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Serialize)]
struct Data<'a> {
    name: &'a str,
    settings: Settings,
}

#[derive(Debug, Deserialize)]
struct Person {
    name: String,
    settings: Settings,
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

    let people: Vec<Person> = db
        .insert("person")
        .content(vec![
            Data {
                name: "Tobie",
                settings: Settings {
                    active: true,
                    marketing: false,
                },
            },
            Data {
                name: "Jaime",
                settings: Settings {
                    active: true,
                    marketing: true,
                },
            },
        ])
        .await?;
    dbg!(people);
    Ok(())
}
```

The `.insert()` method can take an empty tuple instead of a table ID if the following method contains [a record ID](https://docs.rs/surrealdb/latest/surrealdb/struct.RecordId.html).

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::RecordId;

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Serialize)]
struct Data<'a> {
    id: RecordId,
    name: &'a str,
}

#[derive(Debug, Deserialize)]
struct Person {
    name: String,
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

    let people: Vec<Person> = db
        .insert(())
        .content(vec![
            Data {
                id: RecordId::from(("person", "tobie")),
                name: "Tobie",
            },
            Data {
                id: RecordId::from(("person", "jaime")),
                name: "Jaime",
            },
        ])
        .await?;
    dbg!(people);
    Ok(())
}
```

An example of two `person` records and one `company` record, followed by `.insert().relation()` to create a relation between them. Note the usage of the `#[serde(rename)]` attribute to interface between the Rust struct `Founded` and the original relation table, which must have [an `in` and an `out` field](https://surrealdb.com/docs/reference/query-language/statements/relate).

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::RecordId;

#[derive(Debug, Serialize, Deserialize)]
struct Settings {
    active: bool,
    marketing: bool,
}

#[derive(Serialize)]
struct Data<'a> {
    id: RecordId,
    name: &'a str,
}

#[derive(Debug, Deserialize)]
struct Record {
    name: String,
    id: RecordId,
}

#[derive(Debug, Serialize, Deserialize)]
struct Founded {
    #[serde(rename = "in")]
    founder: RecordId,
    #[serde(rename = "out")]
    company: RecordId,
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

    let records: Vec<Record> = db
        .insert(())
        .content(vec![
            Data {
                id: RecordId::from(("person", "tobie")),
                name: "Tobie",
            },
            Data {
                id: RecordId::from(("person", "jaime")),
                name: "Jaime",
            },
            Data {
                id: RecordId::from(("company", "surrealdb")),
                name: "SurrealDB",
            },
        ])
        .await?;
    dbg!(records);

    let founded: Vec<Founded> = db
        .insert("founded")
        .relation(vec![
            Founded {
                founder: RecordId::from(("person", "tobie")),
                company: RecordId::from(("company", "surrealdb")),
            },
            Founded {
                founder: RecordId::from(("person", "jaime")),
                company: RecordId::from(("company", "surrealdb")),
            },
        ])
        .await?;
    dbg!(founded);
    Ok(())
}
```

The equivalent SurrealQL statements to create and query the relations are:

```surql
RELATE [person:jaime, person:tobie]->founded->company:surrealdb;
SELECT ->founded->company FROM person;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/insert#see-also-1)
  * •
[.insert() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.insert)
