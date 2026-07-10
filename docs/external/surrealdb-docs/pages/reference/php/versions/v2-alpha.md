---
title: "https://surrealdb.com/docs/reference/php/versions/v2-alpha"
url: "https://surrealdb.com/docs/reference/php/versions/v2-alpha"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/versions/v2-alpha

Source: https://surrealdb.com/docs/reference/php/versions/v2-alpha

The PHP SDK for SurrealDB lets you connect to a database and query it from your application. This guide covers connecting, authenticating, and running your first queries with the v2 line of the SDK.
Important
Version 2.x is a rewrite with a fluent query builder, typed credentials, and a PSR-based transport layer. It is in **alpha** and introduces breaking changes, so pin the exact version when installing it. The current stable release is documented under [v1](https://surrealdb.com/docs/reference/php/v1), with its [getting-started guide](https://surrealdb.com/docs/languages/php) in the Start section.
##  1. Install the SDK[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#1-install-the-sdk)
Follow the [installation guide](https://surrealdb.com/docs/reference/php/v2/installation) to add the SDK to your project. Once installed, include the autoloader and import the classes you need.

```php
require __DIR__ . '/vendor/autoload.php';

use SurrealDB\SDK\Surreal;
use SurrealDB\SDK\Connection\ConnectOptions;
use SurrealDB\SDK\Auth\RootAuth;
use SurrealDB\SDK\Types\RecordId;
use SurrealDB\SDK\Types\Table;

$db = new Surreal();
```

##  2. Connect to SurrealDB[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#2-connect-to-surrealdb)
Use the `connect()` method with a connection string and a `ConnectOptions` object. The options carry the namespace, database, and authentication details. Passing credentials here lets the SDK re-authenticate automatically after a reconnect.
Supported connection protocols include:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived stateful connections that support live queries
  * •
**HTTP** (`http://`, `https://`) for short-lived stateless connections

```php
$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    namespace: 'surrealdb',
    database: 'docs',
    authentication: new RootAuth('root', 'root'),
));
```

See [Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb) for the full set of options.
##  3. Inserting data into SurrealDB[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#3-inserting-data-into-surrealdb)
The `create()` method starts a `CREATE` statement. Chain `content()` to set the record data, then call `execute()` to run it. Pass a [`RecordId`](https://surrealdb.com/docs/reference/php/v2/api/data-types#recordid) for a specific ID, or a [`Table`](https://surrealdb.com/docs/reference/php/v2/api/data-types#table) to let SurrealDB generate one.

```php
$person = $db->create(new RecordId('person', 'tobie'))
    ->content([
        'name' => 'Tobie',
        'age' => 32,
    ])
    ->execute();

$auto = $db->create(new Table('person'))
    ->content(['name' => 'Jaime'])
    ->execute();
```

##  4. Retrieving data from SurrealDB[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#4-retrieving-data-from-surrealdb)
###  Selecting records[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#selecting-records)
The `select()` method reads records. Pass a `Table` to read all records, or a `RecordId` to read one. Chain `fields()`, `where()`, and `limit()` to refine the query before `execute()`.

```php
$everyone = $db->select(new Table('person'))->execute();

$tobie = $db->select(new RecordId('person', 'tobie'))->execute();

$adults = $db->select(new Table('person'))
    ->fields('name', 'age')
    ->where('age >= 18')
    ->limit(10)
    ->execute();
```

###  Running SurrealQL queries[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#running-surrealql-queries)
For anything the builders do not cover, `run()` executes raw [SurrealQL](https://surrealdb.com/docs/reference/query-language). Pass bindings as the second argument to inject values safely.

```php
[$cheapest] = $db->run(
    'SELECT name, age FROM person WHERE age < $max ORDER BY age',
    ['max' => 40],
);
```

`run()` returns one result per statement, so destructure the first entry for a single-statement query.
##  5. Closing the connection[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#5-closing-the-connection)
Always close the connection when you are done to release resources.

```php
$db->close();
```

##  Next steps[](https://surrealdb.com/docs/reference/php/versions/v2-alpha#next-steps)
You have learned how to install the SDK, connect to SurrealDB, create records, and retrieve data. There is a lot more you can do with the SDK, including updating and deleting records, authentication, live queries, and transactions.
[Connection management Learn how to manage your database connections, including protocols and configuration.](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb)[Authentication Sign in and sign up with root, namespace, database, and record access.](https://surrealdb.com/docs/reference/php/v2/concepts/authentication)[Executing queries Use the query builders and the raw query API in depth.](https://surrealdb.com/docs/reference/php/v2/concepts/executing-queries)[API Reference Complete reference for the core client, query builders, and types.](https://surrealdb.com/docs/reference/php/v2/api/core)
Note
This getting-started guide covers the essentials. For the complete methods, API, and concept reference, see the [PHP (v2) SDK reference](https://surrealdb.com/docs/reference/php/v2).
