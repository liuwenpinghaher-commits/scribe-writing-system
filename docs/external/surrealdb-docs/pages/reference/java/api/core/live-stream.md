---
title: "https://surrealdb.com/docs/reference/java/api/core/live-stream"
url: "https://surrealdb.com/docs/reference/java/api/core/live-stream"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/core/live-stream

Source: https://surrealdb.com/docs/reference/java/api/core/live-stream

The `LiveStream` class provides a blocking interface for receiving real-time notifications from live queries. It implements `AutoCloseable`, so it can be used in a try-with-resources block. Live streams are created by calling [`.selectLive()`](https://surrealdb.com/docs/reference/java/api/core/surreal#select-live) on a `Surreal` instance.
Note
Live queries require a WebSocket connection (`ws://` or `wss://`).
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/core/live-stream#methods)
###  `.next()`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#next)
Blocks until the next live query notification is available and returns it. Returns an empty `Optional` if the stream has been closed.
Method Syntax

```java
stream.next()
```

**Returns:** `Optional`
Example

```java
LiveStream stream = db.selectLive("person");
Optional<LiveNotification> notification = stream.next();
```

###  `.close()`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#close)
Closes the live query subscription and releases associated resources. This is called automatically when using try-with-resources.
Method Syntax

```java
stream.close()
```

**Returns:** `void`
Example

```java
stream.close();
```

* * *
#  `LiveNotification`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#live-notification)
The `LiveNotification` class represents a single real-time notification received from a live query. Each notification contains the action that triggered it, the affected record value, and the live query identifier.
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/core/live-stream#methods-1)
###  `.getAction()`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#get-action)
Returns the type of action that triggered the notification.
Method Syntax

```java
notification.getAction()
```

**Returns:** `String` — one of `"CREATE"`, `"UPDATE"`, or `"DELETE"`
Example

```java
String action = notification.getAction();
```

###  `.getValue()`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#get-value)
Returns the record value associated with the notification. For `CREATE` and `UPDATE` actions, this is the full record. For `DELETE` actions, this may be `null`.
Method Syntax

```java
notification.getValue()
```

**Returns:** `Value` (may be `null` for `DELETE` actions)
Example

```java
Value record = notification.getValue();
```

###  `.getQueryId()`[](https://surrealdb.com/docs/reference/java/api/core/live-stream#get-query-id)
Returns the UUID of the live query that produced this notification.
Method Syntax

```java
notification.getQueryId()
```

**Returns:** `String`
Example

```java
String queryId = notification.getQueryId();
```

* * *
##  Complete example[](https://surrealdb.com/docs/reference/java/api/core/live-stream#complete-example)
Listening for live changes

```java
import com.surrealdb.Surreal;
import com.surrealdb.LiveStream;
import com.surrealdb.LiveNotification;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    try (LiveStream stream = db.selectLive("person")) {
        while (true) {
            Optional<LiveNotification> notification = stream.next();
            if (notification.isEmpty()) break;

            LiveNotification n = notification.get();
            System.out.println(n.getAction() + ": " + n.getValue());
        }
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/core/live-stream#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal) — Connection and method reference
  * •
[Live queries](https://surrealdb.com/docs/reference/java/concepts/live-queries) — Live query concepts and patterns
  * •
[SurrealQL LIVE SELECT](https://surrealdb.com/docs/reference/query-language/statements/live-select) — Live query syntax
