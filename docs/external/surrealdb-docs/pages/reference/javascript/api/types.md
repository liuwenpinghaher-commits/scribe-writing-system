---
title: "https://surrealdb.com/docs/reference/javascript/api/types"
url: "https://surrealdb.com/docs/reference/javascript/api/types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/types

Source: https://surrealdb.com/docs/reference/javascript/api/types

The SDK provides comprehensive TypeScript type definitions for type-safe development. This page documents the key types and interfaces used throughout the SDK.
##  Connection types[](https://surrealdb.com/docs/reference/javascript/api/types#connection-types)
###  `ConnectionStatus`[](https://surrealdb.com/docs/reference/javascript/api/types#connectionstatus)
Represents the current connection state.

```ts
type ConnectionStatus = "disconnected" | "connecting" | "reconnecting" | "connected"
```

**Example:**

```ts
if (db.status === "connected") {
    console.log('Ready to execute queries');
}
```

* * *
###  `DriverOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#driveroptions)
Configuration options for the Surreal driver.

```ts
interface DriverOptions {
    engines?: Engines;
    codecs?: Codecs;
    codecOptions?: CodecOptions;
    websocketImpl?: typeof WebSocket;
    fetchImpl?: typeof fetch;
}
```

**Properties:**
  * •
`engines` - Custom engine factories for different protocols
  * •
`codecs` - Custom codec factories for encoding/decoding
  * •
`codecOptions` - Options for codec behavior
  * •
`websocketImpl` - Custom WebSocket implementation
  * •
`fetchImpl` - Custom fetch implementation

**Example:**

```ts
const db = new Surreal({
    codecOptions: {
        useNativeDates: true
    }
});
```

* * *
###  `ConnectOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#connectoptions)
Options for establishing a connection.

```ts
interface ConnectOptions {
    namespace?: string;
    database?: string;
    authentication?: AuthProvider;
    versionCheck?: boolean;
    invalidateOnExpiry?: boolean;
    reconnect?: boolean | Partial<ReconnectOptions>;
    retry?: boolean | Partial<RetryOptions>;
}
```

**Properties:**
  * •
`namespace` - Namespace to use
  * •
`database` - Database to use
  * •
`authentication` - Authentication details or provider function
  * •
`versionCheck` - Enable version compatibility checking (default: true)
  * •
`invalidateOnExpiry` - Invalidate session on token expiry (default: false)
  * •
`reconnect` - Reconnection behavior configuration (default: true)
  * •
`retry` - Connection-wide default for retrying queries on write conflict (default: disabled)

**Example:**

```ts
await db.connect('ws://localhost:8000', {
    namespace: 'my_namespace',
    database: 'my_database',
    authentication: {
        username: 'root',
        password: 'root'
    },
    reconnect: {
        attempts: 10,
        retryDelay: 1000
    },
    retry: {
        enabled: true,
        attempts: 5,
        retryDelay: 100
    }
});
```

* * *
###  `ReconnectOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#reconnectoptions)
Configuration for automatic reconnection behavior.

```ts
interface ReconnectOptions {
    enabled: boolean;
    attempts: number;
    retryDelay: number;
    retryDelayMax: number;
    retryDelayMultiplier: number;
    retryDelayJitter: number;
    catch?: (error: Error) => boolean;
}
```

**Properties:**
  * •
`enabled` - Enable automatic reconnection
  * •
`attempts` - Maximum reconnection attempts (-1 for unlimited)
  * •
`retryDelay` - Initial delay before reconnecting (ms)
  * •
`retryDelayMax` - Maximum delay between attempts (ms)
  * •
`retryDelayMultiplier` - Multiply delay after each failed attempt
  * •
`retryDelayJitter` - Random offset percentage for delays
  * •
`catch` - Custom error handler for reconnection errors

