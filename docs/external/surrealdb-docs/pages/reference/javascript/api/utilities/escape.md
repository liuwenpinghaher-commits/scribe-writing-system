---
title: "https://surrealdb.com/docs/reference/javascript/api/utilities/escape"
url: "https://surrealdb.com/docs/reference/javascript/api/utilities/escape"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/utilities/escape

Source: https://surrealdb.com/docs/reference/javascript/api/utilities/escape

Escape functions provide safe handling of identifiers and values in SurrealQL queries when you need to construct queries manually.
> !NOTE: Tip  
>  Prefer using [`surql`](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) or [`BoundQuery`](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) for automatic parameterisation. Use escape functions only when absolutely necessary.
**Import:**

```ts
import { 
    escapeIdent,
    escapeNumber,
    escapeIdPart,
    escapeRangeBound
} from 'surrealdb';
```

**Source:** [utils/escape.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/utils/escape.ts)
##  Functions[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#functions)
###  `escapeIdent(name)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#escapeident)
Escape table names, field names, and other identifiers.
Signature

```ts
function escapeIdent(name: string): string
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `name`  | `string`  | The identifier to escape.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#returns)
`string` - Escaped identifier
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#examples)

```ts
import { escapeIdent } from 'surrealdb';

// Simple identifiers (no escaping needed)
console.log(escapeIdent('users')); // 'users'
console.log(escapeIdent('first_name')); // 'first_name'

// Special characters (wrapped in backticks)
console.log(escapeIdent('user-table')); // '`user-table`'
console.log(escapeIdent('my table')); // '`my table`'
console.log(escapeIdent('user.name')); // '`user.name`'

// Reserved keywords
console.log(escapeIdent('select')); // '`select`'
console.log(escapeIdent('from')); // '`from`'
```

* * *
###  `escapeNumber(num)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#escapenumber)
Escape a number to be used as a valid SurrealQL ident.
Signature

```ts
function escapeNumber(num: number | bigint): string
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `num`  | `number | bigint`  | The number to escape.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#returns-1)
`string` - Escaped number representation
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#examples-1)

```ts
import { escapeNumber } from 'surrealdb';

console.log(escapeNumber(123));    // '123'
console.log(escapeNumber(42n));    // '42'
```

* * *
###  `escapeIdPart(id)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#escapeidpart)
Escape a record ID value part. Handles `Uuid`, `string`, `number`, `bigint`, and object values.
Signature

```ts
function escapeIdPart(id: RecordIdValue): string
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `id`  | `RecordIdValue`  | The record ID value part to escape.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#returns-2)
`string` - Escaped record ID part
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#examples-2)

```ts
import { escapeIdPart } from 'surrealdb';

// String IDs
console.log(escapeIdPart('john'));        // 'john' or escaped equivalent

// Numeric IDs
console.log(escapeIdPart(123));           // '123'
console.log(escapeIdPart(42n));           // '42'

// UUID values
console.log(escapeIdPart(new Uuid('...')));
```

* * *
###  `escapeRangeBound(bound)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#escaperangebound)
Escape a range bound value for use in SurrealQL range expressions.
Signature

```ts
function escapeRangeBound<T>(bound: Bound<T>): string
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `bound`  | `Bound<T>`  | The range bound to escape.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#returns-3)
`string` - Escaped range bound representation
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#complete-examples)
###  Dynamic table names[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#dynamic-table-names)

```ts
import { escapeIdent } from 'surrealdb';

async function selectFromTable(tableName: string) {
    // Validate and escape table name
    const safeTable = escapeIdent(tableName);
    
    // Use in query (still prefer Table class)
    const query = `SELECT * FROM ${safeTable}`;
    const [results] = await db.query(query).collect();
    
    return results;
}

await selectFromTable('user-sessions'); // Safe
```

###  Dynamic field selection[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#dynamic-field-selection)

```ts
import { escapeIdent } from 'surrealdb';

async function selectFields(table: string, fields: string[]) {
    const escapedFields = fields.map(escapeIdent).join(', ');
    const escapedTable = escapeIdent(table);
    
    const query = `SELECT ${escapedFields} FROM ${escapedTable}`;
    const [results] = await db.query(query).collect();
    
    return results;
}

await selectFields('users', ['first-name', 'last-name', 'email']);
```

###  Using surql instead (recommended)[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#using-surql-instead-recommended)

```ts
// Prefer surql for safe parameterisation
const filters = { status: 'active', age: 18 };
const query = surql`
    SELECT * FROM users 
    WHERE status = ${filters.status} 
    AND age = ${filters.age}
`;
```

##  When to use[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#when-to-use)
###  ✅ Use escape functions when:[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#-use-escape-functions-when)
  * •
Constructing queries with user-provided table/field names
  * •
Working with identifiers that have special characters
  * •
Building dynamic schema definitions
  * •
Interfacing with external query builders

###  ❌ Prefer other solutions:[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#-prefer-other-solutions)
  * •
**For values:** Use [`surql`](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) or [`BoundQuery`](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query)
  * •
**For tables:** Use [`Table`](https://surrealdb.com/docs/reference/javascript/api/values/table) class
  * •
**For record IDs:** Use [`RecordId`](https://surrealdb.com/docs/reference/javascript/api/values/record-id) class
  * •
**For conditions:** Use [`expr`](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#best-practices)
###  1. Prefer type-safe alternatives[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#1-prefer-type-safe-alternatives)

```ts
// Good: Type-safe
const table = new Table('users');
const users = await db.select(table);

// Avoid: Manual escaping
const escaped = escapeIdent('users');
const users = await db.query(`SELECT * FROM ${escaped}`).collect();
```

###  2. Validate before escaping[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#2-validate-before-escaping)

```ts
// Good: Validate first
function safeQuery(tableName: string) {
    if (!isValidTable(tableName)) {
        throw new Error('Invalid table name');
    }
    
    const escaped = escapeIdent(tableName);
    return `SELECT * FROM ${escaped}`;
}

// Avoid: Blind escaping
function unsafeQuery(tableName: string) {
    return `SELECT * FROM ${escapeIdent(tableName)}`;
}
```

###  3. Use surql for complex queries[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#3-use-surql-for-complex-queries)

```ts
// Good: Automatic parameterisation
const query = surql`SELECT * FROM users WHERE name = ${name}`;

// Avoid: Manual string construction
const query = `SELECT * FROM users WHERE name = '${name}'`;
```

##  Security considerations[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#security-considerations)
Warning
Escaping functions are NOT a complete defense against SQL injection. Always prefer parameterised queries using `surql` or `BoundQuery`.

```ts
// Secure: Parameterised
const query = surql`SELECT * FROM users WHERE name = ${userInput}`;

// Insecure: No escaping
const query = `SELECT * FROM users WHERE name = '${userInput}'`;
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/utilities/escape#see-also)
  * •
[surql](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) - Recommended for parameterised queries
  * •
[BoundQuery](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) - Parameterised query class
  * •
[Table](https://surrealdb.com/docs/reference/javascript/api/values/table) - Type-safe table references
  * •
[RecordId](https://surrealdb.com/docs/reference/javascript/api/values/record-id) - Type-safe record identifiers
