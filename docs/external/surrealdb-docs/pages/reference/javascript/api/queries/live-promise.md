---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/live-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/live-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/live-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/live-promise

Live query promises provide interfaces for subscribing to real-time updates from SurrealDB. There are two variants: `ManagedLivePromise` for new subscriptions and `UnmanagedLivePromise` for existing ones.
**Returned by:** [`SurrealQueryable.live()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live), [`SurrealQueryable.liveOf()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof)
**Source:** [query/live.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/live.ts)
##  `ManagedLivePromise<T>`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#managedlivepromise)
A managed live query subscription that the SDK automatically creates and manages.
**Returned by:** [`SurrealQueryable.live()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live)
###  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#configuration-methods)
####  `.diff()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#diff)
Configure the subscription to return only patches (diffs) instead of full records on updates.
Method Syntax

```ts
livePromise.diff()
```

**Returns:** `ManagedLivePromise` - Chainable promise
**Example:**

```ts
const subscription = await db.live(new Table('users')).diff();

for await (const update of subscription) {
    console.log('Diff:', update.diff); // Only changed fields
}
```

* * *
####  `.fields()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#fields)
Select only specific fields in the live updates.
Method Syntax

```ts
livePromise.fields(...fields)
```

**Parameters:**  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Field<T>[]`  | Field names to include in updates.  |  
**Returns:** `ManagedLivePromise`
**Example:**

```ts
const subscription = await db.live(new Table('users'))
    .fields('name', 'email', 'status');

for await (const update of subscription) {
    // Only includes specified fields
    console.log(update.result); // { name, email, status }
}
```

* * *
####  `.value()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#value)
Return only the value of a specific field in updates.
Method Syntax

```ts
livePromise.value(field)
```

**Parameters:**  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `field`  | `Field<T>`  | Field name to extract.  |  
**Returns:** `ManagedLivePromise`
**Example:**

```ts
const subscription = await db.live(new Table('users'))
    .value('name');

for await (const update of subscription) {
    console.log('Name changed:', update.result); // Just the name string
}
```

* * *
####  `.where()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#where)
Filter live updates to only receive records matching the condition.
Method Syntax

```ts
livePromise.where(expr)
```

**Parameters:**  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `expr`  | `ExprLike`  |  Condition expression to filter updates (string or [Expression](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)object).  |  
**Returns:** `ManagedLivePromise`
**Example:**

```ts
const subscription = await db.live(new Table('users'))
    .where('age >= 18');

for await (const update of subscription) {
    // Only receives updates for users with age >= 18
    console.log(update.action, update.result);
}
```

* * *
####  `.fetch()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#fetch)
Fetch related records in live updates.
Method Syntax

```ts
livePromise.fetch(...fields)
```

**Parameters:**  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Field<T>[]`  | Related fields to fetch.  |  
**Returns:** `ManagedLivePromise`
**Example:**

```ts
const subscription = await db.live(new Table('posts'))
    .fetch('author', 'comments');

for await (const update of subscription) {
    // author and comments are fully populated
    console.log('Post by:', update.result.author.name);
}
```

* * *
####  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#compile)
Compile the query into a BoundQuery.
Method Syntax

```ts
livePromise.compile()
```

**Returns:** `BoundQuery` - The compiled query
* * *
###  Live subscription methods[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#live-subscription-methods)
Once awaited, a `ManagedLivePromise` returns a `LiveSubscription` object:
####  Iteration[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#iteration)

```ts
for await (const update of subscription) {
    console.log(update.action); // 'CREATE' | 'UPDATE' | 'DELETE'
    console.log(update.result); // The record data
}
```

####  `.kill()`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#kill)
Kill the live query subscription.

```ts
await subscription.kill();
```

##  `UnmanagedLivePromise`[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#unmanagedlivepromise)
An unmanaged subscription to an existing live query by its UUID.
**Returned by:** [`SurrealQueryable.liveOf()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof)
###  Usage[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#usage)

