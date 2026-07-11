---
title: "https://surrealdb.com/docs/reference/java/concepts/authentication"
url: "https://surrealdb.com/docs/reference/java/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/concepts/authentication

Source: https://surrealdb.com/docs/reference/java/concepts/authentication

The Java SDK supports signing in as a root, namespace, database, or [record-level user](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users). After signing in, the connection is [authenticated](https://surrealdb.com/docs/learn/security/authentication/authentication) for all subsequent operations until the session is invalidated or the connection is closed.
You can configure authentication in your SurrealDB database using the [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) or [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access) statements.
##  API References[](https://surrealdb.com/docs/reference/java/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.signin(credential)`](https://surrealdb.com/docs/reference/java/api/core/surreal#signin)  | Authenticates with the provided credentials  |  
| [`db.signup(credential)`](https://surrealdb.com/docs/reference/java/api/core/surreal#signup)  | Signs up a new record user  |  
| [`db.authenticate(token)`](https://surrealdb.com/docs/reference/java/api/core/surreal#authenticate)  | Authenticates with a JWT token  |  
| [`db.invalidate()`](https://surrealdb.com/docs/reference/java/api/core/surreal#invalidate)  | Invalidates the current authentication  |  
##  Signing in as a system user[](https://surrealdb.com/docs/reference/java/concepts/authentication#signing-in-as-a-system-user)
[System users](https://surrealdb.com/docs/learn/security/authentication/authentication#system-user) are defined with the [`DEFINE USER`](https://surrealdb.com/docs/reference/query-language/statements/define/user) statement and have access at the root, namespace, or database level. Use the corresponding [credential class](https://surrealdb.com/docs/reference/java/api/types) to sign in.

```java
import com.surrealdb.signin.RootCredential;
import com.surrealdb.signin.NamespaceCredential;
import com.surrealdb.signin.DatabaseCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");

    // Root user — full access to the entire instance
    db.signin(new RootCredential("root", "root"));

    // Namespace user — access to all databases in the namespace
    db.signin(new NamespaceCredential("tobie", "123456", "surrealdb"));

    // Database user — access to a single database
    db.signin(new DatabaseCredential("tobie", "123456", "surrealdb", "docs"));
}
```

##  Signing in as a record user[](https://surrealdb.com/docs/reference/java/concepts/authentication#signing-in-as-a-record-user)
Record users authenticate against a [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access) method defined on a database. Use [`RecordCredential`](https://surrealdb.com/docs/reference/java/api/types#record-credential) with the access method name and any parameters required by the access definition.

```java
import com.surrealdb.signin.RecordCredential;

Map<String, Object> params = Map.of(
    "email", "info@surrealdb.com",
    "password", "123456"
);

Token token = db.signin(new RecordCredential(
    "surrealdb", "docs", "account", params
));
```

##  Signing up a record user[](https://surrealdb.com/docs/reference/java/concepts/authentication#signing-up-a-record-user)
The [`.signup()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signup) method registers a new record user through a record access method and returns a [`Token`](https://surrealdb.com/docs/reference/java/api/types#token). Signup is only available for record-level access.

```java
import com.surrealdb.signin.RecordCredential;

Map<String, Object> params = Map.of(
    "email", "newuser@surrealdb.com",
    "password", "s3cureP@ss"
);

Token token = db.signup(new RecordCredential(
    "surrealdb", "docs", "account", params
));
```

##  Using authentication tokens[](https://surrealdb.com/docs/reference/java/concepts/authentication#using-authentication-tokens)
The [`.signin()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signin) and [`.signup()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signup) methods return a [`Token`](https://surrealdb.com/docs/reference/java/api/types#token) object. Use `.getAccess()` to retrieve the JWT [access token](https://surrealdb.com/docs/learn/security/authentication/authentication#token) and `.getRefresh()` to retrieve the optional refresh token. You can store these tokens and use them later to re-authenticate without credentials.

```java
Token token = db.signin(new RootCredential("root", "root"));

String accessToken = token.getAccess();
String refreshToken = token.getRefresh();

// Later, re-authenticate with the stored token
db.authenticate(accessToken);
```

##  Authenticating with a bearer token[](https://surrealdb.com/docs/reference/java/concepts/authentication#authenticating-with-a-bearer-token)
If you have a bearer key — for example, one defined with a bearer access method — use [`BearerCredential`](https://surrealdb.com/docs/reference/java/api/types#bearer-credential) to authenticate.

```java
import com.surrealdb.signin.BearerCredential;

db.signin(new BearerCredential("eyJhbGciOiJIUzI1NiIs..."));
```

##  Invalidating authentication[](https://surrealdb.com/docs/reference/java/concepts/authentication#invalidating-authentication)
The [`.invalidate()`](https://surrealdb.com/docs/reference/java/api/core/surreal#invalidate) method clears the authentication state for the current connection. After invalidation, subsequent operations execute as an unauthenticated user.

```java
db.invalidate();
```

##  Learn more[](https://surrealdb.com/docs/reference/java/concepts/authentication#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/java/api/core/surreal) for method signatures
  * •
[Java Types reference](https://surrealdb.com/docs/reference/java/api/types) for credential class details
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for connection setup
  * •
[DEFINE USER](https://surrealdb.com/docs/reference/query-language/statements/define/user) for configuring system users
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) for configuring record access
  * •
[Security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices) for token management
  * •
[SurrealDB authentication overview](https://surrealdb.com/docs/learn/security/authentication/authentication) for system users, record users, and token concepts
