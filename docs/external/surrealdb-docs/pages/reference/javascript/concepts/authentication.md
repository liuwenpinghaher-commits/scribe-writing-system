---
title: "https://surrealdb.com/docs/reference/javascript/concepts/authentication"
url: "https://surrealdb.com/docs/reference/javascript/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/authentication

Source: https://surrealdb.com/docs/reference/javascript/concepts/authentication

SurrealDB supports multiple levels of authentication, from [system users](https://surrealdb.com/docs/learn/security/authentication/authentication#system-user) to fine-grained [record-level access](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users). The JavaScript SDK provides methods for signing up and signing in users, managing tokens, and automatically restoring sessions on reconnect.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` db.signin(auth) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signin)  | Signs in as a root, namespace, database, or record user  |  
| [` db.signup(auth) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#signup)  | Signs up a new record user using an access method  |  
| [` db.authenticate(token) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#authenticate)  | Authenticates the session with an existing token or token pair  |  
| [` db.invalidate() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#invalidate)  | Invalidates the current authentication, signing the user out  |  
| [` db.subscribe("auth", callback) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#subscribe)  | Subscribes to authentication state changes  |  
##  Signing in users[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-in-users)
The `.signin()` method authenticates an existing user. SurrealDB supports multiple authentication levels, and the properties you provide determine which level is used.
Root userNamespace userDatabase userRecord access
Authenticate as a root user with full access to all namespaces and databases.

```ts
const tokens = await db.signin({
	username: 'root',
	password: 'surrealdb',
});
```

Authenticate as a [namespace user](https://surrealdb.com/docs/reference/query-language/statements/define/user) with access to all databases in the specified namespace.

```ts
const tokens = await db.signin({
	namespace: 'surrealdb',
	username: 'tobie',
	password: 'surrealdb',
});
```

Authenticate as a [database user](https://surrealdb.com/docs/reference/query-language/statements/define/user) with access scoped to a specific database.

```ts
const tokens = await db.signin({
	namespace: 'surrealdb',
	database: 'docs',
	username: 'tobie',
	password: 'surrealdb',
});
```

Authenticate as a record user through a defined [record access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/record). Pass any required variables under the `variables` key.

```ts
const tokens = await db.signin({
	namespace: 'surrealdb',
	database: 'docs',
	access: 'account',
	variables: {
		email: 'info@surrealdb.com',
		pass: '123456',
	},
});
```

On success, the method returns a [`Tokens`](https://surrealdb.com/docs/reference/javascript/api/types/#tokens) object containing the access token and an optional refresh token. The session is automatically authenticated after signing in.
##  Signing up users[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-up-users)
The `.signup()` method creates a new record user through a defined [record access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/record). You must specify the namespace, database, and access method, along with any variables expected by the access definition.

```ts
const tokens = await db.signup({
    namespace: 'surrealdb',
    database: 'docs',
    access: 'account',
    variables: {
        email: 'info@surrealdb.com',
        pass: '123456',
    },
});
```

Much like the `.signin()` method, the `.signup()` method returns a [`Tokens`](https://surrealdb.com/docs/reference/javascript/api/types/#tokens) object containing the access token and an optional refresh token. The session is automatically authenticated after signing up.
##  Authenticating with an existing token[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#authenticating-with-an-existing-token)
If you already have an access token (for example, stored from a previous session), you can authenticate using the `.authenticate()` method instead of signing in again. This is useful for restoring a user's session without re-entering credentials.

```ts
await db.authenticate(accessToken);
```

When you have a refresh token available, you can pass both tokens as an object. The SDK will exchange the refresh token for a new token pair.

```ts
const newTokens = await db.authenticate({
    access: oldAccessToken,
    refresh: refreshToken,
});
```

##  Providing credentials on connect[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#providing-credentials-on-connect)
Rather than calling `.signin()` separately, you can pass authentication credentials directly to the `.connect()` method using the `authentication` option. This is the preferred approach for system users because it allows the SDK to automatically re-authenticate when the connection drops and reconnects.

```ts
await db.connect('ws://127.0.0.1:8000', {
    namespace: 'surrealdb',
    database: 'docs',
    authentication: {
        username: 'root',
        password: 'surrealdb',
    },
});
```

The `authentication` option also accepts an async function, allowing you to retrieve credentials dynamically.

```ts
await db.connect('ws://127.0.0.1:8000', {
    namespace: 'surrealdb',
    database: 'docs',
    authentication: async () => ({
        username: await getUsername(),
        password: await getPassword(),
    }),
});
```

See the full list of connection options in the [`ConnectOptions`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) type reference.
Note
When you call `.signup()` or `.signin()` manually, the `authentication` property passed to `.connect()` is no longer used for automatic re-authentication. You become responsible for handling token expiry by listening to the [`auth`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth) event.
##  Listening to authentication events[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#listening-to-authentication-events)
The SDK emits an `auth` event whenever the authentication state changes, including on sign in, sign up, token refresh, or invalidation. You can subscribe to this event using the `.subscribe()` method.

```ts
db.subscribe('auth', (tokens) => {
    if (tokens) {
        console.log('Authenticated:', tokens.access);
    } else {
        console.log('Signed out');
    }
});
```

This is particularly useful for record access, where you can subscribe to the `auth` event to automatically update UI or other components when the authentication state changes.
##  Accessing authentication state[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#accessing-authentication-state)
The SDK exposes the current authentication tokens through the `.accessToken` property on any [`Surreal`](https://surrealdb.com/docs/reference/javascript/api/core/surreal) or [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) instance. This is useful for checking whether the current session is authenticated or for forwarding tokens to other services.

```ts
if (db.accessToken) {
    console.log('Session is authenticated');
}
```

##  Signing out[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-out)
The `.invalidate()` method signs the current user out by clearing the session's authentication state. After calling this method, any subsequent queries will run without authentication.

```ts
await db.invalidate();
```

##  Using isolated sessions[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#using-isolated-sessions)
You can create multiple isolated sessions within a single connection, each with their own namespace, database, variables, and authentication state. This is useful when different parts of your application need to operate under different credentials or contexts.

```ts
const session = await db.newSession();

await session.signin({
    namespace: 'surrealdb',
    database: 'docs',
    access: 'account',
    variables: {
        email: 'info@surrealdb.com',
        pass: '123456',
    },
});

const users = await session.select('users');

await session.closeSession();
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/authentication#learn-more)
  * •
[SurrealSession API reference](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) for authentication method signatures
  * •
[Authentication types reference](https://surrealdb.com/docs/reference/javascript/api/types/#anyauth) for all credential type definitions
  * •
[Authentication in SurrealDB](https://surrealdb.com/docs/learn/security/authentication/authentication) for how authentication works at the database level
  * •
[Security best practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#authentication) for securing your application
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) for defining access methods with SurrealQL
  * •
[DEFINE USER](https://surrealdb.com/docs/reference/query-language/statements/define/user) for creating system users
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for connection setup and reconnection behavior
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions) for isolated session management
