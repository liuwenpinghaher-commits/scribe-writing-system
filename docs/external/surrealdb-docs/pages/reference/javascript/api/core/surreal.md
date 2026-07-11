---
title: "https://surrealdb.com/docs/reference/javascript/api/core/surreal"
url: "https://surrealdb.com/docs/reference/javascript/api/core/surreal"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/core/surreal

Source: https://surrealdb.com/docs/reference/javascript/api/core/surreal

The `Surreal` class is the primary interface for connecting to a SurrealDB instance, managing connections, executing queries, and handling database sessions. It extends [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) and inherits all session management and query execution capabilities.
By default, a `Surreal` instance operates with a default session scope, but you can create additional isolated sessions using the session management methods.
**Extends:** [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) → [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable)
**Source:** [api/surreal.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/api/surreal.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#constructor)
###  Syntax[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#syntax)
Constructor Syntax

```ts
new Surreal(options?)
```

###  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  | [DriverOptions](https://surrealdb.com/docs/reference/javascript/api/types/#driveroptions)  | Driver-wide configuration options for customizing engines, codecs, and implementations.  |  
###  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#examples)
Basic Usage

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
```

With Custom Options

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal({
    codecOptions: {
        useNativeDates: true // Use native Date objects instead of DateTime
    }
});
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#properties)
###  `status`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#status)
Returns the current connection status.
**Type:** [`ConnectionStatus`](https://surrealdb.com/docs/reference/javascript/api/types/#connectionstatus)
**Values:** `"disconnected"` | `"connecting"` | `"reconnecting"` | `"connected"`
**Example:**

```ts
console.log(db.status); // "connected"
```

###  `isConnected`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#isconnected)
Returns whether the connection is currently established. This is equivalent to checking if `status === "connected"`.
**Type:** `boolean`
**Example:**

```ts
if (db.isConnected) {
    console.log('Database is connected');
}
```

###  `ready`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#ready)
A promise that resolves when the connection is established and ready, or rejects if a connection error occurs.
**Type:** `Promise`
**Example:**

```ts
await db.ready;
console.log('Connection is ready');
```

###  Inherited properties[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#inherited-properties)
The `Surreal` class inherits all properties from [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session), including:
  * •
`namespace` - Current namespace
  * •
`database` - Current database
  * •
`accessToken` - Current access token
  * •
`parameters` - Session parameters
  * •
`session` - Session ID
  * •
`isValid` - Session validity status

##  Connection methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#connection-methods)
###  `.connect()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#connect)
Connect to a local or remote SurrealDB instance.
Warning
Calling `connect()` will reset and dispose of any existing sessions created with `newSession()`.
Method Syntax

```ts
db.connect(url, opts?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `url`  | `string | URL`  |  The endpoint URL to connect to (e.g., `"ws://localhost:8000"`, `"http://localhost:8000/rpc"`).  |  
| `opts`  | [ConnectOptions](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions)  | Connection-specific options such as namespace, database, and authentication.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns)
`Promise` - Resolves when connection is successful
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#examples-1)
WebSocket Connection

```ts
await db.connect('ws://localhost:8000');
```

HTTP Connection

```ts
await db.connect('http://localhost:8000/rpc');
```

With Namespace and Database

```ts
await db.connect('ws://localhost:8000', {
    namespace: 'my_namespace',
    database: 'my_database'
});
```

With Authentication

```ts
await db.connect('ws://localhost:8000', {
    namespace: 'my_namespace',
    database: 'my_database',
    authentication: {
        username: 'root',
        password: 'root'
    }
});
```

With Custom Reconnect Options

```ts
await db.connect('ws://localhost:8000', {
    reconnect: {
        enabled: true,
        attempts: 10,
        retryDelay: 1000,
        retryDelayMax: 10000,
        retryDelayMultiplier: 2
    }
});
```

###  `.close()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#close)
Disconnect from the active SurrealDB instance.
Method Syntax

```ts
db.close()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-1)
`Promise` - Resolves when disconnection is successful
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example)

```ts
await db.close();
console.log('Connection closed');
```

###  `.health()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#health)
Check the health status of the connected SurrealDB instance.
Method Syntax

```ts
db.health()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-2)
`Promise` - Resolves if the instance is healthy, rejects otherwise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-1)

```ts
try {
    await db.health();
    console.log('Database is healthy');
} catch (error) {
    console.error('Health check failed:', error);
}
```

###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#version)
Retrieve version information from the connected SurrealDB instance.
Method Syntax

```ts
db.version()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-3)
[`Promise`](/docs/reference/javascript/api/types/#versioninfo) - An object containing version information
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-2)

