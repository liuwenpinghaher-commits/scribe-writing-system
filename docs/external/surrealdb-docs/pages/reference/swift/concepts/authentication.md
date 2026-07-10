---
title: "https://surrealdb.com/docs/reference/swift/concepts/authentication"
url: "https://surrealdb.com/docs/reference/swift/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/concepts/authentication

Source: https://surrealdb.com/docs/reference/swift/concepts/authentication

SurrealDB supports a number of methods for authenticating users and securing the database. The Swift SDK exposes these through [`signin`](https://surrealdb.com/docs/reference/swift/methods/signin), [`signup`](https://surrealdb.com/docs/reference/swift/methods/signup), [`authenticate`](https://surrealdb.com/docs/reference/swift/methods/authenticate) and [`invalidate`](https://surrealdb.com/docs/reference/swift/methods/invalidate).
##  Signing in[](https://surrealdb.com/docs/reference/swift/concepts/authentication#signing-in)
The `signin` method accepts a credentials enum describing the level you wish to authenticate at.
###  Root user[](https://surrealdb.com/docs/reference/swift/concepts/authentication#root-user)

```swift
let tokens = try await client.signin(.root(username: "root", password: "root"))
```

###  Namespace user[](https://surrealdb.com/docs/reference/swift/concepts/authentication#namespace-user)

```swift
let tokens = try await client.signin(.namespace(
    namespace: "myapp",
    username: "ns_user",
    password: "secret"
))
```

###  Database user[](https://surrealdb.com/docs/reference/swift/concepts/authentication#database-user)

```swift
let tokens = try await client.signin(.database(
    namespace: "myapp",
    database: "mydb",
    username: "db_user",
    password: "secret"
))
```

###  Record access with variables[](https://surrealdb.com/docs/reference/swift/concepts/authentication#record-access-with-variables)

```swift
let tokens = try await client.signin(.accessVariables(
    namespace: "myapp",
    database: "mydb",
    access: "account",
    variables: ["email": .string("user@example.com"), "pass": .string("secret")]
))
```

###  Bearer token access[](https://surrealdb.com/docs/reference/swift/concepts/authentication#bearer-token-access)

```swift
let tokens = try await client.signin(.accessBearer(
    namespace: "myapp",
    database: "mydb",
    access: "account",
    key: "bearer-token-value"
))
```

##  Signing up[](https://surrealdb.com/docs/reference/swift/concepts/authentication#signing-up)
New record-access users sign up with `signup`:

```swift
let tokens = try await client.signup(.accessRecord(
    namespace: "myapp",
    database: "mydb",
    access: "account",
    variables: ["email": .string("new@example.com"), "pass": .string("secret")]
))
```

##  Resuming a session[](https://surrealdb.com/docs/reference/swift/concepts/authentication#resuming-a-session)
You can re-authenticate an existing client with a previously issued access token:

```swift
try await client.authenticate(tokens.access)
```

Alternatively, provide a token when constructing the client through a `SessionContext`:

```swift
let client = try SurrealHTTPClient(
    endpoint: "http://localhost:8000",
    session: SessionContext(
        namespace: "myapp",
        database: "mydb",
        accessToken: "existing-jwt"
    )
)
```

##  Invalidating a session[](https://surrealdb.com/docs/reference/swift/concepts/authentication#invalidating-a-session)
To clear the current authentication state:

```swift
try await client.invalidate()
```
