---
title: "https://surrealdb.com/docs/reference/dotnet/methods"
url: "https://surrealdb.com/docs/reference/dotnet/methods"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/methods

Source: https://surrealdb.com/docs/reference/dotnet/methods

The .NET SDK for SurrealDB has a single SurrealDB class that provides methods for querying a remote SurrealDB database.  
The class is designed to be simple to use and easy to understand for developers who are new to .NET or SurrealDB.  
This page lists out the methods that are available in the SurrealDB class.
##  Initialization methods[](https://surrealdb.com/docs/reference/dotnet/methods#initialization-methods)  
| Method  | Description  |  
| --- | --- |  
| [` db.Connect() `](https://surrealdb.com/docs/reference/dotnet/methods/connect)  | Connects the client to the underlying endpoint, also improving performance to avoid cold starts  |  
| [` db.Use(namespace, database)`](https://surrealdb.com/docs/reference/dotnet/methods/use)  | Switch to a specific namespace and database  |  
| [`db.Set(key, value)`](https://surrealdb.com/docs/reference/dotnet/methods/set)  | Assigns a value as a parameter for this connection  |  
| [`db.Unset(key)`](https://surrealdb.com/docs/reference/dotnet/methods/unset)  | Removes a parameter for this connection  |  
##  Query methods[](https://surrealdb.com/docs/reference/dotnet/methods#query-methods)  
| Method  | Description  |  
| --- | --- |  
| [`db.Query<T>(sql)`](https://surrealdb.com/docs/reference/dotnet/methods/query)  | Runs a set of [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database  |  
| [`db.RawQuery<T>(sql, vars)`](https://surrealdb.com/docs/reference/dotnet/methods/raw-query)  | Runs a set of [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database, based on a raw SurrealQL query  |  
| [`db.Select<T>(thing)`](https://surrealdb.com/docs/reference/dotnet/methods/select)  | Selects all records in a table, or a specific record  |  
| [`db.LiveQuery<T>(sql)`](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-query)  | Initiate a live query from a [SurrealQL statement](https://surrealdb.com/docs/reference/query-language)  |  
| [`db.LiveRawQuery<T>(sql)`](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-raw-query)  | Initiate a live query from a [SurrealQL statement](https://surrealdb.com/docs/reference/query-language), based on a raw SurrealQL query  |  
| [`db.LiveTable<T>(table, diff)`](https://surrealdb.com/docs/reference/dotnet/core/streaming#live-table)  | Initiate a live query from a table  |  
| [`db.ListenLive<T>(queryUuid)`](https://surrealdb.com/docs/reference/dotnet/core/streaming#listen-live)  | Listen responses from an existing live query  |  
| [`db.Kill(queryUuid)`](https://surrealdb.com/docs/reference/dotnet/core/streaming#kill)  | Kill a running live query  |  
##  Mutation methods[](https://surrealdb.com/docs/reference/dotnet/methods#mutation-methods)  
| Method  | Description  |  
| --- | --- |  
| [`db.Create<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/create)  | Creates a record in the database  |  
| [`db.Insert<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/insert)  | Inserts one or multiple records in the database  |  
| [`db.Update<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/update)  | Updates all records in a table, or a specific record  |  
| [`db.Upsert<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/upsert)  | Creates or updates a specific record  |  
| [`db.Merge<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/merge)  | Modifies all records in a table, or a specific record  |  
| [`db.Patch<T>(thing, data)`](https://surrealdb.com/docs/reference/dotnet/methods/patch)  | Applies JSON Patch changes to all records in a table, or a specific record  |  
| [`db.Delete(thing)`](https://surrealdb.com/docs/reference/dotnet/methods/delete)  | Deletes all records, or a specific record  |  
##  Authentication methods[](https://surrealdb.com/docs/reference/dotnet/methods#authentication-methods)  
| Method  | Description  |  
| --- | --- |  
| [`db.SignUp(credentials)`](https://surrealdb.com/docs/reference/dotnet/methods/signup)  | Signs this connection up to a specific authentication scope  |  
| [`db.SignIn(credentials)`](https://surrealdb.com/docs/reference/dotnet/methods/signin)  | Signs this connection in to a specific authentication scope  |  
| [`db.Invalidate()`](https://surrealdb.com/docs/reference/dotnet/methods/invalidate)  | Invalidates the authentication for the current connection  |  
| [`db.Authenticate(token)`](https://surrealdb.com/docs/reference/dotnet/methods/authenticate)  | Authenticates the current connection with a JWT token  |  
| [`db.Info<T>()`](https://surrealdb.com/docs/reference/dotnet/methods/info)  | Returns the record of an authenticated scope user  |
