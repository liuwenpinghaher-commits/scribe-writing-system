---
title: "https://surrealdb.com/docs/reference/swift/methods"
url: "https://surrealdb.com/docs/reference/swift/methods"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods

Source: https://surrealdb.com/docs/reference/swift/methods

The Swift SDK exposes its functionality through the `SurrealHTTPClient` and `SurrealWebSocketClient` types, which share the same API. This page lists the methods available on a connected client.
##  Initialization methods[](https://surrealdb.com/docs/reference/swift/methods#initialization-methods)  
| Method  | Description  |  
| --- | --- |  
| [`client.connect()`](https://surrealdb.com/docs/reference/swift/methods/connect)  | Connects the client to the underlying endpoint  |  
| [`client.use(namespace, database)`](https://surrealdb.com/docs/reference/swift/methods/use)  | Switch to a specific namespace and database  |  
##  Authentication methods[](https://surrealdb.com/docs/reference/swift/methods#authentication-methods)  
| Method  | Description  |  
| --- | --- |  
| [`client.signup(credentials)`](https://surrealdb.com/docs/reference/swift/methods/signup)  | Signs this connection up to a specific authentication access  |  
| [`client.signin(credentials)`](https://surrealdb.com/docs/reference/swift/methods/signin)  | Signs this connection in to a specific authentication level  |  
| [`client.authenticate(token)`](https://surrealdb.com/docs/reference/swift/methods/authenticate)  | Authenticates the current connection with a JWT token  |  
| [`client.invalidate()`](https://surrealdb.com/docs/reference/swift/methods/invalidate)  | Invalidates the authentication for the current connection  |  
##  Query methods[](https://surrealdb.com/docs/reference/swift/methods#query-methods)  
| Method  | Description  |  
| --- | --- |  
| [`client.select(model)`](https://surrealdb.com/docs/reference/swift/methods/select)  | Selects all records in a table, or a specific record  |  
| [`client.query(query)`](https://surrealdb.com/docs/reference/swift/methods/query)  | Runs a query built with the query DSL or macros  |  
| [`client.queryRaw(sql, bindings)`](https://surrealdb.com/docs/reference/swift/methods/query-raw)  | Runs a raw SurrealQL query with bound parameters  |  
| [`client.live(query)`](https://surrealdb.com/docs/reference/swift/methods/live)  | Subscribes to changes via a live query (WebSocket only)  |  
| [`client.kill(liveQueryID)`](https://surrealdb.com/docs/reference/swift/methods/kill)  | Kills a running live query  |  
##  Mutation methods[](https://surrealdb.com/docs/reference/swift/methods#mutation-methods)  
| Method  | Description  |  
| --- | --- |  
| [`client.create(model)`](https://surrealdb.com/docs/reference/swift/methods/create)  | Creates a record in the database  |  
| [`client.update(model)`](https://surrealdb.com/docs/reference/swift/methods/update)  | Updates matching records, or a specific record  |  
| [`client.upsert(model)`](https://surrealdb.com/docs/reference/swift/methods/upsert)  | Creates or updates matching records  |  
| [`client.delete(model)`](https://surrealdb.com/docs/reference/swift/methods/delete)  | Deletes matching records, or a specific record  |
