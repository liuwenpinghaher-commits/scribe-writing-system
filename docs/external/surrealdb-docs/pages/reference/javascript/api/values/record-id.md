---
title: "https://surrealdb.com/docs/reference/javascript/api/values/record-id"
url: "https://surrealdb.com/docs/reference/javascript/api/values/record-id"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/record-id

Source: https://surrealdb.com/docs/reference/javascript/api/values/record-id

The `RecordId` class provides type-safe record identifiers in SurrealDB. Each record ID consists of a table name and an ID value, represented as `table:id` in SurrealQL.
**Import:**

```ts
import { RecordId } from 'surrealdb';
```

**Source:** [value/record-id.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/record-id.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#type-parameters)
  * •
`Tb extends string` - The table name (string literal type for type safety)
  * •
`Id` - The ID value type (string, number, object, etc.)

##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#constructor)
###  `new RecordId(table, id)`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#constructor)
Create a new record identifier.
Syntax

```ts
new RecordId(table, id)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `Tb | Table<Tb>`  |  The table name, either as a string or a `Table`instance.  |  
| `id`  | `Id`  | The record ID value (string, number, object, array, or RecordId).  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#examples)

```ts
// String IDs
const user = new RecordId('users', 'john');
const post = new RecordId('posts', '123');

// Numeric IDs
const product = new RecordId('products', 42);

// Complex/structured IDs
const metric = new RecordId('metrics', { 
    service: 'api', 
    timestamp: 1234567890 
});

// Array IDs
const compound = new RecordId('items', ['type-a', 123]);

// Nested RecordId
const nested = new RecordId('links', new RecordId('users', 'alice'));

// Type-safe with generics
const typedUser = new RecordId<'users', string>('users', 'john');
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#properties)
###  `table`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#table)
The table name component, returned as a `Table` instance.
**Type:** `Table`

```ts
const userId = new RecordId('users', 'john');
console.log(userId.table);      // Table { name: 'users' }
console.log(userId.table.name); // 'users'
```

* * *
###  `id`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#id)
The ID value component.
**Type:** `Id`

```ts
const userId = new RecordId('users', 'john');
console.log(userId.id); // 'john'

const productId = new RecordId('products', 42);
console.log(productId.id); // 42
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#tostring)
Convert the record ID to its string representation.
Syntax

```ts
recordId.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#returns)
`string` - String representation in format `table:id`
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#examples-1)

```ts
const userId = new RecordId('users', 'john');
console.log(userId.toString()); // 'users:john'

const productId = new RecordId('products', 42);
console.log(productId.toString()); // 'products:42'

const complex = new RecordId('items', { type: 'widget', id: 5 });
console.log(complex.toString()); // 'items:{ type: "widget", id: 5 }'
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#tojson)
Serialize the record ID for JSON.
Syntax

```ts
recordId.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#returns-1)
`string` - JSON-safe string representation

```ts
const userId = new RecordId('users', 'john');
console.log(JSON.stringify(userId)); // '"users:john"'
```

* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#equals)
Check if two record IDs are equal.
Syntax

```ts
recordId.equals(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `unknown`  | Value to compare.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#returns-2)
`boolean` - True if equal

```ts
const a = new RecordId('users', 'john');
const b = new RecordId('users', 'john');
const c = new RecordId('users', 'jane');

console.log(a.equals(b)); // true
console.log(a.equals(c)); // false
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#complete-examples)
###  Basic usage[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#basic-usage)

```ts
import { Surreal, RecordId } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create record with specific ID
const user = await db.create(new RecordId('users', 'john'))
    .content({
        name: 'John Doe',
        email: 'john@example.com'
    });

// Select by record ID
const retrieved = await db.select(new RecordId('users', 'john'));

// Update by record ID
await db.update(new RecordId('users', 'john'))
    .merge({ status: 'active' });

// Delete by record ID
await db.delete(new RecordId('users', 'john'));
```

###  Type-safe record IDs[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#type-safe-record-ids)

```ts
interface User {
    id: RecordId<'users', string>;
    name: string;
    email: string;
}

// TypeScript enforces correct table name
const userId: RecordId<'users', string> = new RecordId('users', 'alice');

// This would be a type error:
// const wrong: RecordId<'posts', string> = new RecordId('users', 'alice');

const user = await db.select<User>(userId);
```

###  Complex ID structures[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#complex-id-structures)

```ts
// Time-series data with structured IDs
const metricId = new RecordId('metrics', {
    service: 'api',
    host: 'server-01',
    timestamp: 1234567890
});

await db.create(metricId).content({
    cpu: 45.2,
    memory: 78.1
});

// Compound keys
const sessionId = new RecordId('sessions', {
    userId: 'john',
    deviceId: 'device-123'
});
```

###  Parsing from strings[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#parsing-from-strings)
Use `StringRecordId` to pass a record ID string directly without parsing it into table and ID components. The string is sent as-is to SurrealDB.

```ts
import { StringRecordId } from 'surrealdb';

// Use a record ID string directly
const userInput = 'users:john';
const userId = new StringRecordId(userInput);
const user = await db.select(userId);

// Use in queries
const recordId = new StringRecordId('users:alice');
const result = await db.select(recordId);
```

###  Working with relations[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#working-with-relations)

```ts
// Create relationship using record IDs
const from = new RecordId('users', 'john');
const to = new RecordId('posts', '123');

const edge = await db.relate(
    from,
    new Table('likes'),
    to,
    { timestamp: DateTime.now() }
);

console.log('Edge from:', edge.in);  // RecordId('users', 'john')
console.log('Edge to:', edge.out);   // RecordId('posts', '123')
```

###  UUID-based record IDs[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#uuid-based-record-ids)

```ts
import { Uuid } from 'surrealdb';

// Generate time-ordered IDs
const userId = new RecordId('users', Uuid.v7());

// Generate random IDs
const sessionId = new RecordId('sessions', Uuid.v4());

await db.create(userId).content({
    name: 'Alice',
    created: DateTime.now()
});
```

###  Validation[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#validation)

```ts
// Table names are validated automatically
try {
    const invalid = new RecordId('invalid-table!', 'id');
} catch (error) {
    console.error('Invalid table name');
}
```

##  RecordIdRange[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#recordidrange)
The `RecordIdRange` class represents a range of record IDs for querying multiple records.
Bounds are specified using the `BoundIncluded` and `BoundExcluded` classes, or `undefined` for unbounded:
  * •
`new BoundIncluded(value)` — inclusive bound (`>=` or `<=`)
  * •
`new BoundExcluded(value)` — exclusive bound (`>` or `<`)
  * •
`undefined` — unbounded (no limit)

###  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#constructor-1)

```ts
new RecordIdRange(table, begin, end)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `table`  | `Tb | Table<Tb>`  |  The table name, either as a string or a `Table`instance.  |  
| `begin`  | `Bound<Id>`  |  Start of the range. Use `BoundIncluded`, `BoundExcluded`, or `undefined`.  |  
| `end`  | `Bound<Id>`  |  End of the range. Use `BoundIncluded`, `BoundExcluded`, or `undefined`.  |  
###  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#examples-2)

```ts
import { RecordIdRange, BoundIncluded, BoundExcluded } from 'surrealdb';

// Select range of users from 'a' (inclusive) to 'f' (exclusive)
const range = new RecordIdRange(
    'users',
    new BoundIncluded('a'),
    new BoundExcluded('f'),
);
const users = await db.select(range);

// Numeric range: 1 (inclusive) to 100 (inclusive)
const numRange = new RecordIdRange(
    'items',
    new BoundIncluded(1),
    new BoundIncluded(100),
);
const items = await db.select(numRange);

// Unbounded start, exclusive end
const upToF = new RecordIdRange(
    'users',
    undefined,
    new BoundExcluded('f'),
);

// Inclusive start, unbounded end
const fromA = new RecordIdRange(
    'users',
    new BoundIncluded('a'),
    undefined,
);

// Delete range
await db.delete(new RecordIdRange(
    'logs',
    new BoundIncluded('2024-01-01'),
    new BoundExcluded('2024-02-01'),
));
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#best-practices)
###  1. Use type parameters[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#1-use-type-parameters)

```ts
// Good: Type-safe
type UserId = RecordId<'users', string>;
const userId: UserId = new RecordId('users', 'john');

// Better: Enforce at compile time
function getUser(id: RecordId<'users', string>) {
    return db.select(id);
}
```

###  2. Prefer RecordId over strings[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#2-prefer-recordid-over-strings)

```ts
// Good: Type-safe with validation
const user = await db.select(new RecordId('users', 'john'));

// Avoid: String-based (no validation)
const user = await db.query('SELECT * FROM users:john').collect();
```

###  3. Use structured IDs for complex keys[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#3-use-structured-ids-for-complex-keys)

```ts
// Good: Structured composite key
const id = new RecordId('events', {
    userId: 'john',
    timestamp: Date.now()
});

// Avoid: String concatenation
const id = new RecordId('events', `john-${Date.now()}`);
```

###  4. Handle construction errors[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#4-handle-construction-errors)

```ts
// Good: Safe construction
try {
    const id = new RecordId(tableName, idValue);
    const record = await db.select(id);
} catch (error) {
    console.error('Invalid record ID format');
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/record-id#see-also)
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Table](https://surrealdb.com/docs/reference/javascript/api/values/table) - Table references
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using RecordId in queries
  * •
[SurrealQL record IDs](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) - Database record ID documentation
