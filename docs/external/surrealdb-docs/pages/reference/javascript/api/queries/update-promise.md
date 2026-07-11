---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/update-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/update-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/update-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/update-promise

The `UpdatePromise` class provides a chainable interface for configuring UPDATE operations before execution. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.update()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#update)
**Source:** [query/update.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/update.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#type-parameters)
  * •
`T` - The result type
  * •
`I` - The input type for record data
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#configuration-methods)
###  `.content()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#content)
Replace the entire record content with new data.
Method Syntax

```ts
updatePromise.content(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Complete replacement data (excluding id field).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns)
`UpdatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#example)

```ts
const user = await db.update(new RecordId('users', 'john'))
    .content({
        name: 'John Smith',
        email: 'john.smith@example.com',
        age: 31
    });
// Replaces all fields
```

* * *
###  `.merge()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#merge)
Merge partial updates into the existing record.
Method Syntax

```ts
updatePromise.merge(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Partial data to merge (only specified fields are updated).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-1)
`UpdatePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#examples)
Update Single Field

```ts
const user = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'newemail@example.com' });
// Only updates email, other fields unchanged
```

Update Multiple Fields

```ts
const user = await db.update(new RecordId('users', 'john'))
    .merge({
        email: 'new@example.com',
        age: 31,
        updated_at: DateTime.now()
    });
```

* * *
###  `.replace()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#replace)
Replace specific fields while keeping others unchanged.
Method Syntax

```ts
updatePromise.replace(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | Fields to replace.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-2)
`UpdatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#example-1)

```ts
const user = await db.update(new RecordId('users', 'john'))
    .replace({ status: 'inactive' });
```

* * *
###  `.patch()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#patch)
Apply JSON Patch operations to update the record.
Method Syntax

```ts
updatePromise.patch(operations)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `operations`  | `Values<I>`  | JSON Patch operations to apply.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-3)
`UpdatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#example-2)

```ts
const user = await db.update(new RecordId('users', 'john'))
    .patch([
        { op: 'replace', path: '/email', value: 'new@example.com' },
        { op: 'add', path: '/tags/-', value: 'premium' }
    ]);
```

* * *
###  `.where()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#where)
Add a WHERE clause to conditionally update records.
Method Syntax

```ts
updatePromise.where(expr)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `expr`  | `ExprLike`  |  The condition expression (string or [Expression](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)object).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-4)
`UpdatePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#examples-1)
Conditional Update

```ts
const users = await db.update(new Table('users'))
    .merge({ verified: true })
    .where('email_confirmed = true');
```

With Expression Builder

```ts
import { expr } from 'surrealdb';

const users = await db.update(new Table('users'))
    .merge({ status: 'inactive' })
    .where(expr(({ lt, field }) => 
        lt(field('last_login'), DateTime.parse('2024-01-01'))
    ));
```

* * *
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#output)
Specify what to return from the update operation.
Method Syntax

```ts
updatePromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  `"NONE"`, `"BEFORE"`, `"AFTER"`, `"DIFF"`, or field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-5)
`UpdatePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#examples-2)
Return Updated Record

```ts
const user = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'new@example.com' })
    .output('AFTER');
// Returns the record after update
```

Return Only Changed Fields

```ts
const diff = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'new@example.com' })
    .output('DIFF');
// Returns only the changed fields
```

Return Original Record

```ts
const original = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'new@example.com' })
    .output('BEFORE');
// Returns the record before update
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#timeout)
Set a timeout for the operation.
Method Syntax

```ts
updatePromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-6)
`UpdatePromise` - Chainable promise
* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
updatePromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-7)
`UpdatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#example-3)

```ts
await db.update(new RecordId('counter', 'c'))
    .merge({ n: 1 })
    .retry({ attempts: 3 });
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#json)
Return result as JSON string.
Method Syntax

```ts
updatePromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-8)
`UpdatePromise` - Promise returning JSON string
* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
updatePromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-9)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#example-4)

```ts
const query = db.update(new Table('users'))
    .merge({ status: 'active' })
    .where('verified = true')
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#stream)
Stream results as they arrive.
Method Syntax

```ts
updatePromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#returns-10)
`AsyncIterableIterator` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#complete-examples)
###  Basic updates[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#basic-updates)

```ts
import { Surreal, RecordId, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Update single record with merge
const user = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'john.new@example.com' });

// Replace entire record content
const user = await db.update(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com',
        age: 30,
        role: 'admin'
    });
```

###  Bulk updates[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#bulk-updates)

```ts
// Update all users matching condition
const updated = await db.update(new Table('users'))
    .merge({ verified: true })
    .where('email_confirmed = true');

console.log(`Updated ${updated.length} users`);
```

###  Conditional updates[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#conditional-updates)

```ts
// Update only if condition is met
const users = await db.update(new Table('users'))
    .merge({ status: 'inactive' })
    .where('last_login < $date', { 
        date: DateTime.parse('2024-01-01') 
    });
```

###  Complex merge[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#complex-merge)

```ts
const user = await db.update(new RecordId('users', 'john'))
    .merge({
        profile: {
            bio: 'Updated bio',
            avatar: 'new-avatar.jpg'
        },
        settings: {
            notifications: true,
            theme: 'dark'
        },
        updated_at: DateTime.now()
    });
```

###  Tracking changes[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#tracking-changes)

```ts
const diff = await db.update(new RecordId('users', 'john'))
    .merge({ 
        email: 'new@example.com',
        age: 31 
    })
    .output('DIFF');

console.log('Changed fields:', diff);
// { email: 'new@example.com', age: 31 }
```

###  Batch update with stream[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#batch-update-with-stream)

```ts
const updates = db.update(new Table('users'))
    .merge({ last_check: DateTime.now() })
    .where('active = true');

for await (const user of updates.stream()) {
    console.log(`Updated user: ${user.id}`);
}
```

##  Difference between methods[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#difference-between-methods)
###  `.content()` vs `.merge()` vs `.replace()`[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#content-vs-merge-vs-replace)

```ts
// CONTENT: Replaces entire record
await db.update(recordId).content({
    name: 'John',
    email: 'john@example.com'
});
// Result: ONLY name and email exist, all other fields removed

// MERGE: Updates specified fields only
await db.update(recordId).merge({
    email: 'john@example.com'
});
// Result: Only email updated, all other fields preserved

// REPLACE: Similar to merge but with different semantics
await db.update(recordId).replace({
    email: 'john@example.com'
});
// Result: Replaces specified fields
```

##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#chaining-pattern)

```ts
const result = await db.update(new Table('users'))
    .merge({ status: 'active' })
    .where('verified = true')
    .output('AFTER')
    .timeout(Duration.parse('5s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise#see-also)
  * •
[SurrealQueryable.update()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#update) - Method that returns UpdatePromise
  * •
[UpsertPromise](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise) - Insert or update
  * •
[CreatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise) - Create records
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
