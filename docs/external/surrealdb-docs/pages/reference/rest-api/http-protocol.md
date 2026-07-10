---
title: "https://surrealdb.com/docs/reference/rest-api/http-protocol"
url: "https://surrealdb.com/docs/reference/rest-api/http-protocol"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rest-api/http-protocol

Source: https://surrealdb.com/docs/reference/rest-api/http-protocol

The HTTP endpoints exposed by SurrealDB instances provide a simple way to interact with the database over a traditional RESTful interface. This includes selecting and modifying one or more records, executing custom SurrealQL queries, and importing and exporting data.
The endpoints are designed to be simple and easy to use in stateless environments, making them ideal for lightweight applications where a persistent database connection is not required.
##  Setup[](https://surrealdb.com/docs/reference/rest-api/http-protocol#setup)
The [`surreal start`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) command without any arguments is all that is needed to start a server at the default `http://localhost:8000` address. Many examples below assume the flags `--user root` and `--pass secret` to create a root user with the name `root` and password `secret`. The `--unauthenticated` flag can be used when experimenting to turn off authentication, effectively allowing root access by any and all connections.
The [local database serving](https://surrealdb.com/docs/explore/surrealist/concepts/local-database-serving) functionality on the Surrealist UI can also be used to start a server.
##  Querying via Postman[](https://surrealdb.com/docs/reference/rest-api/http-protocol#querying-via-postman)
One convenient way to access these endpoints is via SurrealDB's Postman Collection. To do so, follow these steps:
  1. 1.
Open Postman
  2. 2.
Clone the [SurrealDB Postman Collection](https://postman.com/surrealdb/workspace/surrealdb/collection/19100500-3da237f3-588b-4252-8882-6d487c11116a)
  3. 3.
Select the appropriate HTTP method (`GET /health`, `DEL /key/:table`, etc.).
  4. 4.
Enter the endpoint URL.
  5. 5.
If the endpoint requires any parameters or a body, make sure to include those in your request.

##  Supported methods[](https://surrealdb.com/docs/reference/rest-api/http-protocol#supported-methods)
You can use the HTTP endpoints to perform the following actions:
  
  
| Function  | Description  |  
| --- | --- |  
| [`GET /status`](https://surrealdb.com/docs/reference/rest-api/http-protocol#status)  | Checks whether the database web server is running  |  
| [`GET /health`](https://surrealdb.com/docs/reference/rest-api/http-protocol#health)  | Checks the status of the database server and storage engine  |  
| [`GET /ready`](https://surrealdb.com/docs/reference/rest-api/http-protocol#ready)  | Checks whether the instance has finished startup and is ready to serve traffic  |  
| [`GET /version`](https://surrealdb.com/docs/reference/rest-api/http-protocol#version)  | Returns the version of the SurrealDB database server  |  
| [`POST /import`](https://surrealdb.com/docs/reference/rest-api/http-protocol#import)  | Imports data into a specific Namespace and Database  |  
| [`POST /export`](https://surrealdb.com/docs/reference/rest-api/http-protocol#export)  | Exports all data for a specific Namespace and Database  |  
| [`POST /signup`](https://surrealdb.com/docs/reference/rest-api/http-protocol#signup)  | Signs-up as a record user using a specific record access method  |  
| [`POST /signin`](https://surrealdb.com/docs/reference/rest-api/http-protocol#signin)  | Signs-in as a root, namespace, database, or record user  |  
| [`GET /key/:table`](https://surrealdb.com/docs/reference/rest-api/http-protocol#get-table)  | Selects all records in a table from the database  |  
| [`POST /key/:table`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-table)  | Creates a record in a table in the database  |  
| [`PUT /key/:table`](https://surrealdb.com/docs/reference/rest-api/http-protocol#put-table)  | Updates all records in a table in the database  |  
| [`PATCH /key/:table`](https://surrealdb.com/docs/reference/rest-api/http-protocol#patch-table)  | Modifies all records in a table in the database  |  
| [`DELETE /key/:table`](https://surrealdb.com/docs/reference/rest-api/http-protocol#delete-table)  | Deletes all records in a table from the database  |  
| [`GET /key/:table/:id`](https://surrealdb.com/docs/reference/rest-api/http-protocol#get-record)  | Selects the specific record from the database  |  
| [`POST /key/:table/:id`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-record)  | Creates the specific record in the database  |  
| [`PUT /key/:table/:id`](https://surrealdb.com/docs/reference/rest-api/http-protocol#put-record)  | Updates the specified record in the database  |  
| [`PATCH /key/:table/:id`](https://surrealdb.com/docs/reference/rest-api/http-protocol#patch-record)  | Modifies the specified record in the database  |  
| [`DELETE /key/:table/:id`](https://surrealdb.com/docs/reference/rest-api/http-protocol#delete-record)  | Deletes the specified record from the database  |  
| [`POST /sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql)  | Allows custom SurrealQL queries  |  
| [`POST /gql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#gql)  | Runs ISO GQL graph pattern queries (`MATCH … RETURN …`, plus `INSERT` / `SET` / `REMOVE` / `DELETE`)  |  
| [`POST /graphql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql)  | Allows custom GraphQL queries  |  
| [`POST /ml/import`](https://surrealdb.com/docs/reference/rest-api/http-protocol#ml-import)  | Import a SurrealML model into a specific Namespace and Database  |  
| [`GET /ml/export/:name/:version`](https://surrealdb.com/docs/reference/rest-api/http-protocol#ml-export)  | Export a SurrealML model from a specific Namespace and Database  |  
| [`/api/:namespace/:database/:endpoint`](https://surrealdb.com/docs/reference/rest-api/http-protocol#custom)  | Create a custom API endpoint for any number of HTTP methods (GET, POST, etc.)  |  
  

##  `GET /status`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#status)
This HTTP RESTful endpoint checks whether the database web server is running, returning a 200 status code.
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage)
Request

```bash
curl -I http://localhost:8000/status
```

Sample output

```bash
HTTP/1.1 200 OK
vary: origin, access-control-request-method, access-control-request-headers
access-control-allow-origin: *
surreal-version: surrealdb/3.0.0
server: SurrealDB
x-request-id: fdb9bcdb-b085-4da0-80ef-a61105c432f9
content-length: 0
date: Tue, 03 Feb 2026 02:10:33 GMT
```

  

##  `GET /health`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#health)
This HTTP RESTful endpoint checks whether the database server and storage engine are running.
The endpoint returns a `200` status code on success and a `500` status code on failure.
Request

```bash
curl -I http://localhost:8000/health
```

Sample output

```bash
HTTP/1.1 200 OK
vary: origin, access-control-request-method, access-control-request-headers
access-control-allow-origin: *
surreal-version: surrealdb/3.0.0
server: SurrealDB
x-request-id: 66938ec2-ad7c-4afb-928d-683e7a75433a
content-length: 0
date: Tue, 03 Feb 2026 02:15:08 GMT
```

  

##  `GET /ready`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#ready)
Available since: v3.2.0
This HTTP RESTful endpoint is the startup and readiness probe. It returns `200` once deferred startup work (such as import and credential initialisation) has completed and, when a heartbeat budget is configured, the node's cluster heartbeat is fresh. It returns `503` while still starting up or when the heartbeat is stale, and `500` if the heartbeat cannot be read.
Contrast with [`GET /status`](https://surrealdb.com/docs/reference/rest-api/http-protocol#status) (process and listener liveness only) and [`GET /health`](https://surrealdb.com/docs/reference/rest-api/http-protocol#health) (storage backend reachability only). Query and auth endpoints are gated with `503` until startup completes, while `/ready` stays reachable throughout so orchestrators can distinguish _starting_ from _failed_.
The CLI [`surreal isready`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready) command calls this endpoint.
Request

```bash
curl -I http://localhost:8000/ready
```

Sample output (ready)

```bash
HTTP/1.1 200 OK
vary: origin, access-control-request-method, access-control-request-headers
access-control-allow-origin: *
surreal-version: surrealdb/3.2.0
server: SurrealDB
content-length: 0
```

Sample output (still starting)

```bash
HTTP/1.1 503 Service Unavailable
retry-after: 1
content-length: 0
```

  

##  `GET /version`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#version)
This HTTP RESTful endpoint returns the version of the SurrealDB database server.
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-1)
Request

```bash
curl http://localhost:8000/version
```

Sample output

```bash
surrealdb-3.0.0
```

  

##  `POST /import`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#import)
This HTTP RESTful endpoint imports a set of SurrealQL queries into a specific namespace and database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, or database authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-2)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`.
Request

```bash
curl -X POST -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Accept: application/json" \
  -d file.surql \
  http://localhost:8000/import
```

  

##  `POST /export`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#export)
This HTTP RESTful endpoint exports all data for a specific Namespace and Database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-1)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, or database authentication data  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
####  Export options[](https://surrealdb.com/docs/reference/rest-api/http-protocol#export-options)  
| Arguments  | Description  |  
| --- | --- |  
| `only`  | Whether only specific resources should be exported. When provided, only the resources specified will be exported.  |  
| `users`  | Whether system users should be exported possible values: true, false.  |  
| `accesses`  | Whether access methods (Record or JWT) should be exported possible values: true, false  |  
| `params`  | Whether databases parameters should be exported possible values: true, false  |  
| `functions`  | Whether functions should be exported possible values: true, false  |  
| `analyzers`  | Whether analyzers should be exported possible values: true, false  |  
| `tables [tables]`  | Whether tables should be exported, optionally providing a list of tables  |  
| `versions`  | Whether SurrealKV versioned records should be exported possible values: true, false  |  
| `records`  | Whether records should be exported possible values: true, false  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-3)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`. The `-o` allows the output to be written to a file.
Request

```bash
curl -X GET \
  -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Accept: application/json" \
  -o file.surql \
  http://localhost:8000/export
```

Exporting specific parameters

```bash
curl -X POST \
  -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -o file.surql \
  -d '{
        "users": true,
        "accesses": false,
        "params": false,
        "functions": false,
        "analyzers": false,
        "versions": false,
        "tables": ["usersTable", "ordersTable"],
        "records": true
      }' \
  http://localhost:8000/export
```

  

##  `POST /signin`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#signin)
Method and URL

```json
POST /signin
```

This HTTP RESTful endpoint is used to access an existing account inside the SurrealDB database server.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-2)  
| Header  | Description  |  
| --- | --- |  
| `Accept`  | Sets the desired content-type of the response  |  
###  Data[](https://surrealdb.com/docs/reference/rest-api/http-protocol#data)  
| Data  | Description  |  
| --- | --- |  
| `ns`  | The namespace to sign in to this is required FOR DB & RECORD users  |  
| `db`  | The database to sign in to required for RECORD users  |  
| `ac`  | The record access method to use for signing in. required for RECORD users  |  
| `user`  | The username of the database user required for ROOT, NS & DB users  |  
| `pass`  | The password of the database user required for ROOT, NS & DB users  |  
Important
The `ac` parameter is only required if you are signing in using an [access method](https://surrealdb.com/docs/reference/query-language/statements/define/access) as a record user. For system users on the database, namespace, and root level, this parameter can be omitted.
###  Example with a record user[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-with-a-record-user)
The following example will work as long as as an access method has been defined and a record user has been signed up using the [`/signup`](https://surrealdb.com/docs/reference/rest-api/http-protocol#signup) endpoint.
Request

```bash
curl -X POST -H "Accept: application/json" -d '{"ns":"main","db":"main","ac":"users","user":"johndoe","pass":"123456"}' http://localhost:8000/signin
```

Response

```json
{
	"code": 200,
	"details": "Authentication succeeded",
	"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

###  Example with root user[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-with-root-user)
Request

```bash
curl -X POST -H "Accept: application/json" -d '{"user":"root","pass":"secret"}' http://localhost:8000/signin
```

Response

```json
{
	"code": 200,
	"details": "Authentication succeeded",
	"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

###  Example with namespace user[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-with-namespace-user)
To create the namespace user needed for the following query, use the following command.

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'DEFINE USER johndoe ON NAMESPACE PASSWORD "123456" ROLES EDITOR' http://localhost:8000/sql
```

Once the user has been created, use this command to sign in.
Request

```bash
curl -X POST -H "Accept: application/json" -d '{"ns":"main","user":"johndoe","pass":"123456"}' http://localhost:8000/signin
```

Response

```json
{
	"code": 200,
	"details": "Authentication succeeded",
	"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

###  Example usage via postman[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-via-postman)
After you have defined the users permissions for the record user, you can use the `POST /signin` endpoint to sign in as a user.
Using the [user credentials](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users) created add the following to the request body:

```json
{
    "ns": "main",
    "db": "main",
    "ac": "account",
    "email": "",
    "pass": "123456"
}
```

  

##  `POST /signup`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#signup)
This HTTP RESTful endpoint is used to create an account inside the SurrealDB database server.
###  Header[](https://surrealdb.com/docs/reference/rest-api/http-protocol#header)  
| Header  | Description  |  
| --- | --- |  
| `Accept`  | Sets the desired content-type of the response  |  
###  Data[](https://surrealdb.com/docs/reference/rest-api/http-protocol#data-1)  
| Data  | Description  |  
| --- | --- |  
| `ns`  | The namespace to sign up to. This data is `REQUIRED FOR DB & RECORD`  |  
| `db`  | The database to sign up to. This data is `REQUIRED FOR RECORD`  |  
| `access`  | The record access method to use for signing up. This data is `REQUIRED FOR RECORD`  |  
| `user`  | The username of the database user. This data is `REQUIRED FOR ROOT, NS & DB`  |  
| `pass`  | The password of the database user. This data is `REQUIRED FOR ROOT, NS & DB`  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-4)
Request

```bash
curl -X POST -H "Accept: application/json" -d '{"ns":"main","db":"main","ac":"users","user":"johndoe","pass":"123456"}' http://localhost:8000/signup
```

Response

```json
{
	"code": 200,
	"details": "Authentication succeeded",
	"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

The above example will only work if a record access method has already been set up.
###  Setting up a record access method[](https://surrealdb.com/docs/reference/rest-api/http-protocol#setting-up-a-record-access-method)
Before you sign up a new [record user](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users), you must first [define a record access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) for the user. The following curl command will do so on the command line using the [`POST /sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) endpoint.

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'DEFINE ACCESS users ON DATABASE TYPE RECORD
    SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
    SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) )
    DURATION FOR SESSION 24h' http://localhost:8000/sql
```

To do the same using Postman, use the following steps:
  1. 1.
Navigate to the `POST /sql` endpoint in Postman.
  2. 2.
Enter the following query in the body of the request:

```surql
-- Enable authentication directly against a SurrealDB record
DEFINE ACCESS users ON DATABASE TYPE RECORD
    SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
    SIGNIN ( SELECT * FROM user WHERE email = $email
      AND crypto::argon2::compare(pass, $pass) )
    DURATION FOR SESSION 24h
;
```

The above query defines a record access method called `account` that allows users to sign up and sign in. The access method also defines the session duration to be 24 hours.
  3. 3.
Click `Send` to send the request to the SurrealDB database server.
  4. 4.
Navigate to the `POST /signup` endpoint in Postman.
  5. 5.
Enter the following query in the body of the request:

```json
{
    "ns": "main",
    "db": "main",
    "ac": "users",
    "email": "",
    "pass": "123456"
}
```

  6. 6.
In the header of the request, set the following key-value pairs:
     * ◦
`Accept: application/json`
     * ◦
namespace: `test`
     * ◦
database: `test`
     * ◦
access: `account`
  7. 6.
Click `Send` to send the request to the SurrealDB database server. You will receive the following response.

```json
{
    "code": 200,
    "details": "Authentication succeeded",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpYXQiOjE3MDY2MTA4MDMsIm5iZiI6MTcwNjYxMDgwMywiZXhwIjoxNzA2Njk3MjAzLCJpc3MiOiJTdXJyZWFsREIiLCJOUyI6InRlc3QiLCJEQiI6InRlc3QiLCJBQyI6Imh1bWFuIiwiSUQiOiJ1c2VyOjZsOTl1OWI0bzVoa3h0NnY3c3NzIn0.3jR8PHgS8iLefZDuPHBFcdUFNfuB3OBNqQtqxLVVzxAIxVj1RAkD5rCEZHH2QaPV-D2zNwYO5Fh_a8jD1l_cqQ"
}
```

  

##  `GET /key/:table`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#get-table)
This HTTP RESTful endpoint selects all records in a specific table in the database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-3)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query)

```surql
SELECT * FROM type::table($table);
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-5)

```bash
curl -X GET -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" http://localhost:8000/key/person
```

  

##  `POST /key/:table`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-table)
This HTTP RESTful endpoint creates a record in a specific table in the database.
Note
This HTTP endpoint expects the HTTP body to be a **single inert value** (parsed with the SurrealQL value grammar and bound to **`$data`**in the translated statement). Literals,`$param` references, and constants are allowed; function calls, statements, and parenthesised executable forms are rejected. The body is not executed as a script. Use [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-sql) or RPC when you need to run queries in the request body. JSON-shaped objects such as `{ name: "Billy" }` are valid SurrealQL values and are the usual choice on the wire.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-4)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-1)

```surql
CREATE type::table($table) CONTENT $data;
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-6)

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ name: "Billy" }' http://localhost:8000/key/person
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:sf8l6ejkm6swdwoyx2mt",
				"name": "Billy"
			}
		],
		"status": "OK",
		"time": "160.375µs",
		"type": null
	}
]
```

  

##  `PUT /key/:table`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#put-table)
This HTTP RESTful endpoint updates all records in a specific table in the database.
Note
This HTTP endpoint expects the HTTP body to be a **single inert value** (SurrealQL literal / object syntax; not an executable statement). Use [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-sql) or RPC to run SurrealQL in the request body.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-5)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-2)

```surql
UPDATE type::table($table) CONTENT $data;
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-7)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ name: "Billy" }' http://localhost:8000/key/person
```

Then use this `PUT` endpoint to modify the existing record.

```bash
curl -X PUT -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ name: "Not Billy anymore" }' http://localhost:8000/key/person
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:f8i2ej4xluh5dgw2lgko",
				"name": "Not Billy anymore"
			}
		],
		"status": "OK",
		"time": "109.458µs",
		"type": null
	}
]
```

  

##  `PATCH /key/:table`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#patch-table)
This HTTP RESTful endpoint modifies all records in a specific table in the database.
Note
This HTTP endpoint expects the HTTP body to be a **single inert value** (SurrealQL literal / object syntax; not an executable statement). Use [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-sql) or RPC to run SurrealQL in the request body.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-6)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-3)

```surql
UPDATE type::table($table) MERGE $data;
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-8)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ id: person:one, name: "Billy" }' http://localhost:8000/key/person
```

Then use this `PATCH` endpoint to modify the existing records.

```bash
curl -X PATCH -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ "name": "Not Billy anymore" }' http://localhost:8000/key/person
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:one",
				"name": "Not Billy anymore"
			}
		],
		"status": "OK",
		"time": "162.167µs",
		"type": null
	}
]
```

  

##  `DELETE /key/:table`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#delete-table)
This HTTP RESTful endpoint deletes all records from the specified table in the database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-7)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-4)

```surql
DELETE FROM type::table($table) RETURN BEFORE;
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-9)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ id: person:one, name: "Billy" }' http://localhost:8000/key/person
```

Then use this `DELETE` endpoint to delete and return the records that were just removed.

```bash
curl -X DELETE -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" http://localhost:8000/key/person
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:one",
				"name": "Billy"
			}
		],
		"status": "OK",
		"time": "234.75µs",
		"type": null
	}
]
```

  

##  `GET /key/:table/:id`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#get-record)
This HTTP RESTful endpoint selects a specific record from the database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-8)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-5)

```surql
SELECT * FROM type::record($table, $id);
```

  

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-10)

```bash
curl -X GET -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" http://localhost:8000/key/person/1
```

  

##  `POST /key/:table/:id`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-record)
This HTTP RESTful endpoint creates a specific record in a table in the database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-9)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-6)

```surql
CREATE type::record($table, $id) CONTENT $data;
```

  

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-11)

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ name: "Billy" }' http://localhost:8000/key/person/1
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:1",
				"name": "Billy"
			}
		],
		"status": "OK",
		"time": "103.542µs",
		"type": null
	}
]
```

