---
title: "https://surrealdb.com/docs/reference/swift/methods/authenticate"
url: "https://surrealdb.com/docs/reference/swift/methods/authenticate"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/methods/authenticate

Source: https://surrealdb.com/docs/reference/swift/methods/authenticate

Authenticates the current connection with a previously issued JWT access token.
Method Syntax

```swift
try await client.authenticate(token)
```

###  Arguments[](https://surrealdb.com/docs/reference/swift/methods/authenticate#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `token`  | The JWT access token to authenticate the connection with.  |  
###  Example usage[](https://surrealdb.com/docs/reference/swift/methods/authenticate#example-usage)

```swift
try await client.authenticate(tokens.access)
```

You can also resume a session by supplying a token through a [`SessionContext`](https://surrealdb.com/docs/reference/swift/concepts/authentication#resuming-a-session) when constructing the client.
