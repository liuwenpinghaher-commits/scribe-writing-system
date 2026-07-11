---
title: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable"
url: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable

Source: https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable

The `SurrealQueryable` class is an abstract base class that provides all query execution methods for interacting with SurrealDB. It is the foundation for executing database operations and is extended by [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) and [`SurrealTransaction`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction).
**Extended by:** [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session), [`SurrealTransaction`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction)
**Source:** [api/queryable.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/api/queryable.ts)
##  Methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#methods)
###  `.api()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api)
Create a [`SurrealApi`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-api) instance for invoking user-defined API endpoints. You can provide type definitions for type-safe API calls and an optional path prefix.
Method Syntax

```ts
db.api<TPaths>(prefix?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `prefix`  | `string`  | A path prefix to prepend to all API calls made through this instance.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns)
[`SurrealApi`](/docs/reference/javascript/api/core/surreal-api) - An API instance for invoking custom database APIs
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples)
Basic API Access

```ts
const api = db.api();
const result = await api.get('/users');
```

Type-Safe API Access

```ts
type MyPaths = {
    "/users": { get: [void, User[]] };
    [K: `/users/${number}`]: { get: [void, User] };
};

const api = db.api<MyPaths>();
const users = await api.get("/users"); // Type: User[]
```

API with Prefix

```ts
const usersApi = db.api<MyPaths>("/users");
const user = await usersApi.get("123"); // GET /users/123
```

##  Query methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query-methods)
###  `.query()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query)
Execute raw SurrealQL statements against the database.
Method Syntax

```ts
db.query<R>(query, bindings?)
db.query<R>(boundQuery)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query`  |  string | [BoundQuery](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query)  | The SurrealQL query string or BoundQuery instance.  |  
| `bindings`  | `Record<string, unknown>`  | Variables to bind in the query (when using string query).  |  
####  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#type-parameters)
  * •
`R extends unknown[]` - Array of result types for each query statement

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-1)
[`Query`](/docs/reference/javascript/api/queries/query) - A query instance that can be configured and executed
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-1)
Simple Query

```ts
const result = await db.query('SELECT * FROM users').collect();
console.log(result); // [{ success: true, result: [...] }]
```

Query with Bindings

```ts
const result = await db.query(
    'SELECT * FROM users WHERE age > $age',
    { age: 18 }
).collect();
```

Multiple Statements

```ts
const results = await db.query<[User[], Post[]]>(`
    SELECT * FROM users;
    SELECT * FROM posts;
`).collect();

const [users, posts] = results.map(r => r.result);
```

Using BoundQuery

```ts
import { surql } from 'surrealdb';

const query = surql`SELECT * FROM users WHERE age > ${18}`;
const result = await db.query(query).collect();
```

###  `.select()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#select)
Select records from the database by record ID, record ID range, or table.
Method Syntax

```ts
db.select<T>(recordId)
db.select<T>(range)
db.select<T>(table)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `recordId`  | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | A specific record ID to select.  |  
| `range`  | [RecordIdRange](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | A range of record IDs to select.  |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | A table to select all records from.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-2)
  * •
For `RecordId`: [`SelectPromise`](/docs/reference/javascript/api/queries/select-promise) - A promise resolving to a single record or `undefined`
  * •
For `Table` or `RecordIdRange`: [`SelectPromise`](/docs/reference/javascript/api/queries/select-promise) - A promise resolving to an array of records

####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-2)
Select by Record ID

```ts
const user = await db.select(new RecordId('users', 'john'));
```

Select All from Table

```ts
const users = await db.select(new Table('users'));
```

Select with Configuration

```ts
const users = await db.select(new Table('users'))
    .where('age > 18')
    .limit(10)
    .start(0);
```

###  `.create()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#create)
Create new records in the database.
Method Syntax

