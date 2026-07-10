---
title: "https://surrealdb.com/docs/reference/python/concepts/executing-queries"
url: "https://surrealdb.com/docs/reference/python/concepts/executing-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/executing-queries

Source: https://surrealdb.com/docs/reference/python/concepts/executing-queries

The Python SDK lets you execute [SurrealQL](https://surrealdb.com/docs/reference/query-language) statements directly against the database. You can run ad-hoc queries with parameter binding, retrieve processed results, or access the full raw response for advanced use cases.
This page covers how to run queries, bind variables, and work with raw results.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.query(query, vars?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#query)  | Executes a SurrealQL query and returns the processed result  |  
| [`db.query_raw(query, params?)`](https://surrealdb.com/docs/reference/python/api/core/surreal#query-raw)  | Executes a SurrealQL query and returns the full raw response  |  
##  Running a query[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#running-a-query)
The `.query()` method executes a SurrealQL statement and returns the result directly as a [Value](https://surrealdb.com/docs/reference/python/api/types/#value). This is the simplest way to run queries when you need only the result data.
SynchronousAsynchronous

```python
from surrealdb import Surreal

with Surreal("ws://localhost:8000") as db:
    db.use("surrealdb", "docs")
    db.signin({"username": "root", "password": "root"})

    result = db.query("SELECT * FROM users")
    print(result)
```

```python
from surrealdb import AsyncSurreal

async with AsyncSurreal("ws://localhost:8000") as db:
    await db.use("surrealdb", "docs")
    await db.signin({"username": "root", "password": "root"})

    result = await db.query("SELECT * FROM users")
    print(result)
```

##  Passing variables[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#passing-variables)
You can pass a dictionary of variables as the second argument to `.query()`. Variables are referenced in SurrealQL using the `$` prefix and are safely bound, preventing injection attacks.
SynchronousAsynchronous

```python
result = db.query(
    "SELECT * FROM users WHERE age > $min_age AND active = $active",
    {"min_age": 18, "active": True},
)
```

```python
result = await db.query(
    "SELECT * FROM users WHERE age > $min_age AND active = $active",
    {"min_age": 18, "active": True},
)
```

You can bind any Python value supported by the SDK, including strings, numbers, booleans, lists, dictionaries, and SurrealDB-specific types such as [RecordID](https://surrealdb.com/docs/reference/python/api/values/record-id).

```python
from surrealdb import RecordID

result = db.query(
    "SELECT * FROM users WHERE id = $user_id",
    {"user_id": RecordID("users", "tobie")},
)
```

##  Getting raw query results[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#getting-raw-query-results)
The `.query_raw()` method returns the full response from the server, including metadata such as execution time and status for each statement. This is useful for debugging or when you need to inspect how the server processed the query.
SynchronousAsynchronous

```python
response = db.query_raw("SELECT * FROM users; SELECT * FROM products")

for statement in response:
    print(statement["status"])
    print(statement["time"])
    print(statement["result"])
```

```python
response = await db.query_raw("SELECT * FROM users; SELECT * FROM products")

for statement in response:
    print(statement["status"])
    print(statement["time"])
    print(statement["result"])
```

Each element in the response corresponds to one statement in the query and contains the `status`, `time`, and `result` fields.
##  Handling multiple statements[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#handling-multiple-statements)
When a query string contains multiple semicolon-separated statements, `.query()` returns only the result of the **last** statement. If you need the results from every statement, use `.query_raw()` instead.
The following example demonstrates the difference between the two methods for multi-statement queries.
SynchronousAsynchronous

```python
last_result = db.query("""
    CREATE users CONTENT {"name": "Alice", "age": 30};
    SELECT * FROM users;
""")

all_results = db.query_raw("""
    CREATE users CONTENT {"name": "Alice", "age": 30};
    SELECT * FROM users;
""")
```

```python
last_result = await db.query("""
    CREATE users CONTENT {"name": "Alice", "age": 30};
    SELECT * FROM users;
""")

all_results = await db.query_raw("""
    CREATE users CONTENT {"name": "Alice", "age": 30};
    SELECT * FROM users;
""")
```

In the example above, `last_result` contains only the `SELECT` output, while `all_results` contains the full response for both the `CREATE` and `SELECT` statements.
##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/executing-queries#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for complete method signatures and parameters
  * •
[Data manipulation](https://surrealdb.com/docs/reference/python/concepts/data-manipulation) for CRUD operations using dedicated methods
  * •
[SurrealQL reference](https://surrealdb.com/docs/reference/query-language) for the full query language documentation
  * •
[Value types](https://surrealdb.com/docs/reference/python/api/types) for the types returned by query methods