```ts
const info = await db.version();
console.log(info.version); // "surrealdb-2.1.0"
```

###  `.isFeatureSupported()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#isfeatureSupported)
Check whether a specific feature is available in the current connection.
Method Syntax

```ts
db.isFeatureSupported(feature)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `feature`  | `Feature`  |  A feature from the `Features`object (e.g. `Features.LiveQueries`, `Features.Api`).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-4)
`boolean` - `true` if the feature is supported, `false` otherwise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-3)

```ts
import { Surreal, Features } from 'surrealdb';

if (db.isFeatureSupported(Features.LiveQueries)) {
    console.log('Live queries are supported');
}
```

##  Session management methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#session-management-methods)
###  `.sessions()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#sessions)
List all active sessions on the current connection.
Method Syntax

```ts
db.sessions()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-5)
`Promise` - An array of session IDs
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-4)

```ts
const sessionIds = await db.sessions();
console.log('Active sessions:', sessionIds);
```

###  `.newSession()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#newsession)
Create a new isolated session on the current connection. The new session will have its own namespace, database, variables, and authentication state, but will share the same connection.
Sessions are automatically restored when the connection reconnects. Call `reset()` on the returned session to destroy it.
Method Syntax

```ts
db.newSession()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-6)
`Promise` - A new [`SurrealSession`](/docs/reference/javascript/api/core/surreal-session) instance
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-5)

```ts
// Create a new isolated session
const session = await db.newSession();

// Use different namespace/database in the new session
await session.use({ namespace: 'other_ns', database: 'other_db' });

// Query in the new session context
const results = await session.select('users');

// Destroy the session when done
await session.reset();
```

###  `.closeSession()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#closesession)
Close the primary session. This is equivalent to calling [`close()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#close) on the connection.
Method Syntax

```ts
db.closeSession()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-7)
`Promise` - Resolves when the session is closed
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-6)

```ts
await db.closeSession();
```

##  Data management methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#data-management-methods)
###  `.export()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#export)
Export the database contents as a SQL string.
Method Syntax

```ts
db.export(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [SqlExportOptions](https://surrealdb.com/docs/reference/javascript/api/types/#sqlexportoptions)  | Options to customize what gets exported.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-8)
`ExportPromise` - A promise that resolves to the exported database as a SQL string. Has a `.raw()` method that returns the raw `Response` object.
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#examples-2)
Export Everything

```ts
const sql = await db.export();
```

Export Only Specific Tables

```ts
const sql = await db.export({
    tables: ['users', 'posts'],
    records: true
});
```

Export Schema Only (No Records)

```ts
const sql = await db.export({
    records: false,
    tables: true,
    functions: true
});
```

Export as Raw Response

```ts
const response = await db.export().raw();
```

###  `.import()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#import)
Import database contents from a SQL string or a readable stream.
Method Syntax

```ts
db.import(input)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `input`  | `string | ReadableStream<string>`  | The SQL string or readable stream to import into the database.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-9)
`Promise` - Resolves when the import is complete
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-7)

```ts
const sqlData = `
    DEFINE TABLE users SCHEMAFULL;
    DEFINE FIELD name ON users TYPE string;
    CREATE users:john SET name = 'John Doe';
`;

await db.import(sqlData);
console.log('Data imported successfully');
```

###  `.exportModel()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#exportmodel)
Export a SurrealML model from the database.
Method Syntax

```ts
db.exportModel(name, version)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The name of the SurrealML model to export.  |  
| `version`  | `string`  | The version of the model to export.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-10)
`ExportModelPromise` - A promise that resolves to the exported model data. Has a `.raw()` method that returns the raw `Response` object.
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-8)

```ts
const modelData = await db.exportModel('my_model', '1.0.0');
```

Export as Raw Response

```ts
const response = await db.exportModel('my_model', '1.0.0').raw();
```

##  Events[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#events)
The `Surreal` class implements the `EventPublisher` interface and emits various events during the connection lifecycle. Subscribe to events using the [`subscribe()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#subscribe) method.
###  `connecting`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#event-connecting)
Emitted when the connection attempt starts.
**Payload:** None
**Example:**

```ts
const unsubscribe = db.subscribe('connecting', () => {
    console.log('Connecting to database...');
});
```

###  `connected`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#event-connected)
Emitted when the connection is successfully established.
**Payload:** `[version: string]` - The SurrealDB version string
**Example:**

```ts
db.subscribe('connected', (version) => {
    console.log('Connected to SurrealDB version:', version);
});
```