```ts
db.create<T>(recordId)
db.create<T>(table)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `recordId`  | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | The record ID for the new record.  |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | The table to create a record in (auto-generated ID).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-3)
[`CreatePromise, T>`](/docs/reference/javascript/api/queries/create-promise) - A promise with chainable configuration methods
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-3)
Create with Specific ID

```ts
const user = await db.create(new RecordId('users', 'john'))
    .content({ name: 'John Doe', email: 'john@example.com' });
```

Create with Auto-Generated ID

```ts
const user = await db.create(new Table('users'))
    .content({ name: 'Jane Doe', email: 'jane@example.com' });
```

###  `.insert()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#insert)
Insert one or multiple records into the database.
Method Syntax

```ts
db.insert<T>(data)
db.insert<T>(table, data)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | The table to insert records into.  |  
| `data`  | `Values<T> | Values<T>[]`  | One or more records to insert.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-4)
[`InsertPromise`](/docs/reference/javascript/api/queries/insert-promise) - A promise with chainable configuration methods
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-4)
Insert Single Record

```ts
const user = await db.insert({
    id: new RecordId('users', 'alice'),
    name: 'Alice',
    email: 'alice@example.com'
});
```

Insert Multiple Records

```ts
const users = await db.insert([
    { id: new RecordId('users', 'bob'), name: 'Bob' },
    { id: new RecordId('users', 'carol'), name: 'Carol' }
]);
```

Insert into Table

```ts
const users = await db.insert(new Table('users'), [
    { name: 'Dave' },
    { name: 'Eve' }
]);
```

###  `.update()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#update)
Update existing records in the database.
Method Syntax

```ts
db.update<T>(recordId)
db.update<T>(range)
db.update<T>(table)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `recordId`  | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | A specific record ID to update.  |  
| `range`  | [RecordIdRange](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | A range of record IDs to update.  |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | A table to update all records in.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-5)
[`UpdatePromise`](/docs/reference/javascript/api/queries/update-promise) - A promise with chainable configuration methods
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-5)
Update with Content

```ts
const user = await db.update(new RecordId('users', 'john'))
    .content({ name: 'John Smith', email: 'john@example.com' });
```

Update with Merge

```ts
const user = await db.update(new RecordId('users', 'john'))
    .merge({ email: 'newemail@example.com' });
```

Update with Condition

```ts
const users = await db.update(new Table('users'))
    .merge({ verified: true })
    .where('age > 18');
```

###  `.upsert()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#upsert)
Upsert records (insert if they don't exist, replace if they do).
Warning
This function replaces existing record data with the specified data.
Method Syntax

```ts
db.upsert<T>(recordId)
db.upsert<T>(range)
db.upsert<T>(table)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `recordId`  | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | A specific record ID to upsert.  |  
| `range`  | [RecordIdRange](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | A range of record IDs to upsert.  |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | A table to upsert all records in.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-6)
[`UpsertPromise`](/docs/reference/javascript/api/queries/upsert-promise) - A promise with chainable configuration methods
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#example)

```ts
const user = await db.upsert(new RecordId('users', 'john'))
    .content({ name: 'John Doe', email: 'john@example.com' });
```

###  `.delete()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#delete)
Delete records from the database.
Method Syntax

```ts
db.delete<T>(recordId)
db.delete<T>(range)
db.delete<T>(table)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `recordId`  | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | A specific record ID to delete.  |  
| `range`  | [RecordIdRange](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | A range of record IDs to delete.  |  
| `table`  | [Table](https://surrealdb.com/docs/reference/javascript/api/values/table)  | A table to delete all records from.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-7)
[`DeletePromise`](/docs/reference/javascript/api/queries/delete-promise) - A promise with chainable configuration methods
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-6)
Delete Single Record

```ts
const deleted = await db.delete(new RecordId('users', 'john'));
```

Delete All from Table

```ts
const deleted = await db.delete(new Table('users'));
```

###  `.relate()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#relate)
Create graph relationships (edges) between records.
Method Syntax

```ts
db.relate<T>(from, edge, to, data?)
db.relate<T>(from[], edge, to[], data?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-8)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `from`  |  [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)| AnyRecordId[]  | The source record(s) for the relationship.  |  
| `edge`  |  Table | [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)  | The edge table or specific edge record ID.  |  
| `to`  |  [AnyRecordId](https://surrealdb.com/docs/reference/javascript/api/types/#anyrecordid)| AnyRecordId[]  | The target record(s) for the relationship.  |  
| `data`  | `Partial<T>`  | Optional data to store on the edge record.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-8)
[`RelatePromise`](/docs/reference/javascript/api/queries/relate-promise) - A promise for the relationship operation
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-7)
Create Single Relationship

```ts
const edge = await db.relate(
    new RecordId('users', 'john'),
    new Table('likes'),
    new RecordId('posts', '1'),
    { timestamp: new Date() }
);
```

Create Multiple Relationships

```ts
const edges = await db.relate(
    [new RecordId('users', 'john'), new RecordId('users', 'jane')],
    new Table('follows'),
    [new RecordId('users', 'alice'), new RecordId('users', 'bob')]
);
```

###  `.live()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live)
Create a live query subscription to receive real-time updates when records change.
Method Syntax