##  `PUT /key/:table/:id`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#put-record)
This HTTP RESTful endpoint updates a specific record in a table in the database.
Note
This HTTP endpoint expects the HTTP body to be a **single inert value** (SurrealQL literal / object syntax; not an executable statement). Use [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-sql) or RPC to run SurrealQL in the request body.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-10)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-7)

```surql
UPDATE type::record($table, $id) CONTENT $data;
```

  

##  `PATCH /key/:table/:id`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#patch-record)
This HTTP RESTful endpoint modifies a specific record in a table in the database.
Note
This HTTP endpoint expects the HTTP body to be a **single inert value** (SurrealQL literal / object syntax; not an executable statement). Use [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#post-sql) or RPC to run SurrealQL in the request body.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-11)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-8)

```surql
UPDATE type::record($table, $id) MERGE $data;
```

  

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-12)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ name: "Billy" }' http://localhost:8000/key/person/1
```

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-13)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ id: person:one, name: "Billy" }' http://localhost:8000/key/person
```

Then use this `PATCH` endpoint to modify the existing record.

```bash
curl -X PATCH -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ "name": "Not Billy anymore" }' http://localhost:8000/key/person/1
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:one",
				"name": "Not Billy anymore"
			}
		],
		"status": "OK",
		"time": "162.167µs",
		"type": null
	}
]
```

  

