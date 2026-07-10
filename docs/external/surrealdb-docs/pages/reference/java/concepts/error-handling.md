---
title: "https://surrealdb.com/docs/reference/java/concepts/error-handling"
url: "https://surrealdb.com/docs/reference/java/concepts/error-handling"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/error-handling

Source: https://surrealdb.com/docs/reference/java/concepts/error-handling

The Java SDK provides a structured exception hierarchy for handling errors from the database and SDK. All exceptions extend [`SurrealException`](https://surrealdb.com/docs/reference/java/api/errors#surreal-exception), which is an unchecked exception. Server-returned errors are represented as [`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) subclasses with typed error details.
##  API references[](https://surrealdb.com/docs/reference/java/concepts/error-handling#api-references)  
| Error class  | Description  |  
| --- | --- |  
| [`SurrealException`](https://surrealdb.com/docs/reference/java/api/errors#surreal-exception)  | Base exception for all SDK errors  |  
| [`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception)  | Base for server-returned errors  |  
| [`NotFoundException`](https://surrealdb.com/docs/reference/java/api/errors#not-found-exception)  | Thrown when a resource is not found  |  
| [`NotAllowedException`](https://surrealdb.com/docs/reference/java/api/errors#not-allowed-exception)  | Thrown when an operation is not permitted  |  
| [`QueryException`](https://surrealdb.com/docs/reference/java/api/errors#query-exception)  | Thrown when a query fails  |  
| [`AlreadyExistsException`](https://surrealdb.com/docs/reference/java/api/errors#already-exists-exception)  | Thrown when a resource already exists  |  
##  Exception hierarchy[](https://surrealdb.com/docs/reference/java/concepts/error-handling#exception-hierarchy)
[`SurrealException`](https://surrealdb.com/docs/reference/java/api/errors#surreal-exception) is the base class for all exceptions thrown by the SDK. It extends `RuntimeException`, so exceptions are unchecked. [`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) extends `SurrealException` and represents errors returned by the SurrealDB server. Specific exception types extend `ServerException` for common error categories.
  * •
[`SurrealException`](https://surrealdb.com/docs/reference/java/api/errors#surreal-exception) — base for all SDK errors
    * ◦
[`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) — base for server-returned errors
      * ▪
[`NotFoundException`](https://surrealdb.com/docs/reference/java/api/errors#not-found-exception) — resource not found
      * ▪
[`NotAllowedException`](https://surrealdb.com/docs/reference/java/api/errors#not-allowed-exception) — operation not permitted
      * ▪
[`QueryException`](https://surrealdb.com/docs/reference/java/api/errors#query-exception) — query execution failed
      * ▪
[`AlreadyExistsException`](https://surrealdb.com/docs/reference/java/api/errors#already-exists-exception) — resource already exists

##  Catching server errors[](https://surrealdb.com/docs/reference/java/concepts/error-handling#catching-server-errors)
All server errors are [`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) subclasses. Catch specific exceptions first for targeted handling, then fall back to `ServerException` for unexpected server errors.

```java
try {
    db.query("SELECT * FROM protected_table");
} catch (NotAllowedException e) {
    System.err.println("Permission denied: " + e.getMessage());
} catch (QueryException e) {
    System.err.println("Query failed: " + e.getMessage());
} catch (ServerException e) {
    System.err.println("Server error: " + e.getMessage());
}
```

##  Inspecting error details[](https://surrealdb.com/docs/reference/java/concepts/error-handling#inspecting-error-details)
[`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) provides methods for inspecting the error returned by the server.
  * •
`.getKind()` — returns the error kind as a `String`
  * •
`.getKindEnum()` — returns the error kind as an [`ErrorKind`](https://surrealdb.com/docs/reference/java/api/errors#error-kind) enum value
  * •
`.getDetails()` — returns additional error details

The [`ErrorKind`](https://surrealdb.com/docs/reference/java/api/errors#error-kind) enum includes: `VALIDATION`, `CONFIGURATION`, `THROWN`, `QUERY`, `SERIALIZATION`, `NOT_ALLOWED`, `NOT_FOUND`, `ALREADY_EXISTS`, `CONNECTION`, `INTERNAL`, and `UNKNOWN`.

```java
try {
    db.query("INVALID QUERY");
} catch (ServerException e) {
    ErrorKind kind = e.getKindEnum();
    String details = e.getDetails();
    System.err.println(kind + ": " + details);
}
```

##  Traversing error chains[](https://surrealdb.com/docs/reference/java/concepts/error-handling#traversing-error-chains)
Server errors can have nested causes. [`ServerException`](https://surrealdb.com/docs/reference/java/api/errors#server-exception) provides methods for walking the cause chain to find a specific error type.
  * •
`.getServerCause()` — returns the underlying `ServerException` cause, if any
  * •
`.hasKind(kind)` — checks whether this error or any cause matches the given `ErrorKind`
  * •
`.findCause(kind)` — searches the cause chain and returns the first `ServerException` matching the given `ErrorKind`

```java
try {
    db.query("SELECT * FROM users");
} catch (ServerException e) {
    if (e.hasKind(ErrorKind.NOT_ALLOWED)) {
        ServerException cause = e.findCause(ErrorKind.NOT_ALLOWED);
        System.err.println("Permission error: " + cause.getDetails());
    }
}
```

##  Handling specific error types[](https://surrealdb.com/docs/reference/java/concepts/error-handling#handling-specific-error-types)
Specific exception subclasses expose additional context about the error.
[`NotFoundException`](https://surrealdb.com/docs/reference/java/api/errors#not-found-exception) provides `.getTableName()` and `.getRecordId()` to identify the missing resource.

```java
try {
    Optional<Value> user = db.select(new RecordId("users", "nonexistent"));
} catch (NotFoundException e) {
    System.err.println("Table: " + e.getTableName());
    System.err.println("Record: " + e.getRecordId());
}
```

[`NotAllowedException`](https://surrealdb.com/docs/reference/java/api/errors#not-allowed-exception) provides `.isTokenExpired()` and `.isInvalidAuth()` to distinguish authentication failures.

```java
try {
    db.query("SELECT * FROM protected");
} catch (NotAllowedException e) {
    if (e.isTokenExpired()) {
        System.err.println("Token expired, re-authenticate");
    } else if (e.isInvalidAuth()) {
        System.err.println("Invalid credentials");
    }
}
```

[`QueryException`](https://surrealdb.com/docs/reference/java/api/errors#query-exception) provides `.isTimedOut()` and `.isCancelled()` to identify query lifecycle issues.

```java
try {
    db.query("SELECT * FROM large_table");
} catch (QueryException e) {
    if (e.isTimedOut()) {
        System.err.println("Query timed out");
    } else if (e.isCancelled()) {
        System.err.println("Query was cancelled");
    }
}
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/error-handling#learn-more)
  * •
[Errors API reference](https://surrealdb.com/docs/reference/java/api/errors) for complete exception class documentation
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for connection error scenarios
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) for authentication error scenarios
  * •
[SurrealQL THROW](https://surrealdb.com/docs/reference/query-language/statements/throw) for throwing custom errors from queries
