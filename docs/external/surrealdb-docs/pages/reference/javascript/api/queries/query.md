---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/query"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/query

Source: https://surrealdb.com/docs/reference/javascript/api/queries/query

The `Query` class provides a configurable interface for executing raw SurrealQL statements with support for streaming, batch processing, and response handling. It extends `Promise`, allowing you to `await` it directly or use specialized methods.
**Returned by:** [`SurrealQueryable.query()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query)
**Source:** [query/query.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/query.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#type-parameters)
  * •
`R extends unknown[]` - Array of result types for each query statement
  * •
`J extends boolean` - Boolean indicating if result is JSON (default: `false`)

##  Methods[](https://surrealdb.com/docs/reference/javascript/api/queries/query#methods)
###  `.collect()`[](https://surrealdb.com/docs/reference/javascript/api/queries/query#collect)
Collect and return the results of all queries at once. If any query fails, the promise rejects.
You can optionally specify which query indexes to collect.
Method Syntax

```ts
query.collect<T>(...queryIndexes?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `queryIndexes`  | `number[]`  | Specific query indexes to collect. If omitted, collects all.  |  
####  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#type-parameters-1)
  * •
`T extends unknown[]` - Override result types

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/query#returns)
`Promise>` - Array of results
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/query#examples)
Single Query

```ts
const result = await db.query('SELECT * FROM users').collect();
console.log(result); // [{ success: true, result: [...] }]
```

Multiple Queries with Types

```ts
const [users, posts] = await db.query<[User[], Post[]]>(`
    SELECT * FROM users;
    SELECT * FROM posts;
`).collect();
```

Collect Specific Queries

```ts
const [users] = await db.query(`
    SELECT * FROM users;
    SELECT * FROM posts;
    SELECT * FROM comments;
`).collect<[User[]]>(0); // Only collect first query
```

With Bindings

```ts
const result = await db.query(
    'SELECT * FROM users WHERE age > $age',
    { age: 18 }
).collect();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/query#stream)
Stream response frames as they are received from the database.
Each iteration yields a value frame, error frame, or done frame.
Method Syntax

```ts
query.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/query#returns-1)
`AsyncIterableIterator>` - Async iterator of frames
Each frame is one of three types, distinguished by the `type` property:
**Value Frame** (`type: 'value'`)
  * •
`frame.value` - The result data
  * •
`frame.query` - Query index

**Error Frame** (`type: 'error'`)
  * •
`frame.error` - Error information
  * •
`frame.query` - Query index

**Done Frame** (`type: 'done'`)
  * •
`frame.query` - Query index that completed

####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/query#examples-1)
Stream Processing

```ts
for await (const frame of db.query('SELECT * FROM users').stream()) {
    if (frame.type === 'value') {
        console.log('Received data:', frame.value);
    } else if (frame.type === 'error') {
        console.error('Query error:', frame.error);
    } else if (frame.type === 'done') {
        console.log('Query complete');
    }
}
```

Process Large Results

```ts
let count = 0;
for await (const frame of db.query('SELECT * FROM large_table').stream()) {
    if (frame.type === 'value') {
        await processRecord(frame.value);
        count++;
    }
}
console.log(`Processed ${count} records`);
```

* * *
###  `.responses()`[](https://surrealdb.com/docs/reference/javascript/api/queries/query#responses)
Get individual response objects for each query statement, including success/failure status.
You can optionally specify which query indexes to include.
Method Syntax

```ts
query.responses<T>(...queries?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `queries`  | `number[]`  | Specific query indexes to include. If omitted, includes all.  |  
####  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#type-parameters-2)
  * •
`T extends unknown[]` - Override result types

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/query#returns-2)
`Promise>` - Array of [`QueryResponse`](/docs/reference/javascript/api/types/#queryresponse) objects
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/query#examples-2)
Handle Individual Responses

```ts
const responses = await db.query(`
    SELECT * FROM users;
    INVALID QUERY;
    SELECT * FROM posts;
`).responses();

for (const [index, response] of responses.entries()) {
    if (response.success) {
        console.log(`Query ${index} succeeded:`, response.result);
    } else {
        console.error(`Query ${index} failed:`, response.error.message);
    }
}
```

Check Query Statistics

```ts
const responses = await db.query('SELECT * FROM users').responses();

for (const response of responses) {
    if (response.success && response.stats) {
        console.log('Records scanned:', response.stats.recordsScanned);
        console.log('Duration:', response.stats.duration);
    }
}
```

* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/query#retry)
Retry the whole query with exponential backoff if it fails due to a write conflict. Only applies to `.collect()` (and awaiting the query directly) — it does not apply to `.responses()`, which returns partial results, or `.stream()`, which yields results incrementally and cannot be safely replayed mid-stream.
Off by default, since auto-retrying a non-atomic multi-statement query could apply some statements more than once. Passing an options object (or calling with no arguments) opts the query in. This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
query.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/query#returns-3)
`Query` - Chainable query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/query#example)
Retry on Conflict

```ts
const [n] = await db
    .query<[number]>('UPDATE counter:c SET n += 1 RETURN n')
    .retry({ attempts: 3 })
    .collect();
```

By default, a conflict is detected using [`isRetryableConflict`](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict), which matches on the server's error message. You can supply a custom predicate to override this:
Custom Retry Predicate

```ts
const result = await db
    .query('UPDATE counter:c SET n += 1 RETURN n')
    .retry({ attempts: 5, retryable: (error) => error.message.includes('conflict') })
    .collect();
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/query#json)
Configure the query to return results as JSON strings.
Method Syntax

```ts
query.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/query#returns-4)
`Query` - Query returning JSON strings
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/query#example-1)

```ts
const jsonResults = await db.query('SELECT * FROM users').json().collect();
console.log(typeof jsonResults[0]); // 'string'
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/query#complete-examples)
###  Basic query execution[](https://surrealdb.com/docs/reference/javascript/api/queries/query#basic-query-execution)

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Simple query
const result = await db.query('SELECT * FROM users').collect();
console.log(result[0]); // Array of users

// With await (same as .collect())
const result = await db.query('SELECT * FROM users');
```

###  Parameterised queries[](https://surrealdb.com/docs/reference/javascript/api/queries/query#parameterised-queries)

```ts
// Using bindings object
const result = await db.query(
    'SELECT * FROM users WHERE age > $age AND status = $status',
    { age: 18, status: 'active' }
).collect();

// Using surql template
import { surql } from 'surrealdb';

const minAge = 18;
const result = await db.query(
    surql`SELECT * FROM users WHERE age > ${minAge}`
).collect();
```

###  Multiple statements[](https://surrealdb.com/docs/reference/javascript/api/queries/query#multiple-statements)

```ts
const [users, posts, comments] = await db.query<[User[], Post[], Comment[]]>(`
    SELECT * FROM users;
    SELECT * FROM posts WHERE published = true;
    SELECT * FROM comments WHERE approved = true;
`).collect();

console.log('Users:', users);
console.log('Posts:', posts);
console.log('Comments:', comments);
```

###  Streaming large results[](https://surrealdb.com/docs/reference/javascript/api/queries/query#streaming-large-results)

```ts
const query = db.query('SELECT * FROM large_table');

for await (const frame of query.stream()) {
    if (frame.type === 'value') {
        // Process each chunk as it arrives
        await processChunk(frame.value);
    } else if (frame.type === 'error') {
        console.error('Error:', frame.error);
        break;
    }
}
```

###  Error handling with responses[](https://surrealdb.com/docs/reference/javascript/api/queries/query#error-handling-with-responses)

```ts
const responses = await db.query(`
    CREATE users:john SET name = 'John';
    CREATE users:john SET name = 'Duplicate';
    SELECT * FROM users:john;
`).responses();

for (const [i, response] of responses.entries()) {
    if (response.success) {
        console.log(`Query ${i} OK:`, response.result);
    } else {
        console.log(`Query ${i} failed:`, response.error.message);
    }
}
```

###  Transaction queries[](https://surrealdb.com/docs/reference/javascript/api/queries/query#transaction-queries)

```ts
const txn = await db.beginTransaction();

try {
    const [created, updated] = await txn.query<[User, User]>(`
        CREATE users:new SET name = 'New User';
        UPDATE users:john SET updated_at = time::now();
    `).collect();
    
    await txn.commit();
} catch (error) {
    await txn.cancel();
}
```

###  Complex query with statistics[](https://surrealdb.com/docs/reference/javascript/api/queries/query#complex-query-with-statistics)

```ts
const responses = await db.query(`
    SELECT * FROM users WHERE age > 18;
    SELECT count() FROM users GROUP BY status;
`).responses();

for (const response of responses) {
    if (response.success && response.stats) {
        console.log('Execution time:', response.stats.duration);
        console.log('Records scanned:', response.stats.recordsScanned);
        console.log('Bytes received:', response.stats.bytesReceived);
    }
}
```

###  Conditional logic[](https://surrealdb.com/docs/reference/javascript/api/queries/query#conditional-logic)

```ts
const status = 'active';
const minAge = 18;

const result = await db.query(
    surql`
        LET $active_users = SELECT * FROM users WHERE status = ${status};
        LET $adult_users = SELECT * FROM users WHERE age >= ${minAge};
        RETURN {
            active: $active_users,
            adults: $adult_users,
            both: SELECT * FROM $active_users WHERE age >= ${minAge}
        };
    `
).collect();
```

###  Data migration[](https://surrealdb.com/docs/reference/javascript/api/queries/query#data-migration)

```ts
// Batch update with query
const migration = await db.query(`
    -- Add new field to all users
    UPDATE users SET new_field = 'default_value';
    
    -- Migrate data format
    UPDATE users SET profile = {
        bio: bio,
        avatar: avatar_url
    };
    
    -- Remove old fields
    UPDATE users UNSET bio, avatar_url;
`).collect();

console.log('Migration complete');
```

###  Streaming with progress[](https://surrealdb.com/docs/reference/javascript/api/queries/query#streaming-with-progress)

```ts
let totalRecords = 0;
let queriesCompleted = 0;

for await (const frame of db.query('SELECT * FROM users; SELECT * FROM posts;').stream()) {
    if (frame.type === 'value') {
        totalRecords += frame.value.length;
        console.log(`Received ${frame.value.length} records`);
    } else if (frame.type === 'done') {
        queriesCompleted++;
        console.log(`Query ${frame.query} completed`);
    }
}

console.log(`Total: ${totalRecords} records from ${queriesCompleted} queries`);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/queries/query#best-practices)
###  1. Use parameterisation[](https://surrealdb.com/docs/reference/javascript/api/queries/query#1-use-parameterisation)

```ts
// Good: Parameterised
const result = await db.query(
    'SELECT * FROM users WHERE name = $name',
    { name: userName }
).collect();

// Better: Use surql template
const result = await db.query(
    surql`SELECT * FROM users WHERE name = ${userName}`
).collect();

// Avoid: String concatenation (SQL injection risk)
const result = await db.query(
    `SELECT * FROM users WHERE name = '${userName}'`
).collect();
```

###  2. Handle errors appropriately[](https://surrealdb.com/docs/reference/javascript/api/queries/query#2-handle-errors-appropriately)

```ts
// Good: Check individual responses
const responses = await db.query(multiStatementQuery).responses();

for (const response of responses) {
    if (!response.success) {
        handleError(response.error);
    }
}

// Simple: Use collect with try-catch
try {
    const results = await db.query(query).collect();
} catch (error) {
    // First error stops execution
}
```

###  3. Use streaming for large results[](https://surrealdb.com/docs/reference/javascript/api/queries/query#3-use-streaming-for-large-results)

```ts
// Good: Stream large datasets
for await (const frame of db.query('SELECT * FROM large_table').stream()) {
    if (frame.type === 'value') {
        await processChunk(frame.value);
    }
}

// Avoid: Loading everything into memory
const [large] = await db.query('SELECT * FROM large_table').collect();
// May cause memory issues
```

###  4. Leverage type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/query#4-leverage-type-parameters)

```ts
// Good: Type-safe results
const [users, posts] = await db.query<[User[], Post[]]>(`
    SELECT * FROM users;
    SELECT * FROM posts;
`).collect();

// Now TypeScript knows the types
users[0].name; // string
posts[0].title; // string
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/query#see-also)
  * •
[SurrealQueryable.query()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) - Method that returns Query
  * •
[BoundQuery](https://surrealdb.com/docs/reference/javascript/api/utilities/#boundquery) - Parameterised queries
  * •
[surql](https://surrealdb.com/docs/reference/javascript/api/utilities/#surql) - Template tag for queries
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
