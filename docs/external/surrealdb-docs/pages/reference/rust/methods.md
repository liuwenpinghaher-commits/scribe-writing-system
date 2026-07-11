---
title: "https://surrealdb.com/docs/reference/rust/methods"
url: "https://surrealdb.com/docs/reference/rust/methods"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods

Source: https://surrealdb.com/docs/reference/rust/methods

Most methods in the SurrealDB SDK involve either working with or creating an instance of the [`Surreal`](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html) struct, which serves as the database client instance for embedded or remote databases.
The table below lists documented methods **in alphabetical order** (by page name).
##  All methods[](https://surrealdb.com/docs/reference/rust/methods#all-methods)  
| Function  | Description  |  
| --- | --- |  
| [`db.authenticate()`](https://surrealdb.com/docs/reference/rust/methods/authenticate)  | Authenticates the current connection with a JWT token  |  
| [`db.begin()`](https://surrealdb.com/docs/reference/rust/methods/begin)  |  Start a session-scoped multi-statement transaction, returning a `Transaction`handle (commit, cancel, query, and CRUD)  |  
| [`db.connect()`](https://surrealdb.com/docs/reference/rust/methods/connect)  | Connects to a local or remote database endpoint  |  
| [`db.create()`](https://surrealdb.com/docs/reference/rust/methods/create)  | Creates a record in the database  |  
| [`db.delete()`](https://surrealdb.com/docs/reference/rust/methods/delete)  | Deletes all records, or a specific record  |  
| [`db.export()`](https://surrealdb.com/docs/reference/rust/methods/export)  | Exports the database to a file or a live stream of bytes  |  
| [`value.get()`](https://surrealdb.com/docs/reference/rust/methods/get)  |  On `Value`(and query results), reads a field on an object or an index in an array  |  
| [`db.health()`](https://surrealdb.com/docs/reference/rust/methods/health)  | Runs a health check to verify the server accepts commands  |  
| [`db.import()`](https://surrealdb.com/docs/reference/rust/methods/import)  | Imports the contents of another database from a file  |  
| [`Surreal::init()`](https://surrealdb.com/docs/reference/rust/methods/init)  | Initializes a non-connected instance of the database client  |  
| [`db.insert()`](https://surrealdb.com/docs/reference/rust/methods/insert)  | Inserts one or multiple records or relations in the database  |  
| [`db.invalidate()`](https://surrealdb.com/docs/reference/rust/methods/invalidate)  | Invalidates the authentication for the current connection  |  
| [`Surreal::new()`](https://surrealdb.com/docs/reference/rust/methods/new)  | Initializes a connected instance of the database client  |  
| [`db.query()`](https://surrealdb.com/docs/reference/rust/methods/query)  | Runs a set of [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database  |  
| [`db.run()`](https://surrealdb.com/docs/reference/rust/methods/run)  | Runs a SurrealQL function  |  
| [`db.select()`](https://surrealdb.com/docs/reference/rust/methods/select)  | Selects all records in a table, or a specific record  |  
| [`db.select().live()`](https://surrealdb.com/docs/reference/rust/methods/select-live)  | Performs a LIVE SELECT query on the database  |  
| [`db.set()`](https://surrealdb.com/docs/reference/rust/methods/set)  | Assigns a value as a parameter for this connection  |  
| [`db.signin()`](https://surrealdb.com/docs/reference/rust/methods/signin)  | Signs this connection in to a specific authentication scope  |  
| [`db.signup()`](https://surrealdb.com/docs/reference/rust/methods/signup)  | Signs this connection up to a specific authentication scope  |  
| [`db.unset()`](https://surrealdb.com/docs/reference/rust/methods/unset)  | Removes a parameter for this connection  |  
| [`db.update()`](https://surrealdb.com/docs/reference/rust/methods/update)  | Updates all records in a table, or a specific record  |  
| [`db.upsert()`](https://surrealdb.com/docs/reference/rust/methods/upsert)  | Upserts all records in a table, or a specific record  |  
| [`db.use_ns().use_db()`](https://surrealdb.com/docs/reference/rust/methods/use)  | Switch to a specific namespace and database  |  
| [`db.use_defaults()`](https://surrealdb.com/docs/reference/rust/methods/use-defaults)  | Select the default namespace and database for this connection  |  
| [`db.version()`](https://surrealdb.com/docs/reference/rust/methods/version)  | Returns the current database version  |  
| [`db.wait_for()`](https://surrealdb.com/docs/reference/rust/methods/wait-for)  |  Blocks until a connection or database session event (such as `WaitFor::Connection`) is ready  |
