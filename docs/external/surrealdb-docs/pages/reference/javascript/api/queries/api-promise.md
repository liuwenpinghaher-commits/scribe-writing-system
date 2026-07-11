---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/api-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/api-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/api-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/api-promise

The `ApiPromise` class provides an interface for executing user-defined API endpoint calls. It extends `Promise`, allowing you to `await` it directly or configure the response handling.
**Returned by:** Methods on [`SurrealApi`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api)
**Source:** [query/api.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/api.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#type-parameters)
  * •
`Req` - The request body type
  * •
`Res` - The response body type
  * •
`V` - Boolean for value-only response (default: `false`)
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#configuration-methods)
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#json)
Configure the query to return the result as a JSON string.
Method Syntax

```ts
apiPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns)
`ApiPromise` - Promise returning JSON string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#example)

```ts
const jsonString = await db.api().get('/users').json();
console.log(typeof jsonString); // 'string'
```

* * *
###  `.header()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#header)
Append a header to the API request.
Method Syntax

```ts
apiPromise.header(name, value)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The header name.  |  
| `value`  | `string`  | The header value.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns-1)
`ApiPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#example-1)

```ts
const result = await db.api().get('/users')
    .header('X-Custom-Header', 'value')
    .header('Authorization', 'Bearer token');
```

* * *
###  `.value()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#value)
Return only the response body value, without the wrapper object.
Method Syntax

```ts
apiPromise.value()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns-2)
`ApiPromise` - Promise returning only the value
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#examples)
Without .value()

```ts
const response = await db.api().get('/users');
console.log(response.body); // The actual data
console.log(response.status); // HTTP status
console.log(response.headers); // Response headers
```

With .value()

```ts
const users = await db.api().get('/users').value();
console.log(users); // Direct access to user array
```

* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#compile)
Compile the query into a BoundQuery.
Method Syntax

```ts
apiPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns-3)
`BoundQuery` - The compiled query
* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#stream)
Stream results as they are received.
Method Syntax

```ts
apiPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns-4)
`AsyncIterable` - Async iterable of response frames
* * *
###  `.query()`[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#query)
Append a URL query parameter to the API request.
Method Syntax

```ts
apiPromise.query(name, value)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The query parameter name.  |  
| `value`  | `string`  | The query parameter value.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#returns-5)
`ApiPromise` - A new ApiPromise with the query parameter appended
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#example-2)

```ts
const result = await db.api().get('/users')
    .query('filter', 'active')
    .query('sort', 'created_at')
    .value();
```

##  Response structure[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#response-structure)
###  Default response (without `.value()`)[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#default-response-without-value)

```ts
interface ApiResponse<T> {
    body?: T;
    headers?: Record<string, string>;
    status?: number;
}
```

###  Value response (with `.value()`)[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#value-response-with-value)

```ts
// Returns Res directly instead of ApiResponse<Res>
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#complete-examples)
###  Basic API calls[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#basic-api-calls)

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

const api = db.api();

// GET request
const users = await api.get('/users').value();

// POST request
const newUser = await api.post('/users', {
    name: 'John Doe',
    email: 'john@example.com'
}).value();

// PUT request
const updated = await api.put('/users/123', {
    name: 'John Smith'
}).value();

// DELETE request
await api.delete('/users/123').value();
```

###  With full response[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#with-full-response)

```ts
const response = await db.api().get('/users');

console.log('Status:', response.status);
console.log('Headers:', response.headers);
console.log('Body:', response.body);

if (response.status === 200) {
    console.log('Success:', response.body);
}
```

###  Custom headers[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#custom-headers)

```ts
const result = await db.api().post('/protected', data)
    .header('Authorization', `Bearer ${token}`)
    .header('X-API-Version', '2.0')
    .value();
```

###  Type-safe API calls[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#type-safe-api-calls)

```ts
interface User {
    id: string;
    name: string;
    email: string;
}

interface CreateUserRequest {
    name: string;
    email: string;
    password: string;
}

type ApiPaths = {
    "/users": {
        get: [void, User[]];
        post: [CreateUserRequest, User];
    };
};

const api = db.api<ApiPaths>();

// Type-safe calls
const users: User[] = await api.get('/users').value();
const newUser: User = await api.post('/users', {
    name: 'Alice',
    email: 'alice@example.com',
    password: 'secure'
}).value();
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#error-handling)

```ts
try {
    const user = await db.api().get('/users/999').value();
} catch (error) {
    if (error instanceof UnsuccessfulApiError) {
        console.error('API error:', error.response);
        console.error('Status:', error.response.status);
        console.error('Message:', error.response.body);
    }
}
```

###  Pagination[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#pagination)

```ts
async function fetchPage(page: number, pageSize: number) {
    return db.api().get(`/users?page=${page}&limit=${pageSize}`).value();
}

