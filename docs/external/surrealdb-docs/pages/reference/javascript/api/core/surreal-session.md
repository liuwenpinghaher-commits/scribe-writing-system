---
title: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-session"
url: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-session"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/core/surreal-session

Source: https://surrealdb.com/docs/reference/javascript/api/core/surreal-session

The `SurrealSession` class represents a scoped contextual session attached to a SurrealDB connection. It provides authentication, session configuration, and inherits all query execution methods from [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable).
Sessions allow you to maintain isolated contexts with their own namespace, database, variables, and authentication state, while sharing the underlying connection.
**Extends:** [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable)
**Extended by:** [`Surreal`](https://surrealdb.com/docs/reference/javascript/api/core/surreal)
**Source:** [api/session.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/api/session.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#constructor)
The constructor is typically not called directly. Use [`Surreal.newSession()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#newsession) or [`forkSession()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#forksession) to create new sessions.
##  Properties[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#properties)
###  `namespace`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#namespace)
Returns the currently selected namespace for this session.
**Type:** `string | undefined`
**Example:**

```ts
console.log(session.namespace); // "my_namespace"
```

###  `database`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#database)
Returns the currently selected database for this session.
**Type:** `string | undefined`
**Example:**

```ts
console.log(session.database); // "my_database"
```

###  `accessToken`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#accesstoken)
Returns the current authentication access token for this session.
**Type:** `string | undefined`
**Example:**

```ts
if (session.accessToken) {
    console.log('Session is authenticated');
}
```

###  `parameters`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters)
Returns all parameters currently defined on the session.
**Type:** `Record`
**Example:**

```ts
console.log(session.parameters); // { user_id: '123', role: 'admin' }
```

###  `session`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#session)
Returns the unique session ID. For the default session, `undefined` is returned.
**Type:** [`Uuid`](https://surrealdb.com/docs/reference/javascript/api/values/uuid) `| undefined`
**Example:**

```ts
const sessionId = session.session;
console.log('Session ID:', sessionId);
```

###  `isValid`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#isvalid)
Returns whether the session is valid and can be used. This is always `true` for the default session, but will be `false` for sessions that have been disposed via [`reset()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#reset) or [`closeSession()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#closesession).
**Type:** `boolean`
**Example:**

```ts
if (session.isValid) {
    await session.select('users');
} else {
    console.log('Session has been closed');
}
```

##  Session management methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#session-management-methods)
###  `.forkSession()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#forksession)
Create a new session by cloning the current session. The new session inherits all properties from the parent session including namespace, database, variables, and authentication state.
Sessions are automatically restored when the connection reconnects. Call [`reset()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#reset) on the created session to destroy it.
Method Syntax

```ts
session.forkSession()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns)
[`Promise`](/docs/reference/javascript/api/core/surreal-session) - A new session instance
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example)

```ts
// Create a forked session that inherits parent state
const childSession = await session.forkSession();

// The child inherits parent's namespace and database
console.log(childSession.namespace); // Same as parent
console.log(childSession.database); // Same as parent

// But can be changed independently
await childSession.use({ database: 'other_db' });

// Parent session remains unchanged
console.log(session.database); // Original database
console.log(childSession.database); // 'other_db'

// Clean up when done
await childSession.reset();
```

###  `.closeSession()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#closesession)
Closes the current session and disposes of it. After this method is called, the session cannot be used again, and [`isValid`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#isvalid) will return `false`.
Method Syntax

```ts
session.closeSession()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-1)
`Promise` - Resolves when the session is closed
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-1)

```ts
await session.closeSession();
console.log(session.isValid); // false
```

##  Transaction methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#transaction-methods)
###  `.beginTransaction()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#begintransaction)
Create a new transaction scoped to the current session. Transactions allow you to execute multiple queries atomically.
Call [`commit()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#commit) on the transaction to apply changes, or [`cancel()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#cancel) to discard them.
Method Syntax

```ts
session.beginTransaction()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-2)
`Promise` - A new [`SurrealTransaction`](/docs/reference/javascript/api/core/surreal-transaction) instance
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-2)

```ts
// Start a transaction
const txn = await session.beginTransaction();

try {
    // Execute queries within the transaction
    await txn.create(new RecordId('users', 'john'), {
        content: { name: 'John Doe', email: 'john@example.com' }
    });
    
    await txn.create(new RecordId('posts', '1'), {
                content: { author: new RecordId('users', 'john'),
            title: 'Hello' }
    });
    
    // Commit all changes atomically
    await txn.commit();
    console.log('Transaction committed successfully');
} catch (error) {
    // Roll back on error
    await txn.cancel();
    console.error('Transaction cancelled:', error);
}
```

##  Session configuration methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#session-configuration-methods)
###  `.use()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#use)
Switch to the specified namespace and/or database for this session.
Leaving the namespace or database `undefined` will leave the current value unchanged, while passing `null` will unset the selected namespace or database.
Method Syntax

```ts
session.use(what)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `what`  |  Nullable [NamespaceDatabase](https://surrealdb.com/docs/reference/javascript/api/types/#namespacedatabase)  | Object specifying namespace and/or database to switch to. If omitted, returns the current namespace and database.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-3)
[`Promise`](/docs/reference/javascript/api/types/#namespacedatabase) - The current or newly selected namespace and database
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#examples)
Switch Both Namespace and Database

```ts
await session.use({ 
    namespace: 'production', 
    database: 'main' 
});
```

Switch Only Database

```ts
await session.use({ 
    database: 'analytics' 
});
// Namespace remains unchanged
```

Unset Database

```ts
await session.use({ 
    database: null 
});
// Database is now undefined
```

###  `.set()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#set)
Define a variable for the current session. Variables can be used in SurrealQL queries with the `$` prefix.
Method Syntax

```ts
session.set(variable, value)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `variable`  | `string`  | The name of the variable (without the $ prefix).  |  
| `value`  | `unknown`  | The value to assign to the variable.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-4)
`Promise` - Resolves when the variable is set
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-3)

```ts
// Set a variable
await session.set('user_id', '12345');

// Use it in a query
const result = await session.query(
    'SELECT * FROM posts WHERE author = $user_id'
).collect();
```

###  `.unset()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#unset)
Remove a variable from the current session.
Method Syntax

```ts
session.unset(variable)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `variable`  | `string`  | The name of the variable to remove (without the $ prefix).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-5)
`Promise` - Resolves when the variable is removed
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-4)

```ts
await session.unset('user_id');
```

###  `.reset()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#reset)
Resets the current session to its initial state, clearing authentication state, variables, and selected namespace/database.
For non-default sessions, this also closes and disposes of the session.
Method Syntax

```ts
session.reset()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-6)
`Promise` - Resolves when the session is reset
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-5)

```ts
// Reset session to clean state
await session.reset();

// Session is now cleared
console.log(session.namespace); // undefined
console.log(session.accessToken); // undefined
console.log(session.parameters); // {}
```

##  Authentication methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#authentication-methods)
###  `.signup()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signup)
Sign up a new record user to the SurrealDB instance.
Note
When this method is called, the `authentication` property passed to [`connect()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#connect) will be ignored. You are responsible for handling session invalidation by listening to the [`auth`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth) event.
Method Syntax

```ts
session.signup(auth)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `auth`  | [AccessRecordAuth](https://surrealdb.com/docs/reference/javascript/api/types/#accessrecordauth)  | The authentication details including access method and record data.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-7)
[`Promise`](/docs/reference/javascript/api/types/#tokens) - The authentication tokens (access and refresh tokens)
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-6)

```ts
const tokens = await session.signup({
    namespace: 'my_namespace',
    database: 'my_database',
    access: 'user_access',
    variables: {
        email: 'user@example.com',
        password: 'secure_password',
        name: 'John Doe'
    }
});

console.log('Access token:', tokens.access);
console.log('Refresh token:', tokens.refresh);
```

###  `.signin()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signin)
Sign in to the SurrealDB instance with authentication credentials.
Note
When this method is called, the `authentication` property passed to [`connect()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#connect) will be ignored. You are responsible for handling session invalidation by listening to the [`auth`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth) event.
Method Syntax

```ts
session.signin(auth)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `auth`  | [AnyAuth](https://surrealdb.com/docs/reference/javascript/api/types/#anyauth)  | Authentication details (system user, record user, or access method).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-8)
[`Promise`](/docs/reference/javascript/api/types/#tokens) - The authentication tokens
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#examples-1)
System User Authentication

```ts
const tokens = await session.signin({
    username: 'root',
    password: 'root'
});
```

Record User Authentication

```ts
const tokens = await session.signin({
    namespace: 'my_namespace',
    database: 'my_database',
    access: 'user_access',
    variables: {
        email: 'user@example.com',
        password: 'secure_password'
    }
});
```

###  `.authenticate()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#authenticate)
Authenticate the session using an existing access token or access and refresh token combination.
When authenticating with a refresh token, a new refresh token will be issued and returned.
Note
When this method is called, the `authentication` property passed to [`connect()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal#connect) will be ignored. You are responsible for handling session invalidation by listening to the [`auth`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth) event.
Method Syntax

```ts
session.authenticate(token)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `token`  |  [Token](https://surrealdb.com/docs/reference/javascript/api/types/#token)| [Tokens](https://surrealdb.com/docs/reference/javascript/api/types/#tokens)  | The access token or tokens object with access and refresh tokens.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-9)
[`Promise`](/docs/reference/javascript/api/types/#tokens) - The authentication tokens (may include new refresh token)
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#examples-2)
Authenticate with Access Token

```ts
await session.authenticate(accessToken);
```

Authenticate with Refresh Token

```ts
const newTokens = await session.authenticate({
    access: oldAccessToken,
    refresh: refreshToken
});

// Store new tokens
console.log('New access token:', newTokens.access);
console.log('New refresh token:', newTokens.refresh);
```

###  `.invalidate()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#invalidate)
Invalidate the authentication for the current session, signing the user out.
Method Syntax

```ts
session.invalidate()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-10)
`Promise` - Resolves when authentication is invalidated
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-7)

```ts
await session.invalidate();
console.log('User signed out');
```

##  Events[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#events)
The `SurrealSession` class emits events that you can subscribe to for tracking session state changes.
###  `auth`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth)
Emitted when the authentication state changes for this session.
**Payload:** `[tokens:` [`Tokens`](https://surrealdb.com/docs/reference/javascript/api/types/#tokens) `| null]` - The new authentication tokens, or `null` if invalidated
**Example:**

```ts
session.subscribe('auth', (tokens) => {
    if (tokens) {
        console.log('Authenticated with token:', tokens.access);
    } else {
        console.log('Authentication invalidated');
    }
});
```

###  `using`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-using)
Emitted when the namespace or database changes for this session.
**Payload:** `[using:` [`NamespaceDatabase`](https://surrealdb.com/docs/reference/javascript/api/types/#namespacedatabase)`]` - Object containing the new namespace and database
**Example:**

```ts
session.subscribe('using', (using) => {
    console.log('Now using:', using.namespace, '/', using.database);
});
```

###  `.subscribe()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#subscribe)
Subscribe to session events.
Method Syntax

```ts
session.subscribe(event, listener)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `event`  |  keyof [SessionEvents](https://surrealdb.com/docs/reference/javascript/api/types/#sessionevents)  |  The event name to subscribe to ( `"auth"`or `"using"`).  |  
| `listener`  | `Function`  | Callback function invoked when the event is emitted.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-11)
`() => void` - An unsubscribe function
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-8)

```ts
const unsubscribe = session.subscribe('auth', (tokens) => {
    console.log('Auth changed:', tokens);
});

// Later, unsubscribe
unsubscribe();
```

##  Inherited methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#inherited-methods)
As `SurrealSession` extends [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable), it inherits all query execution methods:
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
[`liveOf()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof) - Subscribe to existing live queries
  * •
[`run()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run) - Execute functions
  * •
[`auth()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#auth) - Get authenticated record user
  * •
[`api()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api) - Access user-defined APIs

##  Async disposal[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#async-disposal)
###  `[Symbol.asyncDispose]()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#symbol-asyncdispose)
Supports the [async disposal](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Symbol/asyncDispose) protocol, allowing sessions to be used with `await using` for automatic cleanup.
Method Syntax

```ts
session[Symbol.asyncDispose]()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#returns-12)
`Promise` - Resolves when the session is disposed
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#example-9)

```ts
{
    await using session = await db.newSession();
    await session.use({ namespace: 'main', database: 'main' });
    const users = await session.select('users');
}
// Session is automatically disposed when leaving the block
```

##  Complete example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#complete-example)

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Use the default session
await db.use({ namespace: 'main', database: 'main' });

// Sign in
await db.signin({
    username: 'root',
    password: 'root'
});

// Create an isolated session
const session = await db.newSession();

// Configure the session
await session.use({ 
    namespace: 'main', 
    database: 'main' 
});

// Set session variables
await session.set('user_role', 'admin');

// Subscribe to session events
session.subscribe('auth', (tokens) => {
        console.log('Session auth changed:',
        tokens ? 'authenticated' : 'signed out');
});

session.subscribe('using', (using) => {
    console.log('Using:', using);
});

// Authenticate as a record user
const tokens = await session.signin({
    namespace: 'main',
    database: 'main',
    access: 'user_access',
    variables: {
        email: 'user@example.com',
        password: 'password'
    }
});

// Execute queries in the session context
const users = await session.select('users');

// Start a transaction
const txn = await session.beginTransaction();
await txn.create('logs:1',
    { content: { message: 'User logged in' } });
await txn.commit();

// Fork the session to create an isolated copy
const childSession = await session.forkSession();
await childSession.use({ database: 'analytics' });

// Clean up
await childSession.reset();
await session.closeSession();
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/javascript/api/core/surreal) - Main connection class
  * •
[SurrealQueryable](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable) - Query execution methods
  * •
[SurrealTransaction](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) - Transaction support
  * •
[Authentication Types](https://surrealdb.com/docs/reference/javascript/api/types/#anyauth) - Authentication type definitions
