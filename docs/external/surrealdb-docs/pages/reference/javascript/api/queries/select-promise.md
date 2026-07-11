---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/select-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/select-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/select-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/select-promise

The `SelectPromise` class provides a chainable interface for configuring SELECT queries before execution. It extends `Promise`, allowing you to `await` it directly or chain configuration methods.
**Returned by:** [`SurrealQueryable.select()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#select)
**Source:** [query/select.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/select.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#type-parameters)
  * •
`T` - The result type
  * •
`I` - The input type for field selection
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#configuration-methods)
###  `.fields()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#fields)
Specify which fields to select from the records.
Method Syntax

```ts
selectPromise.fields(...fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `Field<I>[]`  | Field names to select.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns)
`SelectPromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#examples)
Select Specific Fields

```ts
const users = await db.select(new Table('users'))
    .fields('name', 'email', 'age');
// Returns: [{ name, email, age }, ...]
```

Select Nested Fields

```ts
const users = await db.select(new Table('users'))
    .fields('name', 'address.city', 'address.country');
```

Select with Aggregations

```ts
const stats = await db.select(new Table('orders'))
    .fields('count()', 'sum(total)', 'avg(items)');
```

* * *
###  `.value()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#value)
Select only the value of a specific field, unwrapping it from the record structure.
Method Syntax

```ts
selectPromise.value(field)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `field`  | `Field<I>`  | The field name to extract.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-1)
`SelectPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example)
Get Array of Values

```ts
const names = await db.select(new Table('users'))
    .value('name');
// Returns: ['John', 'Jane', 'Bob']

// Instead of: [{ name: 'John' }, { name: 'Jane' }, ...]
```

* * *
###  `.where()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#where)
Add a WHERE clause to filter results.
Method Syntax

```ts
selectPromise.where(expr)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `expr`  | `ExprLike`  |  The condition expression (string or [Expression](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)object).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-2)
`SelectPromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#examples-1)
String Condition

```ts
const adults = await db.select(new Table('users'))
    .where('age >= 18');
```

With Expression Builder

```ts
import { expr } from 'surrealdb';

const activeUsers = await db.select(new Table('users'))
    .where(expr(({ and, eq, gte, field }) =>
        and(
            eq(field('status'), 'active'),
            gte(field('last_login'), new DateTime('2024-01-01'))
        )
    ));
```

Parameterised condition

```ts
const users = await db.query(
    surql`SELECT * FROM users WHERE age >= ${minAge}`
).collect();
```

* * *
###  `.fetch()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#fetch)
Specify related fields to fetch (similar to SQL JOIN).
Method Syntax

```ts
selectPromise.fetch(...fields)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `fields`  | `string[]`  | Field names representing relations to fetch.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-3)
`SelectPromise` - Chainable promise
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#examples-2)
Fetch Related Records

```ts
const posts = await db.select(new Table('posts'))
    .fetch('author');
// Expands author RecordId to full user object
```

Fetch Multiple Relations

```ts
const posts = await db.select(new Table('posts'))
    .fetch('author', 'comments', 'tags');
```

Fetch Nested Relations

```ts
const posts = await db.select(new Table('posts'))
    .fetch('author', 'comments.author');
```

* * *
###  `.start()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#start)
Set the pagination offset (number of records to skip).
Method Syntax

```ts
selectPromise.start(start)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `start`  | `number`  | Number of records to skip.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-4)
`SelectPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-1)
Pagination

```ts
const page = 2;
const pageSize = 10;

const users = await db.select(new Table('users'))
    .start((page - 1) * pageSize)
    .limit(pageSize);
```

* * *
###  `.limit()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#limit)
Limit the number of results returned.
Method Syntax

```ts
selectPromise.limit(limit)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `limit`  | `number`  | Maximum number of records to return.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-5)
`SelectPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-2)
Get Top 10

