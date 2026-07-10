---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise

The `InsertPromise` class provides a chainable interface for configuring INSERT operations for bulk record insertion. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.insert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#insert)
**Source:** [query/insert.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/insert.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#type-parameters)
  * •
`T` - The result type
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#configuration-methods)
###  `.relation()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#relation)
Configure the insert to work with relation (edge) records instead of regular records.
Method Syntax

```ts
insertPromise.relation()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns)
`InsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#example)

```ts
const edges = await db.insert([
    {
        id: new RecordId('likes', '1'),
        in: new RecordId('users', 'john'),
        out: new RecordId('posts', '1')
    }
]).relation();
```

* * *
###  `.ignore()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#ignore)
Ignore records that already exist (skip duplicates without error).
Method Syntax

```ts
insertPromise.ignore()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-1)
`InsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#example-1)

```ts
const users = await db.insert([
    { id: new RecordId('users', 'john'), name: 'John' },
    { id: new RecordId('users', 'jane'), name: 'Jane' }
]).ignore();
// If 'john' exists, it's skipped; 'jane' is inserted
```

* * *
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#output)
Specify which fields to return in the response.
Method Syntax

```ts
insertPromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  `"NONE"`, `"AFTER"`, or specific field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-2)
`InsertPromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#examples)
Return Specific Fields

```ts
const users = await db.insert(userData)
    .output('id', 'name');
// Returns only id and name
```

Return Nothing

```ts
await db.insert(logData)
    .output('NONE');
// No return value, useful for performance
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#timeout)
Set a timeout for the operation.
Method Syntax

```ts
insertPromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-3)
`InsertPromise` - Chainable promise
* * *
###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#version)
Insert at a specific version (for versioned storage engines).
Method Syntax

```ts
insertPromise.version(timestamp)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `timestamp`  | [DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | The version timestamp.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-4)
`InsertPromise` - Chainable promise
* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
insertPromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-5)
`InsertPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#example-2)

```ts
await db.insert(new Table('users')).content(users).retry({ attempts: 3 });
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#json)
Return result as JSON string.
Method Syntax

```ts
insertPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-6)
`InsertPromise` - Promise returning JSON string
* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
insertPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-7)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#example-3)

```ts
const query = db.insert(records)
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#stream)
Stream results as records are inserted.
Method Syntax

```ts
insertPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#returns-8)
`AsyncIterableIterator` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#complete-examples)
###  Basic insertion[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#basic-insertion)

```ts
import { Surreal, RecordId } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Insert single record
const user = await db.insert({
    id: new RecordId('users', 'alice'),
    name: 'Alice',
    email: 'alice@example.com'
});

// Insert multiple records
const users = await db.insert([
    { id: new RecordId('users', 'bob'), name: 'Bob' },
    { id: new RecordId('users', 'carol'), name: 'Carol' }
]);
```

###  Insert into table[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#insert-into-table)

```ts
// Let database generate IDs
const users = await db.insert(new Table('users'), [
    { name: 'Dave', email: 'dave@example.com' },
    { name: 'Eve', email: 'eve@example.com' }
]);
```

###  Ignore duplicates[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#ignore-duplicates)

```ts
// Skip existing records without error
const users = await db.insert([
    { id: new RecordId('users', 'john'), name: 'John' },
    { id: new RecordId('users', 'jane'), name: 'Jane' }
]).ignore();

console.log(`Inserted ${users.length} new users`);
```

###  Bulk insert with streaming[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#bulk-insert-with-streaming)

```ts
const largeDataset = generateThousandsOfRecords();

let count = 0;
for await (const record of db.insert(largeDataset).stream()) {
    count++;
    if (count % 100 === 0) {
        console.log(`Inserted ${count} records`);
    }
}
```

###  Insert relations (edges)[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#insert-relations-edges)

```ts
const likes = await db.insert([
    {
        id: new RecordId('likes', '1'),
        in: new RecordId('users', 'john'),
        out: new RecordId('posts', '1'),
        created_at: DateTime.now()
    },
    {
        id: new RecordId('likes', '2'),
        in: new RecordId('users', 'jane'),
        out: new RecordId('posts', '1'),
        created_at: DateTime.now()
    }
]).relation();
```

###  Optimised insertion[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#optimised-insertion)

```ts
// Don't wait for return values
await db.insert(logEntries)
    .output('NONE');
// Faster execution when you don't need the results
```

###  Insert with timeout[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#insert-with-timeout)

```ts
const users = await db.insert(largeDataset)
    .timeout(Duration.parse('30s'));
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#error-handling)

```ts
try {
    const users = await db.insert([
        { id: new RecordId('users', 'existing'), name: 'Test' }
    ]);
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('Duplicate key error:', error.message);
        
        // Retry with ignore
        const users = await db.insert([
            { id: new RecordId('users', 'existing'), name: 'Test' }
        ]).ignore();
    }
}
```

###  Batch processing[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#batch-processing)

```ts
const BATCH_SIZE = 100;
const allUsers = [...]; // Large array

for (let i = 0; i < allUsers.length; i += BATCH_SIZE) {
    const batch = allUsers.slice(i, i + BATCH_SIZE);
    await db.insert(batch);
    console.log(`Inserted batch ${i / BATCH_SIZE + 1}`);
}
```

##  INSERT vs CREATE[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#insert-vs-create)
###  When to use INSERT vs CREATE[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#when-to-use-insert-vs-create)

```ts
// CREATE: For single records, with more configuration options
const user = await db.create(new RecordId('users', 'john'))
    .content(userData);

// INSERT: For bulk operations, optimized for performance
const users = await db.insert([
    { id: new RecordId('users', 'alice'), ...data1 },
    { id: new RecordId('users', 'bob'), ...data2 },
    { id: new RecordId('users', 'carol'), ...data3 }
]);
```

##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#chaining-pattern)

```ts
const result = await db.insert(records)
    .ignore()
    .output('id', 'name')
    .timeout(Duration.parse('10s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise#see-also)
  * •
[SurrealQueryable.insert()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#insert) - Method that returns InsertPromise
  * •
[CreatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise) - Single record creation
  * •
[UpsertPromise](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise) - Insert or update
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