###  `reconnecting`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#event-reconnecting)
Emitted when the connection is attempting to reconnect after being disconnected.
**Payload:** None
**Example:**

```ts
db.subscribe('reconnecting', () => {
    console.log('Attempting to reconnect...');
});
```

###  `disconnected`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#event-disconnected)
Emitted when the connection is closed.
**Payload:** None
**Example:**

```ts
db.subscribe('disconnected', () => {
    console.log('Disconnected from database');
});
```

###  `error`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#event-error)
Emitted when a connection error occurs.
**Payload:** `[error: Error]` - The error object
**Example:**

```ts
db.subscribe('error', (error) => {
    console.error('Connection error:', error.message);
});
```

###  Inherited events[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#inherited-events)
The `Surreal` class also inherits and re-emits events from [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session):
  * •
`auth` - Emitted when authentication state changes
  * •
`using` - Emitted when namespace/database changes

###  `.subscribe()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#subscribe)
Subscribe to connection and session events.
Method Syntax

```ts
db.subscribe(event, listener)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `event`  |  keyof [SurrealEvents](https://surrealdb.com/docs/reference/javascript/api/types/#surrealevents)  | The event name to subscribe to.  |  
| `listener`  | `Function`  | Callback function invoked when the event is emitted.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#returns-11)
`() => void` - An unsubscribe function to remove the event listener
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#example-9)

```ts
const unsubscribe = db.subscribe('connected', (version) => {
    console.log('Connected:', version);
});

// Later, unsubscribe from the event
unsubscribe();
```

##  Inherited methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#inherited-methods)
As `Surreal` extends [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session), it inherits all authentication and query methods:
###  Authentication methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#authentication-methods)
  * •
[`signup()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signup) - Sign up a new user
  * •
[`signin()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signin) - Sign in with credentials
  * •
[`authenticate()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#authenticate) - Authenticate with a token
  * •
[`invalidate()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#invalidate) - Invalidate the session

###  Session configuration methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#session-configuration-methods)
  * •
[`use()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#use) - Set namespace and database
  * •
[`set()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#set) - Set a session parameter
  * •
[`unset()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#unset) - Remove a session parameter
  * •
[`reset()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#reset) - Reset the session

###  Query methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#query-methods)
As `Surreal` extends [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable) (via `SurrealSession`), it also inherits all query execution methods:
  * •
[`query()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) - Execute raw SurrealQL
  * •
[`select()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#select) - Select records
  * •
[`create()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#create) - Create records
  * •
[`insert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#insert) - Insert records
  * •
[`update()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#update) - Update records
  * •
[`upsert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#upsert) - Upsert records
  * •
[`delete()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#delete) - Delete records
  * •
[`relate()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#relate) - Create graph relationships
  * •
[`live()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live) - Subscribe to live queries
  * •
[`run()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run) - Execute functions

###  Transaction method[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#transaction-method)
  * •
[`beginTransaction()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) - Start a transaction

##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#type-parameters)
This class does not use generic type parameters.
##  Complete example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#complete-example)

```ts
import { Surreal } from 'surrealdb';

// Create and connect
const db = new Surreal({
    codecOptions: {
        useNativeDates: true
    }
});

// Subscribe to connection events
db.subscribe('connecting', () => console.log('Connecting...'));
db.subscribe('connected', (version) => console.log('Connected:', version));
db.subscribe('error', (error) => console.error('Error:', error));

// Connect to database
await db.connect('ws://localhost:8000', {
    namespace: 'my_namespace',
    database: 'my_database',
    authentication: {
        username: 'root',
        password: 'root'
    }
});

// Check connection status
console.log('Connected:', db.isConnected); // true
console.log('Status:', db.status); // "connected"

// Get version info
const version = await db.version();
console.log('Version:', version.version);

// Execute queries (inherited from SurrealSession/SurrealQueryable)
const users = await db.select('users');
console.log('Users:', users);

// Create a new isolated session
const session = await db.newSession();
await session.use({ namespace: 'other_ns', database: 'other_db' });
const otherData = await session.select('data');

// Export database
const backup = await db.export({ records: true });
console.log('Backup size:', backup.length);

// Close connection
await db.close();
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/core/surreal#see-also)
  * •
[SurrealSession](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) - Session management and authentication
  * •
[SurrealQueryable](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable) - Query execution methods
  * •
[SurrealTransaction](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) - Transaction support
  * •
[Connection Engines](https://surrealdb.com/docs/reference/javascript/engines) - Engine-specific documentation
  * •
[Data types](https://surrealdb.com/docs/reference/javascript/api/values) - Working with data types
