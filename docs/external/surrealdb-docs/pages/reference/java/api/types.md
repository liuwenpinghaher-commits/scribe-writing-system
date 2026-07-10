---
title: "https://surrealdb.com/docs/reference/java/api/types"
url: "https://surrealdb.com/docs/reference/java/api/types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/types

Source: https://surrealdb.com/docs/reference/java/api/types

The SDK provides several supporting types for authentication, update operations, and relation modeling. These types are used as parameters to methods on the [`Surreal`](https://surrealdb.com/docs/reference/java/api/core/surreal) class.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Authentication types[](https://surrealdb.com/docs/reference/java/api/types#authentication-types)
###  `Credential`[](https://surrealdb.com/docs/reference/java/api/types#credential)
Interface. Base type for all credentials passed to [`signin()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signin) and [`signup()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signup).
###  `Signin`[](https://surrealdb.com/docs/reference/java/api/types#signin)
Interface. Extends `Credential`. Marker interface for sign-in credentials.
* * *
###  `RootCredential`[](https://surrealdb.com/docs/reference/java/api/types#root-credential)
Implements `Signin`. Authenticates as a root user.
Constructor

```java
RootCredential(String username, String password)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `username`  | `String`  | The root username.  |  
| `password`  | `String`  | The root password.  |  
####  Methods[](https://surrealdb.com/docs/reference/java/api/types#methods)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getUsername()`  | `String`  | The root username  |  
| `.getPassword()`  | `String`  | The root password  |  
Example

```java
db.signin(new RootCredential("root", "root"));
```

* * *
###  `NamespaceCredential`[](https://surrealdb.com/docs/reference/java/api/types#namespace-credential)
Extends `RootCredential`. Authenticates as a namespace user.
Constructor

```java
NamespaceCredential(String username, String password, String namespace)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `username`  | `String`  | The namespace username.  |  
| `password`  | `String`  | The namespace password.  |  
| `namespace`  | `String`  | The namespace to authenticate against.  |  
####  Additional method[](https://surrealdb.com/docs/reference/java/api/types#additional-method)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getNamespace()`  | `String`  | The target namespace  |  
Example

```java
db.signin(new NamespaceCredential("ns_user", "ns_pass", "surrealdb"));
```

* * *
###  `DatabaseCredential`[](https://surrealdb.com/docs/reference/java/api/types#database-credential)
Extends `NamespaceCredential`. Authenticates as a database user.
Constructor

```java
DatabaseCredential(String username, String password, String namespace, String database)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `username`  | `String`  | The database username.  |  
| `password`  | `String`  | The database password.  |  
| `namespace`  | `String`  | The namespace containing the database.  |  
| `database`  | `String`  | The database to authenticate against.  |  
####  Additional method[](https://surrealdb.com/docs/reference/java/api/types#additional-method-1)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getDatabase()`  | `String`  | The target database  |  
Example

```java
db.signin(new DatabaseCredential("db_user", "db_pass", "surrealdb", "docs"));
```

* * *
###  `RecordCredential`[](https://surrealdb.com/docs/reference/java/api/types#record-credential)
Implements `Credential`. Authenticates as a record user via an access method defined with [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access).
Constructors

```java
RecordCredential(String namespace, String database, String access, Object params)
RecordCredential(String access, Object params)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `namespace`  | `String`  | The namespace. Omit to use the session namespace.  |  
| `database`  | `String`  | The database. Omit to use the session database.  |  
| `access`  | `String`  | The access method name.  |  
| `params`  | `Object`  | Additional fields required by the access definition.  |  
####  Methods[](https://surrealdb.com/docs/reference/java/api/types#methods-1)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getNamespace()`  | `String`  | The target namespace  |  
| `.getDatabase()`  | `String`  | The target database  |  
| `.getAccess()`  | `String`  | The access method name  |  
| `.getParams()`  | `Object`  | The additional parameters  |  
Example

```java
Token token = db.signup(new RecordCredential(
    "surrealdb", "docs", "user_access",
    Map.of("email", "user@example.com", "password", "s3cret")
));
```

* * *
###  `BearerCredential`[](https://surrealdb.com/docs/reference/java/api/types#bearer-credential)
Implements `Credential`. Authenticates with an existing token.
Constructor

```java
BearerCredential(String token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `token`  | `String`  | A valid JWT token string.  |  
####  Method[](https://surrealdb.com/docs/reference/java/api/types#method)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getToken()`  | `String`  | The bearer token  |  
Example

```java
db.signin(new BearerCredential("eyJhbGciOiJIUzI1NiIs..."));
```

* * *
###  `Token`[](https://surrealdb.com/docs/reference/java/api/types#token)
Represents authentication tokens returned by [`signin()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signin) and [`signup()`](https://surrealdb.com/docs/reference/java/api/core/surreal#signup).
Constructors

```java
Token(String access, String refresh)
Token(String token)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `access`  | `String`  | The access token (JWT).  |  
| `refresh`  | `String`  |  The refresh token. May be `null`.  |  
| `token`  | `String`  | A single token string (legacy constructor).  |  
####  Methods[](https://surrealdb.com/docs/reference/java/api/types#methods-2)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getAccess()`  | `String`  | The access token (JWT)  |  
| `.getRefresh()`  | `String`  | The refresh token (may be `null`)  |  
| `.getToken()`  | `String`  | The access token  |  
Example

```java
Token token = db.signin(new RootCredential("root", "root"));
String jwt = token.getAccess();
String refresh = token.getRefresh();
```

* * *
##  Operation types[](https://surrealdb.com/docs/reference/java/api/types#operation-types)
###  `UpType`[](https://surrealdb.com/docs/reference/java/api/types#up-type)
Enum for [`update()`](https://surrealdb.com/docs/reference/java/api/core/surreal#update) and [`upsert()`](https://surrealdb.com/docs/reference/java/api/core/surreal#upsert) operation types.  
| Value  | Description  |  
| --- | --- |  
| `CONTENT`  | Replaces the entire record content  |  
| `MERGE`  | Merges fields with the existing record  |  
| `PATCH`  | Applies partial changes  |  
Example

```java
db.update(Person.class, new RecordId("person", "alice"), UpType.MERGE, updates);
```

* * *
##  Relation types[](https://surrealdb.com/docs/reference/java/api/types#relation-types)
###  `Relation`[](https://surrealdb.com/docs/reference/java/api/types#relation)
POJO base class for graph relations. Contains the standard relation fields. Used with [`relate()`](https://surrealdb.com/docs/reference/java/api/core/surreal#relate).
####  Fields[](https://surrealdb.com/docs/reference/java/api/types#fields)  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `RecordId`  | The relation record ID  |  
| `in`  | `RecordId`  | The source record  |  
| `out`  | `RecordId`  | The target record  |  
Example

```java
public class Likes extends Relation {
    public String createdAt;
}

Likes like = db.relate(Likes.class,
    new RecordId("person", "alice"),
    "likes",
    new RecordId("post", "post1")
);
```

* * *
###  `InsertRelation`[](https://surrealdb.com/docs/reference/java/api/types#insert-relation)
POJO for inserting relations. Uses `Id` instead of `RecordId` for the `id` field. Used with [`insertRelation()`](https://surrealdb.com/docs/reference/java/api/core/surreal#insert-relation).
####  Fields[](https://surrealdb.com/docs/reference/java/api/types#fields-1)  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `Id`  | The relation ID  |  
| `in`  | `RecordId`  | The source record  |  
| `out`  | `RecordId`  | The target record  |  
Example

```java
public class Likes extends InsertRelation {
    public String createdAt;
}

Likes like = new Likes();
like.in = new RecordId("person", "alice");
like.out = new RecordId("post", "post1");
like.createdAt = "2025-01-01T00:00:00Z";

Likes result = db.insertRelation(Likes.class, "likes", like);
```

* * *
##  Utility types[](https://surrealdb.com/docs/reference/java/api/types#utility-types)
###  `NsDb`[](https://surrealdb.com/docs/reference/java/api/types#ns-db)
Holds a namespace and database pair.
####  Methods[](https://surrealdb.com/docs/reference/java/api/types#methods-3)  
| Method  | Returns  | Description  |  
| --- | --- | --- |  
| `.getNamespace()`  | `String`  | The namespace  |  
| `.getDatabase()`  | `String`  | The database  |  
* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/types#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal) — Connection and method reference
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) — Authentication concepts and patterns
  * •
[Data manipulation](https://surrealdb.com/docs/reference/java/concepts/data-manipulation) — CRUD operation patterns
  * •
[DEFINE USER](https://surrealdb.com/docs/reference/query-language/statements/define/user) — System user definition for root, namespace, and database credentials
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) — Access method definition for record-level authentication
