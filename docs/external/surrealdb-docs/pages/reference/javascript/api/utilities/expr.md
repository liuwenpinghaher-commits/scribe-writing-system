---
title: "https://surrealdb.com/docs/reference/javascript/api/utilities/expr"
url: "https://surrealdb.com/docs/reference/javascript/api/utilities/expr"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/utilities/expr

Source: https://surrealdb.com/docs/reference/javascript/api/utilities/expr

The `expr()` function creates type-safe SurrealQL expressions using standalone operator functions, providing an alternative to writing raw SurrealQL strings.
**Import:**

```ts
import { 
    expr,
    eq, eeq, ne,
    gt, gte, lt, lte,
    and, or, not,
    contains, containsAny, containsAll, containsNone,
    inside, outside, intersects,
    matches, knn,
    between,
    raw
} from 'surrealdb';
```

**Source:** [utils/expr.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/utils/expr.ts)
##  Function signature[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#function-signature)

```ts
function expr(expression: ExprLike): BoundQuery
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `expression`  | `ExprLike`  | An expression created using operator functions.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#returns)
`BoundQuery` - Compiled query with bindings
##  Comparison operators[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#comparison-operators)
###  `eq(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#eq)
Equality comparison (`=`).

```ts
const adults = expr(eq('age', 18));
await db.select(new Table('users')).where(adults);
// WHERE age = 18
```

* * *
###  `eeq(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#eeq)
Exact equality comparison (`==`).

```ts
const exact = expr(eeq('count', 0));
// WHERE count == 0
```

* * *
###  `ne(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#ne)
Not equal comparison (`!=`).

```ts
const notAdmin = expr(ne('role', 'admin'));
// WHERE role != 'admin'
```

* * *
###  `gt(field, value)`, `gte(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#gt-gte)
Greater than (`>`) and greater than or equal (`>=`).

```ts
const adults = expr(gt('age', 17));
const adultsInclusive = expr(gte('age', 18));
```

* * *
###  `lt(field, value)`, `lte(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#lt-lte)
Less than (`<`) and less than or equal (`<=`).

```ts
const young = expr(lt('age', 30));
const youngInclusive = expr(lte('age', 29));
```

##  Logical operators[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#logical-operators)
###  `and(...conditions)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#and)
Logical AND - all conditions must be true.

```ts
const premiumAdults = expr(and(
    eq('tier', 'premium'),
    gte('age', 18)
));
// WHERE tier = 'premium' AND age >= 18
```

* * *
###  `or(...conditions)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#or)
Logical OR - at least one condition must be true.

```ts
const adminOrModerator = expr(or(
    eq('role', 'admin'),
    eq('role', 'moderator')
));
// WHERE role = 'admin' OR role = 'moderator'
```

* * *
###  `not(condition)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#not)
Logical NOT - inverts the condition.

```ts
const notBanned = expr(not(eq('status', 'banned')));
// WHERE NOT status = 'banned'
```

##  Collection operators[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#collection-operators)
###  `contains(field, value)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#contains)
Check if field contains value (`CONTAINS`).

```ts
const hasTag = expr(contains('tags', 'featured'));
// WHERE tags CONTAINS 'featured'
```

* * *
###  `containsAny(field, values)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#containsany)
Check if field contains any of the values (`CONTAINSANY`).

```ts
const hasAnyTag = expr(containsAny('tags', ['new', 'featured', 'trending']));
// WHERE tags CONTAINSANY ['new', 'featured', 'trending']
```

* * *
###  `containsAll(field, values)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#containsall)
Check if field contains all values (`CONTAINSALL`).

```ts
const hasAllTags = expr(containsAll('tags', ['verified', 'premium']));
// WHERE tags CONTAINSALL ['verified', 'premium']
```

* * *
###  `containsNone(field, values)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#containsnone)
Check if field contains none of the values (`CONTAINSNONE`).

```ts
const noBadTags = expr(containsNone('tags', ['spam', 'banned']));
// WHERE tags CONTAINSNONE ['spam', 'banned']
```

##  Geometry operators[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#geometry-operators)
###  `inside(field, geometry)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#inside)
Check if geometry is inside another (`INSIDE`).

```ts
const inRegion = expr(inside('location', regionPolygon));
// WHERE location INSIDE $regionPolygon
```

* * *
###  `outside(field, geometry)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#outside)
Check if geometry is outside another (`OUTSIDE`).

```ts
const outsideZone = expr(outside('location', restrictedZone));
// WHERE location OUTSIDE $restrictedZone
```

* * *
###  `intersects(field, geometry)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#intersects)
Check if geometries intersect (`INTERSECTS`).

```ts
const overlaps = expr(intersects('area', otherArea));
// WHERE area INTERSECTS $otherArea
```

##  Search operators[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#search-operators)
###  `matches(field, query, ref?)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#matches)
Full-text search match (`@@` or `@ref@`).

```ts
// Basic match
const searchResults = expr(matches('content', 'searchTerm'));
// WHERE content @@ 'searchTerm'

// With reference number
const searchWithRef = expr(matches('content', 'searchTerm', 1));
// WHERE content @1@ 'searchTerm'
```

* * *
###  `knn(field, value, neighbors, metricOrEf?)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#knn)
K-nearest neighbors vector search.

```ts
const similar = expr(knn('embedding', [0.1, 0.2, 0.3], 10, 'cosine'));
// WHERE embedding <|10,COSINE|> [0.1, 0.2, 0.3]
```

##  Range operator[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#range-operator)
###  `between(field, a, b)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#between)
Range check — shortcut for `and(gte(field, a), lte(field, b))`.

```ts
const midRange = expr(between('price', 10, 50));
// WHERE price >= 10 AND price <= 50
```

##  Raw expressions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#raw-expressions)
###  `raw(sql)`[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#raw)
Create raw SurrealQL expressions.
Warning
Only use `raw()` when no other operator is applicable. Incorrect use risks SQL injection.

```ts
const custom = expr(raw('custom_function()'));
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#complete-examples)
###  Basic filtering[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#basic-filtering)

```ts
import { expr, eq, gte } from 'surrealdb';

// Single condition
const active = expr(eq('status', 'active'));
const users = await db.select(new Table('users')).where(active);

// Multiple conditions with AND
const premiumAdults = expr(and(
    eq('tier', 'premium'),
    gte('age', 18),
    eq('active', true)
));

const results = await db.select(new Table('users')).where(premiumAdults);
```

###  Complex conditions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#complex-conditions)

```ts
// Nested OR and AND
const eligibleUsers = expr(or(
    and(
        eq('tier', 'premium'),
        gte('age', 18)
    ),
    and(
        eq('role', 'admin'),
        eq('verified', true)
    )
));

const users = await db.select(new Table('users')).where(eligibleUsers);
```

###  Date filtering[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#date-filtering)

```ts
import { DateTime, Duration } from 'surrealdb';

const cutoffDate = DateTime.now().minus(Duration.parse('30d'));

const recentUsers = expr(gte('created_at', cutoffDate));
const users = await db.select(new Table('users')).where(recentUsers);
```

###  Array operations[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#array-operations)

```ts
// Check if user has specific tags
const hasFeaturedTag = expr(contains('tags', 'featured'));

// Check if has any of these tags
const hasPromotedTags = expr(containsAny('tags', ['featured', 'trending', 'new']));

// Must have all required tags
const fullyVerified = expr(containsAll('badges', ['email-verified', 'phone-verified']));

// Must not have any bad tags
const cleanContent = expr(containsNone('flags', ['spam', 'inappropriate']));
```

###  Geospatial queries[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#geospatial-queries)

```ts
import { GeometryPoint } from 'surrealdb';

const searchArea = new GeometryPolygon([/* ... */]);

// Find locations inside area
const nearby = expr(inside('location', searchArea));
const locations = await db.select(new Table('stores')).where(nearby);

// Find areas that intersect
const overlapping = expr(intersects('coverage_area', searchArea));
const zones = await db.select(new Table('zones')).where(overlapping);
```

###  Full-text search[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#full-text-search)

```ts
// Basic text search
const searchQuery = 'javascript tutorial';
const articles = await db.select(new Table('articles'))
    .where(expr(matches('content', searchQuery)));

// With reference number for multi-field search
const multiField = expr(or(
    matches('title', searchQuery, 1),
    matches('content', searchQuery, 1)
));
```

###  Vector search[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#vector-search)

```ts
// Find similar items using KNN
const queryVector = [0.1, 0.2, 0.3, /* ... */];

const similar = expr(knn('embedding', queryVector, 10, 'cosine'));
const results = await db.select(new Table('items')).where(similar);
```

###  Reusable expressions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#reusable-expressions)

```ts
// Define reusable filters
const activeFilter = expr(eq('active', true));
const verifiedFilter = expr(eq('verified', true));
const premiumFilter = expr(eq('tier', 'premium'));

// Combine as needed
const premiumActive = expr(and(activeFilter, premiumFilter));
const verifiedActive = expr(and(activeFilter, verifiedFilter));

// Use in queries
const users1 = await db.select(new Table('users')).where(premiumActive);
const users2 = await db.select(new Table('users')).where(verifiedActive);
```

###  Update with expressions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#update-with-expressions)

```ts
const condition = expr(and(
    eq('status', 'pending'),
    lt('created_at', DateTime.now().minus(Duration.parse('1h')))
));

const updated = await db.update(new Table('orders'))
    .merge({ status: 'expired' })
    .where(condition);
```

###  Delete with expressions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#delete-with-expressions)

```ts
const oldInactive = expr(and(
    eq('active', false),
    lt('last_login', DateTime.now().minus(Duration.parse('90d')))
));

const deleted = await db.delete(new Table('users')).where(oldInactive);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#best-practices)
###  1. Use expressions for complex conditions[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#1-use-expressions-for-complex-conditions)

```ts
// Good: Type-safe and reusable
const condition = expr(and(
    gte('age', 18),
    eq('verified', true)
));

// Avoid: Raw strings (no type safety)
const condition = 'age >= 18 AND verified = true';
```

###  2. Build expressions compositionally[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#2-build-expressions-compositionally)

```ts
// Good: Compose small expressions
const isAdult = expr(gte('age', 18));
const isVerified = expr(eq('verified', true));
const isActive = expr(eq('active', true));

const eligibleUsers = expr(and(isAdult, isVerified, isActive));

// You can reuse components
const premiumEligible = expr(and(isAdult, isVerified));
```

###  3. Avoid `raw()` when possible[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#3-avoid-raw-when-possible)

```ts
// Good: Use typed operators
const condition = expr(gte('score', 80));

// Avoid: Raw SQL (SQL injection risk)
const condition = expr(raw(`score >= ${userInput}`));
```

###  4. Parameterise dynamic values[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#4-parameterise-dynamic-values)

```ts
// Good: Values are automatically parameterised
const minAge = getUserInput();
const condition = expr(gte('age', minAge));

// Safe: minAge is bound as a parameter, not concatenated
```

##  Common patterns[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#common-patterns)
###  Dynamic filter builder[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#dynamic-filter-builder)

```ts
function buildUserFilter(options: {
    minAge?: number;
    tier?: string;
    active?: boolean;
}) {
    const conditions: ExprLike[] = [];
    
    if (options.minAge !== undefined) {
        conditions.push(gte('age', options.minAge));
    }
    if (options.tier) {
        conditions.push(eq('tier', options.tier));
    }
    if (options.active !== undefined) {
        conditions.push(eq('active', options.active));
    }
    
    return conditions.length > 0 ? expr(and(...conditions)) : null;
}

// Usage
const filter = buildUserFilter({ minAge: 18, tier: 'premium' });
if (filter) {
    const users = await db.select(new Table('users')).where(filter);
}
```

###  Search with multiple criteria[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#search-with-multiple-criteria)

```ts
function searchProducts(criteria: {
    minPrice?: Decimal;
    maxPrice?: Decimal;
    categories?: string[];
    inStock?: boolean;
}) {
    const conditions: ExprLike[] = [];
    
    if (criteria.minPrice) {
        conditions.push(gte('price', criteria.minPrice));
    }
    if (criteria.maxPrice) {
        conditions.push(lte('price', criteria.maxPrice));
    }
    if (criteria.categories?.length) {
        conditions.push(containsAny('categories', criteria.categories));
    }
    if (criteria.inStock !== undefined) {
        conditions.push(eq('in_stock', criteria.inStock));
    }
    
    return expr(and(...conditions));
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/utilities/expr#see-also)
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using expressions in queries
  * •
[surql](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) - Template tag for queries
  * •
[BoundQuery](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) - Parameterised queries
  * •
[SelectPromise.where()](https://surrealdb.com/docs/reference/javascript/api/queries/select-promise#where) - Using expressions with WHERE
