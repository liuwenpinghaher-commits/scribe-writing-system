---
title: "https://surrealdb.com/docs/reference/rest-api"
url: "https://surrealdb.com/docs/reference/rest-api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rest-api

Source: https://surrealdb.com/docs/reference/rest-api

Any language or tool capable of making HTTP requests can interact with SurrealDB through this API. This is useful when an official SDK is not available for your stack, or when you need to integrate SurrealDB with infrastructure tooling, scripts, or third-party platforms.
##  What the API provides[](https://surrealdb.com/docs/reference/rest-api#what-the-api-provides)
  * •
**Query execution** — send SurrealQL statements over HTTP and receive results as JSON.
  * •
**Authentication** — sign in, sign up, and manage tokens via dedicated endpoints.
  * •
**CRUD operations** — create, read, update, and delete records using RESTful conventions.
  * •
**Health and status** — check whether the server is running and accepting connections.

##  Protocol details[](https://surrealdb.com/docs/reference/rest-api#protocol-details)
The full HTTP protocol reference, including request and response formats, authentication headers, and endpoint specifications, is available in the [HTTP protocol](https://surrealdb.com/docs/reference/rest-api/http-protocol) page.
##  Alternative access methods[](https://surrealdb.com/docs/reference/rest-api#alternative-access-methods)
If you prefer a richer client experience, SurrealDB also supports:
  * •
**WebSocket protocol** — persistent connections with real-time capabilities.
  * •
**Official SDKs** — language-specific clients for [JavaScript](https://surrealdb.com/docs/reference/javascript/overview), [Python](https://surrealdb.com/docs/reference/python), [Rust](https://surrealdb.com/docs/reference/rust/overview), [Go](https://surrealdb.com/docs/reference/golang), [Java](https://surrealdb.com/docs/reference/java), [.NET](https://surrealdb.com/docs/reference/dotnet), and [PHP](https://surrealdb.com/docs/reference/php).
