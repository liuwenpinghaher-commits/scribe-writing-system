---
title: "https://surrealdb.com/docs/reference/rust/methods/select"
url: "https://surrealdb.com/docs/reference/rust/methods/select"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/select

Source: https://surrealdb.com/docs/reference/rust/methods/select

3.x2.x
Selects all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.select(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/select#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/select#example-usage)

```rust
// Select all records from a table
let people: Vec<Person> = db.select("person").await?;
// Select a specific record from a table
let person: Option<Person> = db.select(("person",
    "h5wxrf2ewk8xjxosxtyc")).await?;
```

###  Example usage: Retrieve unique id of a record[](https://surrealdb.com/docs/reference/rust/methods/select#example-usage-retrieve-unique-id-of-a-record)

```rust
use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::types::{RecordId, SurrealValue};

#[derive(Debug, SurrealValue)]
struct Person {
    id: RecordId,
    name: String,
    age: u8,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    // Connect to the database
    let db = Surreal::new::<Ws>("localhost:8000").await?;

    // Sign in
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;

    // Select namespace and database to use
    db.use_ns("main").use_db("main").await?;

    // Create a person
    db.query("CREATE person:john SET name = 'John Doe', age = 25")
        .await?
        .check()?;

    // Query that person
    let john: Option<Person> = db.select(("person", "john")).await?;
    dbg!(john);

    Ok(())
}
```

###  Restrict records with `.range()`[](https://surrealdb.com/docs/reference/rust/methods/select#restrict-records-with-range)
When selecting all records in a table (not a single record id), you can restrict results to a record-id range by chaining [`.range(...)`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Select.html#method.range-1). The argument implements [`Into`](https://docs.rs/surrealdb/latest/surrealdb/types/struct.RecordIdKeyRange.html): strings and tuples such as `"a"..="z"` or `(Bound::Included(x), Bound::Excluded(y))` express inclusive or exclusive bounds on the table’s record keys.

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
        .select::<Value>(Resource::from("person"))
        .range("n"..="z")
        .await
        .unwrap()
        .to_sql();
    println!("{res:?}");
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/select#translated-query)
This function will run the following query in the database:

```surql
SELECT * FROM $resource;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/select#see-also)
  * •
[.select() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.select)
  * •
[`Select::range`](https://docs.rs/surrealdb/latest/surrealdb/method/struct.Select.html#method.range-1)
  * •
[Live queries (`select().live()`)](https://surrealdb.com/docs/reference/rust/methods/select-live); alternatively [`query()`](https://surrealdb.com/docs/reference/rust/methods/query#live-select-stream) with `LIVE SELECT` and [`.stream()`](https://docs.rs/surrealdb/latest/surrealdb/method/query/struct.IndexedResults.html#method.stream)

Selects all records in a table, or a specific record, from the database.
Method Syntax

```rust
db.select(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/select#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/select#example-usage-1)

```rust
// Select all records from a table
let people: Vec<Person> = db.select("person").await?;
// Select a specific record from a table
let person: Option<Person> = db.select(("person",
    "h5wxrf2ewk8xjxosxtyc")).await?;
```

###  Example usage: retrieve unique id of a record[](https://surrealdb.com/docs/reference/rust/methods/select#example-usage-retrieve-unique-id-of-a-record-1)

```rust
use serde::Deserialize;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Root;
use surrealdb::RecordId;
use surrealdb::Surreal;

#[derive(Debug, Deserialize)]
struct Person {
	id: RecordId,
	name: String,
	age: u8,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
	// Connect to the database
	let db = Surreal::new::<Ws>("localhost:8000").await?;

	// Sign in
	db.signin(Root {
		username: "root",
		password: "secret",
	})
	.await?;

	// Select namespace and database to use
	db.use_ns("namespace").use_db("database").await?;

	// Create a person
		db.query("CREATE person:john SET name = 'John Doe',
	    age = 25").await?.check()?;

	// Query that person
	let john: Option<Person> = db.select(("person", "john")).await?;
	dbg!(john);

	Ok(())
}
```

###  Translated query[](https://surrealdb.com/docs/reference/rust/methods/select#translated-query-1)
This function will run the following query in the database:

```surql
SELECT * FROM $resource;
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/select#see-also-1)
  * •
[.select() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.select)