##  `DELETE /key/:table/:id`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#delete-record)
This HTTP RESTful endpoint deletes a single specific record from the database.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-12)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Translated query[](https://surrealdb.com/docs/reference/rest-api/http-protocol#translated-query-9)

```surql
DELETE FROM type::record($table, $id) RETURN BEFORE;
```

  

###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-14)
To use this example, first create a record using the `POST` endpoint:

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d '{ id: person:one, name: "Billy" }' http://localhost:8000/key/person/1
```

Then use this `DELETE` endpoint to delete and return the record that was just removed.

```bash
curl -X DELETE -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" http://localhost:8000/key/person/1
```

Response

```json
[
	{
		"result": [
			{
				"id": "person:one",
				"name": "Billy"
			}
		],
		"status": "OK",
		"time": "145.042µs",
		"type": null
	}
]
```

  

##  `POST /sql`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql)
The SQL endpoint enables use of SurrealQL queries.
Note
This HTTP endpoint expects the HTTP body to be a set of SurrealQL statements.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-13)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/http-protocol#parameters)
Query parameters can be provided via URL query parameters. These parameters will securely replace any parameters that are present in the query. This practise is known as prepared statements or parameterised queries, and [should be used](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#query-safety) whenever untrusted inputs are included in a query to prevent injection attacks.
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-15)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`.
V2.x+V2.x with token
Request

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'SELECT * FROM person WHERE age > $age' http://localhost:8000/sql?age=18
```

Request

```bash
curl -X POST -H "Bearer: YourToken" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" \
  -d 'SELECT * FROM person WHERE age > $age' http://localhost:8000/sql?age=18
```

Response

```json
[
	{
		"time": "14.357166ms",
		"status": "OK",
		"result": [
			{
				"age": "23",
				"id": "person:6r7wif0uufrp22h0jr0o"
				"name": "Simon",
			},
			{
				"age": "28",
				"id": "person:6r7wif0uufrp22h0jr0o"
				"name": "Marcus",
			},
		]
	}
]
```

###  Usage in importing data[](https://surrealdb.com/docs/reference/rest-api/http-protocol#usage-in-importing-data)
Available since: v3.0.4
As of SurrealDB 3.0.4, imports via the [`surreal import`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) and [`/import`](https://surrealdb.com/docs/reference/rest-api/http-protocol#import) HTTP endpoint require the automatically generated `OPTION IMPORT` line to be present in order to disable events, live queries, field processing, and result output for optimal import performance. If side effects are desired when importing data, remove the line and use this endpoint instead.
  

##  `POST /gql`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#gql)
Available since: v3.2.0
The GQL endpoint runs [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview) graph pattern queries against your existing tables and `RELATE` edges — `MATCH … RETURN` reads and data-modifying `INSERT`, `SET`, `REMOVE`, and `DELETE` ([GQL mutations](https://surrealdb.com/docs/learn/querying/gql/mutations)).
Warning
GQL is **experimental**. Enable it at server start with [`--allow-experimental gql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start#experimental-capabilities) (or `SURREAL_CAPS_ALLOW_EXPERIMENTAL=gql`). `--allow-all` does **not** enable it. If the capability is off, expect **403**.
Note
This endpoint is **not** [GraphQL](https://surrealdb.com/docs/learn/querying/graphql/overview). GraphQL queries belong on [`POST /graphql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql).
Note
This HTTP endpoint expects the HTTP body to be a **single raw GQL query** (UTF-8 text), not JSON-wrapped. Use [`POST /sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) for SurrealQL.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-14)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response (`application/json` or `application/cbor`)  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Parameters[](https://surrealdb.com/docs/reference/rest-api/http-protocol#parameters-1)
Pass GQL parameters through **WebSocket RPC** (`method: "gql"`, second element of `params` as a JSON object with typed values).
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-16)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`. The server must have been started with `--allow-experimental gql`.
Request

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json" -H "Content-Type: text/plain" \
  -d 'MATCH (n:person) RETURN n.name AS name ORDER BY name' \
  http://localhost:8000/gql
```

Response

```json
[
	{
		"status": "OK",
		"result": [
			{ "name": "A" },
			{ "name": "B" },
			{ "name": "C" }
		],
		"time": "1.5ms"
	}
]
```

Parse errors return **HTTP 400** with an error payload. See [GQL via HTTP](https://surrealdb.com/docs/learn/querying/gql/via-http) for enabling GQL, seeding data, and RPC examples.
  

##  `POST /graphql`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#graphql)
The GraphQL endpoint enables use of GraphQL queries to interact with your data.
Note
This endpoint is **not** [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview). GQL `MATCH` queries belong on [`POST /gql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#gql).
Note
This HTTP endpoint expects the HTTP body to be a GraphQL query.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-15)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `Surreal-NS`  | Sets the selected Namespace for queries  |  
| `Surreal-DB`  | Sets the selected Database for queries  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-17)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`.
First, use the `/sql` endpoint to send in a [`DEFINE CONFIG`](https://surrealdb.com/docs/reference/query-language/statements/define/config#define-config-graphql) statement to set the database up to use GraphQL.

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'DEFINE TABLE person SCHEMAFULL; DEFINE FIELD name ON TABLE person TYPE string; DEFINE FIELD age ON TABLE person TYPE number;' \
  http://localhost:8000/sql

curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'CREATE person:simon SET name = "Simon", age = 23; CREATE person:marcus SET name = "Marcus", age = 28;' \
  http://localhost:8000/sql

curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d 'DEFINE CONFIG GRAPHQL AUTO' \
  http://localhost:8000/sql
```

With that done, a GraphQL query can now be performed.
Request

```bash
curl -X POST \
  -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Accept: application/json" \
  -d '{"query": "query { person { id name age } }"}' \
  http://localhost:8000/graphql
```

Response

```json
{
	"data": {
		"person": [
			{
				"age": 28,
				"id": "person:marcus",
				"name": "Marcus"
			},
			{
				"age": 23,
				"id": "person:simon",
				"name": "Simon"
			}
		]
	}
}
```

  

##  `POST /ml/import`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#ml-import)
This HTTP RESTful endpoint imports a SurrealML machine learning model into a specific Namespace and Database. It expects the file to be a SurrealML file packaged in the `.surml` file format. As machine learning files can be large, the endpoint expects a chunked HTTP request.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-16)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-18)
Note
The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`.
Request

```bash
curl -X POST \
  -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Accept: application/json" \
  -d file.surml \
  http://localhost:8000/ml/import
