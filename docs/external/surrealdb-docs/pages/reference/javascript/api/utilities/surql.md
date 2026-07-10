---
title: "https://surrealdb.com/docs/reference/javascript/api/utilities/surql"
url: "https://surrealdb.com/docs/reference/javascript/api/utilities/surql"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/utilities/surql

Source: https://surrealdb.com/docs/reference/javascript/api/utilities/surql

The `surql` tagged template function creates parameterised SurrealQL queries with automatic value binding and SQL injection prevention.
**Import:**

```ts
import { surql } from 'surrealdb';
```

**Source:** [utils/tagged-template.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/utils/tagged-template.ts)
##  Function signature[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#function-signature)

```ts
function surql(
    strings: TemplateStringsArray, 
    ...values: unknown[]
): BoundQuery
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `strings`  | `TemplateStringsArray`  | Template string segments.  |  
| `values`  | `unknown[]`  | Interpolated values (automatically bound as parameters).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#returns)
`BoundQuery` - Parameterised query with automatic bindings
##  How it works[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#how-it-works)
The `surql` template automatically:
  1. 1.
Extracts interpolated values
  2. 2.
Generates unique parameter names
  3. 3.
Replaces values with parameter references
  4. 4.
Returns a `BoundQuery` with query string and bindings

```ts
const age = 18;
const query = surql`SELECT * FROM users WHERE age > ${age}`;

// Internally becomes:
// query.query = "SELECT * FROM users WHERE age > $bind__1"
// query.bindings = { bind__1: 18 }
```

##  Basic examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#basic-examples)
###  Simple parameterised query[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#simple-parameterised-query)

```ts
import { surql } from 'surrealdb';

const minAge = 18;
const query = surql`SELECT * FROM users WHERE age >= ${minAge}`;

const [users] = await db.query(query).collect();
```

###  Multiple parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#multiple-parameters)

```ts
const status = 'active';
const minAge = 18;
const tier = 'premium';

const query = surql`
    SELECT * FROM users 
    WHERE status = ${status}
    AND age >= ${minAge}
    AND tier = ${tier}
`;

const [users] = await db.query(query).collect();
```

###  With value types[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#with-value-types)

```ts
import { RecordId, DateTime, Duration } from 'surrealdb';

const userId = new RecordId('users', 'john');
const cutoffDate = DateTime.now().minus(Duration.parse('30d'));

const query = surql`
    SELECT * FROM posts 
    WHERE author = ${userId}
    AND created_at >= ${cutoffDate}
    ORDER BY created_at DESC
`;

const [posts] = await db.query(query).collect();
```

##  Advanced examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#advanced-examples)
###  Dynamic query building[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#dynamic-query-building)

```ts
function buildUserQuery(filters: {
    status?: string;
    minAge?: number;
    tier?: string;
}) {
    let query = surql`SELECT * FROM users WHERE 1=1`;
    
    if (filters.status) {
        query.append(surql` AND status = ${filters.status}`);
    }
    if (filters.minAge !== undefined) {
        query.append(surql` AND age >= ${filters.minAge}`);
    }
    if (filters.tier) {
        query.append(surql` AND tier = ${filters.tier}`);
    }
    
    return query;
}

const query = buildUserQuery({ status: 'active', minAge: 18 });
const [users] = await db.query(query).collect();
```

###  Multi-statement queries[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#multi-statement-queries)

```ts
const userId = new RecordId('users', 'john');
const postId = new RecordId('posts', '123');

const query = surql`
    BEGIN TRANSACTION;
    
    UPDATE ${userId} SET post_count += 1;
    
    CREATE ${postId} SET
        author = ${userId},
        title = ${'My Post'},
        content = ${'Post content here'},
        created_at = time::now();
    
    COMMIT TRANSACTION;
`;

await db.query(query).collect();
```

###  Combining with expressions[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#combining-with-expressions)

```ts
import { expr, eq, gte } from 'surrealdb';

const condition = expr(and(
    eq('verified', true),
    gte('age', 18)
));

const tier = 'premium';
const query = surql`
    SELECT * FROM users 
    WHERE ${condition}
    AND tier = ${tier}
`;

const [users] = await db.query(query).collect();
```

###  Inserting arrays[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#inserting-arrays)

```ts
const users = [
    { name: 'Alice', email: 'alice@example.com' },
    { name: 'Bob', email: 'bob@example.com' }
];

const query = surql`INSERT INTO users ${users}`;
await db.query(query).collect();
```

###  Graph traversal[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#graph-traversal)

```ts
const userId = new RecordId('users', 'john');

const query = surql`
    SELECT 
        *,
        ->follows->users.* AS following,
        <-follows<-users.* AS followers
    FROM ${userId}
`;

