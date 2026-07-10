---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise

The `RelatePromise` class provides a chainable interface for configuring RELATE operations to create graph relationships (edges) between records. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.relate()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#relate)
**Source:** [query/relate.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/relate.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#type-parameters)
  * •
`T` - The result type (edge record type)
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#configuration-methods)
###  `.unique()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#unique)
Enforce a unique relationship constraint (only one edge between the same nodes).
Method Syntax

```ts
relatePromise.unique()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns)
`RelatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#example)

```ts
// Only allow one 'likes' edge between user and post
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('likes'),
    new RecordId('posts', '1')
).unique();
// If edge already exists, this won't create a duplicate
```

* * *
###  `.output()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#output)
Specify what to return from the operation.
Method Syntax

```ts
relatePromise.output(fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Output`  |  `"NONE"`, `"AFTER"`, or specific field list.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-1)
`RelatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#example-1)

```ts
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('follows'),
    new RecordId('users', 'jane')
).output('id', 'in', 'out', 'created_at');
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#timeout)
Set a timeout for the operation.
Method Syntax

```ts
relatePromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-2)
`RelatePromise` - Chainable promise
* * *
###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#version)
Create the relationship at a specific version.
Method Syntax

```ts
relatePromise.version(timestamp)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `timestamp`  | [DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | The version timestamp.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-3)
`RelatePromise` - Chainable promise
* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
relatePromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-4)
`RelatePromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#example-2)

```ts
await db.relate(alice, 'follows', bob).retry();
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#json)
Return result as JSON string.
Method Syntax

```ts
relatePromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-5)
`RelatePromise` - Promise returning JSON string
* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#compile)
Compile the query into a BoundQuery.
Method Syntax

```ts
relatePromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-6)
`BoundQuery` - The compiled query
* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#stream)
Stream results as relationships are created.
Method Syntax

```ts
relatePromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#returns-7)
`AsyncIterableIterator` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#complete-examples)
###  Basic relationship[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#basic-relationship)

```ts
import { Surreal, RecordId, Table, DateTime } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create a single relationship
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('likes'),
    new RecordId('posts', '1'),
    { created_at: DateTime.now() }
);

console.log('Edge created:', edge.id);
console.log('From:', edge.in);  // users:john
console.log('To:', edge.out);   // posts:1
```

###  Multiple relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#multiple-relationships)

```ts
// Create multiple edges at once
const edges = await db.relate(
    [new RecordId('users', 'john'), new RecordId('users', 'jane')],
    new Table('follows'),
    [new RecordId('users', 'alice'), new RecordId('users', 'bob')]
);

// Creates 4 edges:
// john->follows->alice
// john->follows->bob
// jane->follows->alice
// jane->follows->bob
```

###  Unique relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#unique-relationships)

```ts
// Prevent duplicate 'likes'
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('likes'),
    new RecordId('posts', '1'),
    { timestamp: DateTime.now() }
).unique();

// Second call won't create duplicate
const duplicate = await db.relate(
    new RecordId('users', 'john'),
    new Table('likes'),
    new RecordId('posts', '1')
).unique();
// Returns existing edge
```

###  Relationship with data[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#relationship-with-data)

```ts
const friendship = await db.relate(
    new RecordId('users', 'john'),
    new Table('friends'),
    new RecordId('users', 'jane'),
    {
        since: DateTime.parse('2024-01-15'),
        strength: 0.8,
        mutual: true,
        tags: ['colleague', 'neighbor']
    }
);
```

###  Specific edge ID[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#specific-edge-id)

```ts
// Use specific ID for the edge
const edge = await db.relate(
    new RecordId('users', 'john'),
    new RecordId('likes', 'specific-edge-id'),
    new RecordId('posts', '1'),
    { strength: 10 }
);
```

###  Fan-out relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#fan-out-relationships)

```ts
// One user follows many
const edges = await db.relate(
    new RecordId('users', 'john'),
    new Table('follows'),
    [
        new RecordId('users', 'alice'),
        new RecordId('users', 'bob'),
        new RecordId('users', 'carol')
    ]
);

