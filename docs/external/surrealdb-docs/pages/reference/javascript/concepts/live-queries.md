---
title: "https://surrealdb.com/docs/reference/javascript/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/javascript/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/live-queries

Source: https://surrealdb.com/docs/reference/javascript/concepts/live-queries

Live queries allow your application to receive real-time notifications whenever records in the database are created, updated, or deleted. The JavaScript SDK provides two approaches: managed live queries that the SDK controls and automatically restarts on reconnect, and unmanaged live queries that you create via SurrealQL and subscribe to manually.
Note
Live queries require a WebSocket connection. They are not supported over HTTP. You can check for support using the [feature testing](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#testing-for-features) mechanism.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` db.live(target) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live)  | Creates a managed live query subscription  |  
| [` db.liveOf(id) `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof)  | Subscribes to an existing live query by its ID  |  
| [` live.subscribe(callback) `](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise)  | Registers a callback for live query updates  |  
| [` live.kill() `](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise)  | Stops the live query and unsubscribes all listeners  |  
##  Creating a managed live query[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#creating-a-managed-live-query)
The `.live()` method creates a managed live query subscription. The SDK handles the lifecycle of the query, including automatically restarting it when the connection reconnects. The provided [`Table`](https://surrealdb.com/docs/reference/javascript/api/values/table) determines the records to listen to.

```ts
import { Table } from 'surrealdb';

const live = await db.live(new Table('users'));
```

Much like the `.select()` method, you can chain multiple methods to configure the live query before executing it. This includes enabling diff results, selecting specific fields, and filtering the records to listen to.

```ts
import { gt } from 'surrealdb';

const live = await db.live(new Table('users'))
    .diff()
    .fields('name', 'email', 'age')
    .where(gt('age', 18));
```

###  Listening with a callback[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#listening-with-a-callback)
Use `.subscribe()` on the returned live query to register a callback. The callback receives the action, the result record, and the record ID.

```ts
live.subscribe((action, result, record) => {
    switch (action) {
        case 'CREATE':
            console.log('New user:', result);
            break;
        case 'UPDATE':
            console.log('Updated user:', record, result);
            break;
        case 'DELETE':
            console.log('Deleted user:', record);
            break;
    }
});
```

###  Iterating messages with async iteration[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#iterating-messages-with-async-iteration)
Live queries also support the `for await...of` pattern, which yields each message as an object with `action` and `value` properties.

```ts
for await (const { action, value } of live) {
    console.log(`${action}:`, value);
}
```

##  Creating an unmanaged live query[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#creating-an-unmanaged-live-query)
If you need to start a live query using SurrealQL (for example, with a custom `WHERE` clause), you can execute a `LIVE SELECT` statement and then subscribe to it using `.liveOf()`. Unmanaged queries are not automatically restarted on reconnect.

```ts
const [id] = await db.query('LIVE SELECT * FROM users WHERE active = true');
const live = db.liveOf(id);

live.subscribe((action, result, record) => {
    console.log(action, result);
});
```

##  Handling live query actions[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#handling-live-query-actions)
Every live query message has an action that indicates what happened to the record:  
| Action  | Description  |  
| --- | --- |  
| `CREATE`  | A new record was created that matches the subscription  |  
| `UPDATE`  | An existing record within the subscription was modified  |  
| `DELETE`  | A record within the subscription was deleted  |  
##  Stopping a live query[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#stopping-a-live-query)
Call `.kill()` to stop a live query and unsubscribe all listeners. This releases resources on both the client and the server.

```ts
await live.kill();
```

##  Automatic restart on reconnect[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#automatic-restart-on-reconnect)
Managed live queries created with `.live()` are automatically restarted when the SDK reconnects to the database after a connection drop. This means your application will continue receiving updates without any manual intervention.
Unmanaged live queries created via `LIVE SELECT` and `.liveOf()` are not automatically restarted. If you need reconnection resilience with custom queries, prefer using a managed live query or re-subscribing manually by listening to the [`connected`](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-status) event.
##  Checking for live query support[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#checking-for-live-query-support)
Live queries require a WebSocket-based engine. Before creating a live query, you can verify that the current connection supports them.

```ts
import { Features } from 'surrealdb';

if (db.isFeatureSupported(Features.LiveQueries)) {
    const live = await db.live(new Table('users'));
}
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/live-queries#learn-more)
  * •
[Live query API reference](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise) for detailed method signatures
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for WebSocket connection setup
  * •
[LIVE SELECT](https://surrealdb.com/docs/reference/query-language/statements/live-select) for the SurrealQL live query syntax