const [result] = await db.query(query).collect();
console.log('Following:', result.following);
console.log('Followers:', result.followers);
```

###  Conditional updates[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#conditional-updates)

```ts
const status = 'inactive';
const threshold = DateTime.now().minus(Duration.parse('90d'));

const query = surql`
    UPDATE users 
    SET status = ${status}
    WHERE active = false 
    AND last_login < ${threshold}
`;

const [updated] = await db.query(query).collect();
console.log(`Updated ${updated.length} users`);
```

###  Variable definition[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#variable-definition)

```ts
const minScore = 80;
const category = 'tech';

const query = surql`
    LET $high_scorers = SELECT * FROM users WHERE score >= ${minScore};
    LET $tech_users = SELECT * FROM users WHERE category = ${category};
    
    RETURN {
        high_scorers: $high_scorers,
        tech_users: $tech_users,
        intersection: SELECT * FROM $high_scorers WHERE category = ${category}
    };
`;

const [result] = await db.query(query).collect();
```

###  Batch operations[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#batch-operations)

```ts
const recordIds = [
    new RecordId('users', 'alice'),
    new RecordId('users', 'bob'),
    new RecordId('users', 'carol')
];

const query = surql`
    SELECT * FROM [${recordIds[0]}, ${recordIds[1]}, ${recordIds[2]}]
`;

const [users] = await db.query(query).collect();
```

##  SQL injection prevention[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#sql-injection-prevention)
The `surql` template prevents SQL injection by automatically parameterising all values:

```ts
// User input
const userInput = "'; DROP TABLE users; --";

// Safe: Treated as a parameter value
const query = surql`SELECT * FROM users WHERE name = ${userInput}`;
// Becomes: SELECT * FROM users WHERE name = $bind__1
// With binding: { bind__1: "'; DROP TABLE users; --" }

// The malicious SQL is safely treated as a string value
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#best-practices)
###  1. Always use surql for user input[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#1-always-use-surql-for-user-input)

```ts
// Good: Safe parameterisation
const userName = getUserInput();
const query = surql`SELECT * FROM users WHERE name = ${userName}`;

// Dangerous: SQL injection risk
const query = `SELECT * FROM users WHERE name = '${userName}'`;
```

###  2. Use for complex queries[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#2-use-for-complex-queries)

```ts
// Good: Clear and safe
const query = surql`
    SELECT *,
        ->purchased->products.* AS purchases,
        <-manages<-departments.* AS departments
    FROM ${userId}
    WHERE active = ${true}
`;

// Harder to read and maintain
const query = new BoundQuery(
    'SELECT *, ->purchased->products.* AS purchases FROM $userId WHERE active = $active',
    { userId, active: true }
);
```

###  3. Leverage type system[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#3-leverage-type-system)

```ts
// Good: Type-safe values
const recordId = new RecordId('users', 'john');
const datetime = DateTime.now();

const query = surql`
    UPDATE ${recordId}
    SET last_login = ${datetime}
`;

// Values maintain their types through the query
```

###  4. Build queries incrementally[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#4-build-queries-incrementally)

```ts
// Good: Append for dynamic queries
let query = surql`SELECT * FROM products WHERE 1=1`;

if (minPrice) {
    query.append(surql` AND price >= ${minPrice}`);
}
if (category) {
    query.append(surql` AND category = ${category}`);
}

query.append(surql` ORDER BY created_at DESC LIMIT ${limit}`);
```

##  Common pitfalls[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#common-pitfalls)
###  1. Identifier interpolation[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#1-identifier-interpolation)

```ts
// Problem: Table names can't be parameterised
const tableName = 'users';
const wrong = surql`SELECT * FROM ${tableName}`; // Creates $bind__1

// Solution: Use Table class
const table = new Table('users');
const correct = surql`SELECT * FROM ${table}`;
```

###  2. Field names[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#2-field-names)

```ts
// Problem: Field names as parameters
const fieldName = 'age';
const wrong = surql`SELECT * FROM users WHERE ${fieldName} > 18`;

// Solution: Use raw SQL for field names (with validation)
import { escapeIdent } from 'surrealdb';
const validated = escapeIdent(fieldName);
const correct = surql`SELECT * FROM users WHERE ${raw(validated)} > 18`;
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/utilities/surql#see-also)
  * •
[BoundQuery](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) - Parameterised query class
  * •
[expr](https://surrealdb.com/docs/reference/javascript/api/utilities/expr) - Expression builder
  * •
[Query](https://surrealdb.com/docs/reference/javascript/api/queries/query) - Executing queries
  * •
[SurrealQueryable.query()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) - Query method
