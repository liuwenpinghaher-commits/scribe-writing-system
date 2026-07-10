---
title: "https://surrealdb.com/docs/reference/rust/methods/delete"
url: "https://surrealdb.com/docs/reference/rust/methods/delete"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/delete

Source: https://surrealdb.com/docs/reference/rust/methods/delete

3.x2.x
Deletes all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.delete(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/delete#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select. Will also accept a tuple of record name and ID.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/delete#example-usage)

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Person {
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
    db.use_ns("ns").use_db("db").await?;

    // Create three `person` records
    db.create(Resource::from(("person", "one"))).await?;
    db.create(Resource::from(("person", "two"))).await?;
    db.create(Resource::from(("person", "three"))).await?;

        let deleted_one: Option<Person> = db.delete(("person",
        "one")).await?;
    dbg!(deleted_one);
    let deleted_rest: Vec<Person> = db.delete("person").await?;
    dbg!(deleted_rest);
    Ok(())
}
```

###  Restrict records with `.range()`[](https://surrealdb.com/docs/reference/rust/methods/delete#restrict-records-with-range)
For deletes targeting every record in a table, chain [`.range(...)`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Delete.html#method.range-1) so only record IDs inside the [`RecordIdKeyRange`](https://docs.rs/surrealdb/latest/surrealdb/types/struct.RecordIdKeyRange.html) are removed.

```rust
use surrealdb::{
    engine::any::connect,
    opt::Resource,
    types::{ToSql, Value},
};

#[tokio::main]
async fn main() {
    let db = connect("memory").await.unwrap();
    db.use_ns("ns").use_db("db").await.unwrap();

    db.query("CREATE person:alucard, person:plato, person:vlad")
        .await
        .unwrap();

    let res = db
        .delete::<Value>(Resource::from("person"))
        .range("n"..="z")
        .await
        .unwrap()
        .to_sql();
    println!("{res:?}");
}
```

Deletes all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.delete(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/delete#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select. Will also accept a tuple of record name and ID.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/delete#example-usage-1)

```rust
use serde::{Deserialize, Serialize};
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;
use surrealdb::RecordId;

#[derive(Debug, Serialize, Deserialize)]
struct Person {
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

    // Create three `person` records
    db.create(Resource::from(("person", "one"))).await?;
    db.create(Resource::from(("person", "two"))).await?;
    db.create(Resource::from(("person", "three"))).await?;

        let deleted_one: Option<Person> = db.delete(("person",
        "one")).await?;
    dbg!(deleted_one);
    let deleted_rest: Vec<Person> = db.delete("person").await?;
    dbg!(deleted_rest);
    Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/delete#translated-query)
While SurrealQL's `DELETE` statement returns an empty array by default, this function translates into a query that adds a `RETURN BEFORE` clause to return the deleted items.

```surql
DELETE FROM $resource RETURN BEFORE;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/delete#see-also)
  * •
[.delete() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.delete)
