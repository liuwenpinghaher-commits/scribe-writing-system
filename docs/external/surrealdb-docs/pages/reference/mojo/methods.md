---
title: "https://surrealdb.com/docs/reference/mojo/methods"
url: "https://surrealdb.com/docs/reference/mojo/methods"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods

Source: https://surrealdb.com/docs/reference/mojo/methods

Most methods in the SurrealDB Mojo SDK are called on an instance of `AsyncSurrealClient` or its blocking wrapper `SurrealClient`. Both expose the same surface.
The table below lists documented methods **in alphabetical order** (by page name).
##  All methods[](https://surrealdb.com/docs/reference/mojo/methods#all-methods)  
| Method  | Description  |  
| --- | --- |  
| [`client.api()`](https://surrealdb.com/docs/reference/mojo/methods/api)  | Calls a custom API handler defined on the database  |  
| [`client.authenticate()`](https://surrealdb.com/docs/reference/mojo/methods/authenticate)  | Authenticates the current connection with a token  |  
| [`client.begin_transaction()`](https://surrealdb.com/docs/reference/mojo/methods/begin-transaction)  | Starts a session-scoped transaction, returning a handle  |  
| [`client.call()`](https://surrealdb.com/docs/reference/mojo/methods/call)  | Runs a SurrealQL function  |  
| [`client.close()`](https://surrealdb.com/docs/reference/mojo/methods/close)  | Closes the connection  |  
| [`client.connect()`](https://surrealdb.com/docs/reference/mojo/methods/connect)  | Connects to a database endpoint  |  
| [`client.create()`](https://surrealdb.com/docs/reference/mojo/methods/create)  | Creates a record in the database  |  
| [`client.delete()`](https://surrealdb.com/docs/reference/mojo/methods/delete)  | Deletes all records, or a specific record  |  
| [`client.health()`](https://surrealdb.com/docs/reference/mojo/methods/health)  | Runs a health check against the server  |  
| [`client.insert()`](https://surrealdb.com/docs/reference/mojo/methods/insert)  | Inserts one or more records into a table  |  
| [`client.insert_relation()`](https://surrealdb.com/docs/reference/mojo/methods/insert-relation)  | Inserts one or more relations into a table  |  
| [`client.invalidate()`](https://surrealdb.com/docs/reference/mojo/methods/invalidate)  | Invalidates the authentication for the current connection  |  
| [`client.kill()`](https://surrealdb.com/docs/reference/mojo/methods/kill)  | Stops a running live query  |  
| [`client.live_query()`](https://surrealdb.com/docs/reference/mojo/methods/live)  | Starts a live query on a table  |  
| [`client.merge()`](https://surrealdb.com/docs/reference/mojo/methods/merge)  | Merges data into a record  |  
| [`client.patch()`](https://surrealdb.com/docs/reference/mojo/methods/patch)  | Applies a JSON Patch to a record  |  
| [`client.query()`](https://surrealdb.com/docs/reference/mojo/methods/query)  | Runs a set of SurrealQL statements against the database  |  
| [`client.select()`](https://surrealdb.com/docs/reference/mojo/methods/select)  | Selects all records in a table, or a specific record  |  
| [`client.set()`](https://surrealdb.com/docs/reference/mojo/methods/set)  | Assigns a value as a parameter for this connection  |  
| [`client.signin()`](https://surrealdb.com/docs/reference/mojo/methods/signin)  | Signs in to the database with credentials  |  
| [`client.signup()`](https://surrealdb.com/docs/reference/mojo/methods/signup)  | Signs up to a record-access method  |  
| [`client.transaction_multi()`](https://surrealdb.com/docs/reference/mojo/methods/transaction-multi)  | Runs a list of statements as one atomic transaction  |  
| [`client.unset()`](https://surrealdb.com/docs/reference/mojo/methods/unset)  | Removes a parameter for this connection  |  
| [`client.update()`](https://surrealdb.com/docs/reference/mojo/methods/update)  | Updates all records in a table, or a specific record  |  
| [`client.upsert()`](https://surrealdb.com/docs/reference/mojo/methods/upsert)  | Upserts all records in a table, or a specific record  |  
| [`client.use()`](https://surrealdb.com/docs/reference/mojo/methods/use)  | Switches to a specific namespace and database  |  
| [`client.version()`](https://surrealdb.com/docs/reference/mojo/methods/version)  | Returns the database version  |
