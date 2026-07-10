---
title: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-api"
url: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/core/surreal-api

Source: https://surrealdb.com/docs/reference/javascript/api/core/surreal-api

The `SurrealApi` class exposes methods to interact with user-defined API endpoints in SurrealDB. It provides type-safe HTTP-style methods (GET, POST, PUT, DELETE, PATCH, TRACE) for invoking custom database APIs.
**Source:** [api/api.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/api/api.ts)
##  Overview[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#overview)
SurrealApi allows you to access custom API endpoints defined in your SurrealDB database. The class supports type-safe API definitions for better development experience.

```ts
// Define your API paths with types
type MyPaths = {
    "/users": { get: [void, User[]] };
    "/users/:id": { get: [void, User] };
    "/users": { post: [CreateUserInput, User] };
};

// Access with type safety
const api = db.api<MyPaths>();
const users = await api.get("/users"); // Type: User[]
```

##  Creating an API instance[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#creating-an-api-instance)
API instances are created through the [`api`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api) property on [`Surreal`](https://surrealdb.com/docs/reference/javascript/api/core/surreal), [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session), or [`SurrealTransaction`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction):

```ts
// Basic API access
const api = db.api();

// Type-safe API access
const api = db.api<MyPaths>();

// API with path prefix
const usersApi = db.api<MyPaths>("/users");
```

##  Type definitions[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#type-definitions)
###  `PathDef`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#pathdef)
Defines the HTTP methods available for an API path:

```ts
type PathDef = Partial<Record<HttpMethod, MethodDef>>;
type HttpMethod = "get" | "post" | "put" | "delete" | "patch" | "trace";
type MethodDef = [RequestBody, ResponseBody] | [];
```

###  Example path definitions[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example-path-definitions)

```ts
type MyApiPaths = {
    // GET endpoint with no request body, returns User[]
    "/users": {
        get: [void, User[]];
        post: [CreateUserRequest, User];
    };
    
    // Dynamic path parameters
    [K: `/users/${string}`]: {
        get: [void, User];
        put: [UpdateUserRequest, User];
        delete: [void, void];
    };
    
    // POST endpoint with request/response bodies
    "/auth/login": {
        post: [{ email: string; password: string }, { token: string }];
    };
};
```

##  Methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#methods)
###  `.header()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#header)
Configure a header for all requests sent by this API instance. Useful for setting common headers like authentication tokens or content types.
Method Syntax

```ts
api.header(name, value)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The name of the header to configure.  |  
| `value`  | `string | null`  |  The value to set, or `null`to remove the header.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns)
`void`
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#examples)
Set Custom Header

```ts
api.header('X-API-Key', 'my-secret-key');
```

Remove Header

```ts
api.header('X-API-Key', null);
```

Set Authorization Header

```ts
api.header('Authorization', `Bearer ${token}`);
```

###  `.invoke()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#invoke)
Invoke a user-defined API with a custom request object. This is the generic method used by all HTTP method-specific functions.
> !NOTE: Tip  
>  Prefer using method-specific functions ([`.get()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#get), [`.post()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#post), etc.) for better type safety.
Method Syntax

```ts
api.invoke<T>(path, request?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `string`  | The API path to invoke.  |  
| `request`  |  [ApiRequest](https://surrealdb.com/docs/reference/javascript/api/types/#apirequest)T  | The request configuration object.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-1)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the API response
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example)

```ts
const result = await api.invoke('/custom', {
    method: 'post',
    body: { data: 'value' },
    headers: { 'X-Custom': 'header' },
    query: { filter: 'active' }
});
```

###  `.get()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#get)
Invoke a user-defined GET API endpoint.
Method Syntax

```ts
api.get(path)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "get">`  | The API path to invoke.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-2)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the GET response
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#examples-1)
Get All Users

```ts
const users = await api.get("/users");
```

Get Specific User

```ts
const user = await api.get("/users/123");
```

###  `.post()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#post)
Invoke a user-defined POST API endpoint.
Method Syntax

```ts
api.post(path, body?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "post">`  | The API path to invoke.  |  
| `body`  | `RequestBody<TPaths, P, "post">`  | The request body to send.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-3)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the POST response
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example-1)

```ts
const newUser = await api.post("/users", {
    name: "John Doe",
    email: "john@example.com"
});
```

###  `.put()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#put)
Invoke a user-defined PUT API endpoint.
Method Syntax

```ts
api.put(path, body?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "put">`  | The API path to invoke.  |  
| `body`  | `RequestBody<TPaths, P, "put">`  | The request body to send.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-4)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the PUT response
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example-2)

```ts
const updated = await api.put("/users/123", {
    name: "John Smith",
    email: "john.smith@example.com"
});
```

###  `.delete()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#delete)
Invoke a user-defined DELETE API endpoint.
Method Syntax