console.log(`Created ${edges.length} follow edges`);
```

###  Streaming bulk relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#streaming-bulk-relationships)

```ts
const users = await db.select(new Table('users'));
const popularPost = new RecordId('posts', 'viral-post');

const edges = db.relate(
    users.map(u => u.id),
    new Table('viewed'),
    popularPost,
    { viewed_at: DateTime.now() }
);

for await (const edge of edges.stream()) {
    console.log(`Created view edge: ${edge.id}`);
}
```

###  Bidirectional relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#bidirectional-relationships)

```ts
// Create friendship in both directions
await db.relate(
    new RecordId('users', 'john'),
    new Table('friends'),
    new RecordId('users', 'jane')
);

await db.relate(
    new RecordId('users', 'jane'),
    new Table('friends'),
    new RecordId('users', 'john')
);
```

###  Relationship metadata[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#relationship-metadata)

```ts
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('rated'),
    new RecordId('movies', 'inception'),
    {
        rating: 5,
        review: 'Amazing movie!',
        watched_at: DateTime.parse('2024-01-15'),
        platform: 'Netflix'
    }
);
```

###  Temporal relationships[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#temporal-relationships)

```ts
// Track when relationship was created
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('employed_at'),
    new RecordId('companies', 'acme'),
    {
        started_at: DateTime.parse('2024-01-01'),
        position: 'Developer',
        department: 'Engineering'
    }
);
```

###  Weighted graph[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#weighted-graph)

```ts
// Create weighted edges for graph algorithms
const edge = await db.relate(
    new RecordId('cities', 'new-york'),
    new Table('connected_to'),
    new RecordId('cities', 'boston'),
    {
        distance: 215,  // miles
        travel_time: Duration.parse('4h'),
        cost: 50
    }
);
```

###  Delete and recreate pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#delete-and-recreate-pattern)

```ts
// Remove existing relationship and create new one
const userId = new RecordId('users', 'john');
const postId = new RecordId('posts', '1');

// Delete existing edge
await db.query(
    surql`DELETE FROM likes WHERE in = ${userId} AND out = ${postId}`
).collect();

// Create new edge with updated data
const edge = await db.relate(
    userId,
    new Table('likes'),
    postId,
    { created_at: DateTime.now() }
);
```

##  Graph traversal example[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#graph-traversal-example)

```ts
// Create relationships
await db.relate(
    new RecordId('users', 'john'),
    new Table('follows'),
    new RecordId('users', 'jane')
);

// Query traversal
const followers = await db.query(
    surql`SELECT <-follows<-users.* AS followers FROM users:jane`
).collect();

console.log('Jane has followers:', followers);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#best-practices)
###  1. Use unique for one-to-one[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#1-use-unique-for-one-to-one)

```ts
// Good: Prevent duplicate likes
await db.relate(from, new Table('likes'), to).unique();

// Avoid: Allowing duplicates
await db.relate(from, new Table('likes'), to);
// May create multiple edges
```

###  2. Include metadata[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#2-include-metadata)

```ts
// Good: Track when relationship was created
await db.relate(from, edge, to, {
    created_at: DateTime.now(),
    source: 'web-app'
});

// Basic: No metadata
await db.relate(from, edge, to);
```

###  3. Use specific edge IDs for updates[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#3-use-specific-edge-ids-for-updates)

```ts
// Good: use a specific ID so you can update the edge later
const edgeId = new RecordId('likes', [from.toString(), to.toString()]);
await db.relate(from, edgeId, to, metadata);

// Later: update by record ID
await db.update(edgeId).merge({ updated_at: DateTime.now() });
```

As of SurrealDB 3.1.5, when the edge ID already exists, `INSERT RELATION` returns an error unless you use `ON DUPLICATE KEY UPDATE`. See [Explicit edge record IDs](https://surrealdb.com/docs/reference/query-language/statements/relate#explicit-edge-record-ids) for more details.
##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/relate-promise#see-also)
  * •
[SurrealQueryable.relate()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#relate) - Method that returns RelatePromise
  * •
[Graph relationships](https://surrealdb.com/docs/reference/query-language/statements/relate) - SurrealQL RELATE documentation
  * •
[RecordId](https://surrealdb.com/docs/reference/javascript/api/values/#recordid) - Record identifier type
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
