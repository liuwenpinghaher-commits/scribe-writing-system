---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/create-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/create-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/create-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/create-promise

The `CreatePromise` class provides a chainable interface for configuring CREATE operations before execution. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.create()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#create)
**Source:** [query/create.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/create.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#type-parameters)
  * •
`T` - The result type
  * •
`I` - The input type for record data
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#configuration-methods)
###  `.content()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#content)
Set the complete content for the new record.
Method Syntax

```ts
createPromise.content(data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `data`  | `Values<I>`  | The record data (excluding id field).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns)
`CreatePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#examples)
Create with Specific ID

```ts
const user = await db.create(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com',
        age: 30
    });
```

Create with Auto-Generated ID

```ts
const user = await db.create(new Table('users'))
    .content({
        name: 'Jane Doe',
        email: 'jane@example.com',
        age: 28
    });
```

* * *
###  `.patch()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#patch)
Apply JSON Patch operations to set record data.
Method Syntax

```ts
createPromise.patch(operations)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `operations`  | `Values<I>`  | JSON Patch operations to apply.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-1)
`CreatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example)

```ts
const user = await db.create(new Table('users'))
    .patch([
        { op: 'add', path: '/name', value: 'John' },
        { op: 'add', path: '/email', value: 'john@example.com' }
    ]);
```

* * *
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#output)
Specify which fields to return in the response.
Method Syntax

```ts
createPromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  Output specification: `"NONE"`, `"BEFORE"`, `"AFTER"`, `"DIFF"`, or field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-2)
`CreatePromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#examples-1)
Return Specific Fields

```ts
const user = await db.create(new Table('users'))
    .content(userData)
    .output('id', 'name');
// Returns only id and name
```

Return Full Record

```ts
const user = await db.create(new Table('users'))
    .content(userData)
    .output('AFTER');
// Returns complete created record
```

Return Nothing

```ts
await db.create(new Table('logs'))
    .content(logData)
    .output('NONE');
// Returns undefined, useful for fire-and-forget
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#timeout)
Set a timeout for the operation.
Method Syntax

```ts
createPromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait for operation completion.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-3)
`CreatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-1)

```ts
const user = await db.create(new Table('users'))
    .content(userData)
    .timeout(Duration.parse('5s'));
```

* * *
###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#version)
Create the record at a specific version (for versioned storage engines).
Method Syntax

```ts
createPromise.version(timestamp)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `timestamp`  | [DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | The version timestamp.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-4)
`CreatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-2)

```ts
const user = await db.create(new Table('users'))
    .content(userData)
    .version(DateTime.now());
```

* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
createPromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-5)
`CreatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-3)

```ts
const user = await db.create(new Table('users'))
    .content(userData)
    .retry({ attempts: 3 });
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#json)
Return result as JSON string instead of parsed object.
Method Syntax

```ts
createPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-6)
`CreatePromise` - Promise returning JSON string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-4)

```ts
const jsonString = await db.create(new Table('users'))
    .content(userData)
    .json();
```

* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
createPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-7)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-5)

```ts
const query = db.create(new Table('users'))
    .content(userData)
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#stream)
Stream the operation result (useful when creating multiple records).
Method Syntax

```ts
createPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#returns-8)
`AsyncIterableIterator` - Async iterator
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#example-6)

```ts
const results = db.create(new Table('users'))
    .content(multipleUsers);
    
for await (const user of results.stream()) {
    console.log('Created:', user);
}
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#complete-examples)
###  Basic creation[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#basic-creation)

```ts
import { Surreal, RecordId, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create with specific ID
const user = await db.create(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin'
    });

// Create with auto-generated ID
const post = await db.create(new Table('posts'))
    .content({
        title: 'Hello World',
        content: 'My first post',
        author: new RecordId('users', 'john')
    });
```

###  Creation with output control[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#creation-with-output-control)

```ts
// Only return the ID
const { id } = await db.create(new Table('users'))
    .content(userData)
    .output('id');

// Return specific fields
const summary = await db.create(new Table('users'))
    .content(userData)
    .output('id', 'name', 'created_at');
```

###  Bulk creation with streaming[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#bulk-creation-with-streaming)

```ts
const users = [
    { name: 'Alice', email: 'alice@example.com' },
    { name: 'Bob', email: 'bob@example.com' },
    { name: 'Carol', email: 'carol@example.com' }
];

for await (const user of db.create(new Table('users')).content(users).stream()) {
    console.log(`Created user: ${user.name} with ID: ${user.id}`);
}
```

###  With relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#with-relationships)

```ts
const post = await db.create(new Table('posts'))
    .content({
        title: 'New Post',
        content: 'Post content here',
        author: new RecordId('users', 'john'),
        tags: [
            new RecordId('tags', 'javascript'),
            new RecordId('tags', 'tutorial')
        ],
        created_at: DateTime.now()
    });
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#error-handling)

```ts
try {
    const user = await db.create(new RecordId('users', 'existing'))
        .content(userData);
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('User already exists:', error.message);
    }
}
```

###  With timeout[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#with-timeout)

```ts
const user = await db.create(new Table('users'))
    .content(complexUserData)
    .timeout(Duration.parse('10s'));
```

##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#chaining-pattern)
All configuration methods return a new `CreatePromise`, allowing method chaining:

```ts
const result = await db.create(new Table('users'))
    .content(userData)
    .output('id', 'name', 'email')
    .timeout(Duration.parse('5s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise#see-also)
  * •
[SurrealQueryable.create()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#create) - Method that returns CreatePromise
  * •
[InsertPromise](https://surrealdb.com/docs/reference/javascript/api/queries/insert-promise) - Bulk insertion
  * •
[UpsertPromise](https://surrealdb.com/docs/reference/javascript/api/queries/upsert-promise) - Insert or replace
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
