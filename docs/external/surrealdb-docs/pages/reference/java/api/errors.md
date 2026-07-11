---
title: "https://surrealdb.com/docs/reference/java/api/errors"
url: "https://surrealdb.com/docs/reference/java/api/errors"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/errors

Source: https://surrealdb.com/docs/reference/java/api/errors

The Java SDK uses a hierarchy of exceptions rooted at `SurrealException`. Server-returned errors are represented by `ServerException` and its subclasses, which provide structured access to error details, kinds, and cause chains.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Exception hierarchy[](https://surrealdb.com/docs/reference/java/api/errors#exception-hierarchy)
  * •
`SurrealException` (extends `RuntimeException`)
    * ◦
`ServerException`
      * ▪
`NotFoundException`
      * ▪
`NotAllowedException`
      * ▪
`QueryException`
      * ▪
`AlreadyExistsException`
      * ▪
`ValidationException`
      * ▪
`ConfigurationException`
      * ▪
`SerializationException`
      * ▪
`InternalException`
      * ▪
`ThrownException`

* * *
##  `SurrealException`[](https://surrealdb.com/docs/reference/java/api/errors#surreal-exception)
Base exception for all SDK errors. Extends `RuntimeException`.
All exceptions thrown by the Java SDK are subclasses of `SurrealException`, making it possible to catch all SDK-related errors with a single catch block.
Example

```java
try {
    db.query("SELECT * FROM users");
} catch (SurrealException e) {
    System.err.println("SDK error: " + e.getMessage());
}
```

* * *
##  `ServerException`[](https://surrealdb.com/docs/reference/java/api/errors#server-exception)
Base class for all server-returned errors. Extends `SurrealException`.
`ServerException` provides structured access to the error kind, details, and cause chain returned by the server. All specific server error types extend this class.
###  `.getKind()`[](https://surrealdb.com/docs/reference/java/api/errors#get-kind)
Returns the error kind as a string.
Method Syntax

```java
exception.getKind()
```

**Returns:** `String`
Example

```java
try {
    db.select(Person.class, new RecordId("person", "missing"));
} catch (ServerException e) {
    String kind = e.getKind();
}
```

###  `.getKindEnum()`[](https://surrealdb.com/docs/reference/java/api/errors#get-kind-enum)
Returns the error kind as an [`ErrorKind`](https://surrealdb.com/docs/reference/java/api/errors#error-kind) enum value.
Method Syntax

```java
exception.getKindEnum()
```

**Returns:** `ErrorKind`
Example

```java
try {
    db.query("INVALID QUERY");
} catch (ServerException e) {
    ErrorKind kind = e.getKindEnum();
}
```

###  `.getDetails()`[](https://surrealdb.com/docs/reference/java/api/errors#get-details)
Returns structured error details provided by the server.
Method Syntax

```java
exception.getDetails()
```

**Returns:** `Object`
###  `.getServerCause()`[](https://surrealdb.com/docs/reference/java/api/errors#get-server-cause)
Returns the typed server cause if the error was caused by another server error.
Method Syntax

```java
exception.getServerCause()
```

**Returns:** `ServerException`
###  `.hasKind(kind)`[](https://surrealdb.com/docs/reference/java/api/errors#has-kind)
Checks if the error or any error in its cause chain matches a specific kind.
Method Syntax

```java
exception.hasKind(kind)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `kind`  |  `String`or `ErrorKind`  | The error kind to check for.  |  
**Returns:** `boolean`
Example

```java
try {
    db.query("SELECT * FROM protected_table");
} catch (ServerException e) {
    if (e.hasKind(ErrorKind.NOT_ALLOWED)) {
        System.err.println("Permission denied");
    }
}
```

###  `.findCause(kind)`[](https://surrealdb.com/docs/reference/java/api/errors#find-cause)
Finds the first error in the cause chain that matches a specific kind.
Method Syntax

```java
exception.findCause(kind)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `kind`  |  `String`or `ErrorKind`  | The error kind to search for.  |  
**Returns:** `ServerException`
Example

```java
try {
    db.query("CREATE person SET name = 'Alice'");
} catch (ServerException e) {
    ServerException cause = e.findCause(ErrorKind.ALREADY_EXISTS);
    if (cause != null) {
        System.err.println("Duplicate: " + cause.getMessage());
    }
}
```

* * *
##  `ErrorKind`[](https://surrealdb.com/docs/reference/java/api/errors#error-kind)
Enum representing error categories returned by the server.  
| Value  | Description  |  
| --- | --- |  
| `VALIDATION`  | Data validation failed  |  
| `CONFIGURATION`  | Configuration error  |  
| `THROWN`  | Explicitly thrown error from SurrealQL  |  
| `QUERY`  | Query execution error  |  
| `SERIALIZATION`  | Serialization/deserialization error  |  
| `NOT_ALLOWED`  | Operation not permitted  |  
| `NOT_FOUND`  | Resource not found  |  
| `ALREADY_EXISTS`  | Resource already exists  |  
| `CONNECTION`  | Connection error  |  
| `INTERNAL`  | Internal server error  |  
| `UNKNOWN`  | Unknown error kind  |  
###  `ErrorKind.fromString(kind)`[](https://surrealdb.com/docs/reference/java/api/errors#from-string)
Converts a string to an `ErrorKind` enum value. Returns `UNKNOWN` if the string does not match any known kind.
Method Syntax

```java
ErrorKind.fromString(kind)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `kind`  | `String`  | The error kind string to convert.  |  
**Returns:** `ErrorKind`
Example

```java
ErrorKind kind = ErrorKind.fromString("NotFound");
```

* * *
##  `NotFoundException`[](https://surrealdb.com/docs/reference/java/api/errors#not-found-exception)
Thrown when a requested resource does not exist. Extends `ServerException`.
###  Additional methods[](https://surrealdb.com/docs/reference/java/api/errors#additional-methods)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getTableName()`  | `String`  | The table that was queried  |  
| `.getRecordId()`  | `String`  | The record ID that was not found  |  
| `.getMethodName()`  | `String`  | The method that triggered the error  |  
| `.getNamespaceName()`  | `String`  | The namespace that was not found  |  
| `.getDatabaseName()`  | `String`  | The database that was not found  |  
| `.getSessionId()`  | `String`  | The session ID that was not found  |  
Example

```java
try {
    db.select(Person.class, new RecordId("person", "nonexistent"));
} catch (NotFoundException e) {
    String table = e.getTableName();
    String record = e.getRecordId();
}
```

* * *
##  `NotAllowedException`[](https://surrealdb.com/docs/reference/java/api/errors#not-allowed-exception)
Thrown when an operation is not permitted. Extends `ServerException`.
###  Additional methods[](https://surrealdb.com/docs/reference/java/api/errors#additional-methods-1)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.isTokenExpired()`  | `boolean`  | Whether the authentication token has expired  |  
| `.isInvalidAuth()`  | `boolean`  | Whether the authentication credentials are invalid  |  
| `.isScriptingBlocked()`  | `boolean`  | Whether scripting is disabled on the server  |  
| `.getMethodName()`  | `String`  | The method that was not allowed  |  
| `.getFunctionName()`  | `String`  | The function that was not allowed  |  
| `.getTargetName()`  | `String`  | The target resource that was not accessible  |  
Example

```java
try {
    db.query("SELECT * FROM protected_table");
} catch (NotAllowedException e) {
    if (e.isTokenExpired()) {
        db.signin(new RootCredential("root", "root"));
    }
}
```

* * *
##  `QueryException`[](https://surrealdb.com/docs/reference/java/api/errors#query-exception)
Thrown when a query fails to execute. Extends `ServerException`.
###  Additional methods[](https://surrealdb.com/docs/reference/java/api/errors#additional-methods-2)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.isNotExecuted()`  | `boolean`  | Whether the query was not executed  |  
| `.isTimedOut()`  | `boolean`  | Whether the query timed out  |  
| `.isCancelled()`  | `boolean`  | Whether the query was cancelled  |  
| `.getTimeout()`  | `Map<String, Object>`  | The timeout details if the query timed out  |  
Example

```java
try {
    db.query("SELECT * FROM large_table TIMEOUT 1s");
} catch (QueryException e) {
    if (e.isTimedOut()) {
        System.err.println("Query timed out: " + e.getTimeout());
    }
}
```

* * *
##  `AlreadyExistsException`[](https://surrealdb.com/docs/reference/java/api/errors#already-exists-exception)
Thrown when attempting to create a resource that already exists. Extends `ServerException`.
###  Additional methods[](https://surrealdb.com/docs/reference/java/api/errors#additional-methods-3)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getRecordId()`  | `String`  | The record ID that already exists  |  
| `.getTableName()`  | `String`  | The table containing the duplicate  |  
| `.getSessionId()`  | `String`  | The session ID that already exists  |  
| `.getNamespaceName()`  | `String`  | The namespace that already exists  |  
| `.getDatabaseName()`  | `String`  | The database that already exists  |  
Example

```java
try {
    db.create(Person.class, new RecordId("person", "alice"), person);
} catch (AlreadyExistsException e) {
    String recordId = e.getRecordId();
}
```

* * *
##  `ValidationException`[](https://surrealdb.com/docs/reference/java/api/errors#validation-exception)
Thrown when data validation fails. Extends `ServerException`. No additional methods.
* * *
##  `ConfigurationException`[](https://surrealdb.com/docs/reference/java/api/errors#configuration-exception)
Thrown when there is a configuration error. Extends `ServerException`. No additional methods.
* * *
##  `SerializationException`[](https://surrealdb.com/docs/reference/java/api/errors#serialization-exception)
Thrown when serialization or deserialization fails. Extends `ServerException`. No additional methods.
* * *
##  `InternalException`[](https://surrealdb.com/docs/reference/java/api/errors#internal-exception)
Thrown for internal server errors. Extends `ServerException`. No additional methods.
* * *
##  `ThrownException`[](https://surrealdb.com/docs/reference/java/api/errors#thrown-exception)
Thrown when a SurrealQL [`THROW`](https://surrealdb.com/docs/reference/query-language/statements/throw) statement is executed. Extends `ServerException`. No additional methods.
Example

```java
try {
    db.query("THROW 'custom error message'");
} catch (ThrownException e) {
    System.err.println("SurrealQL threw: " + e.getMessage());
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/errors#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal) — Connection and method reference
  * •
[Error handling](https://surrealdb.com/docs/reference/java/concepts/error-handling) — Error handling concepts and patterns
  * •
[SurrealQL THROW](https://surrealdb.com/docs/reference/query-language/statements/throw) — Throwing custom errors from queries
