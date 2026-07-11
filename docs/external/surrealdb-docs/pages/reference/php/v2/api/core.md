---
title: "https://surrealdb.com/docs/reference/php/v2/api/core"
url: "https://surrealdb.com/docs/reference/php/v2/api/core"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/api/core

Source: https://surrealdb.com/docs/reference/php/v2/api/core

The `Surreal` class is the entry point for version 2 of the SDK. It manages the connection, the session, authentication, and query execution.
**Namespace:** `SurrealDB\SDK\Surreal`
**Source:** [src/Surreal.php](https://github.com/surrealdb/surrealdb.php/blob/main/src/Surreal.php)
##  Constructor[](https://surrealdb.com/docs/reference/php/v2/api/core#constructor)
Syntax

```php
new Surreal(?DriverOptions $options = null)
```

`DriverOptions` customises driver-wide behaviour such as the codec, HTTP client, scheduler, and middleware. Pass `null` for the defaults.

```php
use SurrealDB\SDK\Surreal;

$db = new Surreal();
```

##  Connection methods[](https://surrealdb.com/docs/reference/php/v2/api/core#connection-methods)
###  `connect()`[](https://surrealdb.com/docs/reference/php/v2/api/core#connect)
Connect to a SurrealDB endpoint.
Syntax

```php
$db->connect(string|Endpoint $url, ?ConnectOptions $options = null): void
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `string | Endpoint`  |  The endpoint to connect to, such as `ws://127.0.0.1:8000/rpc`.  |  
| `options`  | [ConnectOptions](https://surrealdb.com/docs/reference/php/v2/api/core#connectoptions)  | Namespace, database, authentication, and reconnection settings.  |  

```php
$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    namespace: 'surrealdb',
    database: 'docs',
));
```

###  `close()`[](https://surrealdb.com/docs/reference/php/v2/api/core#close)
Close the connection and release its resources.
Syntax

```php
$db->close(): void
```

###  `status()`[](https://surrealdb.com/docs/reference/php/v2/api/core#status)
Return the current [`ConnectionStatus`](https://surrealdb.com/docs/reference/php/v2/api/core#connectionstatus).
Syntax

```php
$db->status(): ConnectionStatus
```

###  `isConnected()`[](https://surrealdb.com/docs/reference/php/v2/api/core#isconnected)
Return whether the connection is established. Equivalent to `status() === ConnectionStatus::Connected`.
Syntax

```php
$db->isConnected(): bool
```

###  `health()`[](https://surrealdb.com/docs/reference/php/v2/api/core#health)
Throw if the instance is unreachable, otherwise return nothing.
Syntax

```php
$db->health(): void
```

###  `version()`[](https://surrealdb.com/docs/reference/php/v2/api/core#version)
Return the server version string, for example `surrealdb-2.1.0`.
Syntax

```php
$db->version(): string
```

###  `isFeatureSupported()`[](https://surrealdb.com/docs/reference/php/v2/api/core#isfeaturesupported)
Return whether a feature is available on the current connection and server.
Syntax

```php
$db->isFeatureSupported(Feature $feature): bool
```

###  `subscribe()`[](https://surrealdb.com/docs/reference/php/v2/api/core#subscribe)
Subscribe to a lifecycle event: `connecting`, `connected`, `reconnecting`, `disconnected`, `error`, `auth`, or `using`. Returns a closure that removes the listener.
Syntax

```php
$db->subscribe(string $event, callable $listener): Closure
```

###  `connection()`[](https://surrealdb.com/docs/reference/php/v2/api/core#connection)
Return the underlying [`ConnectionController`](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller) for advanced operations such as transactions, sessions, and import/export.
Syntax

```php
$db->connection(): ConnectionController
```

##  Session methods[](https://surrealdb.com/docs/reference/php/v2/api/core#session-methods)
###  `use()`[](https://surrealdb.com/docs/reference/php/v2/api/core#use)
Select a namespace and an optional database.
Syntax

```php
$db->use(?string $namespace, ?string $database = null): void
```

###  `let()`[](https://surrealdb.com/docs/reference/php/v2/api/core#let)
Define a session parameter, available in later queries as `$name`.
Syntax

```php
$db->let(string $name, mixed $value): void
```

###  `unset()`[](https://surrealdb.com/docs/reference/php/v2/api/core#unset)
Remove a session parameter.
Syntax

```php
$db->unset(string $name): void
```

##  Authentication methods[](https://surrealdb.com/docs/reference/php/v2/api/core#authentication-methods)
###  `signin()`[](https://surrealdb.com/docs/reference/php/v2/api/core#signin)
Sign in with a [credential object](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#credential-types) or an array. Returns a [`Tokens`](https://surrealdb.com/docs/reference/php/v2/api/core#tokens) object.
Syntax

```php
$db->signin(Credentials|array $auth): Tokens
```

###  `signup()`[](https://surrealdb.com/docs/reference/php/v2/api/core#signup)
Sign up a new record user. Returns a [`Tokens`](https://surrealdb.com/docs/reference/php/v2/api/core#tokens) object.
Syntax

```php
$db->signup(Credentials|array $auth): Tokens
```

###  `authenticate()`[](https://surrealdb.com/docs/reference/php/v2/api/core#authenticate)
Authenticate the session with an existing token.
Syntax

```php
$db->authenticate(Token|string $token): void
```

###  `invalidate()`[](https://surrealdb.com/docs/reference/php/v2/api/core#invalidate)
Clear the session's authentication.
Syntax

```php
$db->invalidate(): void
```

##  Query methods[](https://surrealdb.com/docs/reference/php/v2/api/core#query-methods)
###  `query()`[](https://surrealdb.com/docs/reference/php/v2/api/core#query)
Execute a [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery), returning one result per statement.
Syntax

```php
$db->query(BoundQuery $query): array
```

###  `run()`[](https://surrealdb.com/docs/reference/php/v2/api/core#run)
Execute raw SurrealQL with optional bindings, returning one result per statement.
Syntax

```php
$db->run(string $surql, array $bindings = []): array
```

###  Statement builders[](https://surrealdb.com/docs/reference/php/v2/api/core#statement-builders)
These methods start a fluent [query builder](https://surrealdb.com/docs/reference/php/v2/api/query-builders). Call `execute()` to run it.
  * •
`select($what)`, `create($what)`, `update($what)`, `upsert($what)`, `delete($what)`
  * •
`insert($tableOrData, $data = null)`, `relate($from, $edge, $to, $data = null)`
  * •
`call($name, $version = null, $args = [])`, `auth()`

###  `live()`[](https://surrealdb.com/docs/reference/php/v2/api/core#live)
Subscribe to a live query by its ID. Returns an iterable of [`LiveMessage`](https://surrealdb.com/docs/reference/php/v2/api/core#livemessage) objects.
Syntax

```php
$db->live(string $queryUuid): iterable
```

Iterating the result blocks the process while it waits for messages. See [running without blocking the application](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#running-without-blocking-the-application) for consuming live queries in a worker.
* * *
#  Supporting types[](https://surrealdb.com/docs/reference/php/v2/api/core#supporting-types)
##  `ConnectOptions`[](https://surrealdb.com/docs/reference/php/v2/api/core#connectoptions)
Per-connection settings passed to `connect()`.
**Namespace:** `SurrealDB\SDK\Connection\ConnectOptions`
Constructor

```php
new ConnectOptions(
    ?string $namespace = null,
    ?string $database = null,
    Credentials|Token|AuthProviderInterface|Closure|string|null $authentication = null,
    bool $versionCheck = true,
    bool $invalidateOnExpiry = false,
    bool|array|ReconnectStrategyInterface $reconnect = true,
)
```

##  `ConnectionStatus`[](https://surrealdb.com/docs/reference/php/v2/api/core#connectionstatus)
A string-backed enum with the connection lifecycle states.
**Namespace:** `SurrealDB\SDK\Connection\ConnectionStatus`
**Values:** `Disconnected`, `Connecting`, `Reconnecting`, `Connected`
##  `Tokens`[](https://surrealdb.com/docs/reference/php/v2/api/core#tokens)
The result of `signin()` and `signup()`: an access token and an optional refresh token.
**Namespace:** `SurrealDB\SDK\Auth\Tokens`
Properties

```php
$tokens->access;   // ?string
$tokens->refresh;  // ?string
```

##  `LiveMessage`[](https://surrealdb.com/docs/reference/php/v2/api/core#livemessage)
A single live query notification.
**Namespace:** `SurrealDB\SDK\Live\LiveMessage`
Properties

```php
$message->queryId;  // string
$message->action;   // LiveAction (Create, Update, Delete, Killed)
$message->record;   // mixed: the affected record id
$message->value;    // mixed: the new record value
```

* * *
#  `ConnectionController`[](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller)
The controller orchestrates the connection. Access it with `$db->connection()` for operations that are not on the `Surreal` facade.
**Namespace:** `SurrealDB\SDK\Connection\ConnectionController`
##  Transactions[](https://surrealdb.com/docs/reference/php/v2/api/core#transactions)
Syntax

```php
$db->connection()->begin(?string $session = null): string
$db->connection()->commit(string $txn, ?string $session = null): void
$db->connection()->cancel(string $txn, ?string $session = null): void
```

##  Import and export[](https://surrealdb.com/docs/reference/php/v2/api/core#import-and-export)
Syntax

```php
$db->connection()->importSql(string $data): void
$db->connection()->exportSql(array $options = []): string
```

```php
$sql = $db->connection()->exportSql();
$db->connection()->importSql($sql);
```

##  Token renewal[](https://surrealdb.com/docs/reference/php/v2/api/core#token-renewal)
Syntax

```php
$db->connection()->refresh(Tokens $tokens, ?string $session = null): Tokens
$db->connection()->revoke(Tokens $tokens, ?string $session = null): void
```

##  Sessions[](https://surrealdb.com/docs/reference/php/v2/api/core#sessions)
Syntax

```php
$db->connection()->sessions(): array
$db->connection()->createSession(?string $clone = null): string
$db->connection()->destroySession(?string $session): void
```

##  See also[](https://surrealdb.com/docs/reference/php/v2/api/core#see-also)
  * •
[Query Builders](https://surrealdb.com/docs/reference/php/v2/api/query-builders) for the fluent statement API
  * •
[Data types](https://surrealdb.com/docs/reference/php/v2/api/data-types) for the value classes
  * •
[Utilities](https://surrealdb.com/docs/reference/php/v2/api/utilities) for `BoundQuery`, enums, and driver options
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb) for the connection guide
