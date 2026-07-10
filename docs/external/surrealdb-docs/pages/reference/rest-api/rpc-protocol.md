---
title: "https://surrealdb.com/docs/reference/rest-api/rpc-protocol"
url: "https://surrealdb.com/docs/reference/rest-api/rpc-protocol"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rest-api/rpc-protocol

Source: https://surrealdb.com/docs/reference/rest-api/rpc-protocol

The RPC protocol allows for network protocol agnostic communication with SurrealDB. It is used internally by our client SDKs, and supports both HTTP and WebSocket based communication. Combined with the power of our [CBOR protocol](https://surrealdb.com/docs/reference/rest-api/cbor) specification, the RPC protocol provides a fully type-safe and efficient way to interact with SurrealDB over the network.
##  Session variables[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#session-variables)
SurrealDB's session variables provide a robust mechanism for managing session-specific data. Think of them as temporary storage tied directly to a user's active connection, ideal for tasks like maintaining application state, storing user preferences, or holding temporary data relevant only to the current session.
A key characteristic of session variables is their scope: they are strictly confined to the individual connection. This isolation ensures that one user's session data remains private and does not interfere with others, allowing for personalized experiences within a multi-user environment.  
You can interact with session variables in the following ways:
  1. 1.
**Explicit Session-Wide Management:**
     * ◦
Use the [`let`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#let-) method to define a new variable or update an existing one within the current session. This variable will persist for the duration of the connection.
     * ◦
Use the [`unset`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#unset-) method to remove a previously defined variable from the session.
     * ◦
The [`reset`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#reset) method, in addition to its other functions, clears _all_ currently defined session variables, restoring the session's variable state.
  2. 2.
**Implicit Request-Scoped Management:**
     * ◦
Methods [`query`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#query), [`select`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#select), [`insert`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#insert), [`create`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#create), [`upsert`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#upsert), [`update`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#update), [`relate`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#relate), and [`delete`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#delete), accept an optional `vars` parameter. This parameter is an object containing key-value pairs, where each key represents the variable name (without the leading `$`) and the value is the data to be assigned.
     * ◦
Variables passed via this parameter are defined _only_ for the execution context of that specific method call. They temporarily override any session-wide variable with the same name for that request but do not permanently alter the session state. These variables are automatically discarded once the method execution completes.

To utilize a session variable within a query or method, prefix its name with a dollar sign (`$`), for example, `$user_id`.
##  Supported methods[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#supported-methods)
You can use the RPC protocol to perform the following actions:  
| Function  | Description  |  
| --- | --- |  
| [`authenticate [ token ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#authenticate)  | Authenticate a user against SurrealDB with a token  |  
| [`create [ thing, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#create)  | Create a record with a random or specified ID  |  
| [`delete [ thing ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#delete)  | Delete either all records in a table or a single record  |  
| [`info`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#info)  | Returns the record of an authenticated record user  |  
| [`insert [ thing, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#insert)  | Insert one or multiple records in a table  |  
| [`insert_relation [ table, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#insert_relation)  | Insert a new relation record into a specified table or infer the table from the data  |  
| [`invalidate`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#invalidate)  | Invalidate a user's session for the current connection  |  
| [`kill [ queryUuid ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#kill-)  | Kill an active live query  |  
| [`let [ name, value ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#let-)  | Define a variable on the current connection  |  
| [`live [ table, diff ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#live-)  | Initiate a live query  |  
| [`merge [ thing, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#merge)  | Merge specified data into either all records in a table or a single record  |  
| [`patch [ thing, patches, diff ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#patch)  | Patch either all records in a table or a single record with specified patches  |  
| [`ping`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#ping)  | Sends a ping to the database  |  
| [`query [ sql, vars ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#query)  | Execute a custom query with optional variables  |  
| [`relate [ in, relation, out, data? ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#relate)  | Create graph relationships between created records  |  
| [`reset`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#reset)  | Resets all attributes for the current connection  |  
| [`run [ func_name, version, args ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#run)  | Execute built-in functions, custom functions, or machine learning models with optional arguments.  |  
| [`select [ thing ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#select)  | Select either all records in a table or a single record  |  
| [`signin [NS, DB, AC, ... ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#signin)  | Signin a root, NS, DB or record user against SurrealDB  |  
| [`signup [ NS, DB, AC, ... ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#signup)  | Signup a user using the SIGNUP query defined in a record access method  |  
| [`unset [ name ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#unset-)  | Remove a variable from the current connection  |  
| [`update [ thing, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#update)  | Modify either all records in a table or a single record with specified data if the record already exists  |  
| [`upsert [ thing, data ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#upsert)  | Replace either all records in a table or a single record with specified data  |  
| [`use [ ns, db ]`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#use)  | Specifies or unsets the namespace and/or database for the current connection  |  
| [`version`](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#version)  | Returns version information about the database/server  |  
  

##  `authenticate`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#authenticate)
This method allows you to authenticate a user against SurrealDB with a token.
Method Syntax

```json
authenticate [ token ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters)  
| Parameter  | Description  |  
| --- | --- |  
| `token`  | The token that authenticates the user  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage)
Request

```json
{
    "id": 1,
    "method": "authenticate",
    "params": [ "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA" ]
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

  

##  `create`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#create)
This method creates a record either with a random or specified ID.
Method Syntax

```json
create [ thing, data ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-1)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to create. Passing just a table will result in a randomly generated ID  |  
| `data`  | The content of the record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-1)
Request

```json
{
    "id": 1,
    "method": "create",
    "params": [
        "person",
        {
            "name": "Mary Doe"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": [
        {
            "id": "person:s5fa6qp4p8ey9k5j0m9z",
            "name": "Mary Doe"
        }
    ]
}
```

  

##  `delete`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#delete)
This method deletes either all records in a table or a single record.
Method Syntax

```json
delete [ thing ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-2)  
| Parameter  | Description  |  
| --- | --- |  
| `record_id`  | The record_id (Table or Record ID) to delete  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-2)
Request

```json
{
    "id": 1,
    "method": "delete",
    "params": [ "person:8s0j0bbm3ngrd5c9bx53" ]
}
```

Notice how the deleted record is returned. This differs from a [`DELETE`](https://surrealdb.com/docs/reference/query-language/statements/delete) statement via the CLI or Surrealist which returns nothing unless the `RETURN BEFORE` clause is used.
Response

```json
{
    "id": 1,
    "result": {
        "active": true,
        "id": "person:8s0j0bbm3ngrd5c9bx53",
        "last_updated": "2023-06-16T08:34:25Z",
        "name": "John Doe"
    }
}
```

  

##  `info`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#info)
This method returns the record of an authenticated record user.
Method Syntax

```json
info
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-3)
Request

```json
{
    "id": 1,
    "method": "info"
}
```

The result property of the response is likely different depending on your schema and the authenticated user. However, it does represent the overall structure of the responding message.
Response

```json
{
    "id": 1,
    "result": {
        "id": "user:john",
        "name": "John Doe"
    }
}
```

  

##  `insert`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#insert)
This method creates a record either with a random or specified ID.
Method Syntax

```json
insert [ thing, data ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-3)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The table to insert in to  |  
| `data`  | One or multiple record(s)  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-4)
Request

```json
{
    "id": 1,
    "method": "insert",
    "params": [
        "person",
        {
            "name": "Mary Doe"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": [
        {
            "id": "person:s5fa6qp4p8ey9k5j0m9z",
            "name": "Mary Doe"
        }
    ]
}
```

###  Bulk insert[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#bulk-insert)
Request

```json
{
    "id": 1,
    "method": "insert",
    "params": [
        "person",
        [
            {
                "name": "Mary Doe"
            },
            {
                "name": "John Doe"
            }
        ]
    ]
}
```

Response

```json
{
    "id": 1,
    "result": [
        {
            "id": "person:s5fa6qp4p8ey9k5j0m9z",
            "name": "Mary Doe"
        },
        {
            "id": "person:xtbbojcm82a97vus9x0j",
            "name": "John Doe"
        }
    ]
}
```

  

##  `insert_relation`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#insert_relation)
This method inserts a new relation record into the database. You can specify the relation table to insert into and provide the data for the new relation.
Method Syntax

```json
insert_relation [ table, data ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-4)  
| Parameter  | Description  |  
| --- | --- |  
| `table`  | The name of the relation table to insert into. If `null` or `none`, the table is determined from the `id` field in the `data`.  |  
| `data`  | An object containing the data for the new relation record, including `in`, `out`, and any additional fields.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-5)
**Inserting a Relation into a Specified Table**
Request

```json
{
    "id": 1,
    "method": "insert_relation",
    "params": [
        "likes",                   // (relation table)
        {                          // data
            "in": "user:alice",
            "out": "post:123",
            "since": "2024-09-15T12:34:56Z"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": {
        "id": "likes:user:alice:post:123",
        "in": "user:alice",
        "out": "post:123",
        "since": "2024-09-15T12:34:56Z"
    }
}
```

**Inserting a Relation Without Specifying the Table**
If you do not specify the `table` parameter (i.e., set it to `null` or `none`), the relation table is inferred from the `id` field within the `data`.
Request

```json
{
    "id": 2,
    "method": "insert_relation",
    "params": [
        null,                      // relation table is null
        {                          // data
            "id": "follows:user:alice:user:bob",
            "in": "user:alice",
            "out": "user:bob",
            "since": "2024-09-15T12:34:56Z"
        }
    ]
}
```

Response

```json
{
    "id": 2,
    "result": {
        "id": "follows:user:alice:user:bob",
        "in": "user:alice",
        "out": "user:bob",
        "since": "2024-09-15T12:34:56Z"
    }
}
```

###  Notes[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#notes)
  * •
**`table`parameter:**
    * ◦
Specifies the relation table into which the new relation record will be inserted.
    * ◦
If `table` is `null` or `none`, the method expects the `data` to contain an `id` from which it can infer the relation table.
  * •
**`data`parameter:**
    * ◦
Must include at least the `in` and `out` fields, representing the starting and ending points of the relation.
    * ◦
Can include additional fields to store more information within the relation.
  * •
**Relation IDs:**
    * ◦
If an `id` is provided in the `data`, it will be used as the identifier for the new relation record.
    * ◦
If no `id` is provided, the system may generate one based on the `table`, `in`, and `out` fields.
  * •
**Single vs. multiple inserts:**
    * ◦
The method primarily handles single relation inserts.
    * ◦
The `one` variable in the code determines if the `table` parameter refers to a single item.

###  Error handling[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#error-handling)
  * •
**Invalid parameters:**
    * ◦
If you provide fewer than two parameters or incorrect parameter types, you will receive an `InvalidParams` error.
    * ◦
The method expects exactly two parameters: `table` and `data`.

**Example of invalid parameters:**
Request with missing parameters

```json
{
    "id": 3,
    "method": "insert_relation",
    "params": [
        "likes"  // Missing the data parameter
    ]
}
```

Response

```json
{
    "id": 3,
    "error": {
        "code": -32602,
        "message": "Invalid parameters"
    }
}
```

###  Best practices[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#best-practices)
  * •
**Include`in` and `out` Fields:**
    * ◦
Always provide the `in` and `out` fields in your `data` to define the relation endpoints.
  * •
**Specifying the Relation Table:**
    * ◦
If possible, specify the `table` parameter to clearly indicate the relation table.
    * ◦
If not specified, ensure that the `id` in `data` correctly reflects the desired relation table.
  * •
**Providing an`id` in `data`:**
    * ◦
If you want to control the `id` of the relation, include it in the `data`.
    * ◦
This is especially important when `table` is `null` or `none`.

###  Additional examples[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#additional-examples)
**Inserting a Relation with Auto-Generated ID**
Request

```json
{
    "id": 4,
    "method": "insert_relation",
    "params": [
        "friendship",              // table (relation table)
        {                          // data
            "in": "user:alice",
            "out": "user:bob",
            "since": "2024-09-15"
        }
    ]
}
```

Response

```json
{
    "id": 4,
    "result": {
        "id": "friendship:user:alice:user:bob",
        "in": "user:alice",
        "out": "user:bob",
        "since": "2024-09-15"
    }
}
```

**Notes:**
  * •
The `id` is generated based on the `table`, `in`, and `out` fields.
  * •
The relation is inserted into the `friendship` table.

The `insert_relation` method is a powerful way to insert new relation records into your database, allowing you to specify the relation table and include detailed data for each relation. By understanding the parameters and how the method operates, you can effectively manage relationships between records in your database.
Note
This method is particularly useful in databases that support graph-like relations, enabling complex data modeling and querying capabilities.
  

##  `invalidate`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#invalidate)
This method will invalidate the user's session for the current connection.
Method Syntax

```json
invalidate
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-6)
Request

```json
{
    "id": 1,
    "method": "invalidate"
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

  

##  `let` [](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#let-label-labelwebsocket-only-)
This method stores a variable on the current connection.
Method Syntax

```json
let [ name, value ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-5)  
| Parameter  | Description  |  
| --- | --- |  
| `name`  | The name for the variable without a prefixed $ character  |  
| `value`  | The value for the variable  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-7)
Request

```json
{
    "id": 1,
    "method": "let",
    "params": [ "website", "https://surrealdb.com/" ]
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

  

##  `live` [](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#live-label-labelwebsocket-only-)
This methods initiates a live query for a specified table name.
Method Syntax

```json
live[ table ]
```

Important
For more advanced live queries where filters are needed, use the Query method to initiate a custom live query.
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-6)  
| Parameter  | Description  |  
| --- | --- |  
| `table`  | The table to initiate a live query for  |  
| `diff`  | If set to true, live notifications will contain an array of [JSON Patches](https://jsonpatch.com) instead of the entire record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-8)
Request

```json
{
    "id": 1,
    "method": "live",
    "params": [ "person" ]
}
```

Response

```json
{
    "id": 1,
    "result": "0189d6e3-8eac-703a-9a48-d9faa78b44b9"
}
```

###  Live notification[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#live-notification)
For every creation, update or deletion on the specified table, a live notification will be sent. Live notifications do not have an ID attached, but rather include the Live Query's UUID in the result object.

```json
{
    "result": {
        "action": "CREATE",
        "id": "0189d6e3-8eac-703a-9a48-d9faa78b44b9",
        "result": {
            "id": "person:8s0j0bbm3ngrd5c9bx53",
            "name": "John"
        }
    }
}
```

  

##  `merge`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#merge)
This method merges specified data into either all records in a table or a single record.
Method Syntax

```json
merge [ thing, data ]
```

Note
This function merges the current document / record data with the specified data. If no merge data is passed it will simply trigger an update.
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-7)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to merge into  |  
| `data`  | The content of the record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-9)
Request

```json
{
    "id": 1,
    "method": "merge",
    "params": [
        "person",
        {
            "active": true
        }
    ]
}
```

Response

```json
{
  "id": 1,
  "result": [
      {
          "active": true,
          "id": "person:8s0j0bbm3ngrd5c9bx53",
          "name": "John Doe"
      },
      {
          "active": true,
          "id": "person:s5fa6qp4p8ey9k5j0m9z",
          "name": "Mary Doe"
      }
  ]
}
```

  

##  `patch`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#patch)
This method patches either all records in a table or a single record with specified patches.
Method Syntax

```json
patch [ thing, patches, diff ]
```

Note
This function patches the current document / record data with the specified [JSON Patch](https://jsonpatch.com) data.
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-8)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to patch  |  
| `patches`  | An array of patches following the [JSON Patch specification](https://jsonpatch.com)  |  
| `diff`  | A boolean representing if just a diff should be returned.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-10)
Request

```json
{
    "id": 1,
    "method": "patch",
    "params": [
        "person",
        [
            { "op": "replace", "path": "/last_updated", "value": "2023-06-16T08:34:25Z" }
        ]
    ]
}
```

Response

```json
{
    "id": 1,
    "result": [
        [
            {
                "op": "add",
                "path": "/last_updated",
                "value": "2023-06-16T08:34:25Z"
            }
        ],
        [
            {
                "op": "add",
                "path": "/last_updated",
                "value": "2023-06-16T08:34:25Z"
            }
        ]
    ]
}
```

  

##  `ping`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#ping)
Method Syntax

```json
ping
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-11)
Request

```json
{
    "id": 1,
    "method": "ping",
}
```

Response

```json
{
  "id": 1,
  "result": null
}
```

  

##  `query`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#query)
This methods sends a custom SurrealQL query.
Method Syntax

```json
query [ sql, vars ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-9)  
| Parameter  | Description  |  
| --- | --- |  
| `sql`  | The query to execute against SurrealDB  |  
| `vars`  | A set of variables used by the query  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-12)
Request

```json
{
    "id": 1,
    "method": "query",
    "params": [
        "CREATE person SET name = 'John'; SELECT * FROM type::table($tb);",
        {
            "tb": "person"
        }
    ]
}
```

Response

```json
{
  "id": 1,
  "result": [
      {
          "status": "OK",
          "time": "152.5µs",
          "result": [
              {
                  "id": "person:8s0j0bbm3ngrd5c9bx53",
                  "name": "John"
              }
          ]
      },
      {
          "status": "OK",
          "time": "32.375µs",
          "result": [
              {
                  "id": "person:8s0j0bbm3ngrd5c9bx53",
                  "name": "John"
              }
          ]
      }
  ]
}
```

##  `relate`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#relate)
This method relates two records with a specified relation.
Method Syntax

```json
relate [ in, relation, out, data? ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-10)  
| Parameter  | Description  |  
| --- | --- |  
| `in`  | The record to relate to  |  
| `relation`  | The relation table  |  
| `out`  | The record to relate from  |  
| `data`  | The content of the record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-13)
Request

```json
{
    "id": 1,
    "method": "relate",
    "params": [
        "person:12s0j0bbm3ngrd5c9bx53",
        "knows",
        "person:8s0j0bbm3ngrd5c9bx53"
    ]
}
```

Response

```json
{
    "id": 1,
    "result": {
        "id": "knows:12s0j0bbm3ngrd5c9bx53:8s0j0bbm3ngrd5c9bx53",
        "in": "person:12s0j0bbm3ngrd5c9bx53",
        "out": "person:8s0j0bbm3ngrd5c9bx53"
    }
}
```

###  Creating a relation with additional data[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#creating-a-relation-with-additional-data)
Request

```json
{
    "id": 2,
    "method": "relate",
    "params": [
        "person:john_doe",          // in
        "knows",                    // relation
        "person:jane_smith",        // out
        { "since": "2020-01-01" }   // data
    ]
}
```

Response

```json
{
    "id": 2,
    "result": {
        "id": "knows:person:john_doe:person:jane_smith",
        "in": "person:jane_smith",
        "out": "person:john_doe",
        "since": "2020-01-01"
    }
}
```

  

##  `reset`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#reset)
This method will reset all attributes for the current connection. reset your authentication (much like invalidate) unsets the selected NS/DB, unsets any defined connection params, and aborts any active live queries.
Method Syntax

```json
reset
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-14)
Request

```json
{
    "id": 1,
    "method": "reset"
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

  

##  `run`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#run)
This method allows you to execute built-in functions, custom functions, or machine learning models with optional arguments.
Method Syntax

```json
run [ func_name, version?, args? ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-11)  
| Parameter  | Description  |  
| --- | --- |  
| `func_name`  | The name of the function or model to execute. Prefix with `fn::` for custom functions or `ml::` for machine learning models.  |  
| `version`  | The version of the function or model to execute.  |  
| `args`  | The arguments to pass to the function or model.  |  
###  Executing a built-in function[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#executing-a-built-in-function)
Request

```json
{
    "id": 1,
    "method": "run",
    "params": [ "time::now" ]
}
```

Response

```json
{
    "id": 1,
    "result": "2024-09-15T12:34:56Z"
}
```

###  Executing a custom function[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#executing-a-custom-function)
Request

```json
{
    "id": 1,
    "method": "run",
    "params": [ "fn::calculate_discount", null, [ 100, 15 ] ]
}
```

Response

```json
{
    "id": 1,
    "result": 85
}
```

###  Executing a machine learning model[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#executing-a-machine-learning-model)
Request

```json
{
    "id": 1,
    "method": "run",
    "params": [ "ml::image_classifier", "v2.1", [ "image_data_base64" ] ]
}
```

Response

```json
{
    "id": 1,
    "result": "cat"
}
```

Important
When using a machine learning model (prefixed with `ml::`), the `version` parameter is **required**.
  

##  `select`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#select)
This method selects either all records in a table or a single record.
Method Syntax

```json
select [ thing ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-12)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to select  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-15)
Request

```json
{
    "id": 1,
    "method": "select",
    "params": [ "person" ]
}
```

Response

```json
{
    "id": 1,
    "result": [
        {
            "id": "person:8s0j0bbm3ngrd5c9bx53",
            "name": "John"
        }
    ]
}
```

  

##  `signin`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#signin)
This method allows you to sign in as a root, namespace, or database user, or with a record access method.
The object returned will contain a `token` property and an optional `refresh` property.
Method Syntax

```json
signin [ NS, DB, AC, ... ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-13)  
| Parameter  | Description  |  
| --- | --- |  
| `NS`  | The namespace to sign in to. Only required for `DB & RECORD` authentication  |  
| `DB`  | The database to sign in to. Only required for `RECORD` authentication  |  
| `AC`  | Specifies the access method. Only required for `RECORD` authentication  |  
| `user`  | The username of the database user. Only required for `ROOT, NS & DB` authentication  |  
| `pass`  | The password of the database user. Only required for `ROOT, NS & DB` authentication  |  
| `...`  | Specifies any variables to pass to the `SIGNIN` query. Only relevant for `RECORD` authentication  |  
###  Example with root user[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-with-root-user)
Request

```json
{
    "id": 1,
    "method": "signin",
    "params": [
        {
            "user": "tobie",
            "pass": "3xtr3m3ly-s3cur3-p@ssw0rd"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

###  Example with record user[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-with-record-user)
Request

```json
{
    "id": 1,
    "method": "signin",
    "params": [
        {
            "NS": "surrealdb",
            "DB": "docs",
            "AC": "commenter",

            "username": "johndoe",
            "password": "SuperStrongPassword!"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA"
}
```

  

##  `signup`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#signup)
This method allows you to sign a user up using the `SIGNUP` query defined in a record access method.
The object returned will contain an optional `token` property and an optional `refresh` property.
Method Syntax

```json
signup [ NS, DB, AC, ... ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-14)  
| Parameter  | Description  |  
| --- | --- |  
| `NS`  | Specifies the namespace of the record access method  |  
| `DB`  | Specifies the database of the record access method  |  
| `AC`  | Specifies the access method  |  
| `...`  | Specifies any variables used by the SIGNUP query of the record access method  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-16)
Request

```json
{
    "id": 1,
    "method": "signup",
    "params": [
        {
            "NS": "surrealdb",
            "DB": "docs",
            "AC": "commenter",

            "username": "johndoe",
            "password": "SuperStrongPassword!"
        }
    ]
}
```

Response

```json
{
  "id": 1,
  "result": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJTdXJyZWFsREIiLCJpYXQiOjE1MTYyMzkwMjIsIm5iZiI6MTUxNjIzOTAyMiwiZXhwIjoxODM2NDM5MDIyLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJTQyI6InVzZXIiLCJJRCI6InVzZXI6dG9iaWUifQ.N22Gp9ze0rdR06McGj1G-h2vu6a6n9IVqUbMFJlOxxA"
}
```

  

##  `unset` [](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#unset-label-labelwebsocket-only-)
This method removes a variable from the current connection.
Method Syntax

```json
unset [ name ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-15)  
| Parameter  | Description  |  
| --- | --- |  
| `name`  | The name of the variable without a prefixed $ character  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-17)
Request

```json
{
    "id": 1,
    "method": "unset",
    "params": [ "website" ]
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

  

##  `update`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#update)
This method replaces either all records in a table or a single record with specified data.
Method Syntax

```json
update [ thing, data ]
```

Note
This function replaces the current document / record data with the specified data if that document / record has already been created. If no document has been created this will return an empty array. Also, if no replacement data is passed it will simply trigger an update.
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-16)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to update  |  
| `data`  | The content of the record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-18)
Request

```json
{
    "id": 1,
    "method": "update",
    "params": [
        "person:8s0j0bbm3ngrd5c9bx53",
        {
            "name": "John Doe"
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": {
        "id": "person:8s0j0bbm3ngrd5c9bx53",
        "name": "John Doe"
    }
}
```

  

##  `upsert`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#upsert)
Method Syntax

```json
upsert [ thing, data ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-17)  
| Parameter  | Description  |  
| --- | --- |  
| `thing`  | The thing (Table or Record ID) to upsert  |  
| `data`  | The content of the record  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-19)
Request

```json
{
    "id": 1,
    "method": "upsert",
    "params": [
        "person:12s0j0bbm3ngrd5c9bx53",
        {
            "name": "John Doe",
            "job": "Software developer",
        }
    ]
}
```

Response

```json
{
    "id": 1,
    "result": {
        "id": "person:12s0j0bbm3ngrd5c9bx53",
        "name": "John Doe",
        "job": "Software developer"
    }
}
```

  

##  `use`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#use)
This method specifies or unsets the namespace and/or database for the current connection.
Method Syntax

```json
use [ ns, db ]
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-18)  
| Parameter  | Description  |  
| --- | --- |  
| `NS`  | Sets the selected Namespace for queries  |  
| `DB`  | Sets the selected Database for queries  |  
###  Accepted values[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#accepted-values)
For either the namespace or database, a string will change the value, `null` will unset the value, and `none` will cause the value to not be affected.
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-20)
Request

```json
{
    "id": 1,
    "method": "use",
    "params": [ "surrealdb", "docs" ]
}
```

Response

```json
{
    "id": 1,
    "result": null
}
```

Example Combinations

```surql
[none, none]     -- Won't change ns or db
["test", none]   -- Change ns to test
[none, "test"]   -- Change db to test
["test", "test"] -- Change ns and db to test

[none, null]     -- Will only unset the database
[null, none]     -- Will throw an error, you cannot unset only the database
[null, null]     -- Will unset both ns and db
["test", null]   -- Change ns to test and unset db
```

  

##  `version`[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#version)
This method returns version information about the database/server.
Method Syntax

```json
version
```

###  Parameters[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#parameters-19)
This method does not accept any parameters.
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#example-usage-21)
Request

```json
{
    "id": 1,
    "method": "version"
}
```

Response

```json
{
    "id": 1,
    "result": {
        "version": "3.2.0",
        "build": "abc123",
        "timestamp": "2024-09-15T12:34:56Z"
    }
}
```

###  Notes[](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#notes-1)
  * •
**Parameters:** Providing any parameters will result in an `InvalidParams` error.
  * •
**Result Fields:**
    * ◦
`version`: The version number of the database/server.
    * ◦
`build`: The build identifier.
    * ◦
`timestamp`: The timestamp when the version was built or released.

Note
The actual values in the response will depend on your specific database/server instance.
