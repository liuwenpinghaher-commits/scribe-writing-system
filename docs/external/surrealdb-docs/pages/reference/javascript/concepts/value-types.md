---
title: "https://surrealdb.com/docs/reference/javascript/concepts/value-types"
url: "https://surrealdb.com/docs/reference/javascript/concepts/value-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/value-types

Source: https://surrealdb.com/docs/reference/javascript/concepts/value-types

SurrealDB has types that JavaScript does not: record IDs, nanosecond datetimes, arbitrary-precision decimals, and others. They live in [`@surrealdb/sqon`](https://www.npmjs.com/package/@surrealdb/sqon), which also ships codecs and a few core utilities. The `surrealdb` package re-exports all of it, so either import path works:

```ts
// With the driver (usual choice)
import { RecordId, Table, DateTime } from 'surrealdb';

// SQON only (no database client)
import { RecordId, Table, DateTime } from '@surrealdb/sqon';
```

The classes validate input, keep database precision, and plug into query methods and [codecs](https://surrealdb.com/docs/reference/javascript/concepts/codecs).
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#api-references)  
| Class  | Description  |  
| --- | --- |  
| [` RecordId `](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | Type-safe record identifiers with table and ID components  |  
| [` Table `](https://surrealdb.com/docs/reference/javascript/api/values/table)  | Type-safe table references for query methods  |  
| [` DateTime `](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | Datetime values with nanosecond precision  |  
| [` Duration `](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Time duration values with multiple unit support  |  
| [` Decimal `](https://surrealdb.com/docs/reference/javascript/api/values/decimal)  | Arbitrary precision decimal numbers  |  
| [` Uuid `](https://surrealdb.com/docs/reference/javascript/api/values/uuid)  | Universally unique identifiers (v4 and v7)  |  
| [` Range `](https://surrealdb.com/docs/reference/javascript/api/values/range)  | Bounded or unbounded range values  |  
| [` FileRef `](https://surrealdb.com/docs/reference/javascript/api/values/file-ref)  | References to files stored in SurrealDB  |  
| [` Geometry* `](https://surrealdb.com/docs/reference/javascript/api/values/geometry)  | GeoJSON geometry types (Point, Line, Polygon, etc.)  |  
##  Type mapping[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#type-mapping)
SurrealQL types map to JavaScript types as follows:  
| SurrealQL type  | JavaScript type  | Example  |  
| --- | --- | --- |  
| `bool`  | `boolean`  |  `true`, `false`  |  
|  `int`, `float`  | `number`  |  `42`, `3.14`  |  
| `string`  | `string`  | `"hello"`  |  
| `null`  | `null`  | `null`  |  
| `none`  | `undefined`  | `undefined`  |  
| `array`  | `Array`  | `[1, 2, 3]`  |  
| `object`  | `Object`  | `{`{ key: "value" }`}`  |  
| `set`  | `Set`  | `new Set([1, 2, 3])`  |  
| `bytes`  | `Uint8Array`  | `new Uint8Array([...])`  |  
| `record`  | [`RecordId`](https://surrealdb.com/docs/reference/javascript/api/values/record-id)  | `new RecordId('users', 'john')`  |  
| 
  * •

 | [`Table`](https://surrealdb.com/docs/reference/javascript/api/values/table)  | `new Table('users')`  |  
| `datetime`  | [`DateTime`](https://surrealdb.com/docs/reference/javascript/api/values/datetime)  | `DateTime.now()`  |  
| `duration`  | [`Duration`](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | `Duration.parse('1h30m')`  |  
| `decimal`  | [`Decimal`](https://surrealdb.com/docs/reference/javascript/api/values/decimal)  | `new Decimal('19.99')`  |  
| `uuid`  | [`Uuid`](https://surrealdb.com/docs/reference/javascript/api/values/uuid)  | `Uuid.v7()`  |  
| `geometry`  | [`Geometry*`](https://surrealdb.com/docs/reference/javascript/api/values/geometry)  | `new GeometryPoint([1, 2])`  |  
| `range`  | [`Range`](https://surrealdb.com/docs/reference/javascript/api/values/range)  | `new Range(1, 10)`  |  
| `file`  | [`FileRef`](https://surrealdb.com/docs/reference/javascript/api/values/file-ref)  | `record.avatar`  |  
##  RecordId and Table[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#recordid-and-table)
A [`RecordId`](https://surrealdb.com/docs/reference/javascript/api/values/record-id) is a table name plus an ID. A [`Table`](https://surrealdb.com/docs/reference/javascript/api/values/table) is a table reference on its own. From v2 onward, query methods expect a `Table` instance for table names, not a bare string, so table names are not confused with record IDs.

```ts
import { RecordId, Table } from 'surrealdb';

const userId = new RecordId('users', 'john');
const user = await db.select(userId);

const usersTable = new Table('users');
const allUsers = await db.select(usersTable);

const parsed = RecordId.parse('users:john');
```

The ID component of a `RecordId` can be a `string`, `number`, `bigint`, `Uuid`, array, or object. The `Table` class also supports a type parameter for type-safe query results.

```ts
const users = new Table<User>('users');
const results: User[] = await db.select(users);
```

##  DateTime and Duration[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#datetime-and-duration)
A [`DateTime`](https://surrealdb.com/docs/reference/javascript/api/values/datetime) is a timestamp with nanosecond precision. JavaScript's `Date` stops at milliseconds, so `DateTime` keeps what SurrealDB actually stored. A [`Duration`](https://surrealdb.com/docs/reference/javascript/api/values/duration) follows SurrealQL duration syntax.

```ts
import { DateTime, Duration } from 'surrealdb';

const now = DateTime.now();
const parsed = DateTime.parse('2024-01-15T12:00:00.123456789Z');
const jsDate = now.toDate();
const iso = now.toString();

const duration = Duration.parse('1h30m45s');
const ms = duration.toMilliseconds();
const seconds = duration.toSeconds();
```

##  Decimal[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#decimal)
A [`Decimal`](https://surrealdb.com/docs/reference/javascript/api/values/decimal) holds a decimal without floating-point rounding. Construct it from a string when precision matters.

```ts
import { Decimal } from 'surrealdb';

const price = new Decimal('19.99');
const display = price.toString();
const number = price.toNumber();
```

Note
Converting a `Decimal` to a `number` with `.toNumber()` may lose precision. Use `.toString()` when precision matters.
##  Uuid[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#uuid)
A [`Uuid`](https://surrealdb.com/docs/reference/javascript/api/values/uuid) represents a universally unique identifier. The class supports generating both v4 (random) and v7 (time-ordered) UUIDs.

```ts
import { Uuid } from 'surrealdb';

const random = Uuid.v4();
const timeOrdered = Uuid.v7();
const parsed = Uuid.parse('550e8400-e29b-41d4-a716-446655440000');
```

##  Range[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#range)
A [`Range`](https://surrealdb.com/docs/reference/javascript/api/values/range) is a bounded or open-ended span of values. In SurrealQL you use ranges to slice record IDs or filter numbers and times. `RecordIdRange` is the variant for a table ID range.

```ts
import { Range, RecordIdRange } from 'surrealdb';

const numericRange = new Range(1, 10);

const idRange = new RecordIdRange('users', { begin: 'a', end: 'f' });
const slice = await db.select(idRange);
```

##  FileRef[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#fileref)
A `FileRef` points at a file stored in SurrealDB. You see one when working with [file uploads](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files); it carries bucket and key metadata.

```ts
const [record] = await db.query('SELECT avatar FROM user:john');

if (record.avatar instanceof FileRef) {
    console.log(record.avatar.bucket);
    console.log(record.avatar.key);
}
```

##  Geometry types[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#geometry-types)
The SDK provides classes for all [GeoJSON geometry types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries): `GeometryPoint`, `GeometryLine`, `GeometryPolygon`, `GeometryMultiPoint`, `GeometryMultiLine`, `GeometryMultiPolygon`, and `GeometryCollection`.

```ts
import { GeometryPoint, GeometryLine, GeometryPolygon } from 'surrealdb';

const point = new GeometryPoint([longitude, latitude]);
const line = new GeometryLine([
    new GeometryPoint([1, 2]),
    new GeometryPoint([3, 4]),
]);
```

##  Parsing from strings[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#parsing-from-strings)
Most classes accept the same string forms as SurrealQL. Invalid input throws.

```ts
const recordId = RecordId.parse('users:john');
const datetime = DateTime.parse('2024-01-15T12:00:00Z');
const duration = Duration.parse('1h30m45s');
const uuid = Uuid.parse('550e8400-e29b-41d4-a716-446655440000');
```

##  Using native dates[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#using-native-dates)
By default, datetimes come back as `DateTime`. Set `useNativeDates` in [codec options](https://surrealdb.com/docs/reference/javascript/concepts/codecs#codec-options) if you would rather work with `Date` and can accept millisecond precision.

```ts
const db = new Surreal({
    codecOptions: {
        useNativeDates: true,
    },
});
```

##  String prefixes[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#string-prefixes)
The `surrealdb` package includes tagged templates that mirror SurrealQL's `s`, `d`, `r`, and `u` prefixes. They are not part of `@surrealdb/sqon`.

```ts
import { s, d, r, u } from 'surrealdb';

const string = s`I am a string`;
const date = d`2024-05-06T17:44:57.085Z`;
const record = r`person:tobie`;
const uuid = u`92b84bde-39c8-4b4b-92f7-626096d6c4d9`;
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#best-practices)
###  Use type parameters for type-safe queries[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#use-type-parameters-for-type-safe-queries)

```ts
const users = new Table<User>('users');
const results: User[] = await db.select(users);

const userId = new RecordId<'users', string>('users', 'john');
```

###  Prefer value classes over raw strings[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#prefer-value-classes-over-raw-strings)

```ts
await db.select(new RecordId('users', 'john'));

// Avoid string-based queries when possible
await db.query('SELECT * FROM users:john');
```

###  Validate parsed input[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#validate-parsed-input)

```ts
try {
    const uuid = Uuid.parse(userInput);
} catch (error) {
    console.error('Invalid UUID format');
}
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/value-types#learn-more)
  * •
[Data types API reference](https://surrealdb.com/docs/reference/javascript/api/values/) for the full list of value class documentation
  * •
[Codecs](https://surrealdb.com/docs/reference/javascript/concepts/codecs) for serialising and deserialising value types
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) for the database-level type system
  * •
[Utilities](https://surrealdb.com/docs/reference/javascript/concepts/utilities) for comparing and converting values