const page1 = await fetchPage(1, 20);
const page2 = await fetchPage(2, 20);
```

###  File upload[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#file-upload)

```ts
const formData = new FormData();
formData.append('file', fileBlob);
formData.append('name', 'profile-picture');

const result = await db.api().post('/upload', formData)
    .header('Content-Type', 'multipart/form-data')
    .value();
```

###  Authentication flow[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#authentication-flow)

```ts
// Login
const loginResult = await db.api().post('/auth/login', {
    email: 'user@example.com',
    password: 'password123'
}).value();

const { access_token } = loginResult;

// Use token for subsequent requests
const api = db.api();
api.header('Authorization', `Bearer ${access_token}`);

const profile = await api.get('/profile').value();
const orders = await api.get('/orders').value();
```

###  Conditional requests[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#conditional-requests)

```ts
const api = db.api();

// Check if resource exists
const checkResponse = await api.get('/users/123');

if (checkResponse.status === 404) {
    // Create if doesn't exist
    await api.post('/users/123', userData).value();
} else {
    // Update if exists
    await api.put('/users/123', userData).value();
}
```

###  Batch operations[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#batch-operations)

```ts
const api = db.api();

const promises = userIds.map(id =>
    api.get(`/users/${id}`).value()
);

const users = await Promise.all(promises);
console.log(`Fetched ${users.length} users`);
```

###  Response transformation[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#response-transformation)

```ts
const response = await db.api().get('/users');

const transformed = {
    data: response.body,
    timestamp: new Date(),
    status: response.status,
    cached: response.headers?.['X-Cache'] === 'HIT'
};
```

###  Retry pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#retry-pattern)

```ts
async function apiWithRetry(
    apiCall: () => Promise<any>,
    maxRetries = 3
) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await apiCall();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(r => setTimeout(r, 1000 * (i + 1)));
        }
    }
}

const result = await apiWithRetry(() =>
    db.api().get('/unstable-endpoint').value()
);
```

###  Query parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#query-parameters)

```ts
// Build query params manually
const params = new URLSearchParams({
    filter: 'active',
    sort: 'created_at',
    order: 'desc'
});

const users = await db.api().get(`/users?${params}`).value();
```

###  WebSocket vs API endpoints[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#websocket-vs-api-endpoints)

```ts
// Both use the same connection
const db = new Surreal();
await db.connect('ws://localhost:8000');

// Regular query (via WebSocket/HTTP RPC)
const users1 = await db.select(new Table('users'));

// API endpoint (via defined API routes)
const users2 = await db.api().get('/users').value();

// Both work, but API endpoints allow custom logic
```

##  Response headers[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#response-headers)

```ts
const response = await db.api().get('/users');

console.log('Content-Type:', response.headers?.['Content-Type']);
console.log('Cache-Control:', response.headers?.['Cache-Control']);
console.log('X-Custom:', response.headers?.['X-Custom-Header']);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#best-practices)
###  1. Use type definitions[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#1-use-type-definitions)

```ts
// Good: Type-safe API
type MyApi = {
    "/users": { get: [void, User[]] };
};
const api = db.api<MyApi>();

// Avoid: Untyped
const api = db.api();
```

###  2. Use .value() for simpler code[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#2-use-value-for-simpler-code)

```ts
// Good: Direct value access
const users = await api.get('/users').value();

// More verbose:
const response = await api.get('/users');
const users = response.body;
```

###  3. Handle errors gracefully[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#3-handle-errors-gracefully)

```ts
// Good: Specific error handling
try {
    const result = await api.get('/users').value();
} catch (error) {
    if (error instanceof UnsuccessfulApiError) {
        // Handle API errors
    }
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/api-promise#see-also)
  * •
[SurrealApi](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api) - API instance methods
  * •
[SurrealQueryable.api](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api) - Creating API instances
  * •
[User-Defined APIs](https://surrealdb.com/docs/reference/query-language/statements/define/api) - Defining APIs in SurrealDB
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
