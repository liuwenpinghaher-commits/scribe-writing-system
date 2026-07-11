---
title: "https://surrealdb.com/docs/reference/java/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/java/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/live-queries

Source: https://surrealdb.com/docs/reference/java/concepts/live-queries

The Java SDK supports real-time [live queries](https://surrealdb.com/docs/reference/query-language/statements/live-select) that stream changes from the database to your application. When records in a table are created, updated, or deleted, the SDK delivers notifications through a [`LiveStream`](https://surrealdb.com/docs/reference/java/api/core/live-stream) that you can consume in a loop or process asynchronously.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/live-queries#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.selectLive(table)`](https://surrealdb.com/docs/reference/java/api/core/surreal#select-live)  | Starts a live query on a table  |  
| [`stream.next()`](https://surrealdb.com/docs/reference/java/api/core/live-stream#next)  | Returns the next notification  |  
| [`stream.close()`](https://surrealdb.com/docs/reference/java/api/core/live-stream#close)  | Closes the live query  |  
##  Starting a live query[](https://surrealdb.com/docs/reference/java/concepts/live-queries#starting-a-live-query)
The [`.selectLive()`](https://surrealdb.com/docs/reference/java/api/core/surreal#select-live) method subscribes to changes on a table and returns a [`LiveStream`](https://surrealdb.com/docs/reference/java/api/core/live-stream). Live queries require a WebSocket connection (`ws://` or `wss://`) because the server pushes notifications over the persistent connection.

```java
try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    LiveStream stream = db.selectLive("users");
}
```

##  Receiving notifications[](https://surrealdb.com/docs/reference/java/concepts/live-queries#receiving-notifications)
Call [`.next()`](/docs/reference/java/api/core/live-stream#next) on the `LiveStream` to block until the next notification arrives. It returns an `Optional` — the optional is empty if the stream has been closed.
Each [`LiveNotification`](https://surrealdb.com/docs/reference/java/api/core/live-stream#live-notification) provides:
  * •
`.getAction()` — the type of change: `CREATE`, `UPDATE`, or `DELETE`
  * •
`.getValue()` — the record data as a [`Value`](https://surrealdb.com/docs/reference/java/api/values/value)
  * •
`.getQueryId()` — the unique identifier of the live query

```java
LiveStream stream = db.selectLive("users");

while (true) {
    Optional<LiveNotification> notification = stream.next();
    if (notification.isEmpty()) break;

    LiveNotification n = notification.get();
    System.out.println(n.getAction() + ": " + n.getValue());
}
```

##  Closing a live query[](https://surrealdb.com/docs/reference/java/concepts/live-queries#closing-a-live-query)
Call [`.close()`](https://surrealdb.com/docs/reference/java/api/core/live-stream#close) to unsubscribe from the live query and release the server-side subscription. `LiveStream` implements `AutoCloseable`, so you can use try-with-resources to ensure the stream is closed automatically.

```java
try (LiveStream stream = db.selectLive("users")) {
    Optional<LiveNotification> notification = stream.next();
    notification.ifPresent(n ->
        System.out.println(n.getAction() + ": " + n.getValue())
    );
}
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/live-queries#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal#select-live) for the selectLive method
  * •
[LiveStream API reference](https://surrealdb.com/docs/reference/java/api/core/live-stream) for stream and notification details
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for WebSocket connection setup
  * •
[SurrealQL LIVE SELECT](https://surrealdb.com/docs/reference/query-language/statements/live-select) for the underlying query syntax
  * •
[DEFINE TABLE ... CHANGEFEED](https://surrealdb.com/docs/reference/query-language/statements/define/table) for configuring changefeeds on tables