```

###  Usage in Python[](https://surrealdb.com/docs/reference/rest-api/http-protocol#usage-in-python)
When using Python, the [surreaml](https://github.com/surrealdb/surrealml) package can be used to upload the model with the following code:

```python
from surrealml import SurMlFile

url = "http://0.0.0.0:8000/ml/import"
SurMlFile.upload("./linear_test.surml", url, 5)
```

  

##  `GET /ml/export/:name/:version`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#ml-export)
This HTTP RESTful endpoint exports a SurrealML machine learning model from a specific Namespace and Database. The output file with be a SurrealML file packaged in the `.surml` file format. As machine learning files can be large, the endpoint outputs a chunked HTTP response.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-17)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, or database authentication data  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-19)
Note
_Note:_ The `-u` in the example below is a shorthand used by curl to send an Authorization header (name and password), in this case assuming the username `root` and password `secret`. The `-o` allows the output to be written to a file.
Request

```bash
curl -X GET \
  -u "root:secret" \
  -H "Surreal-NS: main" \
  -H "Surreal-DB: main" \
  -H "Accept: application/json" \
  -o file.surml \
  http://localhost:8000/ml/export/prediction/1.0.0
```

##  Custom endpoint at `/api/:ns/:db/:endpoint`[](https://surrealdb.com/docs/reference/rest-api/http-protocol#custom)
Available since: v2.2.0
A custom endpoint can be set using a [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) statement. The possible HTTP methods (GET, PUT, etc.) are set using the statement itself. The path begins with `/api`, continues with the namespace and database, and ends with a custom endpoint that can include both static and dynamic path segments.
###  Headers[](https://surrealdb.com/docs/reference/rest-api/http-protocol#headers-18)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, or database authentication data  |  
| `Surreal-NS`  | Sets the selected Namespace for queries.  |  
| `Surreal-DB`  | Sets the selected Database for queries.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rest-api/http-protocol#example-usage-20)
To begin, start a server with the `surreal start` command.

```bash
surreal start --user root --pass secret
```

A custom endpoint can first be set up using a `DEFINE API` statement via the `/sql` endpoint.

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" -d 'DEFINE API "/custom_response" FOR get MIDDLEWARE api::res::body("json") THEN { { status: 200, body: { some: "info" } } }' http://localhost:8000/sql
```

Once this is set up, a simple curl command to the endpoint will suffice to see the response.
Request

```bash
curl http://localhost:8000/api/main/main/custom_response -H "Surreal-NS: ns" -H "Surreal-DB: db" -H "Accept: application/json"
```

Response

```json
{"some":"info"}
```