* * *
###  `RetryOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#retryoptions)
Configuration for retrying a query, mutation, or transaction when it fails with a write conflict. Modeled on [`ReconnectOptions`](https://surrealdb.com/docs/reference/javascript/api/types#reconnectoptions), and applied the same way: as a connection-wide default via [`ConnectOptions.retry`](https://surrealdb.com/docs/reference/javascript/api/types#connectoptions), or per call via `.retry()`.

```ts
interface RetryOptions {
    enabled: boolean;
    attempts: number;
    retryDelay: number;
    retryDelayMax: number;
    retryDelayMultiplier: number;
    retryDelayJitter: number;
    retryable?: (error: Error) => boolean;
}
```

**Properties:**
  * •
`enabled` - Enable retrying on write conflict
  * •
`attempts` - Maximum retry attempts
  * •
`retryDelay` - Initial delay before retrying (ms)
  * •
`retryDelayMax` - Maximum delay between attempts (ms)
  * •
`retryDelayMultiplier` - Multiply delay after each failed attempt
  * •
`retryDelayJitter` - Random offset percentage for delays
  * •
`retryable` - Custom predicate deciding whether an error should be retried (default: [`isRetryableConflict`](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict))

Retry is off by default. Passing an options object, or calling `.retry()` with no arguments, opts a query, mutation, or transaction in. Retrying a non-atomic multi-statement query can apply some statements more than once, so it must always be enabled explicitly.
**Example:**

```ts
// Connection-wide default
await db.connect('ws://localhost:8000', {
    retry: { enabled: true, attempts: 5, retryDelay: 100 }
});

// Per-query override
const [n] = await db
    .query<[number]>('UPDATE counter:c SET n += 1 RETURN n')
    .retry({ attempts: 3 })
    .collect();
```

* * *
###  `VersionInfo`[](https://surrealdb.com/docs/reference/javascript/api/types#versioninfo)
SurrealDB version information.

```ts
interface VersionInfo {
    version: string;
}
```

**Example:**

```ts
const info = await db.version();
console.log(info.version); // "surrealdb-2.1.0"
```

##  Authentication types[](https://surrealdb.com/docs/reference/javascript/api/types#authentication-types)
###  `AnyAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#anyauth)
Union type for all authentication methods.

```ts
type AnyAuth = SystemAuth | AccessAuth
```

* * *
###  `SystemAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#systemauth)
Union of system-level authentication types.

```ts
type SystemAuth = RootAuth | NamespaceAuth | DatabaseAuth
```

* * *
###  `RootAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#rootauth)
Root-level authentication.

```ts
interface RootAuth {
    username: string;
    password: string;
}
```

**Example:**

```ts
await db.signin({
    username: 'root',
    password: 'root'
});
```

* * *
###  `NamespaceAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#namespaceauth)
Namespace-level authentication.

```ts
interface NamespaceAuth {
    namespace: string;
    username: string;
    password: string;
}
```

**Example:**

```ts
await db.signin({
    namespace: 'my_namespace',
    username: 'ns_user',
    password: 'ns_pass'
});
```

* * *
###  `DatabaseAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#databaseauth)
Database-level authentication.

```ts
interface DatabaseAuth {
    namespace: string;
    database: string;
    username: string;
    password: string;
}
```

**Example:**

```ts
await db.signin({
    namespace: 'my_namespace',
    database: 'my_database',
    username: 'db_user',
    password: 'db_pass'
});
```

* * *
###  `AccessAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#accessauth)
Union of access-based authentication types.

```ts
type AccessAuth = AccessSystemAuth | AccessBearerAuth | AccessRecordAuth
```

* * *
###  `AccessSystemAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#accesssystemauth)
System access authentication with credentials.

```ts
interface AccessSystemAuth {
    namespace: string;
    database: string;
    access: string;
    username: string;
    password: string;
}
```

* * *
###  `AccessBearerAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#accessbearerauth)
Bearer token access authentication.

```ts
interface AccessBearerAuth {
    namespace: string;
    database: string;
    access: string;
    token: string;
}
```

* * *
###  `AccessRecordAuth`[](https://surrealdb.com/docs/reference/javascript/api/types#accessrecordauth)
Record user authentication via access methods.

```ts
interface AccessRecordAuth {
    namespace: string;
    database: string;
    access: string;
    variables?: Record<string, unknown>;
}
```

**Example:**

```ts
await db.signup({
    namespace: 'my_namespace',
    database: 'my_database',
    access: 'user_access',
    variables: {
        email: 'user@example.com',
        password: 'password123'
    }
});
```

* * *
###  `Token`[](https://surrealdb.com/docs/reference/javascript/api/types#token)
A string alias representing an authentication token (JWT).

```ts
type Token = string
```

* * *
###  `Tokens`[](https://surrealdb.com/docs/reference/javascript/api/types#tokens)
Authentication token pair.

```ts
interface Tokens {
    access: Token;
    refresh?: Token;
}
```

**Example:**

```ts
const tokens = await db.signin(credentials);
console.log(tokens.access); // JWT access token
console.log(tokens.refresh); // Optional refresh token
```

* * *
###  `AuthProvider`[](https://surrealdb.com/docs/reference/javascript/api/types#authprovider)
Function or static value for providing authentication.

```ts
type AuthProvider = 
    | AnyAuth 
    | (() => AnyAuth | Promise<AnyAuth>)
```

**Example:**

```ts
await db.connect('ws://localhost:8000', {
    authentication: async () => ({
        username: await getUsername(),
        password: await getPassword()
    })
});
```

##  Session types[](https://surrealdb.com/docs/reference/javascript/api/types#session-types)
###  `Session`[](https://surrealdb.com/docs/reference/javascript/api/types#session)
Session identifier type.

```ts
type Session = Uuid | undefined
```

* * *
###  `NamespaceDatabase`[](https://surrealdb.com/docs/reference/javascript/api/types#namespacedatabase)
Namespace and database pair.

```ts
interface NamespaceDatabase {
    namespace?: string;
    database?: string;
}
```

**Example:**

```ts
await db.use({
    namespace: 'production',
    database: 'main'
});
```

* * *
###  `SessionEvents`[](https://surrealdb.com/docs/reference/javascript/api/types#sessionevents)
Events emitted by sessions.

```ts
type SessionEvents = {
    auth: [Tokens | null];
    using: [NamespaceDatabase];
}
```

* * *
###  `SurrealEvents`[](https://surrealdb.com/docs/reference/javascript/api/types#surrealevents)
Events emitted by Surreal instances.

```ts
type SurrealEvents = SessionEvents & {
    connecting: [];
    connected: [string];
    reconnecting: [];
    disconnected: [];
    error: [Error];
}
```

##  Query types[](https://surrealdb.com/docs/reference/javascript/api/types#query-types)
###  `RecordResult<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#recordresult)
Ensures records have an `id` field of type `RecordId`.

```ts
type RecordResult<T> = T extends object
    ? { id: RecordId } & T
    : { id: RecordId }
```

**Example:**

```ts
interface User {
    name: string;
    email: string;
}

const user: RecordResult<User> = await db.select(new RecordId('users', 'john'));
console.log(user.id); // RecordId
console.log(user.name); // string
```

* * *
###  `QueryResponse<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#queryresponse)
Response from a query execution.

```ts
type QueryResponse<T = unknown> = 
    | QueryResponseSuccess<T> 
    | QueryResponseFailure

interface QueryResponseSuccess<T> {
    success: true;
    stats?: QueryStats;
    type: "live" | "kill" | "other";
    result: T;
}

interface QueryResponseFailure {
    success: false;
    stats?: QueryStats;
    error: {
        code: number;
        message: string;
    };
}
```

**Example:**

```ts
const responses = await db.query('SELECT * FROM users').responses();

for (const response of responses) {
    if (response.success) {
        console.log('Result:', response.result);
    } else {
        console.error('Error:', response.error.message);
    }
}
```

* * *
###  `QueryStats`[](https://surrealdb.com/docs/reference/javascript/api/types#querystats)
Query execution statistics.

```ts
interface QueryStats {
    recordsReceived: number;
    bytesReceived: number;
    recordsScanned: number;
    bytesScanned: number;
    duration: Duration;
}
```

* * *
###  `Output`[](https://surrealdb.com/docs/reference/javascript/api/types#output)
Output format for query results.

```ts
type Output = "full" | "diff" | "none"
```

* * *
###  `Mutation`[](https://surrealdb.com/docs/reference/javascript/api/types#mutation)
Represents a mutation event from a live query.

```ts
interface Mutation<T = unknown> {
    action: "CREATE" | "UPDATE" | "DELETE";
    result: T;
}
```

* * *
###  `LiveResource`[](https://surrealdb.com/docs/reference/javascript/api/types#liveresource)
Resources that can be subscribed to with live queries.

```ts
type LiveResource = Table
```

* * *
###  `LiveMessage`[](https://surrealdb.com/docs/reference/javascript/api/types#livemessage)
Message received from a live query subscription.

```ts
interface LiveMessage<T = unknown> {
    action: "CREATE" | "UPDATE" | "DELETE";
    result: T;
    diff?: unknown;
}
```

**Example:**

```ts
for await (const message of subscription) {
    console.log(`${message.action}:`, message.result);
}
```

##  Value types[](https://surrealdb.com/docs/reference/javascript/api/types#value-types)
###  `RecordIdValue`[](https://surrealdb.com/docs/reference/javascript/api/types#recordidvalue)
Valid types for record ID components.

```ts
type RecordIdValue = 
    | string 
    | number 
    | Uuid 
    | bigint 
    | unknown[] 
    | Record<string, unknown>
```

* * *
###  `AnyRecordId`[](https://surrealdb.com/docs/reference/javascript/api/types#anyrecordid)
Union type representing any record identifier.

```ts
type AnyRecordId = RecordId | RecordIdRange
```

* * *
###  `Values<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#values)
Extract values from a type, excluding `id` field.

```ts
type Values<T> = Omit<T, 'id'>
```

**Example:**

```ts
interface User {
    id: RecordId;
    name: string;
    email: string;
}

const userData: Values<User> = {
    name: 'John',
    email: 'john@example.com'
    // id is excluded
};
```

* * *
###  `Nullable<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#nullable)
Make properties nullable.

```ts
type Nullable<T> = {
    [K in keyof T]: T[K] | null;
}
```

##  Codec types[](https://surrealdb.com/docs/reference/javascript/api/types#codec-types)
###  `CodecOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#codecoptions)
Options for value encoding/decoding.

```ts
interface CodecOptions {
    useNativeDates?: boolean;
    valueEncodeVisitor?: (value: unknown) => unknown;
    valueDecodeVisitor?: (value: unknown) => unknown;
}
```

**Properties:**
  * •
`useNativeDates` - Use native Date objects instead of DateTime (loses nanosecond precision)
  * •
`valueEncodeVisitor` - Custom function to transform values before encoding
  * •
`valueDecodeVisitor` - Custom function to transform values after decoding

**Example:**

```ts
const db = new Surreal({
    codecOptions: {
        useNativeDates: true,
        valueDecodeVisitor: (value) => {
            // Custom transformation
            return value;
        }
    }
});
```

##  Export/import types[](https://surrealdb.com/docs/reference/javascript/api/types#exportimport-types)
###  `SqlExportOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#sqlexportoptions)
Options for database export.

```ts
interface SqlExportOptions {
    users: boolean;
    accesses: boolean;
    params: boolean;
    functions: boolean;
    analyzers: boolean;
    tables: boolean | string[];
    versions: boolean;
    records: boolean;
    sequences: boolean;
    v3: boolean;
}
```

The `v3` option controls whether to include v3-specific export content.
**Example:**

```ts
const sql = await db.export({
    tables: ['users', 'posts'],
    records: true,
    functions: false
});
```

* * *
###  `MlExportOptions`[](https://surrealdb.com/docs/reference/javascript/api/types#mlexportoptions)
Options for exporting a machine learning model.

```ts
interface MlExportOptions {
    name: string;
    version: string;
}
```

**Example:**

```ts
const model = await db.export({
    name: 'prediction-model',
    version: '1.0.0'
});
```

##  Utility types[](https://surrealdb.com/docs/reference/javascript/api/types#utility-types)
###  `Prettify<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#prettify)
Expand type for better IDE display.

```ts
type Prettify<T> = { [K in keyof T]: T[K] } & {}
```

* * *
###  `EventPublisher<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#eventpublisher)
Interface for event subscription.

```ts
interface EventPublisher<T extends Record<string, unknown[]>> {
    subscribe<K extends keyof T>(
        event: K,
        listener: (...payload: T[K]) => void
    ): () => void;
}
```

* * *
###  `ApiRequest<T>`[](https://surrealdb.com/docs/reference/javascript/api/types#apirequest)
Request options for user-defined API endpoints.

```ts
interface ApiRequest<T = unknown> {
    body?: T;
    method?: string;
    headers?: Record<string, string>;
    query?: Record<string, string>;
}
```

**Properties:**
  * •
`body` - Request body to send
  * •
`method` - HTTP method (default: `"get"`)
  * •
`headers` - Additional headers for the request
  * •
`query` - Query parameters to append to the URL

**Example:**

```ts
const api = db.api();
const result = await api.invoke('/custom', {
    method: 'post',
    body: { data: 'value' },
    headers: { 'X-Custom': 'header' },
    query: { filter: 'active' }
});
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/types#best-practices)
###  1. Use generic type parameters[](https://surrealdb.com/docs/reference/javascript/api/types#1-use-generic-type-parameters)
Leverage generics for type-safe operations:

```ts
interface User {
    name: string;
    email: string;
}

// Type-safe selection
const users = await db.select<User>(new Table('users'));
users[0].name; // TypeScript knows this is a string
```

###  2. Define custom types[](https://surrealdb.com/docs/reference/javascript/api/types#2-define-custom-types)
Create types for your data models:

```ts
interface Post {
    title: string;
    content: string;
    author: RecordId<'users'>;
    created_at: DateTime;
}

const posts = await db.select<Post>(new Table('posts'));
```

###  3. Use type guards[](https://surrealdb.com/docs/reference/javascript/api/types#3-use-type-guards)
Implement type guards for runtime type checking:

```ts
function isUser(value: unknown): value is User {
    return (
        typeof value === 'object' &&
        value !== null &&
        'name' in value &&
        'email' in value
    );
}

if (isUser(data)) {
    console.log(data.email); // Type-safe
}
```

###  4. Handle union types[](https://surrealdb.com/docs/reference/javascript/api/types#4-handle-union-types)
Properly handle discriminated unions:

```ts
const response = await db.query('SELECT * FROM users').responses();

for (const r of response) {
    if (r.success) {
        console.log(r.result); // Success case
    } else {
        console.error(r.error); // Failure case
    }
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/types#see-also)
  * •
[Core classes](https://surrealdb.com/docs/reference/javascript/api/core/) - Classes using these types
  * •
[Value types](https://surrealdb.com/docs/reference/javascript/api/values/) - Value type classes
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Query builder types

**Source:** [types/](https://github.com/surrealdb/surrealdb.js/tree/main/packages/sdk/src/types)
