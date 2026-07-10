---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise

The `UpsertPromise` class provides a chainable interface for configuring UPSERT operations (insert if not exists, replace if exists). It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
Warning
UPSERT replaces the entire record if it exists. Use [`update().merge()`](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#merge) for partial updates.
**Returned by:** [`SurrealQueryable.upsert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#upsert)
**Source:** [query/upsert.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/upsert.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#type-parameters)
  * •
`T` - The result type
  * •
`I` - The input type for record data
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#configuration-methods)
###  `.content()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#content)
Set the complete content for the record (insert or replace).
Method Syntax

```ts
upsertPromise.content(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Complete record data (excluding id field).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns)
`UpsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#example)

```ts
const user = await db.upsert(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com',
        age: 30
    });
// Inserts if not exists, replaces entirely if exists
```

* * *
###  `.merge()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#merge)
Merge data into the record (insert if not exists, merge if exists).
Method Syntax

```ts
upsertPromise.merge(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Partial data to merge.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-1)
`UpsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#example-1)

```ts
const user = await db.upsert(new RecordId('users', 'john'))
    .merge({
        name: 'John Doe',
        last_login: DateTime.now()
    });
// If exists: merges fields; if not: creates with these fields
```

* * *
###  `.replace()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#replace)
Replace specific fields.
Method Syntax

```ts
upsertPromise.replace(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Fields to replace.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-2)
`UpsertPromise` - Chainable promise
* * *
###  `.patch()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#patch)
Apply JSON Patch operations.
Method Syntax

```ts
upsertPromise.patch(operations)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `operations`  | `Values<I>`  | JSON Patch operations.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-3)
`UpsertPromise` - Chainable promise
* * *
###  `.where()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#where)
Add a WHERE clause for conditional upsert.
Method Syntax

```ts
upsertPromise.where(expr)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `expr`  | `ExprLike`  |  The condition expression (string or [Expression](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)object).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-4)
`UpsertPromise` - Chainable promise
* * *
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#output)
Specify what to return.
Method Syntax

```ts
upsertPromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  `"NONE"`, `"BEFORE"`, `"AFTER"`, `"DIFF"`, or field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-5)
`UpsertPromise` - Chainable promise
* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#timeout)
Set operation timeout.
Method Syntax

```ts
upsertPromise.timeout(duration)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-6)
`UpsertPromise` - Chainable promise
* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
upsertPromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-7)
`UpsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#example-2)

```ts
await db.upsert(new RecordId('users', 'john'))
    .merge({ visits: 1 })
    .retry();
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#json)
Return result as JSON string.
Method Syntax

```ts
upsertPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-8)
`UpsertPromise` - Promise returning JSON string
* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
upsertPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-9)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#example-3)

```ts
const query = db.upsert(new RecordId('users', 'john'))
    .content(userData)
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#stream)
Stream results as they arrive.
Method Syntax

```ts
upsertPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#returns-10)
`AsyncIterableIterator` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#complete-examples)
###  Basic upsert[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#basic-upsert)

```ts
import { Surreal, RecordId } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Upsert: insert if not exists, replace if exists
const user = await db.upsert(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com',
        role: 'user'
    });
```

###  Upsert with merge[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#upsert-with-merge)

```ts
// Safer: merge instead of replace
const user = await db.upsert(new RecordId('users', 'john'))
    .merge({
        last_login: DateTime.now(),
        login_count: 1
    });
// If user exists: only updates these fields
// If not: creates user with these fields
```

###  Bulk upsert[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#bulk-upsert)

```ts
const users = await db.upsert(new Table('users'))
    .content(userDataArray);
```

###  Track changes[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#track-changes)

```ts
const result = await db.upsert(new RecordId('users', 'john'))
    .content(userData)
    .output('DIFF');

if (result) {
    console.log('Created or updated:', result);
}
```

###  Conditional upsert[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#conditional-upsert)

```ts
const user = await db.upsert(new RecordId('users', 'john'))
    .merge({ status: 'active' })
    .where('verified = true');
```

##  UPSERT vs CREATE vs UPDATE[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#upsert-vs-create-vs-update)

```ts
// CREATE: Fails if record exists
try {
    await db.create(recordId).content(data);
} catch (error) {
    // Error if exists
}

// UPDATE: Fails if record doesn't exist
try {
    await db.update(recordId).merge(data);
} catch (error) {
    // Error if not found
}

// UPSERT: Works in both cases
await db.upsert(recordId).content(data);
// Always succeeds
```

##  Use cases[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#use-cases)
###  Session management[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#session-management)

```ts
// Update session or create new one
async function updateSession(sessionId: string, data: SessionData) {
    return db.upsert(new RecordId('sessions', sessionId))
        .merge({
            ...data,
            last_activity: DateTime.now()
        });
}
```

###  Cache pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#cache-pattern)

```ts
// Write-through cache
async function cacheSet(key: string, value: unknown) {
    return db.upsert(new RecordId('cache', key))
        .content({
            value,
            expires_at: DateTime.now().plus(Duration.parse('1h'))
        });
}
```

###  Counter pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#counter-pattern)

```ts
// Increment counter or initialize
const counter = await db.upsert(new RecordId('counters', 'page_views'))
    .merge({
        count: 1,
        last_increment: DateTime.now()
    });
```

##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#chaining-pattern)

```ts
const result = await db.upsert(new RecordId('users', 'john'))
    .content(userData)
    .output('AFTER')
    .timeout(Duration.parse('5s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise#see-also)
  * •
[SurrealQueryable.upsert()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#upsert) - Method that returns UpsertPromise
  * •
[CreatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise) - Create only
  * •
[UpdatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise) - Update only
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
