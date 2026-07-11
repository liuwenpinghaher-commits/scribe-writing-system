---
title: "https://surrealdb.com/docs/reference/php/v2/api/query-builders"
url: "https://surrealdb.com/docs/reference/php/v2/api/query-builders"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/api/query-builders

Source: https://surrealdb.com/docs/reference/php/v2/api/query-builders

The fluent builders compile a statement and run it through the connection. Each builder method on `Surreal` returns a builder object you configure with chained calls, then run with `execute()` or inspect with `compile()`.
All builders extend `QueryBuilder` in the `SurrealDB\SDK\Query` namespace.
##  Shared methods[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#shared-methods)
Every builder provides these methods.  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `execute()`  | `mixed`  | Run the statement and return the first statement's result  |  
| `compile()`  | [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery)  | Compile to SurrealQL and bindings without running  |  
| `json(bool $json = true)`  | `static`  | Request JSON-compatible results  |  
##  Raw queries[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#raw-queries)
###  `run()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#run)
Execute raw SurrealQL with optional bindings. Returns one result per statement.
Syntax

```php
$db->run(string $surql, array $bindings = []): array
```

```php
[$people] = $db->run('SELECT * FROM person WHERE age > $min', ['min' => 18]);
```

###  `query()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#query)
Execute a pre-built [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery). Returns one result per statement.
Syntax

```php
$db->query(BoundQuery $query): array
```

##  `select()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#select)
Start a `SELECT`. Accepts a `RecordId`, `Table`, or string target.
Methods

```php
->fields(string ...$fields)   // SELECT specific fields
->value(string $field)        // SELECT VALUE for one field
->where(string|BoundQuery $cond)
->start(int $start)
->limit(int $limit)
->fetch(string ...$fields)    // resolve record links
->timeout(string $duration)   // e.g. "5s"
->version(string $datetime)   // historical read
```

```php
$people = $db->select(new Table('person'))
    ->fields('name', 'age')
    ->where('age >= 18')
    ->limit(10)
    ->execute();
```

##  `create()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#create)
Start a `CREATE`. Accepts a `RecordId`, `Table`, or string target.
Methods

```php
->content(array|object $data)       // CONTENT
->patch(array $patches)             // PATCH
->output(Output $output)            // RETURN clause
->timeout(string $duration)
->version(string $datetime)
```

```php
$person = $db->create(new RecordId('person', 'tobie'))
    ->content(['name' => 'Tobie'])
    ->execute();
```

##  `update()` and `upsert()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#update)
Start an `UPDATE` or `UPSERT`. `update()` modifies existing records; `upsert()` creates the record if it does not exist.
Methods

```php
->content(array|object $data)   // replace the record
->merge(array|object $data)     // merge fields
->replace(array|object $data)   // REPLACE
->patch(array $patches)         // JSON Patch
->where(string|BoundQuery $cond)
->output(Output $output)
->timeout(string $duration)
```

```php
$db->update(new RecordId('person', 'tobie'))
    ->merge(['age' => 33])
    ->execute();

$db->upsert(new RecordId('person', 'tobie'))
    ->content(['name' => 'Tobie', 'age' => 33])
    ->execute();
```

##  `delete()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#delete)
Start a `DELETE`. It defaults to `RETURN BEFORE`, so deleted records are returned.
Methods

```php
->output(Output $output)
->timeout(string $duration)
->version(string $datetime)
```

```php
$db->delete(new RecordId('person', 'tobie'))->execute();
```

##  `insert()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#insert)
Start an `INSERT`. Pass a target table and records, or records alone when each carries its own ID.
Methods

```php
->relation()   // INSERT RELATION
->ignore()     // INSERT IGNORE
->output(Output $output)
->timeout(string $duration)
->version(string $datetime)
```

```php
$db->insert(new Table('person'), [
    ['name' => 'Alice'],
    ['name' => 'Bob'],
])->execute();
```

##  `relate()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#relate)
Start a `RELATE`, creating one or more graph edges.
Methods

```php
->content(array|object $data)   // store data on the edge
->unique()
->output(Output $output)
->timeout(string $duration)
->version(string $datetime)
```

```php
$db->relate(
    new RecordId('person', 'tobie'),
    new Table('likes'),
    new RecordId('post', 'surrealdb'),
)->content(['since' => 2024])->execute();
```

##  `call()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#call)
Invoke a SurrealQL or SurrealML function by name. `run()` already handles raw SurrealQL, so function invocation has its own method.
Syntax

```php
$db->call(string $name, ?string $version = null, array $args = []): RunQuery
```

```php
$greeting = $db->call('fn::greet', null, ['Tobie'])->execute();
```

##  `auth()`[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#auth)
Compile to `SELECT * FROM ONLY $auth`, returning the authenticated record user.

```php
$me = $db->auth()->execute();
```

##  Modifiers[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#modifiers)
###  Output[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#output)
`output()` accepts the `SurrealDB\SDK\Enum\Output` enum: `NONE`, `NULL_`, `DIFF`, `BEFORE`, `AFTER`.

```php
use SurrealDB\SDK\Enum\Output;

$db->update(new RecordId('person', 'tobie'))
    ->merge(['age' => 33])
    ->output(Output::AFTER)
    ->execute();
```

###  Where[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#where)
`where()` accepts a SurrealQL string or a [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery) fragment. Use a `BoundQuery` to keep dynamic values parameterised.
###  Timeout[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#timeout)
`timeout()` accepts a SurrealQL duration string such as `5s` or `1m30s`.
##  See also[](https://surrealdb.com/docs/reference/php/v2/api/query-builders#see-also)
  * •
[Executing queries](https://surrealdb.com/docs/reference/php/v2/concepts/executing-queries) for the guide
  * •
[Core classes](https://surrealdb.com/docs/reference/php/v2/api/core) for the `Surreal` entry point
  * •
[Utilities](https://surrealdb.com/docs/reference/php/v2/api/utilities) for `BoundQuery` and the `Output` enum
