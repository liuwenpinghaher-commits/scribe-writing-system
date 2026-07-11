---
title: "https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query"
url: "https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query

Source: https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query

The `BoundQuery` class represents a parameterised SurrealQL query with bound variables, providing safe query composition and preventing SQL injection.
**Import:**

```ts
import { BoundQuery } from 'surrealdb';
```

**Source:** [utils/bound-query.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/utils/bound-query.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#type-parameters)
  * •
`R extends unknown[]` - Array of result types for the query

##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#constructor)
###  `new BoundQuery(query?, bindings?)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#constructor)
Create a new bound query.
Syntax

```ts
new BoundQuery() // Empty query
new BoundQuery(boundQuery) // Clone existing
new BoundQuery(query, bindings?) // From string and bindings
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `query`  | `string | BoundQuery`  | Query string or existing BoundQuery to clone.  |  
| `bindings`  | `Record<string, unknown>`  | Parameter bindings.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#examples)

```ts
// Empty query
const query = new BoundQuery();

// From string
const query = new BoundQuery('SELECT * FROM users');

// With bindings
const query = new BoundQuery(
    'SELECT * FROM users WHERE age > $age',
    { age: 18 }
);

// Clone existing
const clone = new BoundQuery(existingQuery);
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#properties)
###  `query`[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#query)
The query string with parameter placeholders.
**Type:** `string`

```ts
const query = new BoundQuery(
    'SELECT * FROM users WHERE age > $age',
    { age: 18 }
);

console.log(query.query);
// 'SELECT * FROM users WHERE age > $age'
```

* * *
###  `bindings`[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#bindings)
A copy of the parameter bindings.
**Type:** `Record`

```ts
console.log(query.bindings);
// { age: 18 }
```

##  Methods[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#methods)
###  `.append()`[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#append)
Append another query or string to this query.
Method Syntax

```ts
query.append(other)
query.append(queryString, bindings?)
query.append`template ${value}`
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `BoundQuery | string | TemplateStringsArray`  | Query to append.  |  
| `bindings`  | `Record<string, unknown>`  | Bindings for the appended query.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#returns)
`this` - Chainable
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#examples-1)
Append BoundQuery

```ts
const base = new BoundQuery('SELECT * FROM users WHERE 1=1');
const filter = new BoundQuery(' AND age > $age', { age: 18 });

base.append(filter);
```

Append String

```ts
const query = new BoundQuery('SELECT * FROM users');
query.append(' WHERE active = $active', { active: true });
```

Append with Template

```ts
const query = new BoundQuery('SELECT * FROM users');
const status = 'active';
query.append` WHERE status = ${status}`;
```

* * *
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#tostring)
Get the query string.
Method Syntax

```ts
query.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#returns-1)
`string` - The query string
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#complete-examples)
###  Basic parameterised query[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#basic-parameterised-query)

```ts
import { BoundQuery } from 'surrealdb';

const query = new BoundQuery(
    'SELECT * FROM users WHERE age >= $minAge AND status = $status',
    {
        minAge: 18,
        status: 'active'
    }
);

const [users] = await db.query(query).collect();
```

###  Building queries incrementally[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#building-queries-incrementally)

```ts
// Start with base query
const query = new BoundQuery('SELECT * FROM products WHERE 1=1');

// Add conditions dynamically
if (category) {
    query.append(' AND category = $category', { category });
}

if (minPrice) {
    query.append(' AND price >= $minPrice', { minPrice });
}

if (maxPrice) {
    query.append(' AND price <= $maxPrice', { maxPrice });
}

query.append(' ORDER BY created_at DESC LIMIT $limit', { limit: 10 });

const [products] = await db.query(query).collect();
```

###  Query builder pattern[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#query-builder-pattern)

```ts
class QueryBuilder {
    private query: BoundQuery;
    
    constructor(table: string) {
        this.query = new BoundQuery(`SELECT * FROM ${table} WHERE 1=1`);
    }
    
    where(field: string, value: unknown): this {
                this.query.append(` AND ${field} = $${field}`,
            { [field]: value });
        return this;
    }
    
    limit(count: number): this {
        this.query.append(' LIMIT $limit', { limit: count });
        return this;
    }
    
    build(): BoundQuery {
        return this.query;
    }
}

// Usage
const builder = new QueryBuilder('users');
const query = builder
    .where('status', 'active')
    .where('verified', true)
    .limit(10)
    .build();

const [users] = await db.query(query).collect();
```

###  Reusable query fragments[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#reusable-query-fragments)

```ts
// Define reusable fragments
const activeFilter = new BoundQuery('status = $status',
    { status: 'active' });
const verifiedFilter = new BoundQuery('verified = $verified',
    { verified: true });

// Combine them
const query = new BoundQuery('SELECT * FROM users WHERE ');
query.append(activeFilter);
query.append(' AND ');
query.append(verifiedFilter);

const [users] = await db.query(query).collect();
```

###  Complex multi-statement query[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#complex-multi-statement-query)

```ts
const userId = new RecordId('users', 'john');
const postData = {
    title: 'My Post',
    content: 'Content here'
};

const query = new BoundQuery();

query.append('BEGIN TRANSACTION;');

query.append(
    'UPDATE $userId SET post_count += 1;',
    { userId }
);

query.append(
        'CREATE posts SET author = $author, title = $title,
        content = $content;',
    {
        author: userId,
        title: postData.title,
        content: postData.content
    }
);

query.append('COMMIT TRANSACTION;');

await db.query(query).collect();
```

###  Pagination helper[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#pagination-helper)

```ts
function paginatedQuery(
    table: string,
    page: number,
    pageSize: number,
    filters?: Record<string, unknown>
): BoundQuery {
    const query = new BoundQuery(`SELECT * FROM ${table} WHERE 1=1`);
    
    if (filters) {
        for (const [key, value] of Object.entries(filters)) {
            query.append(` AND ${key} = $${key}`, { [key]: value });
        }
    }
    
    const offset = (page - 1) * pageSize;
    query.append(' START $offset LIMIT $limit', {
        offset,
        limit: pageSize
    });
    
    return query;
}

// Usage
const query = paginatedQuery('users', 2, 20, { status: 'active' });
const [users] = await db.query(query).collect();
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#best-practices)
###  1. Use surql template instead[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#1-use-surql-template-instead)
For most cases, the `surql` template is easier:

```ts
// Good: surql template (recommended)
const query = surql`SELECT * FROM users WHERE age > ${age}`;

// Also good: BoundQuery (more manual)
const query = new BoundQuery(
    'SELECT * FROM users WHERE age > $age',
    { age }
);
```

###  2. Validate parameter names[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#2-validate-parameter-names)

```ts
// Good: Consistent parameter naming
const query = new BoundQuery(
    'SELECT * FROM users WHERE age > $age AND status = $status',
    { age: 18, status: 'active' }
);

// Avoid: Mismatched names
const query = new BoundQuery(
    'SELECT * FROM users WHERE age > $minAge',
    { age: 18 } // Wrong key name
);
```

###  3. Use append() for dynamic queries[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#3-use-append-for-dynamic-queries)

```ts
// Good: Incremental building
const query = new BoundQuery('SELECT * FROM users WHERE 1=1');
if (filter) {
    query.append(' AND status = $status', { status: filter });
}

// Avoid: String concatenation
let queryStr = 'SELECT * FROM users WHERE 1=1';
if (filter) {
    queryStr += ` AND status = '${filter}'`; // Unsafe!
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query#see-also)
  * •
[surql](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) - Template tag for queries
  * •
[Query](https://surrealdb.com/docs/reference/javascript/api/queries/query) - Query execution class
  * •
[SurrealQueryable.query()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) - Query method
  * •
[expr](https://surrealdb.com/docs/reference/javascript/api/utilities/expr) - Expression builder
