---
title: "https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis"
url: "https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis

Source: https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis

SurrealDB allows you to define custom [API endpoints](https://surrealdb.com/docs/reference/query-language/statements/define/api) that expose database operations through HTTP-style routes. The JavaScript SDK provides the `.api()` method to invoke these endpoints with full type safety, custom headers, and structured responses.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` db.api(prefix?) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api)  | Creates a SurrealApi instance for invoking user-defined endpoints  |  
| [` api.get(path) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#get)  | Invokes a GET endpoint  |  
| [` api.post(path, body?) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#post)  | Invokes a POST endpoint  |  
| [` api.invoke(path, request?) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#invoke)  | Invokes an endpoint with a custom request object  |  
##  Accessing API endpoints[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#accessing-api-endpoints)
To invoke user-defined endpoints, call `.api()` on any `Surreal`, `SurrealSession`, or `SurrealTransaction` instance. The returned [`SurrealApi`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api) object exposes HTTP-style methods like `.get()`, `.post()`, `.put()`, `.delete()`, and `.patch()`.

```ts
// Obtain the API reference
const api = db.api();

// Execute a GET request
const users = await api.get('/users').value();

// Execute a POST request
const newUser = await api.post('/users', {
    name: 'John Doe',
    email: 'john@example.com',
}).value();
```

By default, API calls return a response object containing `body`, `status`, and `headers`. Chaining `.value()` returns only the response body directly.

```ts
const response = await api.get('/users');

console.log(response.status);	// 200
console.log(response.headers);	// { 'content-type': 'application/json' }
console.log(response.body);	// [ { id: RecordId, name: 'John Doe', email: 'john@example.com' } ]

const users = await api.get('/users').value();

console.log(users); // [ { id: RecordId, name: 'John Doe', email: 'john@example.com' } ]
```

##  Defining type-safe APIs[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#defining-type-safe-apis)
You can define TypeScript types for your API paths to get compile-time type checking on both request bodies and responses. Each path maps HTTP methods to a tuple of `[RequestBody, ResponseBody]`.

```ts
// Define API types using an object literal
type MyApi = {
    '/users': {
        get: [void, User[]];
        post: [CreateUserInput, User];
    };
    [K: `/users/${string}`]: {
        get: [void, User];
        put: [UpdateUserInput, User];
        delete: [void, void];
    };
};

// Pass the custom API types to the .api() method
const api = db.api<MyApi>();

// All handlers will now be type-safe
const users: User[] = await api.get('/users').value();
```

##  Setting request headers[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#setting-request-headers)
You can set headers on individual requests by chaining `.header()`, or set default headers on the API instance using `api.header()`. Setting a header value to `null` removes it.

```ts
// Single-request header
const result = await api.get('/protected')
    .header('X-Custom-Header', 'value')
    .value();

// Global header
api.header('Content-Type', 'application/json');

// Remove global header
api.header('Content-Type', null);
```

##  Using a path prefix[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#using-a-path-prefix)
When working with a group of related endpoints, you can pass a prefix to `.api()`. All subsequent calls will be relative to that prefix.

```ts
const usersApi = db.api<UserPaths>('/users');

const allUsers = await usersApi.get('/').value();
const user = await usersApi.get('/123').value();
```

##  Handling API errors[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#handling-api-errors)
When an API call fails, the SDK throws an [`UnsuccessfulApiError`](https://surrealdb.com/docs/reference/javascript/api/errors#unsuccessfulapierror). This error includes the path, HTTP method, and the full response object.

```ts
import { UnsuccessfulApiError } from 'surrealdb';

try {
    await api.get('/users/999').value();
} catch (error) {
    if (error instanceof UnsuccessfulApiError) {
        console.error(`${error.method} ${error.path} failed`);
        console.error('Status:', error.response.status);
    }
}
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/invoking-apis#learn-more)
  * •
[SurrealApi API reference](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api) for the complete list of methods and type parameters
  * •
[ApiPromise API reference](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise) for response configuration options
  * •
[DEFINE API](https://surrealdb.com/docs/reference/query-language/statements/define/api) for defining custom API endpoints in SurrealQL
