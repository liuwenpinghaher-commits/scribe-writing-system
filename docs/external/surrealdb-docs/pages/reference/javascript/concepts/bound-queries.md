---
title: "https://surrealdb.com/docs/reference/javascript/concepts/bound-queries"
url: "https://surrealdb.com/docs/reference/javascript/concepts/bound-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/bound-queries

Source: https://surrealdb.com/docs/reference/javascript/concepts/bound-queries

When composing dynamic queries, it is important to avoid string interpolation to prevent injection vulnerabilities. The JavaScript SDK provides bound queries and the `surql` template tag to safely parameterise values, along with an expressions API for composing dynamic conditions.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#api-references)  
| Utility  | Description  |  
| --- | --- |  
| [` surql `](https://surrealdb.com/docs/reference/javascript/api/utilities/surql)  | Tagged template literal for composing parameterised queries  |  
| [` BoundQuery `](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query)  | Class for manually building parameterised queries  |  
| [` expr() `](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)  | Composes type-safe expressions for use in queries  |  
##  Using the surql template tag[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#using-the-surql-template-tag)
The `surql` tagged template literal is the recommended way to compose parameterised queries. Interpolated values are automatically bound as parameters, preventing injection and preserving type safety.

```ts
import { surql } from 'surrealdb';

const name = 'John';
const minAge = 18;

const query = surql`SELECT * FROM users WHERE name = ${name} AND age > ${minAge}`;
const [users] = await db.query(query);
```

The `surrealql` export is an alias for `surql` if you prefer the longer name.

```ts
import { surrealql } from 'surrealdb';

const query = surrealql`CREATE person CONTENT ${{ name: 'Tobie' }}`;
```

Note
The SurrealQL [VSCode extension](https://marketplace.visualstudio.com/items?itemName=surrealdb.surrealql) provides syntax highlighting for surql template literals.
##  Building queries with boundquery[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#building-queries-with-boundquery)
The `BoundQuery` class provides manual control over query composition. You can construct a query with initial bindings, and incrementally append fragments with additional parameters.

```ts
import { BoundQuery } from 'surrealdb';

const query = new BoundQuery(
    'SELECT * FROM users WHERE status = $status',
    { status: 'active' },
);

await db.query(query);
```

###  Appending query fragments[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#appending-query-fragments)
Use the `.append()` method to conditionally add SurrealQL fragments. The method uses the same tagged template literal syntax as `surql`, so interpolated values are automatically bound.

```ts
const query = new BoundQuery('SELECT * FROM person');
const filterName = 'Alice';

if (filterName) {
    query.append(surql` WHERE name = ${filterName}`);
}

const [results] = await db.query(query);
```

##  Composing expressions[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#composing-expressions)
The [expressions API](https://surrealdb.com/docs/reference/javascript/api/utilities/expr) provides functions for building dynamic conditions in a type-safe way. Expressions integrate with both `surql` and query builder methods like `.where()`.

```ts
const checkActive = true;

await db.query(surql`SELECT * FROM users WHERE ${eq('active', checkActive)}`);
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#learn-more)
  * •
[surql API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) for template tag details
  * •
[BoundQuery API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) for manual query building
  * •
[expr API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/expr) for the full expressions API
  * •
[Executing queries](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) for running queries against the database
