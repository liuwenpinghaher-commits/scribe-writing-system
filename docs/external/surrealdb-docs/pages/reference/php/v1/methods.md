---
title: "https://surrealdb.com/docs/reference/php/v1/methods"
url: "https://surrealdb.com/docs/reference/php/v1/methods"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/methods

Source: https://surrealdb.com/docs/reference/php/v1/methods

The SurrealDB SDK for PHP has a single SurrealDB class that provides methods for querying a remote SurrealDB database.  
The class is designed to be simple to use and easy to understand for developers who are new to PHP or SurrealDB.  
This page lists out the methods that are available in the SurrealDB class.
##  Initialization methods[](https://surrealdb.com/docs/reference/php/v1/methods#initialization-methods)  
| Function  | Description  |  
| --- | --- |  
| [` $db->connect($url, $options) `](https://surrealdb.com/docs/reference/php/v1/methods/connect)  | Connects to a local or remote database endpoint  |  
| [` $db->close() `](https://surrealdb.com/docs/reference/php/v1/methods/close)  | Closes the persistent connection to the database  |  
| [` $db->use($options)`](https://surrealdb.com/docs/reference/php/v1/methods/use)  | Switch to a specific namespace and database  |  
| [`$db->let($key,$val)`](https://surrealdb.com/docs/reference/php/v1/methods/let)  | Assigns a value as a parameter for this connection  |  
| [`$db->unset($key)`](https://surrealdb.com/docs/reference/php/v1/methods/unset)  | Removes a parameter for this connection  |  
##  Query methods[](https://surrealdb.com/docs/reference/php/v1/methods#query-methods)  
| Function  | Description  |  
| --- | --- |  
| [`$db->query($sql,$vars)`](https://surrealdb.com/docs/reference/php/v1/methods/query)  | Runs a set of [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database  |  
| [`$db->select($thing)`](https://surrealdb.com/docs/reference/php/v1/methods/select)  | Selects all records in a table, or a specific record  |  
##  Mutation methods[](https://surrealdb.com/docs/reference/php/v1/methods#mutation-methods)  
| Function  | Description  |  
| --- | --- |  
| [`$db->create($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/create)  | Creates a record in the database  |  
| [`$db->insert($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/insert)  | Inserts one or multiple records in the database  |  
| [`$db->insertRelation($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/insert-relation)  | Inserts one or multiple records in the database  |  
| [`$db->update($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/update)  | Updates all records in a table, or a specific record  |  
| [`$db->merge($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/merge)  | Modifies all records in a table, or a specific record  |  
| [`$db->patch($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/patch)  | Applies JSON Patch changes to all records in a table, or a specific record  |  
| [`$db->delete($thing,$data)`](https://surrealdb.com/docs/reference/php/v1/methods/delete)  | Deletes all records, or a specific record  |  
##  Authentication methods[](https://surrealdb.com/docs/reference/php/v1/methods#authentication-methods)  
| Function  | Description  |  
| --- | --- |  
| [`$db->signup($vars)`](https://surrealdb.com/docs/reference/php/v1/methods/signup)  | Signs this connection up to a specific authentication scope  |  
| [`$db->signin($vars)`](https://surrealdb.com/docs/reference/php/v1/methods/signin)  | Signs this connection in to a specific authentication scope  |  
| [`$db->invalidate()`](https://surrealdb.com/docs/reference/php/v1/methods/invalidate)  | Invalidates the authentication for the current connection  |  
| [`$db->authenticate(token)`](https://surrealdb.com/docs/reference/php/v1/methods/authenticate)  | Authenticates the current connection with a JWT token  |  
| [`$db->info()`](https://surrealdb.com/docs/reference/php/v1/methods/info)  | Returns the record of an authenticated scope user  |  
##  Utility methods[](https://surrealdb.com/docs/reference/php/v1/methods#utility-methods)  
| Function  | Description  |  
| --- | --- |  
| [`$db->import($content, $username, $password)`](https://surrealdb.com/docs/reference/php/v1/methods/import)  | Imports data into the database  |  
| [`$db->export($username, $password)`](https://surrealdb.com/docs/reference/php/v1/methods/export)  | Exports data from the database  |  
| [`$db->health()`](https://surrealdb.com/docs/reference/php/v1/methods/health)  | Checks wether the database is running and the storage engine is healthy  |  
| [`$db->status()`](https://surrealdb.com/docs/reference/php/v1/methods/status)  | Wether the database is running or is reachable  |
