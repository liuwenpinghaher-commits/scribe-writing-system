---
title: "https://surrealdb.com/docs/reference/rust/methods/export"
url: "https://surrealdb.com/docs/reference/rust/methods/export"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/export

Source: https://surrealdb.com/docs/reference/rust/methods/export

3.x2.x
Dumps the database contents to a file.
Note
WebSocket connections currently do not support exports and imports. Be sure to use an HTTP endpoint and the `protocol-http` feature when using this method.
Method Syntax

```rust
db.export(target)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/export#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select. Will also accept a tuple of record name and ID.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/export#example-usage)
The `.export()` method can be used to save the contents of a database to a file.

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("main").use_db("main").await?;

    // Create a `person` record
    db.create(Resource::from("person")).await?;

    db.export("backup.surql").await?;
    Ok(())
}
```

If an empty tuple is passed in for the file name, the `.export()` method will instead return an async stream of bytes.

```rust
use futures::StreamExt;
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("main").use_db("main").await?;

    // Create a `person` record
    db.create(Resource::from("person")).await?;

    let mut stream = db.export(()).await?;

    while let Some(Ok(line)) = stream.next().await {
        let content = String::from_utf8(line).unwrap();
        println!("{content}");
    }
    Ok(())
}
```

The output for the above sample should look like the following.

```
-- ------------------------------

-- OPTION

-- ------------------------------

OPTION IMPORT;

-- ------------------------------

-- TABLE: person

-- ------------------------------

DEFINE TABLE person TYPE ANY SCHEMALESS PERMISSIONS NONE;

-- ------------------------------

-- TABLE DATA: person

-- ------------------------------

INSERT [ { id: person:bgq0b0rblnozrufizdjm } ];
```

