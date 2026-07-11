---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/sessions"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/sessions

Source: https://surrealdb.com/docs/reference/php/v2/concepts/sessions

A session is an independent context on a connection. It carries its own selected namespace and database, its own session variables, and its own authentication state. Version 2 of the PHP SDK opens one default session when you connect, and every method on the `Surreal` class runs against it.
For most applications the default session is all you need. Multiple sessions are useful when a single long-lived connection has to serve several independent contexts, for example different authenticated users on the same WebSocket.
Important
Multiple sessions require a WebSocket connection and SurrealDB `3.0.0` or later. Check support with `isFeatureSupported()` before relying on them.

```php
use SurrealDB\SDK\Protocol\Features;

if ($db->isFeatureSupported(Features::sessions())) {
    // safe to create extra sessions
}
```

##  Managing sessions[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#managing-sessions)
Additional sessions are managed through the [`ConnectionController`](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller), which you reach with `connection()`.
###  Creating a session[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#creating-a-session)
`createSession()` opens a new session and returns its id. Pass the id of an existing session to `clone` to copy its namespace, database, and variables into the new one.
Syntax

```php
$db->connection()->createSession(?string $clone = null): string
```

```php
$session = $db->connection()->createSession();
```

###  Listing sessions[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#listing-sessions)
`sessions()` returns the ids of the open sessions.
Syntax

```php
$db->connection()->sessions(): array
```

###  Destroying a session[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#destroying-a-session)
`destroySession()` closes a session and releases it. Passing an unknown id throws an `InvalidSessionException`.
Syntax

```php
$db->connection()->destroySession(?string $session): void
```

```php
$db->connection()->destroySession($session);
```

##  Running queries in a session[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#running-queries-in-a-session)
The methods on `Surreal` always use the default session. To run a statement in another session, call `query()` on the controller and pass the session id. It returns an iterable of result chunks, one per statement; call `resultOrThrow()` on each to get its value or raise the server error.

```php
use SurrealDB\SDK\Query\BoundQuery;

$session = $db->connection()->createSession();

foreach ($db->connection()->query(
    new BoundQuery('SELECT * FROM person'),
    $session,
) as $chunk) {
    $people = $chunk->resultOrThrow();
}

$db->connection()->destroySession($session);
```

The same call accepts a transaction id as a third argument, so a session can run statements inside an explicit [transaction](https://surrealdb.com/docs/reference/php/v2/concepts/transactions).
##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/sessions#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller) for the session methods
  * •
[Transactions](https://surrealdb.com/docs/reference/php/v2/concepts/transactions) for running statements atomically
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb) for the default session and WebSocket setup