```ts
const topUsers = await db.select(new Table('users'))
    .where('score > 0')
    .limit(10);
```

* * *
###  `.timeout()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#timeout)
Set a timeout for the query operation.
Method Syntax

```ts
selectPromise.timeout(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Maximum time to wait for query completion.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-6)
`SelectPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-3)

```ts
const users = await db.select(new Table('users'))
    .timeout(Duration.parse('5s'));
```

* * *
###  `.version()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#version)
Select records at a specific version/timestamp (time-travel queries).
Method Syntax

```ts
selectPromise.version(timestamp)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `timestamp`  | [DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | The timestamp to query at.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-7)
`SelectPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-4)
Query Historical Data

```ts
const historicalUsers = await db.select(new Table('users'))
    .version(DateTime.parse('2024-01-01T00:00:00Z'));
```

* * *
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#json)
Return results as JSON strings instead of parsed objects.
Method Syntax

```ts
selectPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-8)
`SelectPromise` - Promise returning JSON string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-5)

```ts
const jsonString = await db.select(new Table('users')).json();
console.log(typeof jsonString); // 'string'
```

* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#compile)
Compile the query into a `BoundQuery` without executing it.
Method Syntax

```ts
selectPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-9)
`BoundQuery` - The compiled query
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-6)

```ts
const query = db.select(new Table('users'))
    .where('age >= 18')
    .compile();
```

* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#stream)
Stream results as they arrive instead of waiting for all results.
Method Syntax

```ts
selectPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#returns-10)
`AsyncIterableIterator` - Async iterator for streaming results
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#example-7)

```ts
for await (const user of db.select(new Table('users')).stream()) {
    console.log('Received user:', user);
}
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#complete-examples)
###  Basic selection[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#basic-selection)

```ts
import { Surreal, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Select all
const allUsers = await db.select(new Table('users'));

// Select specific record
const user = await db.select(new RecordId('users', 'john'));
```

###  Filtered selection[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#filtered-selection)

```ts
const activeAdults = await db.select(new Table('users'))
    .where('age >= 18 AND status = "active"')
    .fields('name', 'email', 'age');
```

###  Paginated selection[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#paginated-selection)

```ts
function getPage(page: number, pageSize: number) {
    return db.select(new Table('users'))
        .start((page - 1) * pageSize)
        .limit(pageSize);
}

const page1 = await getPage(1, 20);
const page2 = await getPage(2, 20);
```

###  Complex query with relations[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#complex-query-with-relations)

```ts
const posts = await db.select(new Table('posts'))
    .where('published = true')
    .fields('title', 'content', 'author', 'created_at')
    .fetch('author', 'comments.author')
    .limit(10);

// posts[0].author is now a full User object
// posts[0].comments[0].author is also expanded
```

###  Aggregation[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#aggregation)

```ts
import { expr, gte } from 'surrealdb';

const stats = await db.select(new Table('orders'))
    .where(expr(gte('created_at', DateTime.parse('2024-01-01'))))
    .fields('count() as total_orders', 'sum(amount) as total_revenue', 'avg(amount) as avg_order');
```

###  Streaming large results[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#streaming-large-results)

```ts
let count = 0;
for await (const user of db.select(new Table('users')).stream()) {
    await processUser(user);
    count++;
    if (count % 100 === 0) {
        console.log(`Processed ${count} users`);
    }
}
```

##  Chaining pattern[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#chaining-pattern)
All configuration methods return a new `SelectPromise`, allowing you to chain them in any order:

```ts
const result = await db.select(new Table('users'))
    .where('status = "active"')
    .fields('name', 'email')
    .fetch('profile')
    .start(0)
    .limit(10)
    .timeout(Duration.parse('5s'));
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#see-also)
  * •
[SurrealQueryable.select()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#select) - Method that returns SelectPromise
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
  * •
[Expression builders](https://surrealdb.com/docs/reference/javascript/api/utilities/#expr) - Building complex conditions
