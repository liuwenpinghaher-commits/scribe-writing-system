---
title: "https://surrealdb.com/docs/reference/java/concepts/multiple-sessions"
url: "https://surrealdb.com/docs/reference/java/concepts/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/multiple-sessions

Source: https://surrealdb.com/docs/reference/java/concepts/multiple-sessions

The Java SDK supports creating multiple isolated sessions over a single connection. Each session maintains its own namespace, database, and authentication state while sharing the underlying transport, which avoids the overhead of establishing multiple connections.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/multiple-sessions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.newSession()`](https://surrealdb.com/docs/reference/java/api/core/surreal#new-session)  | Creates a new isolated session  |  
##  Creating a new session[](https://surrealdb.com/docs/reference/java/concepts/multiple-sessions#creating-a-new-session)
The [`.newSession()`](https://surrealdb.com/docs/reference/java/api/core/surreal#new-session) method returns a new [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) instance that shares the underlying connection but has its own independent state. The new session starts without a selected namespace, database, or authentication — you must configure these separately.

```java
Surreal session = db.newSession();
session.useNs("surrealdb").useDb("docs");
session.signin(new RootCredential("root", "root"));
```

##  Session isolation[](https://surrealdb.com/docs/reference/java/concepts/multiple-sessions#session-isolation)
Each session independently manages its own namespace, database selection, and authentication. Changes to one session do not affect others. This means you can sign in with different credentials, select different databases, or invalidate authentication on one session without impacting the rest.

```java
try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");

    Surreal session1 = db.newSession();
    session1.useNs("tenant_a").useDb("main");
    session1.signin(new RootCredential("root", "root"));

    Surreal session2 = db.newSession();
    session2.useNs("tenant_b").useDb("main");
    session2.signin(new RootCredential("root", "root"));
}
```

In this example, `session1` and `session2` operate on different namespaces over the same WebSocket connection. Queries on `session1` only see data in `tenant_a`, while queries on `session2` only see data in `tenant_b`.
##  When to use multiple sessions[](https://surrealdb.com/docs/reference/java/concepts/multiple-sessions#when-to-use-multiple-sessions)
Multiple sessions are useful when your application needs to interact with SurrealDB using different contexts over a single connection:
  * •
**Multi-tenant applications** — isolate each tenant's data by using separate sessions with different namespaces or databases.
  * •
**Background tasks** — run background operations with elevated or restricted credentials without affecting the main application session.
  * •
**Testing** — create isolated sessions to test different permission levels or database states without opening additional connections.

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/multiple-sessions#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal#new-session) for the newSession method
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for connection setup
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) for per-session authentication
  * •
[DEFINE NAMESPACE](https://surrealdb.com/docs/reference/query-language/statements/define/namespace) for namespace isolation in multi-tenant setups
