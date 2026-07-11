---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/live-queries

Source: https://surrealdb.com/docs/reference/php/v2/concepts/live-queries

Live queries notify your application whenever records that match a query are created, updated, or deleted. You start a `LIVE SELECT` statement to get a query ID, then iterate the messages the server pushes for that ID.
Note
Live queries require a WebSocket connection. They are not available over HTTP. Check support with [`isFeatureSupported()`](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#testing-for-features) before relying on one.
##  Starting a live query[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#starting-a-live-query)
Run a [`LIVE SELECT`](https://surrealdb.com/docs/reference/query-language/statements/live-select) statement with `run()`. The result is the live query ID.

```php
[$queryId] = $db->run('LIVE SELECT * FROM person');
```

##  Receiving messages[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#receiving-messages)
Pass the ID to `live()`. It returns an iterable of [`LiveMessage`](https://surrealdb.com/docs/reference/php/v2/api/core#livemessage) objects, one per change. Each message carries the `action`, the affected `record` ID, and the new `value`.

```php
use SurrealDB\SDK\Live\LiveAction;

foreach ($db->live($queryId) as $message) {
    match ($message->action) {
        LiveAction::Create => handleCreate($message->value),
        LiveAction::Update => handleUpdate($message->value),
        LiveAction::Delete => handleDelete($message->record),
        LiveAction::Killed => break,
    };
}
```

##  Running without blocking the application[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#running-without-blocking-the-application)
A `foreach` over `live()` blocks the current PHP process while it waits for the next message. The standard PHP runtime (PHP-FPM or the CLI) handles one task per worker, so a process parked on a live query cannot serve anything else.
Warning
Consume live queries in a dedicated, long-running worker, and run the PHP runtime with several workers so that one worker blocked on a live query does not freeze the rest of your application. Avoid opening a live query inside a normal web request.
To run live queries alongside the rest of your application, choose an asynchronous runtime or run dedicated workers. See [Runtimes and workers](https://surrealdb.com/docs/reference/php/v2/concepts/runtimes) for configuring PHP-FPM with dedicated workers, OpenSwoole, and FrankenPHP.
##  Live actions[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#live-actions)
Every message has an action from the `LiveAction` enum:  
| Action  | Description  |  
| --- | --- |  
| `LiveAction::Create`  | A new record matched the query  |  
| `LiveAction::Update`  | A matching record was modified  |  
| `LiveAction::Delete`  | A matching record was removed  |  
| `LiveAction::Killed`  | The live query was stopped on the server  |  
##  Stopping a live query[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#stopping-a-live-query)
Stop a live query by running a [`KILL`](https://surrealdb.com/docs/reference/query-language/statements/kill) statement with its ID. The loop receives a final `LiveAction::Killed` message and ends.

```php
$db->run('KILL $id', ['id' => $queryId]);
```

##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/live-queries#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/php/v2/api/core#live) for the `live()` signature
  * •
[LIVE SELECT](https://surrealdb.com/docs/reference/query-language/statements/live-select) for the SurrealQL syntax
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb) for WebSocket setup
