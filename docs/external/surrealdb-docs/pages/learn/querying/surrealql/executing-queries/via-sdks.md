---
title: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks"
url: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks

Source: https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks

SurrealDB supports a number of methods for connecting to the database and performing data queries. Each SDK has its own set of methods for connecting to the database and performing data queries.
In each SDK, you can connect to the database using a local or remote connection. Once you are connected, you can start performing data queries. Here is a list of all the Supported SDKs:
[ Rust available ](https://surrealdb.com/docs/reference/rust/overview)[ JavaScript available ](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb)[ TypeScript available ](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb)[ Python available ](https://surrealdb.com/docs/reference/python)[ Node.js available ](https://surrealdb.com/docs/reference/javascript/engines/node)[ .NET available ](https://surrealdb.com/docs/reference/dotnet)[ Golang available ](https://surrealdb.com/docs/reference/golang)[ Java available ](https://surrealdb.com/docs/reference/java)[ PHP available ](https://surrealdb.com/docs/reference/php)
##  Writing SurrealQL queries in SDKs[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#writing-surrealql-queries-in-sdks)
In addition to the variety of methods provided by the SDKs to perform data queries, the `query` method works as a catch-all way to run [SurrealQL statements](https://surrealdb.com/docs/reference/query-language) against the database.
JavascriptPHPPython.NETGolangRust
Method Syntax

```ts
async db.query<T>(query, vars)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `query`  | Specifies the SurrealQL statements.  |  
| `vars`  | Assigns variables which can be used in the query.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage)

```ts
type Person = {
	id: string;
	name: string;
};

// Assign the variable on the connection
const result = await db.query<[Person[], Person[]]>(
	'CREATE person SET name = "John"; SELECT * FROM type::table($tb);',
	{ tb: 'person' }
);

// Get the first result from the first query
const created = result[0].result[0];

// Get all of the results from the second query
const people = result[1].result;
```

`.query_raw()`
With `.query_raw()`, you will get back the raw RPC response. In contrast to the `.query()` method, this will not throw errors that occur in individual queries, but will rather give those back as a string, and this will include the time it took to execute the individual queries.
Method Syntax

```php
$db->query($query, $vars)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `$query`  | Specifies the SurrealQL statements.  |  
| `$vars`  | Assigns variables which can be used in the query.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-1)

```php
// Assign the variable on the connection
$result = db->query(
	'CREATE person SET name = "John"; SELECT * FROM type::table($tb);',
	[ "tb" => "person" ]
);

// Get the first result from the first query
$created = $result[0]->result[0];

// Get all of the results from the second query
$people = $result[1]->result;
```

Method Syntax

```python
db.query(sql, vars)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `vars`  | Assigns variables which can be used in the query.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-2)

```python
# Assign the variable on the connection
result = await db.query('CREATE person; SELECT * FROM type::table($tb)', {
	'tb': 'person',
})
# Get the first result from the first query
result[0]['result'][0]
# Get all of the results from the second query
result[1]['result']
```

Method Syntax

```csharp
await db.Query(sql)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-3)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-3)

```csharp
// Execute query with params
const string table = "person";
var result = await db.Query($"CREATE person; SELECT * FROM type::table({table});");

// Get the first result from the first query
var created = result.GetValue<Person>(0);

// Get all of the results from the second query
var people = result.GetValue<List<Person>>(1);
```

  

`.RawQuery()` : Runs a set of SurrealQL statements against the database, based on a raw SurrealQL query.
Method Syntax

```csharp
await db.RawQuery(sql, params)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-4)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `params`  | Assigns variables which can be used in the query.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-4)

```csharp
// Assign the variable on the connection
var @params = new Dictionary<string, object> { { "table", "person" } };
var result = await db.RawQuery("CREATE person; SELECT * FROM type::table($table);", @params);

// Get the first result from the first query
var created = result.GetValue<Person>(0);

// Get all of the results from the second query
var people = result.GetValue<List<Person>>(1);
```

Method Syntax

```go
db.Query(sql, vars)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-5)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `vars`  | Assigns variables which can be used in the query.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-5)

```go
// Assign the variable on the connection
result, err := db.Query("CREATE person; SELECT * FROM type::table($tb);", map[string]string{
	"tb": "person"
});
```

Method Syntax

```rust
db.query(sql).bind(vars)
```

####  Arguments[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#arguments-6)  
| Arguments  | Description  |  
| --- | --- |  
| `sql`  | Specifies the SurrealQL statements.  |  
| `vars`  | Assigns variables which can be used in the query.  |  
####  Example usage[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#example-usage-6)

```rust
// Run some queries
let sql = "
    CREATE person;
    SELECT * FROM type::table($table);
";
let mut result = db
    .query(sql)
    .bind(("table", "person"))
    .await?;
// Get the first result from the first query
let created: Option<Person> = result.take(0)?;
// Get all of the results from the second query
let people: Vec<Person> = result.take(1)?;
```

##  Learn more[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-sdks#learn-more)
Learn more about the [SurrealQL query language](https://surrealdb.com/docs/reference/query-language).