```ts
const liveQueryId: Uuid = /* from somewhere */;
const subscription = await db.liveOf(liveQueryId);

for await (const update of subscription) {
    console.log(update);
}
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#complete-examples)
###  Basic live query[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#basic-live-query)

```ts
import { Surreal, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Subscribe to all user changes
const subscription = await db.live(new Table('users'));

for await (const update of subscription) {
    console.log(`${update.action}:`, update.result);
}

// Clean up when done
await subscription.kill();
```

###  Filtered live query[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#filtered-live-query)

```ts
// Only receive updates for active users
const subscription = await db.live(new Table('users'))
    .where('status = "active"');

for await (const update of subscription) {
    if (update.action === 'CREATE') {
        console.log('New active user:', update.result);
    } else if (update.action === 'UPDATE') {
        console.log('Active user updated:', update.result);
    } else if (update.action === 'DELETE') {
        console.log('Active user deleted:', update.result);
    }
}
```

###  Live query with specific fields[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#live-query-with-specific-fields)

```ts
const subscription = await db.live(new Table('users'))
    .fields('name', 'email', 'status')
    .where('role = "admin"');

for await (const update of subscription) {
    // Only receives name, email, status fields
    console.log('Admin update:', update.result);
}

await subscription.kill();
```

###  Diff-based updates[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#diff-based-updates)

```ts
// Get only changes, not full records
const subscription = await db.live(new Table('users')).diff();

for await (const update of subscription) {
    if (update.action === 'UPDATE') {
        console.log('Changed fields:', update.diff);
        // { email: 'new@example.com' } instead of full record
    }
}
```

###  Live query with relations[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#live-query-with-relations)

```ts
const subscription = await db.live(new Table('posts'))
    .fetch('author', 'comments')
    .where('published = true');

for await (const update of subscription) {
    // author is fully populated
    console.log('Post by:', update.result.author.name);
    console.log('Comments:', update.result.comments.length);
}
```

###  Real-time dashboard[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#real-time-dashboard)

```ts
async function monitorUsers(callback: (stats: any) => void) {
    const subscription = await db.live(new Table('users'));
    
    const stats = {
        created: 0,
        updated: 0,
        deleted: 0
    };
    
    for await (const update of subscription) {
        if (update.action === 'CREATE') stats.created++;
        else if (update.action === 'UPDATE') stats.updated++;
        else if (update.action === 'DELETE') stats.deleted++;
        
        callback(stats);
    }
}

monitorUsers((stats) => {
    console.log('User stats:', stats);
});
```

###  Watch specific record[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#watch-specific-record)

```ts
// Subscribe to changes on a specific record
const subscription = await db.live(new RecordId('users', 'john'));

for await (const update of subscription) {
    if (update.action === 'UPDATE') {
        console.log('John was updated:', update.result);
    } else if (update.action === 'DELETE') {
        console.log('John was deleted');
        break;
    }
}
```

###  Auto-reconnect live query[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#auto-reconnect-live-query)

```ts
let subscription: LiveSubscription | null = null;

async function setupLiveQuery() {
    subscription = await db.live(new Table('users'))
        .where('active = true');
    
    for await (const update of subscription) {
        console.log('Update:', update);
    }
}

// Handle reconnection
db.subscribe('reconnecting', () => {
    console.log('Connection lost, live query will be restored...');
});

db.subscribe('connected', async () => {
    console.log('Reconnected, live queries restored automatically');
});

await setupLiveQuery();
```

###  Cleanup pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#cleanup-pattern)

```ts
const subscriptions: LiveSubscription[] = [];

// Create multiple subscriptions
subscriptions.push(await db.live(new Table('users')));
subscriptions.push(await db.live(new Table('posts')));
subscriptions.push(await db.live(new Table('comments')));

// Process updates
// ...

// Cleanup all subscriptions
async function cleanup() {
    await Promise.all(subscriptions.map(sub => sub.kill()));
    console.log('All subscriptions cleaned up');
}

// Call on app shutdown
await cleanup();
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#error-handling)

```ts
try {
    const subscription = await db.live(new Table('users'));
    
    try {
        for await (const update of subscription) {
            await processUpdate(update);
        }
    } catch (error) {
        console.error('Error processing update:', error);
    } finally {
        await subscription.kill();
    }
} catch (error) {
    if (error instanceof LiveSubscriptionError) {
        console.error('Failed to create subscription:', error);
    }
}
```

##  Update message structure[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#update-message-structure)
Each update message conforms to the [`LiveMessage`](/docs/reference/javascript/api/types/#livemessage) interface with `action`, `result`, and optional `diff` properties.
###  Processing updates[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#processing-updates)

```ts
for await (const update of subscription) {
    switch (update.action) {
        case 'CREATE':
            await handleCreate(update.result);
            break;
        case 'UPDATE':
            await handleUpdate(update.result, update.diff);
            break;
        case 'DELETE':
            await handleDelete(update.result);
            break;
    }
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/live-promise#see-also)
  * •
[SurrealQueryable.live()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live) - Create managed live subscription
  * •
[SurrealQueryable.liveOf()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof) - Subscribe to existing live query
  * •
[Live queries guide](https://surrealdb.com/docs/reference/query-language/statements/live-select) - SurrealQL LIVE documentation
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
