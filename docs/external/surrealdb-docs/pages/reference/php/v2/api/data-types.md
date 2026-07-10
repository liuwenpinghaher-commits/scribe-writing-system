---
title: "https://surrealdb.com/docs/reference/php/v2/api/data-types"
url: "https://surrealdb.com/docs/reference/php/v2/api/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/api/data-types

Source: https://surrealdb.com/docs/reference/php/v2/api/data-types

Version 2 represents SurrealQL types that PHP lacks with value classes in the `SurrealDB\SDK\Types` namespace. Every class extends the abstract `Value` and provides `escape()` (the inline SurrealQL form), `jsonSerialize()`, `equals()`, and `__toString()`.
##  `RecordId`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#recordid)
A record identifier: a table name and an ID.
Constructor

```php
new RecordId(string $table, string|int|array|object $id)
RecordId::from(string $table, string|int|array|object $id)
```

```php
use SurrealDB\SDK\Types\RecordId;

$id = new RecordId('person', 'tobie');
echo $id->table; // "person"
echo $id->id;    // "tobie"

$composite = new RecordId('temperature', ['city' => 'London', 'time' => 1700000000]);
```

The ID can be a string, integer, array, or object. The `table` and `id` properties expose the parts.
##  `StringRecordId`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#stringrecordid)
A record ID kept as a raw string. Use it to pass an ID through verbatim and let the server parse it.
Constructor

```php
new StringRecordId(StringRecordId|RecordId|string $id)
```

```php
use SurrealDB\SDK\Types\StringRecordId;

$db->select(new StringRecordId('person:tobie'))->execute();
```

##  `Table`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#table)
A table reference.
Constructor

```php
new Table(string $name)
```

```php
use SurrealDB\SDK\Types\Table;

$table = new Table('person');
echo $table->name; // "person"
```

##  `DateTime`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#datetime)
A datetime with nanosecond precision, stored as a `(seconds, nanoseconds)` pair.
Constructor and factories

```php
new DateTime(int $seconds = 0, int $nanoseconds = 0)
DateTime::fromString(string $iso)
DateTime::fromDateTime(DateTimeInterface $dateTime)
DateTime::now()
DateTime::epoch()
```

```php
use SurrealDB\SDK\Types\DateTime;

$now = DateTime::now();
$parsed = DateTime::fromString('2024-01-15T12:00:00.123456789Z');

$native = $now->toDateTimeImmutable(); // microsecond precision
$iso = $now->toIso();
```

##  `Duration`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#duration)
A duration with nanosecond precision, rendered with SurrealQL's compact syntax such as `1h30m`.
Constructor and factories

```php
new Duration(int $seconds = 0, int $nanoseconds = 0)
Duration::fromString(string $input)
Duration::seconds(int $value)   // also: nanoseconds, microseconds, milliseconds, minutes, hours, days, weeks, years
```

```php
use SurrealDB\SDK\Types\Duration;

$ttl = Duration::fromString('1h30m');
$combined = Duration::hours(1)->add(Duration::minutes(30));
echo $combined->totalNanoseconds();
```

##  `Decimal`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#decimal)
An arbitrary-precision decimal backed by `Brick\Math\BigDecimal`. Construct from a string to keep precision.
Constructor

```php
new Decimal(Decimal|BigDecimal|string|int|float $value)
```

```php
use SurrealDB\SDK\Types\Decimal;

$price = new Decimal('19.99');
$total = $price->multipliedBy(3); // 59.97
echo $total; // "59.97"
```

Arithmetic methods include `plus()`, `minus()`, `multipliedBy()`, `dividedBy()`, `abs()`, and `negated()`.
##  `Uuid`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#uuid)
A universally unique identifier, backed by `symfony/uid`.
Factories

```php
Uuid::v4()                      // random
Uuid::v7()                      // time-ordered
Uuid::fromString(string $uuid)
Uuid::fromBytes(string $bytes)
```

```php
use SurrealDB\SDK\Types\Uuid;

$id = Uuid::v7();
echo $id;            // canonical RFC 4122 string
$binary = $id->toBytes();
```

##  `Range` and `RecordIdRange`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#range)
A `Range` is a bounded or open interval. A `RecordIdRange` is a range of record IDs in a table. Bounds are `BoundIncluded`, `BoundExcluded`, or `null` for an open end.
Constructors

