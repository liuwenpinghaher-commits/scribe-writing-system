---
title: "https://surrealdb.com/docs/reference/swift/methods/signup"
url: "https://surrealdb.com/docs/reference/swift/methods/signup"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/signup

Source: https://surrealdb.com/docs/reference/swift/methods/signup

Signs a new record-access user up and returns the issued tokens.
Method Syntax

```swift
let tokens = try await client.signup(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/signup#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `credentials`  |  The record-access credentials to sign up with, created via `.accessRecord`.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/signup#example-usage)

```swift
let tokens = try await client.signup(.accessRecord(
    namespace: "myapp",
    database: "mydb",
    access: "account",
        variables: ["email": .string("new@example.com"),
        "pass": .string("secret")]
))
```

See [Authentication](https://surrealdb.com/docs/reference/swift/concepts/authentication) for more detail.
