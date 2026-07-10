---
title: "https://surrealdb.com/docs/reference/javascript/concepts/utilities"
url: "https://surrealdb.com/docs/reference/javascript/concepts/utilities"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/utilities

Source: https://surrealdb.com/docs/reference/javascript/concepts/utilities

Helpers are split across two packages. [`@surrealdb/sqon`](https://www.npmjs.com/package/@surrealdb/sqon) covers value comparison, conversion, and escaping. The `surrealdb` driver adds query-building tools for parameterised SurrealQL. Import from `surrealdb` when you use the driver and want both layers in one place.

```ts
// SQON (either package)
import { equals, jsonify, escapeIdent } from '@surrealdb/sqon';

// SDK only
import { surql, expr, BoundQuery, s, d, r, u } from 'surrealdb';
```

##  SQON utilities[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#sqon-utilities)
These live in `@surrealdb/sqon` alongside the [value types](https://surrealdb.com/docs/reference/javascript/concepts/value-types). You do not need the database client to use them.  
| Utility  | Description  |  
| --- | --- |  
| [` equals(a, b) `](https://surrealdb.com/docs/reference/javascript/api/utilities/equals)  | Deep equality comparison for all value types  |  
| ` jsonify(value) `  | Converts value types to JSON-safe string representations  |  
| [` escapeIdent(name) `](https://surrealdb.com/docs/reference/javascript/api/utilities/escape)  | Escapes table and field names for use in SurrealQL  |  
| [` escapeKey(key) `](https://surrealdb.com/docs/reference/javascript/api/utilities/escape)  | Escapes object keys for use in queries  |  
| [` escapeRid(value) `](https://surrealdb.com/docs/reference/javascript/api/utilities/escape)  | Escapes record ID components  |  
| [` escapeValue(value) `](https://surrealdb.com/docs/reference/javascript/api/utilities/escape)  | Escapes arbitrary values for embedding in queries  |  
| ` toSurqlString(value) `  | Converts a value tree to a SurrealQL string representation  |  
###  Comparing values with deep equality[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#comparing-values-with-deep-equality)
`===` compares object references, so two `RecordId` instances with the same table and ID still fail an identity check. `equals()` walks the structure instead, including nested objects, arrays, SurrealDB value classes, `Date`, `RegExp`, and mixed `bigint`/`number` values.

```ts
import { equals, RecordId } from '@surrealdb/sqon';

const id1 = new RecordId('users', 'john');
const id2 = new RecordId('users', 'john');

console.log(id1 === id2);        // false (different references)
console.log(equals(id1, id2));    // true (same value)
```

Handy when you want to know whether a fetched record changed between two reads:

```ts
const user1 = await db.select(userId);
const user2 = await db.select(userId);

if (!equals(user1, user2)) {
    console.log('Record was modified');
}
```

Note
Individual value classes also expose an `.equals()` instance method for single-type comparisons (e.g. `recordId.equals(other)`). Use the standalone `equals()` function for generic or cross-type comparisons.
###  Jsonifying query results[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#jsonifying-query-results)
`jsonify()` turns SurrealDB value classes in a result into the JSON string forms SurrealDB would use. Plain numbers, strings, and objects are left as they are. The return type reflects the conversion.

```ts
import { jsonify, RecordId, Decimal, Duration } from '@surrealdb/sqon';

const result = jsonify({
    rid: new RecordId('person', 'tobie'),
    dec: new Decimal('3.333333'),
    dur: new Duration('1d2h'),
    num: 123,
    str: 'hello',
});
```

```json
{
    "rid": "person:tobie",
    "dec": "3.333333",
    "dur": "1d2h",
    "num": 123,
    "str": "hello"
}
```

You can also call `.json()` on [query methods](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries#converting-results-to-json) to jsonify the result in one step.
For JSON with explicit type wrappers (for example `{ "$recordId": ... }`), use [`JsonCodec`](https://surrealdb.com/docs/reference/javascript/concepts/codecs#json-codec) instead.
###  Escaping identifiers and values[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#escaping-identifiers-and-values)
The escape helpers quote identifiers and values for hand-built SurrealQL. Prefer [bound queries](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries) or [value classes](https://surrealdb.com/docs/reference/javascript/concepts/value-types) when you can.

```ts
import { escapeIdent, escapeKey, escapeRid, escapeValue } from '@surrealdb/sqon';

escapeIdent('users');           // 'users'
escapeIdent('user-table');      // '`user-table`'
escapeIdent('select');          // '`select`'

escapeKey('user-property');     // properly escaped for object notation

escapeRid('john');              // 'john'
escapeRid('user@email.com');    // '`user@email.com`'

escapeValue('hello');           // "'hello'"
escapeValue(42);                // '42'
escapeValue(null);              // 'null'
escapeValue(undefined);         // 'none'
```

Warning
Escaping alone does not stop injection. Use [`surql`](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries) or [`BoundQuery`](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) for dynamic values.
###  Converting to SurrealQL strings[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#converting-to-surrealql-strings)
`toSurqlString()` walks a value tree (objects, arrays, SQON classes) and returns a SurrealQL literal string. Useful for logs, debugging, or SurrealQL snippets outside bound queries.

```ts
import { toSurqlString, RecordId, Decimal } from '@surrealdb/sqon';

toSurqlString(new RecordId('person', 'tobie')); // r"person:tobie"
toSurqlString(new Decimal('3.14'));             // 3.14dec
```

##  SDK utilities[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#sdk-utilities)
These ship with the `surrealdb` driver and tie into its query engine. They are not exported from `@surrealdb/sqon`.  
| Utility  | Description  |  
| --- | --- |  
| [` expr() `](https://surrealdb.com/docs/reference/javascript/api/utilities/expr)  | Composes type-safe expressions for WHERE clauses and conditions  |  
| [` surql `](https://surrealdb.com/docs/reference/javascript/api/utilities/surql)  | Tagged template for composing parameterised queries  |  
| [` BoundQuery `](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query)  | Parameterised query class with manual control  |  
| ` s, d, r, u `  | Tagged templates for SurrealQL string, datetime, record, and UUID prefixes  |  
| [` isRetryableConflict(error) `](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict)  |  Default predicate used by `.retry()`to detect retryable write conflicts  |  
###  Building expressions[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#building-expressions)
`expr()` and its operators build conditions for `.where()` and for `surql` templates. See [Bound queries](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries#composing-expressions) for the full list.

```ts
import { expr, surql, eq, gte, and, Table } from 'surrealdb';

const premiumAdults = expr(and(
    eq('tier', 'premium'),
    gte('age', 18),
));

const users = await db.select(new Table('users')).where(premiumAdults);
```

Operators cover comparisons (`eq`, `ne`, `gt`, `gte`, `lt`, `lte`), logic (`and`, `or`, `not`), strings and arrays (`contains`, `containsAny`, `containsAll`), geometry (`inside`, `outside`, `intersects`), and search (`matches`, `knn`).
###  Composing parameterised queries[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#composing-parameterised-queries)
`surql` and `BoundQuery` bind parameters so you do not splice user input into query strings. See [Bound queries](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries).

```ts
import { surql, BoundQuery } from 'surrealdb';

const minAge = 18;
const query = surql`SELECT * FROM users WHERE age >= ${minAge}`;
const [users] = await db.query(query);

const bound = new BoundQuery(
    'SELECT * FROM users WHERE status = $status',
    { status: 'active' },
);
bound.bind('tier', 'premium');
const [results] = await db.query(bound);
```

###  String prefix templates[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#string-prefix-templates)
The `s`, `d`, `r`, and `u` templates build typed literals with SurrealQL's string prefixes. See [Value types](https://surrealdb.com/docs/reference/javascript/concepts/value-types#string-prefixes).
##  Best practices[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#best-practices)
###  Use surql for parameterisation[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#use-surql-for-parameterisation)

```ts
const query = surql`SELECT * FROM users WHERE name = ${userName}`;

// Avoid string concatenation (injection risk)
const query = `SELECT * FROM users WHERE name = '${userName}'`;
```

###  Use expr for complex conditions[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#use-expr-for-complex-conditions)

```ts
const condition = expr(and(
    eq('status', 'active'),
    gte('age', 18),
));

await db.select(new Table('users')).where(condition);
```

###  Use equals for deep comparison[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#use-equals-for-deep-comparison)

```ts
if (equals(recordId1, recordId2)) {
    // Same value
}

// Avoid reference comparison (only true if same instance)
if (recordId1 === recordId2) { ... }
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/utilities#learn-more)
  * •
[equals API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/equals) for deep comparison details
  * •
[expr API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/expr) for expression builder operators
  * •
[surql API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/surql) for template tag details
  * •
[BoundQuery API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/bound-query) for manual query building
  * •
[Escape functions API reference](https://surrealdb.com/docs/reference/javascript/api/utilities/escape) for all escape utilities
  * •
[Codecs](https://surrealdb.com/docs/reference/javascript/concepts/codecs) for serialising value types over CBOR and JSON
  * •
[Bound queries](https://surrealdb.com/docs/reference/javascript/concepts/bound-queries) for safe query composition
  * •
[Value types](https://surrealdb.com/docs/reference/javascript/concepts/value-types) for SurrealDB-specific data classes
