---
title: "https://surrealdb.com/docs/reference/javascript/api/values/range"
url: "https://surrealdb.com/docs/reference/javascript/api/values/range"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/range

Source: https://surrealdb.com/docs/reference/javascript/api/values/range

The `Range` class provides generic range values for representing inclusive or exclusive ranges of ordered data types.
**Import:**

```ts
import { Range, BoundIncluded, BoundExcluded } from 'surrealdb';
```

**Source:** [value/range.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/range.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/values/range#type-parameters)
  * •
`Beg` - The type of the beginning bound
  * •
`End` - The type of the ending bound

##  Bound types[](https://surrealdb.com/docs/reference/javascript/api/values/range#bound-types)
Bounds are represented using `BoundIncluded` and `BoundExcluded` classes:
  * •
`new BoundIncluded(value)` — The bound includes the value
  * •
`new BoundExcluded(value)` — The bound excludes the value
  * •
`undefined` — Unbounded (no limit)

**Type:** `Bound = BoundIncluded | BoundExcluded | undefined`
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/range#constructor)
###  `new Range(begin, end)`[](https://surrealdb.com/docs/reference/javascript/api/values/range#constructor)
Create a new range value.
Syntax

```ts
new Range(begin, end)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/range#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `begin`  | `Bound<Beg>`  | The beginning bound (can be inclusive, exclusive, or undefined for unbounded).  |  
| `end`  | `Bound<End>`  | The ending bound (can be inclusive, exclusive, or undefined for unbounded).  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/range#examples)

```ts
// Numeric range [1, 100]
const numericRange = new Range(
    new BoundIncluded(1),
    new BoundIncluded(100)
);

// Date range
const dateRange = new Range(
    new BoundIncluded(new DateTime('2024-01-01')),
    new BoundIncluded(new DateTime('2024-12-31'))
);

// Half-open range [0, 10)
const halfOpen = new Range(
    new BoundIncluded(0),
    new BoundExcluded(10)
);
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/range#properties)
###  `begin`[](https://surrealdb.com/docs/reference/javascript/api/values/range#begin)
The beginning bound of the range.
**Type:** `Bound` — A `BoundIncluded`, `BoundExcluded`, or `undefined`

```ts
const range = new Range(
    new BoundIncluded(1),
    new BoundIncluded(10)
);

console.log(range.begin.value); // 1
console.log(range.begin instanceof BoundIncluded); // true
```

* * *
###  `end`[](https://surrealdb.com/docs/reference/javascript/api/values/range#end)
The ending bound of the range.
**Type:** `Bound` — A `BoundIncluded`, `BoundExcluded`, or `undefined`

```ts
const range = new Range(
    new BoundIncluded(1),
    new BoundIncluded(10)
);

console.log(range.end.value); // 10
console.log(range.end instanceof BoundIncluded); // true
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/range#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/range#tostring)
Convert to string representation.
Syntax

```ts
range.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/range#returns)
`string` - Range string (e.g., `1..10`, `1..=10`, `1>..10`)
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/range#examples-1)

```ts
// Inclusive range [1, 10]
const inclusive = new Range(
    new BoundIncluded(1),
    new BoundIncluded(10)
);
console.log(inclusive.toString()); // '1..=10'

// Exclusive range (1, 10)
const exclusive = new Range(
    new BoundExcluded(1),
    new BoundExcluded(10)
);
console.log(exclusive.toString()); // '1>..10'

// Half-open [1, 10)
const halfOpen = new Range(
    new BoundIncluded(1),
    new BoundExcluded(10)
);
console.log(halfOpen.toString()); // '1..10'
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/range#tojson)
Serialize for JSON.
Syntax

```ts
range.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/range#returns-1)
`string` - Range string representation
* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/range#equals)
Check if two ranges are equal.
Syntax

```ts
range.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/range#returns-2)
`boolean` - True if equal
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/range#complete-examples)
###  Numeric ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#numeric-ranges)

```ts
import { Surreal, Range, BoundIncluded } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Define age range for filtering
const adultRange = new Range(
    new BoundIncluded(18),
    new BoundIncluded(120)
);

// Query with range
const adults = await db.query(`
    SELECT * FROM users 
    WHERE age IN $range
`, {
    range: adultRange
}).collect();
```

###  Date ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#date-ranges)

```ts
import { DateTime, Range, BoundIncluded } from 'surrealdb';

// Define fiscal year
const fiscalYear = new Range(
    new BoundIncluded(new DateTime('2024-01-01T00:00:00Z')),
    new BoundIncluded(new DateTime('2024-12-31T23:59:59Z'))
);

// Query events in date range
const events = await db.query(`
    SELECT * FROM events 
    WHERE date IN $range
`, {
    range: fiscalYear
}).collect();
```

###  Price ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#price-ranges)

```ts
import { Decimal, Range, BoundIncluded } from 'surrealdb';

// Define price range for product filtering
const budgetRange = new Range(
    new BoundIncluded(new Decimal('0')),
    new BoundIncluded(new Decimal('100'))
);

const products = await db.query(`
    SELECT * FROM products 
    WHERE price IN $range
`, {
    range: budgetRange
}).collect();
```

###  Score ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#score-ranges)

```ts
import { Range, BoundIncluded } from 'surrealdb';

// Grade ranges
const gradeA = new Range(
    new BoundIncluded(90),
    new BoundIncluded(100)
);

const gradeB = new Range(
    new BoundIncluded(80),
    new BoundIncluded(89)
);

// Assign grades
const students = await db.query(`
    SELECT *,
        CASE
            WHEN score IN $gradeA THEN 'A'
            WHEN score IN $gradeB THEN 'B'
            ELSE 'C'
        END AS grade
    FROM students
`, {
    gradeA,
    gradeB
}).collect();
```

###  Time-based filtering[](https://surrealdb.com/docs/reference/javascript/api/values/range#time-based-filtering)

```ts
import { DateTime, Duration, Range, BoundIncluded } from 'surrealdb';

// Recent activity (last 30 days)
const now = DateTime.now();
const thirtyDaysAgo = now.sub(new Duration('30d'));

const recentRange = new Range(
    new BoundIncluded(thirtyDaysAgo),
    new BoundIncluded(now)
);

const recentActivity = await db.query(`
    SELECT * FROM activity_log 
    WHERE timestamp IN $range
    ORDER BY timestamp DESC
`, {
    range: recentRange
}).collect();
```

###  Pagination with ID ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#pagination-with-id-ranges)

```ts
import { RecordId, Range, BoundIncluded, BoundExcluded } from 'surrealdb';

// Fetch records in ID range
const idRange = new Range(
    new BoundIncluded(new RecordId('users', 'a')),
    new BoundExcluded(new RecordId('users', 'f'))
);

const users = await db.query(`
    SELECT * FROM users 
    WHERE id IN $range
`, {
    range: idRange
}).collect();
```

###  Exclusive ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#exclusive-ranges)

```ts
import { Range, BoundExcluded } from 'surrealdb';

// Exclusive range (not including boundaries)
const exclusive = new Range(
    new BoundExcluded(0),
    new BoundExcluded(100)
);
// Matches: 0 < x < 100

const results = await db.query(`
    SELECT * FROM measurements 
    WHERE value IN $range
`, {
    range: exclusive
}).collect();
```

###  Half-open ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#half-open-ranges)

```ts
import { Range, BoundIncluded, BoundExcluded } from 'surrealdb';

// Half-open range [start, end)
const halfOpen = new Range(
    new BoundIncluded(0),
    new BoundExcluded(10)
);
// Matches: 0 <= x < 10

// Common for array-like indexing
const items = await db.query(`
    SELECT * FROM items 
    WHERE index IN $range
`, {
    range: halfOpen
}).collect();
```

###  Multiple ranges[](https://surrealdb.com/docs/reference/javascript/api/values/range#multiple-ranges)

```ts
import { Range, BoundIncluded } from 'surrealdb';

// Define multiple severity levels
const low = new Range(
    new BoundIncluded(0),
    new BoundIncluded(3)
);

const medium = new Range(
    new BoundIncluded(4),
    new BoundIncluded(6)
);

const high = new Range(
    new BoundIncluded(7),
    new BoundIncluded(10)
);

// Query by severity
const criticalIssues = await db.query(`
    SELECT * FROM issues 
    WHERE severity IN $range
`, {
    range: high
}).collect();
```

###  Range queries in application[](https://surrealdb.com/docs/reference/javascript/api/values/range#range-queries-in-application)

```ts
import { Range, BoundIncluded, BoundExcluded, DateTime } from 'surrealdb';

function queryByRange<T>(
    start: T,
    end: T,
    inclusive: boolean = true
): Range<T, T> {
    return new Range(
        new BoundIncluded(start),
        inclusive ? new BoundIncluded(end) : new BoundExcluded(end)
    );
}

// Usage
const dateRange = queryByRange(
    new DateTime('2024-01-01'),
    new DateTime('2024-12-31')
);

const orders = await db.query(`
    SELECT * FROM orders 
    WHERE created_at IN $range
`, {
    range: dateRange
}).collect();
```

##  Range notation[](https://surrealdb.com/docs/reference/javascript/api/values/range#range-notation)
SurrealDB uses specific notation for ranges:  
| Notation  | Description  | Example  |  
| --- | --- | --- |  
| `a..=b`  | Inclusive both ends `[a, b]`  | `1..=10`  |  
| `a..b`  | Inclusive start, exclusive end `[a, b)`  | `1..10`  |  
| `a>..b`  | Exclusive start, exclusive end `(a, b)`  | `1>..10`  |  
| `a>..=b`  | Exclusive start, inclusive end `(a, b]`  | `1>..=10`  |  
##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/range#best-practices)
###  1. Use appropriate inclusivity[](https://surrealdb.com/docs/reference/javascript/api/values/range#1-use-appropriate-inclusivity)

```ts
// Good: Inclusive for dates (including full days)
const dateRange = new Range(
    new BoundIncluded(new DateTime('2024-01-01T00:00:00Z')),
    new BoundIncluded(new DateTime('2024-01-31T23:59:59Z'))
);

// Good: Exclusive end for array-like indexing
const arrayRange = new Range(
    new BoundIncluded(0),
    new BoundExcluded(10)
); // [0, 10)
```

###  2. Type safety[](https://surrealdb.com/docs/reference/javascript/api/values/range#2-type-safety)

```ts
// Good: Explicit types
const range: Range<number, number> = new Range(
    new BoundIncluded(1),
    new BoundIncluded(100)
);

// Good: Consistent types
const dateRange: Range<DateTime, DateTime> = new Range(
    new BoundIncluded(DateTime.now()),
    new BoundIncluded(DateTime.now().add(new Duration('1d')))
);
```

###  3. Validate bounds[](https://surrealdb.com/docs/reference/javascript/api/values/range#3-validate-bounds)

```ts
// Good: Ensure start <= end
function createRange<T>(start: T, end: T): Range<T, T> | null {
    if (start > end) {
        console.error('Invalid range: start must be <= end');
        return null;
    }
    
    return new Range(
        new BoundIncluded(start),
        new BoundIncluded(end)
    );
}
```

##  Use cases[](https://surrealdb.com/docs/reference/javascript/api/values/range#use-cases)
  * •
**Filtering** - Filter records by numeric, date, or other ordered values
  * •
**Pagination** - Query records in ID ranges
  * •
**Time Windows** - Define time-based query windows
  * •
**Price Filtering** - E-commerce price range searches
  * •
**Score Categorization** - Categorize by score ranges (grades, ratings)
  * •
**Geographic Bounds** - Coordinate ranges for maps

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/range#see-also)
  * •
[RecordIdRange](https://surrealdb.com/docs/reference/javascript/api/values/record-id#recordidrange) - Range of record IDs
  * •
[DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime) - Datetime values for date ranges
  * •
[Decimal](https://surrealdb.com/docs/reference/javascript/api/values/decimal) - Precise numbers for price ranges
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[SurrealQL Ranges](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges) - Database range syntax
