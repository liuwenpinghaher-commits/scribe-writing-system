---
title: "https://surrealdb.com/docs/reference/python/concepts/authentication"
url: "https://surrealdb.com/docs/reference/python/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/concepts/authentication

Source: https://surrealdb.com/docs/reference/python/concepts/authentication

The Python SDK supports signing in as a root, namespace, database, or record-level user. After signing in, the connection is authenticated for all subsequent operations until the session is invalidated or the connection is closed.
This page covers how to sign in, sign up, manage tokens, and inspect the current user.
##  API references[](https://surrealdb.com/docs/reference/python/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`db.signin(vars)`](https://surrealdb.com/docs/reference/python/api/core/surreal#signin)  | Signs in as a root, namespace, database, or record user  |  
| [`db.signup(vars)`](https://surrealdb.com/docs/reference/python/api/core/surreal#signup)  | Signs up a new record user via an access method  |  
| [`db.authenticate(token)`](https://surrealdb.com/docs/reference/python/api/core/surreal#authenticate)  | Authenticates the connection with an existing JWT token  |  
| [`db.invalidate()`](https://surrealdb.com/docs/reference/python/api/core/surreal#invalidate)  | Invalidates the current authentication session  |  
| [`db.info()`](https://surrealdb.com/docs/reference/python/api/core/surreal#info)  | Returns the record data for the currently authenticated record user  |  
##  Signing in users[](https://surrealdb.com/docs/reference/python/concepts/authentication#signing-in-users)
The `.signin()` method authenticates the connection. The fields you pass determine the authentication level. The method returns [Tokens](https://surrealdb.com/docs/reference/python/api/types/#tokens) on success, which contain the JWT access token and optional refresh token.
Refer to the [API reference](https://surrealdb.com/docs/reference/python/api/core/surreal#signin) for the full list of parameters at each level.
Root userNamespace userDatabase userRecord access
A root user has full access to the SurrealDB instance. Only `username` and `password` are required.

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()

tokens = db.signin({
    "username": "root",
    "password": "root",
})
```

A namespace user has access to all databases within a specific namespace. Provide the `namespace` alongside credentials.

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()

tokens = db.signin({
    "namespace": "surrealdb",
    "username": "tobie",
    "password": "123456",
})
```

A database user has access to a single database. Provide both `namespace` and `database` alongside credentials.

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()

tokens = db.signin({
    "namespace": "surrealdb",
    "database": "docs",
    "username": "tobie",
    "password": "123456",
})
```

A record access user authenticates against a [`DEFINE ACCESS`](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) method defined on a database. Provide `namespace`, `database`, `access`, and any variables required by the access definition.

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()

tokens = db.signin({
    "namespace": "surrealdb",
    "database": "docs",
    "access": "account",
    "variables": {
        "email": "info@surrealdb.com",
        "password": "123456",
    },
})
```

All examples above use the synchronous API. The async variant works the same way — prefix each call with `await`.
##  Signing up users[](https://surrealdb.com/docs/reference/python/concepts/authentication#signing-up-users)
The `.signup()` method registers a new record user through a [record access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/record) and returns [Tokens](https://surrealdb.com/docs/reference/python/api/types/#tokens). Signup is only available for record-level access.
You must provide the `namespace`, `database`, and `access` fields, along with any `variables` expected by the access definition.
SynchronousAsynchronous

```python
from surrealdb import Surreal

db = Surreal("ws://localhost:8000")
db.connect()

tokens = db.signup({
    "namespace": "surrealdb",
    "database": "docs",
    "access": "account",
    "variables": {
        "email": "newuser@surrealdb.com",
        "password": "s3cureP@ss",
    },
})
```

```python
from surrealdb import AsyncSurreal

db = AsyncSurreal("ws://localhost:8000")
await db.connect()

tokens = await db.signup({
    "namespace": "surrealdb",
    "database": "docs",
    "access": "account",
    "variables": {
        "email": "newuser@surrealdb.com",
        "password": "s3cureP@ss",
    },
})
```

##  Authenticating with an existing token[](https://surrealdb.com/docs/reference/python/concepts/authentication#authenticating-with-an-existing-token)
If you already have a JWT token — for example, one returned from a previous `.signin()` or stored in a cookie — you can authenticate the connection directly with `.authenticate()`.
SynchronousAsynchronous

```python
db.authenticate("eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9...")
```

```python
await db.authenticate("eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9...")
```

This is useful in server-side applications where the token is passed from a client request and needs to be forwarded to the database connection.
##  Retrieving user information[](https://surrealdb.com/docs/reference/python/concepts/authentication#retrieving-user-information)
The `.info()` method returns the record data for the currently authenticated record user. This is only available when signed in as a record-level user.
SynchronousAsynchronous

```python
user = db.info()
print(user)
```

```python
user = await db.info()
print(user)
```

The return value is a [Value](https://surrealdb.com/docs/reference/python/api/types/#value) containing the fields of the authenticated user's record. If no record user is authenticated, the method returns `None`.
##  Signing out[](https://surrealdb.com/docs/reference/python/concepts/authentication#signing-out)
The `.invalidate()` method clears the authentication state for the current connection. After invalidation, subsequent operations will execute as an unauthenticated user.
SynchronousAsynchronous

```python
db.invalidate()
```

```python
await db.invalidate()
```

##  Learn more[](https://surrealdb.com/docs/reference/python/concepts/authentication#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/python/api/core/surreal) for complete method signatures and parameters
  * •
[Tokens type reference](https://surrealdb.com/docs/reference/python/api/types/#tokens) for the structure of the returned tokens
  * •
[Authentication in SurrealDB](https://surrealdb.com/docs/learn/security/authentication/authentication) for an overview of authentication concepts
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) for defining record and JWT access methods
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb) for connection setup and protocol options
