---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/data-types"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/data-types

Source: https://surrealdb.com/docs/reference/php/v2/concepts/data-types

SurrealDB has types that PHP does not, such as record IDs, nanosecond datetimes, durations, and arbitrary-precision decimals. Version 2 of the SDK represents these with value classes in the `SurrealDB\SDK\Types` namespace. Native PHP types pass through unchanged.
##  Type mapping[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#type-mapping)  
| SurrealQL type  | PHP type  |  
| --- | --- |  
| `bool`  | `bool`  |  
|  `int`, `float`  |  `int`, `float`  |  
| `string`  | `string`  |  
| `null`  | `null`  |  
| `none`  | [`None`](https://surrealdb.com/docs/reference/php/v2/api/data-types#none)  |  
| `array`  |  `array` (list)  |  
| `object`  |  `array` (associative)  |  
| `set`  | [`Set`](https://surrealdb.com/docs/reference/php/v2/api/data-types#set)  |  
| `bytes`  | [`Bytes`](https://surrealdb.com/docs/reference/php/v2/api/data-types#bytes)  |  
| `datetime`  | [`DateTime`](https://surrealdb.com/docs/reference/php/v2/api/data-types#datetime)  |  
| `duration`  | [`Duration`](https://surrealdb.com/docs/reference/php/v2/api/data-types#duration)  |  
| `decimal`  | [`Decimal`](https://surrealdb.com/docs/reference/php/v2/api/data-types#decimal)  |  
| `uuid`  | [`Uuid`](https://surrealdb.com/docs/reference/php/v2/api/data-types#uuid)  |  
| `record`  | [`RecordId`](https://surrealdb.com/docs/reference/php/v2/api/data-types#recordid)  |  
| `range`  | [`Range`](https://surrealdb.com/docs/reference/php/v2/api/data-types#range)  |  
| `geometry`  |  [`Geometry`](https://surrealdb.com/docs/reference/php/v2/api/data-types#geometry) types  |  
| `file`  | [`File`](https://surrealdb.com/docs/reference/php/v2/api/data-types#file)  |  
##  Record IDs and tables[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#record-ids-and-tables)
A [`RecordId`](https://surrealdb.com/docs/reference/php/v2/api/data-types#recordid) is a table name plus an ID. A [`Table`](https://surrealdb.com/docs/reference/php/v2/api/data-types#table) is a table reference on its own. The query builders accept either, so the SDK can tell a record from a table.

```php
use SurrealDB\SDK\Types\RecordId;
use SurrealDB\SDK\Types\Table;

$tobie = new RecordId('person', 'tobie');
$people = new Table('person');

$record = $db->select($tobie)->execute();
$all = $db->select($people)->execute();
```

The ID can be a string, integer, array, or object for composite keys.

```php
$metric = new RecordId('metric', ['service' => 'api', 'host' => 'server-01']);
```

To send a record ID that is already a string, wrap it in `StringRecordId` so the server parses it.

```php
use SurrealDB\SDK\Types\StringRecordId;

$db->select(new StringRecordId('person:tobie'))->execute();
```

##  Datetimes and durations[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#datetimes-and-durations)
A [`DateTime`](https://surrealdb.com/docs/reference/php/v2/api/data-types#datetime) keeps nanosecond precision, which PHP's native `DateTime` does not. A [`Duration`](https://surrealdb.com/docs/reference/php/v2/api/data-types#duration) follows SurrealQL duration syntax.

```php
use SurrealDB\SDK\Types\DateTime;
use SurrealDB\SDK\Types\Duration;

$now = DateTime::now();
$parsed = DateTime::fromString('2024-01-15T12:00:00.123456789Z');

$ttl = Duration::fromString('1h30m');
```

##  Decimals[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#decimals)
A [`Decimal`](https://surrealdb.com/docs/reference/php/v2/api/data-types#decimal) holds a number without floating-point rounding. Construct it from a string when precision matters.

```php
use SurrealDB\SDK\Types\Decimal;

$price = new Decimal('19.99');
```

##  UUIDs[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#uuids)
A [`Uuid`](https://surrealdb.com/docs/reference/php/v2/api/data-types#uuid) represents a universally unique identifier, with helpers for v4 (random) and v7 (time-ordered).

```php
use SurrealDB\SDK\Types\Uuid;

$random = Uuid::v4();
$timeOrdered = Uuid::v7();
```

##  Geometries[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#geometries)
The SDK provides classes for every [GeoJSON geometry type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries): `GeometryPoint`, `GeometryLine`, `GeometryPolygon`, `GeometryMultiPoint`, `GeometryMultiLine`, `GeometryMultiPolygon`, and `GeometryCollection`.

```php
use SurrealDB\SDK\Types\GeometryPoint;
use SurrealDB\SDK\Types\GeometryLine;

$point = new GeometryPoint(-0.118092, 51.509865);
$line = new GeometryLine(
    new GeometryPoint(0, 0),
    new GeometryPoint(1, 1),
);
```

##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/data-types#learn-more)
  * •
[Data types API reference](https://surrealdb.com/docs/reference/php/v2/api/data-types) for every value class and its methods
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) for the database type system
