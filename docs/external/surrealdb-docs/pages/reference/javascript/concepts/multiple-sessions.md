---
title: "https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions"
url: "https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions

Source: https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions

The JavaScript SDK allows you to create multiple isolated sessions within a single connection. Each session maintains its own namespace, database, variables, and authentication state, while sharing the underlying connection to SurrealDB. This is useful when different parts of your application need to operate under different credentials or contexts simultaneously.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` db.newSession() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal#newsession)  | Creates a new isolated session on the connection  |  
| [` session.forkSession() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#forksession)  | Creates a copy of a session, inheriting its state  |  
| [` session.closeSession() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#closesession)  | Destroys a session and releases its resources  |  
| [` session.reset() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#reset)  | Resets a session's state without destroying it  |  
##  Creating isolated sessions[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#creating-isolated-sessions)
Call `.newSession()` on a `Surreal` instance to create a new session. The new session starts with no namespace, database, or authentication, and must be configured independently.

```ts
const session = await db.newSession();

await session.use({ namespace: 'production', database: 'main' });

await session.signin({
    namespace: 'production',
    database: 'main',
    access: 'user_access',
    variables: {
        email: 'user@example.com',
        password: 'secure_password',
    },
});

const users = await session.select(new Table('users'));
```

Sessions support all the same query methods as the main `Surreal` instance, including `.query()`, `.select()`, `.create()`, `.update()`, `.delete()`, and [more](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries).
##  Forking an existing session[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#forking-an-existing-session)
The `.forkSession()` method creates a new session that inherits the namespace, database, variables, and authentication state from the parent session. This is useful when you need a temporary context that starts with the same setup.

```ts
const primary = await db.newSession();
await primary.use({ namespace: 'app', database: 'main' });
await primary.signin({ username: 'admin', password: 'secret' });

const forked = await primary.forkSession();
await forked.use({ database: 'analytics' });
```

The forked session operates independently after creation. Changes to the parent session do not affect the fork, and vice versa.
##  Automatic cleanup with await using[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#automatic-cleanup-with-await-using)
Sessions support the [await using](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/await_using) declaration. When you declare a session with `await using`, JavaScript automatically closes the session when execution leaves the current scope.

```ts
{
    await using session = await db.newSession();
    await session.use({ namespace: 'main', database: 'main' });
    const data = await session.select(new Table('users'));
}
```

This is equivalent to manually calling `session.closeSession()` in a `finally` block, but with cleaner syntax.
##  Closing and resetting sessions[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#closing-and-resetting-sessions)
When you are done with a session, call `.closeSession()` to destroy it and release server-side resources.

```ts
const session = await db.newSession();

await session.select(new Table('users'));

await session.closeSession();
```

If you want to clear a session's state without destroying it, use `.reset()`. This removes all variables and invalidates authentication, but keeps the session alive for reuse.

```ts
await session.reset();
```

Note
Using a session after it has been closed throws an [`InvalidSessionError`](https://surrealdb.com/docs/reference/javascript/api/errors#invalidsessionerror).
##  Reconnection behavior[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#reconnection-behavior)
Sessions are automatically restored when the underlying connection reconnects after a drop. The SDK re-establishes each session's namespace, database, variables, and authentication state on the server. If a session used the `authentication` property from the original `.connect()` call, it will be re-authenticated automatically.
Sessions that were authenticated via `.signin()` or `.signup()` rely on the [`auth`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#event-auth) event for re-authentication. See [Authentication](https://surrealdb.com/docs/reference/javascript/concepts/authentication#listening-to-authentication-events) for details.
##  Subscribing to session events[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#subscribing-to-session-events)
Each session emits its own events, independent of other sessions and the main `Surreal` instance. You can subscribe to the `auth` and `using` events on any session.

```ts
session.subscribe('auth', (tokens) => {
    if (tokens) {
        console.log('Session authenticated');
    } else {
        console.log('Session signed out');
    }
});

session.subscribe('using', (using) => {
    console.log('Now using:', using.namespace, '/', using.database);
});
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions#learn-more)
  * •
[SurrealSession API reference](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) for the full session interface
  * •
[Surreal.newSession()](https://surrealdb.com/docs/reference/javascript/api/core/surreal#newsession) for session creation details
  * •
[Authentication](https://surrealdb.com/docs/reference/javascript/concepts/authentication) for session-level authentication
  * •
[Transactions](https://surrealdb.com/docs/reference/javascript/concepts/transactions) for atomic operations within sessions
