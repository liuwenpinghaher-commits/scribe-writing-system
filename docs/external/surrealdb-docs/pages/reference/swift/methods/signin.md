---
title: "https://surrealdb.com/docs/reference/swift/methods/signin"
url: "https://surrealdb.com/docs/reference/swift/methods/signin"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/signin

Source: https://surrealdb.com/docs/reference/swift/methods/signin

Signs this connection in to a specific authentication level and returns the issued tokens.
Method Syntax

```swift
let tokens = try await client.signin(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/signin#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  |  The credentials to authenticate with: one of `.root`, `.namespace`, `.database`, `.accessVariables`or `.accessBearer`.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/signin#example-usage)

```swift
// Root user
let tokens = try await client.signin(.root(username: "root",
    password: "root"))

// Database user
let tokens = try await client.signin(.database(
    namespace: "myapp",
    database: "mydb",
    username: "db_user",
    password: "secret"
))

// Record access with variables
let tokens = try await client.signin(.accessVariables(
    namespace: "myapp",
    database: "mydb",
    access: "account",
        variables: ["email": .string("user@example.com"),
        "pass": .string("secret")]
))
```

See [Authentication](https://surrealdb.com/docs/reference/swift/concepts/authentication) for every supported credentials variant.