```ts
db.live<T>(what)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-9)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `what`  | [LiveResource](https://surrealdb.com/docs/reference/javascript/api/types/#liveresource)  | The table, record ID, or range to subscribe to.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-9)
[`ManagedLivePromise`](/docs/reference/javascript/api/queries/live-promise) - A managed live query subscription
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#example-1)

```ts
const subscription = await db.live(new Table('users'));

for await (const update of subscription) {
    console.log('Update:', update.action, update.result);
}
```

###  `.liveOf()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof)
Subscribe to an existing live query using its ID.
Note
This function is for use with live queries not managed by the driver.
Method Syntax

```ts
db.liveOf<T>(id)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-10)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | [Uuid](https://surrealdb.com/docs/reference/javascript/api/values/uuid)  | The UUID of the existing live query.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-10)
[`UnmanagedLivePromise`](/docs/reference/javascript/api/queries/live-promise) - An unmanaged live query subscription
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#example-2)

```ts
const liveQueryId = await db.query('LIVE SELECT * FROM users').collect();
const subscription = db.liveOf(liveQueryId);
```

###  `.run()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run)
Execute a SurrealDB function or SurrealML model.
Method Syntax

```ts
db.run<T>(name, args?)
db.run<T>(name, version, args?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#parameters-11)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  |  The full name of the function to run (e.g., `"fn::calculate"`).  |  
| `version`  | `string`  | The version of a SurrealML model to use.  |  
| `args`  | `unknown[]`  | Arguments to pass to the function.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-11)
[`RunPromise`](/docs/reference/javascript/api/queries/run-promise) - A promise for the function result
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#examples-8)
Run Custom Function

```ts
const result = await db.run('fn::calculate', [10, 20]);
```

Run SurrealML Model

```ts
const prediction = await db.run('ml::predict', '1.0.0', [inputData]);
```

###  `.auth()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#auth)
Get the currently authenticated record user by selecting the `$auth` parameter.
Note
The user must have permission to select their own record, otherwise an empty result is returned.
Method Syntax

```ts
db.auth<T>()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#returns-12)
`AuthPromise` - A promise for the authenticated user record, or `undefined` if not authenticated
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#example-3)

```ts
const user = await db.auth();
console.log('Current user:', user);
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#see-also)
  * •
[SurrealSession](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) - Session management extending this class
  * •
[SurrealTransaction](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) - Transaction support extending this class
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Detailed query builder documentation
  * •
[SelectPromise](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise) - SELECT query configuration
  * •
[CreatePromise](https://surrealdb.com/docs/reference/javascript/api/queries/create-promise) - CREATE query configuration
