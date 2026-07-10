---
title: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http"
url: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http

Source: https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http

SurrealDB provides a [RESTful HTTP API](https://surrealdb.com/docs/reference/rest-api/http-protocol) for interacting with the database programmatically. This is useful when you need to integrate SurrealDB into existing HTTP-based workflows, scripts, or environments where an SDK is not available.
##  Using curl `POST /sql`[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#using-curl-post-sql)
The `/sql` endpoint enables use of SurrealQL queries.
Important
This HTTP endpoint expects the HTTP body to be a set of SurrealQL statements.
###  Headers[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#headers)  
| Header  | Description  |  
| --- | --- |  
| `Authorization`  | Sets the root, namespace, database, or record authentication data  |  
| `Accept`  | Sets the desired content-type of the response  |  
| `surreal-ns`  | Sets the selected Namespace for queries.  |  
| `surreal-db`  | Sets the selected Database for queries.  |  
###  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#example-usage)
Important
The `-u` in the example below is a shorthand used by curl to send an Authorization header.
Request

```bash
curl -X POST -u "root:secret" -H "surreal-ns: main" -H "surreal-db: main" -H "Accept: application/json" -d "SELECT * FROM person WHERE age > 18" http://localhost:8000/sql
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

##  Using Postman[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#using-postman)
Postman is a popular tool for testing APIs. You can use it to send HTTP requests to your SurrealDB instance and perform various database operations.
  1. 1.
**Set up Postman** : Download and install Postman from the [official website](https://www.postman.com/).
  2. 2.
**Create a new request** : Open Postman and create a new HTTP request.
  3. 3.
**Configure the request** :
     * ◦
Set the request method to `POST`.
     * ◦
Enter the URL of your SurrealDB instance, e.g., `http://localhost:8000/sql`.
     * ◦
In the [headers section](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#headers), add a `Content-Type` header with the value `application/json`.
     * ◦
In the Body section, select `raw` and set the type to `Text`. Enter your SQL query, for example:

```surql
INFO FOR DB;
```

  4. 4.
**Send the request** : Click the `Send` button to execute the query. You will see the response from SurrealDB in the lower section of the Postman interface.

##  Learn more[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-http#learn-more)
Learn more about other [HTTP Endpoints](https://surrealdb.com/docs/reference/rest-api/http-protocol) available in SurrealDB. For a more detailed tutorial on using Postman with SurrealDB, refer to the [working with SurrealDB over HTTP via Postman tutorial](https://surrealdb.com/docs/tutorials/working-with-surrealdb-over-http-via-postman).