###  Export configuration[](https://surrealdb.com/docs/reference/rust/methods/export#export-configuration)
The [`Export`](https://docs.rs/surrealdb/2/surrealdb/method/struct.Export.html) struct has a method called `.with_config()` that gives access to the configuration parameters for the export. These can be chained one after another inside a single line of code. The majority of these functions take a single `bool`:
  * •
`.versions()`: whether to include [version information](https://surrealdb.com/docs/reference/query-language/statements/select#the-version-clause) for the SurrealKV storage backend
  * •
`.accesses()`: whether to include [`DEFINE ACCESS` statements](https://surrealdb.com/docs/reference/query-language/statements/define/access/record)
  * •
`.analyzers()`: whether to include [`DEFINE ANALYZER` statements](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer)
  * •
`.functions()`: whether to include [`DEFINE FUNCTION` statements](https://surrealdb.com/docs/reference/query-language/statements/define/function)
  * •
`.apis()`: whether to include API definitions in the export
  * •
`.buckets()`: whether to include bucket definitions
  * •
`.modules()`: whether to include [`DEFINE MODULE`](https://surrealdb.com/docs/reference/query-language/statements/define/module) statements
  * •
`.configs()`: whether to include stored configuration definitions
  * •
`.records()`: whether to include the existing records in the database
  * •
`.params()`: whether to include [`DEFINE PARAM` statements](https://surrealdb.com/docs/reference/query-language/statements/define/param)
  * •
`.users()`: whether to include [`DEFINE USER` statements](https://surrealdb.com/docs/reference/query-language/statements/define/user)

`.tables()` takes a `Vec` of strings in addition to a boolean.
  * •
`.tables()`: a list of tables to export, as opposed to all of the tables in the database.

Example of export configuration:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root".to_string(),
        password: "secret".to_string(),
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query(
        "
    DEFINE FUNCTION fn::get_cats() { RETURN SELECT * FROM cat };
    DEFINE TABLE person SCHEMAFULL;
    DEFINE FIELD name ON person TYPE string;
    DEFINE FIELD age ON person TYPE int;
    CREATE person SET name = 'Aeon', age = 20;
    CREATE cat SET name = 'Cat of Aeon';
    ",
    )
    .await?;

    // Cat-related implementation is still experimental
    // so don't export the cat table or get_cats() function
    db.export("backup.surql")
        .with_config()
        .tables(vec!["person"])
        .functions(false)
        .await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/export#see-also)
  * •
[.export() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.export)

Dumps the database contents to a file.
Note
WebSocket connections currently do not support exports and imports. Be sure to use an HTTP endpoint when using this method.
Method Syntax

```rust
db.export(target)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/export#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `resource`  | The table name or a record ID to select. Will also accept a tuple of record name and ID.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/export#example-usage-1)
The `.export()` method can be used to save the contents of a database to a file.

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    // Create a `person` record
    db.create(Resource::from("person")).await?;

    db.export("backup.surql").await?;
    Ok(())
}
```

If an empty tuple is passed in for the file name, the `.export()` method will instead return an async stream of bytes.

```rust
use futures::StreamExt;
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;
use surrealdb::opt::Resource;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    // Create a `person` record
    db.create(Resource::from("person")).await?;

    let mut stream = db.export(()).await?;

    while let Some(Ok(line)) = stream.next().await {
        let content = String::from_utf8(line).unwrap();
        println!("{content}");
    }
    Ok(())
}
```

The output for the above sample should look like the following.

```
-- ------------------------------

-- OPTION

-- ------------------------------

OPTION IMPORT;

-- ------------------------------

-- TABLE: person

-- ------------------------------

DEFINE TABLE person TYPE ANY SCHEMALESS PERMISSIONS NONE;

-- ------------------------------

-- TABLE DATA: person

-- ------------------------------

INSERT [ { id: person:bgq0b0rblnozrufizdjm } ];
```

###  Export configuration[](https://surrealdb.com/docs/reference/rust/methods/export#export-configuration-1)
The [`Export`](https://docs.rs/surrealdb/2/surrealdb/method/struct.Export.html) struct has a method called `.with_config()` that gives access to the configuration parameters for the export. These can be chained one after another inside a single line of code. The majority of these functions take a single `bool`:
  * •
`.versions()`: whether to include [version information](https://surrealdb.com/docs/reference/query-language/statements/select#the-version-clause) for backends with versioning enabled
  * •
`.accesses()`: whether to include [`DEFINE ACCESS` statements](https://surrealdb.com/docs/reference/query-language/statements/define/access/record)
  * •
`.analyzers()`: whether to include [`DEFINE ANALYZER` statements](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer)
  * •
`.functions()`: whether to include [`DEFINE FUNCTION` statements](https://surrealdb.com/docs/reference/query-language/statements/define/function)
  * •
`.apis()`: whether to include [defined APIs](https://surrealdb.com/docs/reference/query-language/statements/define/api) in the export
  * •
`.buckets()`: whether to include [defined buckets](https://surrealdb.com/docs/reference/query-language/statements/define/bucket)
  * •
`.modules()`: whether to include [`DEFINE MODULE`](https://surrealdb.com/docs/reference/query-language/statements/define/module) statements
  * •
`.configs()`: whether to include stored configuration definitions
  * •
`.records()`: whether to include the existing records in the database
  * •
`.params()`: whether to include [`DEFINE PARAM` statements](https://surrealdb.com/docs/reference/query-language/statements/define/param)
  * •
`.users()`: whether to include [`DEFINE USER` statements](https://surrealdb.com/docs/reference/query-language/statements/define/user)

`.tables()` takes a `Vec` of strings in addition to a boolean.
  * •
`.tables()`: a list of tables to export, as opposed to all of the tables in the database.

Example of export configuration:

```rust
use surrealdb::engine::any::connect;
use surrealdb::opt::auth::Root;

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = connect("http://localhost:8000").await?;
    db.signin(Root {
        username: "root",
        password: "secret",
    })
    .await?;
    db.use_ns("ns").use_db("db").await?;

    db.query(
        "
    DEFINE FUNCTION fn::get_cats() { RETURN SELECT * FROM cat };
    DEFINE TABLE person SCHEMAFULL;
    DEFINE FIELD name ON person TYPE string;
    DEFINE FIELD age ON person TYPE int;
    CREATE person SET name = 'Aeon', age = 20;
    CREATE cat SET name = 'Cat of Aeon';
    ",
    )
    .await?;

    // Cat-related implementation is still experimental
    // so don't export the cat table or get_cats() function
    db.export("backup.surql")
        .with_config()
        .tables(vec!["person"])
        .functions(false)
        .await?;
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/export#see-also-1)
  * •
[.export() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.export)