```ts
api.delete(path, body?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "delete">`  | The API path to invoke.  |  
| `body`  | `RequestBody<TPaths, P, "delete">`  | Optional request body.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-5)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the DELETE response
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example-3)

```ts
await api.delete("/users/123");
```

###  `.patch()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#patch)
Invoke a user-defined PATCH API endpoint.
Method Syntax

```ts
api.patch(path, body?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "patch">`  | The API path to invoke.  |  
| `body`  | `RequestBody<TPaths, P, "patch">`  | The partial updates to apply.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-6)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the PATCH response
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#example-4)

```ts
const updated = await api.patch("/users/123", {
    email: "newemail@example.com"
});
```

###  `.trace()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#trace)
Invoke a user-defined TRACE API endpoint.
Method Syntax

```ts
api.trace(path, body?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `path`  | `P extends ValidPaths<TPaths, "trace">`  | The API path to invoke.  |  
| `body`  | `RequestBody<TPaths, P, "trace">`  | Optional request body.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#returns-7)
[`ApiPromise`](/docs/reference/javascript/api/queries/api-promise) - A promise for the TRACE response
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#complete-examples)
###  Basic API usage[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#basic-api-usage)

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Get API instance
const api = db.api();

// Make API calls
const users = await api.get('/users');
const user = await api.get('/users/123');
const created = await api.post('/users', {
    name: 'New User',
    email: 'user@example.com'
});
```

###  Type-safe API[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#type-safe-api)

```ts
// Define your API contract
type ApiPaths = {
    "/users": {
        get: [void, User[]];
        post: [CreateUserRequest, User];
    };
    [K: `/users/${string}`]: {
        get: [void, User];
        put: [UpdateUserRequest, User];
        delete: [void, void];
    };
    "/auth/login": {
        post: [LoginRequest, LoginResponse];
    };
};

// Create type-safe API instance
const api = db.api<ApiPaths>();

// All calls are type-checked
const users: User[] = await api.get("/users");
const user: User = await api.get("/users/123");
const newUser: User = await api.post("/users", {
    name: "Alice",
    email: "alice@example.com"
});
```

###  Using headers[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#using-headers)

```ts
const api = db.api();

// Set authentication header
const token = await login();
api.header('Authorization', `Bearer ${token}`);

// All subsequent requests include the header
const protected Data = await api.get('/protected-endpoint');

// Remove header
api.header('Authorization', null);
```

###  API with prefix[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#api-with-prefix)

```ts
type UserPaths = {
    "/": { get: [void, User[]] };
    [K: `/${string}`]: {
        get: [void, User];
        put: [UpdateUserRequest, User];
        delete: [void, void];
    };
};

// Create API with prefix
const usersApi = db.api<UserPaths>("/users");

// Calls are prefixed automatically
const all Users = await usersApi.get("/");        // GET /users/
const user = await usersApi.get("/123");          // GET /users/123
const updated = await usersApi.put("/123", data); // PUT /users/123
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#error-handling)

```ts
const api = db.api();

try {
    const user = await api.get('/users/999');
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('API error:', error.message);
        console.error('Status code:', error.code);
    } else {
        console.error('Unexpected error:', error);
    }
}
```

###  With transaction[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#with-transaction)

```ts
const txn = await db.beginTransaction();

try {
    // API calls within transaction
    const api = txn.api();
    const user = await api.post('/users', userData);
    const profile = await api.post('/profiles', {
        userId: user.id,
        ...profileData
    });
    
    await txn.commit();
} catch (error) {
    await txn.cancel();
    throw error;
}
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#best-practices)
###  1. Define API types[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#1-define-api-types)
Always define types for your API paths for better developer experience:

```ts
// Good: Type-safe
type MyApi = {
    "/users": { get: [void, User[]] };
};
const api = db.api<MyApi>();

// Avoid: Untyped
const api = db.api();
```

###  2. Reuse API instances[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#2-reuse-api-instances)
Create and reuse API instances rather than creating new ones for each call:

```ts
// Good: Reuse instance
const api = db.api();
await api.get('/users');
await api.get('/posts');

// Avoid: Creating multiple instances
await db.api().get('/users');
await db.api().get('/posts');
```

###  3. Use prefixes for namespacing[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#3-use-prefixes-for-namespacing)
Use path prefixes to organize related endpoints:

```ts
const usersApi = db.api("/users");
const postsApi = db.api("/posts");

await usersApi.get("/123");  // GET /users/123
await postsApi.get("/456");  // GET /posts/456
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api#see-also)
  * •
[SurrealQueryable.api](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api) - Creating API instances
  * •
[ApiPromise](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise) - API response handling
  * •
[User-Defined APIs Guide](https://surrealdb.com/docs/reference/query-language/statements/define/api) - Defining APIs in SurrealDB
