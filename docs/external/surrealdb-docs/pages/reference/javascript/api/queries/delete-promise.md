---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise

The `DeletePromise` class provides a chainable interface for configuring DELETE operations before execution. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.delete()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#delete)
**Source:** [query/delete.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/delete.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#type-parameters)
  * •
`T` - The result type (deleted record data)
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#configuration-methods)
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#output)
Specify what to return from the delete operation.
Method Syntax

```ts
deletePromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  `"NONE"`, `"BEFORE"`, or specific field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns)
`DeletePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#examples)
Return Deleted Record

```ts
const deleted = await db.delete(new RecordId('users', 'john'))
    .output('BEFORE');
// Returns the record before deletion
```

Return Specific Fields

```ts
const deleted = await db.delete(new RecordId('users', 'john'))
    .output('id', 'name', 'email');
// Returns only specified fields of deleted record
```

Return Nothing

```ts
await db.delete(new RecordId('logs', '123'))
    .output('NONE');
// Faster when you don't need the data
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#timeout)
Set a timeout for the operation.
Method Syntax

```ts
deletePromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-1)
`DeletePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#example)

```ts
const deleted = await db.delete(new Table('users'))
    .timeout(Duration.parse('10s'));
```

* * *
###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#version)
Delete at a specific version (for versioned storage engines).
Method Syntax

```ts
deletePromise.version(timestamp)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `timestamp`  | [DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | The version timestamp.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-2)
`DeletePromise` - Chainable promise
* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
deletePromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-3)
`DeletePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#example-1)

```ts
await db.delete(new RecordId('users', 'john')).retry();
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#json)
Return result as JSON string.
Method Syntax

```ts
deletePromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-4)
`DeletePromise` - Promise returning JSON string
* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
deletePromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-5)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#example-2)

```ts
const query = db.delete(new Table('temp_data'))
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#stream)
Stream deleted records as they are removed.
Method Syntax

```ts
deletePromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#returns-6)
`AsyncIterableIterator` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#complete-examples)
###  Basic deletion[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#basic-deletion)

```ts
import { Surreal, RecordId, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Delete single record
const deleted = await db.delete(new RecordId('users', 'john'));
console.log('Deleted user:', deleted);

// Delete by range
const deleted = await db.delete(
    new RecordIdRange('users', 'a', 'f')
);
console.log(`Deleted ${deleted.length} users`);

// Delete entire table
const deleted = await db.delete(new Table('temp_data'));
console.log(`Deleted ${deleted.length} records`);
```

###  Capture deleted data[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#capture-deleted-data)

```ts
// Store deleted data before removing
const user = await db.delete(new RecordId('users', 'john'))
    .output('BEFORE');

// Archive the deleted user
await db.create(new RecordId('archived_users', user.id))
    .content({
        ...user,
        deleted_at: DateTime.now()
    });
```

###  Conditional deletion[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#conditional-deletion)

```ts
// Note: WHERE clauses are not directly supported on delete promises
// Use query() for conditional deletes
const result = await db.query(
    surql`DELETE FROM users WHERE inactive = true`
).collect();

console.log(`Deleted ${result[0].result.length} inactive users`);
```

###  Bulk deletion with streaming[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#bulk-deletion-with-streaming)

```ts
const deletedRecords = db.delete(new Table('old_logs'));

let count = 0;
for await (const record of deletedRecords.stream()) {
    count++;
    if (count % 100 === 0) {
        console.log(`Deleted ${count} records`);
    }
}
```

###  Soft delete pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#soft-delete-pattern)

```ts
// Instead of deleting, mark as deleted
const user = await db.update(new RecordId('users', 'john'))
    .merge({
        deleted: true,
        deleted_at: DateTime.now()
    });

// Actual delete with backup
const user = await db.delete(new RecordId('users', 'john'))
    .output('BEFORE');

if (user) {
    await db.create(new RecordId('deleted_users', user.id))
        .content(user);
}
```

###  Delete with error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#delete-with-error-handling)

```ts
try {
    const deleted = await db.delete(new RecordId('users', 'john'));
    
    if (!deleted) {
        console.log('User not found');
    } else {
        console.log('User deleted successfully');
    }
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('Delete failed:', error.message);
    }
}
```

###  Performance optimization[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#performance-optimization)

```ts
// Don't wait for deleted data if not needed
await db.delete(new Table('temp_cache'))
    .output('NONE');
// Faster execution
```

###  Delete with timeout[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#delete-with-timeout)

```ts
// For large deletions
const deleted = await db.delete(new Table('old_logs'))
    .timeout(Duration.parse('30s'));
```

###  Cascading deletes[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#cascading-deletes)

```ts
// Delete user and all related data
const userId = new RecordId('users', 'john');

// Delete user
const user = await db.delete(userId);

// Delete related posts
await db.query(
    surql`DELETE FROM posts WHERE author = ${userId}`
).collect();

// Delete related comments
await db.query(
    surql`DELETE FROM comments WHERE author = ${userId}`
).collect();

console.log('User and related data deleted');
```

###  Batch deletion[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#batch-deletion)

```ts
const idsToDelete = ['user1', 'user2', 'user3'];

for (const id of idsToDelete) {
    await db.delete(new RecordId('users', id));
}

// Or using query for better performance
const result = await db.query(
    surql`DELETE FROM users WHERE id IN ${idsToDelete.map(id => new RecordId('users', id))}`
).collect();
```

###  Archive before delete[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#archive-before-delete)

```ts
async function archiveAndDelete(recordId: RecordId) {
    // Get the record
    const record = await db.select(recordId);
    
    if (!record) {
        throw new Error('Record not found');
    }
    
    // Archive it
    await db.create(new RecordId('archive', record.id))
        .content({
            ...record,
            archived_at: DateTime.now()
        });
    
    // Delete original
    await db.delete(recordId).output('NONE');
    
    return record;
}

await archiveAndDelete(new RecordId('users', 'john'));
```

##  Important notes[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#important-notes)
Warning
DELETE operations are permanent and cannot be undone. Always ensure you have backups or use the `.output('BEFORE')` method to capture data before deletion.
> !NOTE: Tip  
>  For conditional deletions, use [`db.query()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) with a DELETE statement including a WHERE clause.
##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#chaining-pattern)

```ts
const result = await db.delete(new Table('users'))
    .output('BEFORE')
    .timeout(Duration.parse('10s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/delete-promise#see-also)
  * •
[SurrealQueryable.delete()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#delete) - Method that returns DeletePromise
  * •
[UpdatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/update-promise) - Update records
  * •
[Query](https://surrealdb.com/docs/reference/javascript/api/queries/query) - Raw SurrealQL for conditional deletes
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
