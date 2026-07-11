---
title: "https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb

The first step towards interacting with [SurrealDB](https://surrealdb.com/docs/start) is to create a new connection to a database instance. This involves initializing a new [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) instance, connecting it to an endpoint, and selecting a namespace and database. The SDK supports remote connections over WebSocket and HTTP, as well as embedded in-process databases.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`new Surreal()`](https://surrealdb.com/docs/reference/java/api/core/surreal#constructor)  | Creates a new Surreal instance  |  
| [`db.connect(url)`](https://surrealdb.com/docs/reference/java/api/core/surreal#connect)  | Connects to a SurrealDB instance  |  
| [`db.close()`](https://surrealdb.com/docs/reference/java/api/core/surreal#close)  | Closes the active connection  |  
| [`db.useNs(namespace)`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-ns)  | Switches to a specific namespace  |  
| [`db.useDb(database)`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-db)  | Switches to a specific database  |  
| [`db.useDefaults()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-defaults)  | Uses the default namespace and database  |  
| [`db.version()`](https://surrealdb.com/docs/reference/java/api/core/surreal#version)  | Returns the server version  |  
| [`db.health()`](https://surrealdb.com/docs/reference/java/api/core/surreal#health)  | Checks the server health  |  
##  Opening a connection[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#opening-a-connection)
Create a new [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) instance and call [`.connect()`](https://surrealdb.com/docs/reference/java/api/core/surreal#connect) with a connection string pointing to your SurrealDB instance. The `Surreal` class implements `AutoCloseable`, so you can use it in a try-with-resources block to ensure the connection is closed automatically.

```java
Surreal db = new Surreal();
db.connect("ws://localhost:8000");
```

##  Connection string protocols[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#connection-string-protocols)
The connection string determines the protocol and transport used to communicate with SurrealDB. For more on server configuration, see the [start command](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) documentation.  
| Protocol  | Description  |  
| --- | --- |  
| `ws://`  | Plain WebSocket connection  |  
| `wss://`  | Secure WebSocket connection (TLS)  |  
| `http://`  | Plain HTTP connection  |  
| `https://`  | Secure HTTP connection (TLS)  |  
| `memory://`  | In-memory embedded database  |  
| `surrealkv://`  | Disk-based embedded database  |  
The `memory://` and `surrealkv://` protocols run SurrealDB in-process using JNI, which eliminates network overhead. See [Embedded databases](https://surrealdb.com/docs/reference/java/concepts/embedded-databases) for details on configuring embedded connections.
##  Feature support by protocol[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#feature-support-by-protocol)
Not all features are available on every protocol. The table below summarizes what is supported for each connection type.  
| Feature  | WebSocket  | HTTP  | Embedded  |  
| --- | --- | --- | --- |  
| Authentication  | Yes  | Yes  | Yes  |  
| Queries  | Yes  | Yes  | Yes  |  
| CRUD operations  | Yes  | Yes  | Yes  |  
| Live queries  | Yes  | No  | No  |  
| Transactions  | Yes  | No  | Yes  |  
| Multiple sessions  | Yes  | No  | Yes  |  
| Export / Import  | Yes  | Yes  | Yes  |  
##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
After connecting, select a [namespace](https://surrealdb.com/docs/reference/query-language/statements/define/namespace) and [database](https://surrealdb.com/docs/reference/query-language/statements/define/database) using [`.useNs()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-ns) and [`.useDb()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-db). These methods return the `Surreal` instance, so they can be chained.

```java
db.useNs("surrealdb").useDb("docs");
```

To reset the namespace and database to the server defaults, call [`.useDefaults()`](https://surrealdb.com/docs/reference/java/api/core/surreal#use-defaults).

```java
db.useDefaults();
```

##  Using try-with-resources[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#using-try-with-resources)
Since [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) implements `AutoCloseable`, Java's try-with-resources statement ensures that [`.close()`](https://surrealdb.com/docs/reference/java/api/core/surreal#close) is called when the block exits, even if an exception is thrown. This is the recommended pattern for managing connections.

```java
import com.surrealdb.Surreal;
import com.surrealdb.signin.RootCredential;

public class Example {

    public static void main(String[] args) {
        try (Surreal db = new Surreal()) {
            db.connect("ws://localhost:8000");
            db.useNs("surrealdb").useDb("docs");
            db.signin(new RootCredential("root", "root"));

            String version = db.version();
            System.out.println("Connected to SurrealDB " + version);
        }
    }

}
```

##  Effect of connection protocol on token and session duration[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#effect-of-connection-protocol-on-token-and-session-duration)
The connection protocol affects how authentication tokens and sessions behave.
  * •
**WebSocket** connections are stateful and long-lived. After the initial authentication, the session persists for the lifetime of the connection. The session duration defaults to `NONE`, meaning it never expires unless explicitly configured.
  * •
**HTTP** connections are stateless. Each request must include a valid token, and the server creates a short-lived session for the duration of that request. The token duration defaults to 1 hour.

You can configure token and session durations using the `DURATION` clause on [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access) or [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) statements. See the [security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#expiration) documentation for guidance on choosing appropriate durations.
##  Closing a connection[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#closing-a-connection)
The [`.close()`](https://surrealdb.com/docs/reference/java/api/core/surreal#close) method releases all resources associated with the connection. If you are not using try-with-resources, call `.close()` explicitly when you are done with the connection.

```java
db.close();
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal) for complete method signatures
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) for signing in and managing sessions
  * •
[Embedded databases](https://surrealdb.com/docs/reference/java/concepts/embedded-databases) for running SurrealDB in-process
  * •
[Error handling](https://surrealdb.com/docs/reference/java/concepts/error-handling) for handling connection errors
  * •
[SurrealDB authentication](https://surrealdb.com/docs/learn/security/authentication/authentication) for an overview of authentication concepts
  * •
[DEFINE NAMESPACE](https://surrealdb.com/docs/reference/query-language/statements/define/namespace) and [DEFINE DATABASE](https://surrealdb.com/docs/reference/query-language/statements/define/database) for namespace and database configuration