```php
new Range(BoundIncluded|BoundExcluded|null $begin, BoundIncluded|BoundExcluded|null $end)
new RecordIdRange(string $table, $begin, $end)
new BoundIncluded(mixed $value)
new BoundExcluded(mixed $value)
```

```php
use SurrealDB\SDK\Types\RecordIdRange;
use SurrealDB\SDK\Types\BoundIncluded;
use SurrealDB\SDK\Types\BoundExcluded;

// person:1..=100
$range = new RecordIdRange('person', new BoundIncluded(1), new BoundIncluded(100));
$slice = $db->select($range)->execute();
```

##  `Set`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#set)
An array whose items are deduplicated.
Constructor

```php
new Set(iterable $items = [])
```

```php
use SurrealDB\SDK\Types\Set;

$tags = new Set(['a', 'b', 'a']); // ['a', 'b']
```

##  `Bytes`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#bytes)
A binary value. Construct from a raw string or a base64url string.
Constructor and factory

```php
new Bytes(string $bytes)
Bytes::fromBase64(string $base64)
```

```php
use SurrealDB\SDK\Types\Bytes;

$bytes = new Bytes($raw);
echo $bytes->toBase64();
```

##  `None`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#none)
The SurrealQL `NONE` value, distinct from `null`. It is a singleton.

```php
use SurrealDB\SDK\Types\None;

$none = None::instance();
```

##  `File`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#file)
A reference to a file stored in a bucket.
Constructor

```php
new File(string $bucket, string $key)
```

```php
use SurrealDB\SDK\Types\File;

$file = new File('avatars', '/tobie.png');
echo $file->bucket; // "avatars"
echo $file->key;    // "/tobie.png"
```

##  `Future`[](https://surrealdb.com/docs/reference/php/v2/api/data-types#future)
An uncomputed SurrealQL [future](/docs/reference/query-language/language-primitives/data-types/futures), such as ` { ... }`. The body is the SurrealQL expression to evaluate.
Constructor

```php
new Future(string $body)
```

```php
use SurrealDB\SDK\Types\Future;

$future = new Future('{ created_at + 1w }');
echo $future->body;
```

Note
Futures were removed in SurrealDB `3.0`. This type is retained for compatibility with older servers and parity with the JavaScript SDK, and is deprecated.
##  Geometry[](https://surrealdb.com/docs/reference/php/v2/api/data-types#geometry)
Classes for each [GeoJSON geometry type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries). They all extend the abstract `Geometry`, which provides `toGeoJson()`, `is()`, and the static `Geometry::fromGeoJson()`.  
| Class  | Constructor  |  
| --- | --- |  
| `GeometryPoint`  | `new GeometryPoint(float $longitude, float $latitude)`  |  
| `GeometryLine`  | `new GeometryLine(GeometryPoint $first, GeometryPoint ...$rest)`  |  
| `GeometryPolygon`  | `new GeometryPolygon(GeometryLine $exterior, GeometryLine ...$interior)`  |  
| `GeometryMultiPoint`  | `new GeometryMultiPoint(GeometryPoint $first, GeometryPoint ...$rest)`  |  
| `GeometryMultiLine`  | `new GeometryMultiLine(GeometryLine $first, GeometryLine ...$rest)`  |  
| `GeometryMultiPolygon`  | `new GeometryMultiPolygon(GeometryPolygon $first, GeometryPolygon ...$rest)`  |  
| `GeometryCollection`  | `new GeometryCollection(Geometry $first, Geometry ...$rest)`  |  

```php
use SurrealDB\SDK\Types\GeometryPoint;
use SurrealDB\SDK\Types\GeometryLine;

$point = new GeometryPoint(-0.118092, 51.509865);
$line = new GeometryLine(
    new GeometryPoint(0, 0),
    new GeometryPoint(1, 1),
);

$geojson = $line->toGeoJson();
```

##  See also[](https://surrealdb.com/docs/reference/php/v2/api/data-types#see-also)
  * •
[Data types concept](https://surrealdb.com/docs/reference/php/v2/concepts/data-types) for the type mapping and guidance
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) for the database type system
