---
title: "https://surrealdb.com/docs/reference/golang/concepts/authentication"
url: "https://surrealdb.com/docs/reference/golang/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/authentication

Source: https://surrealdb.com/docs/reference/golang/concepts/authentication

The Go SDK supports signing in at different access levels, signing up record users, and managing authentication tokens. Authentication is required before most operations and determines what data the connection can access.
This page covers the different authentication levels, how to use refresh tokens, and how to manage authentication state on a connection.
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.SignIn(ctx, authData)`](https://surrealdb.com/docs/reference/golang/api/core/db#signin)  | Signs in an existing user and returns a JWT token  |  
| [`db.SignInWithRefresh(ctx, authData)`](https://surrealdb.com/docs/reference/golang/api/core/db#signinwithrefresh)  | Signs in and returns both an access token and a refresh token  |  
| [`db.SignUp(ctx, authData)`](https://surrealdb.com/docs/reference/golang/api/core/db#signup)  | Signs up a new record user and returns a JWT token  |  
| [`db.SignUpWithRefresh(ctx, authData)`](https://surrealdb.com/docs/reference/golang/api/core/db#signupwithrefresh)  | Signs up a new record user and returns both tokens  |  
| [`db.Authenticate(ctx, token)`](https://surrealdb.com/docs/reference/golang/api/core/db#authenticate)  | Authenticates the connection with a JWT token  |  
| [`db.Invalidate(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/db#invalidate)  | Invalidates the current authentication  |  
| [`db.Info(ctx)`](https://surrealdb.com/docs/reference/golang/api/core/db#info)  | Returns the record of the currently authenticated user  |  
##  Authentication levels[](https://surrealdb.com/docs/reference/golang/concepts/authentication#authentication-levels)
SurrealDB supports four authentication levels. The fields you provide in the authentication data determine which level is used.  
| Level  | Required fields  | Access to  |  
| --- | --- | --- |  
| Root  |  `Username`, `Password`  | All namespaces and databases  |  
| Namespace  |  `Namespace`, `Username`, `Password`  | All databases in the namespace  |  
| Database  |  `Namespace`, `Database`, `Username`, `Password`  | A single database  |  
| Record  |  `Namespace`, `Database`, `Access`, `Username`, `Password`  | Records determined by the access method  |  
You can provide credentials using either the [`Auth`](https://surrealdb.com/docs/reference/golang/api/types#auth) struct or a `map[string]any`.
##  Signing in as a system user[](https://surrealdb.com/docs/reference/golang/concepts/authentication#signing-in-as-a-system-user)
To sign in as a root, namespace, or database user, provide the appropriate fields. The level is determined by which fields are set.

```go
token, err := db.SignIn(ctx, surrealdb.Auth{
	Username: "root",
	Password: "root",
})
```

```go
token, err := db.SignIn(ctx, surrealdb.Auth{
	Namespace: "my_ns",
	Database:  "my_db",
	Username:  "db_user",
	Password:  "db_pass",
})
```

##  Signing in as a record user[](https://surrealdb.com/docs/reference/golang/concepts/authentication#signing-in-as-a-record-user)
Record-level authentication requires the `Access` field, which specifies which [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access) method to use.

```go
token, err := db.SignIn(ctx, surrealdb.Auth{
	Namespace: "my_ns",
	Database:  "my_db",
	Access:    "user_access",
	Username:  "tobie",
	Password:  "s3cret",
})
```

You can also use a `map[string]any` to pass additional fields required by the access method:

```go
token, err := db.SignIn(ctx, map[string]any{
	"NS":   "my_ns",
	"DB":   "my_db",
	"AC":   "user_access",
	"user": "tobie",
	"pass": "s3cret",
})
```

##  Signing up new record users[](https://surrealdb.com/docs/reference/golang/concepts/authentication#signing-up-new-record-users)
The `.SignUp()` method creates a new record user using a `DEFINE ACCESS ... TYPE RECORD` access method. The access method must be defined before calling `.SignUp()`.

```go
token, err := db.SignUp(ctx, map[string]any{
	"NS":    "my_ns",
	"DB":    "my_db",
	"AC":    "user_access",
	"user":  "new_user",
	"pass":  "s3cret",
	"email": "user@example.com",
})
```

##  Using refresh tokens[](https://surrealdb.com/docs/reference/golang/concepts/authentication#using-refresh-tokens)
SurrealDB v3 supports refresh tokens for `TYPE RECORD` access methods that have `WITH REFRESH` enabled. Use `.SignInWithRefresh()` or `.SignUpWithRefresh()` to receive both an access token and a refresh token.

```go
tokens, err := db.SignInWithRefresh(ctx, map[string]any{
	"NS":   "my_ns",
	"DB":   "my_db",
	"AC":   "user_access",
	"user": "tobie",
	"pass": "s3cret",
})
```

The returned [`Tokens`](https://surrealdb.com/docs/reference/golang/api/types#tokens) contains an `Access` field (JWT) and a `Refresh` field. To obtain new tokens without re-entering credentials, pass the refresh token:

```go
newTokens, err := db.SignInWithRefresh(ctx, map[string]any{
	"NS":      "my_ns",
	"DB":      "my_db",
	"AC":      "user_access",
	"refresh": tokens.Refresh,
})
```

Note
Refresh tokens are only available with `TYPE RECORD` access methods that have `WITH REFRESH` enabled (SurrealDB v3+).
##  Using bearer access[](https://surrealdb.com/docs/reference/golang/concepts/authentication#using-bearer-access)
For `TYPE BEARER` access methods (SurrealDB v3+), use the `key` parameter with a bearer key obtained from `ACCESS ... GRANT`. No username or password is required.

```go
token, err := db.SignIn(ctx, map[string]any{
	"NS":  "my_ns",
	"DB":  "my_db",
	"AC":  "bearer_api",
	"key": bearerKey,
})
```

##  Authenticating with an existing token[](https://surrealdb.com/docs/reference/golang/concepts/authentication#authenticating-with-an-existing-token)
Use `.Authenticate()` to apply a previously obtained JWT to the connection. This is useful when restoring a session from a stored token or transferring authentication to a new connection.

```go
if err := db.Authenticate(ctx, token); err != nil {
	log.Fatal(err)
}
```

##  Invalidating authentication[](https://surrealdb.com/docs/reference/golang/concepts/authentication#invalidating-authentication)
Call `.Invalidate()` to remove the current authentication from the connection. After calling this, the connection returns to an unauthenticated state.

```go
if err := db.Invalidate(ctx); err != nil {
	log.Fatal(err)
}
```

##  Retrieving user information[](https://surrealdb.com/docs/reference/golang/concepts/authentication#retrieving-user-information)
The `.Info()` method returns the record of the currently authenticated user. This is only available when signed in as a record user.

```go
info, err := db.Info(ctx)
if err != nil {
	log.Fatal(err)
}
fmt.Println(info)
```

##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/authentication#learn-more)
  * •
[DB API reference](https://surrealdb.com/docs/reference/golang/api/core/db) for complete method signatures and parameters
  * •
[Types reference](https://surrealdb.com/docs/reference/golang/api/types) for `Auth` and `Tokens` type definitions
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb) for connection protocols and their effect on authentication
  * •
[DEFINE ACCESS statement](https://surrealdb.com/docs/reference/query-language/statements/define/access) for configuring access methods
  * •
[Security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices) for token and session duration configuration
