---
title: "https://surrealdb.com/docs/reference/php/v1/concepts/data-types"
url: "https://surrealdb.com/docs/reference/php/v1/concepts/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/concepts/data-types

Source: https://surrealdb.com/docs/reference/php/v1/concepts/data-types

The PHP SDK translates all SurrealQL datatypes into native PHP types, or a custom implementation. This document describes all datatypes, and links to their respective documentation.
##  Data types overview[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#data-types-overview)  
| Datatype  | Kind  | Documentation  |  
| --- | --- | --- |  
| String  | Native  | [`string`on php.net](https://www.php.net/manual/en/language.types.string.php)  |  
| Int  | Native  | [`integer`on php.net](https://www.php.net/manual/en/language.types.integer.php)  |  
| Float  | Native  | [`float`on php.net](https://www.php.net/manual/en/language.types.float.php)  |  
| Bool  | Native  | [`bool`on php.net](https://www.php.net/manual/en/language.types.boolean.php)  |  
| null  | Native  | [`null`on php.net](https://www.php.net/manual/en/language.types.null.php)  |  
| Array / Associative  | Native  | [`array`on php.net](https://www.php.net/manual/en/language.types.array.php)  |  
| Datetime  | Native  | [`DateTime`on php.net](https://www.php.net/manual/en/class.datetime)  |  
| Binary  | Custom  | [`CborByteString`](https://github.com/welpie21/cbor.php/blob/main/src/utils/CborByteString.php)  |  
| None  | Custom  | [`[None](#none)`](https://github.com/surrealdb/surrealdb.php/blob/main/src/Cbor/Types/None.php)  |  
| RecordId  | Custom  | `[RecordId](#recordid)`  |  
| Uuid  | Custom  | `[Uuid](#uuid)`  |  
| Duration  | Custom  | `[Duration](#duration)`  |  
| Geometry  | Custom  | `[Geometry](#geometry)`  |  
| Decimal  | Custom  | `[Decimal](#decimal)`  |  
| Table  | Custom  | `[Table](#table)`  |  
  
  

##  `RecordId`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#recordid)
When you receive a RecordId from SurrealDB, it will always be represented as a `RecordId` class.  
This class holds a `tb` and `id` field, representing the table name, and a unique identifier for the record on that table.  
A `RecordId` can be converted into a string, and will be represented as such when it's converted to JSON.
Signature

```php
new RecordId(string $tb, string|int|array $id)
```

###  Working with a `RecordId`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#working-with-a-recordid)
Constructing

```php
// table is "person"
// unique identifier on the table is "john"
$rid = new RecordId("person", "john");
```

Extracting data

```php
// Simple
$rid = new RecordId("person", "john");
$rid->tb // "person"
$rid->id // "john"

// Complex
$rid = new RecordId("recording", ["city" => "London", "data" => 123 ]);

$rid->id         // [ "city" => "London", "data" => 123 ]
$rid->id["city"] // "London"
$rid->id["data"] // 123
```

###  Convert to String[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#convert-to-string)
The PHP SDK efficiently handles escaping the `tb` and `id` parts in Record Id's into their string counterparts.  
Below are some examples
Simple

```php
$rid = (new RecordId("table", 123))->toString();
// 'table:123'
$rid = (new RecordId("table", "abc"))->toString();
// 'table:abc'
```

Complex characters

```php
$rid = (new RecordId("table", "123"))->toString();
// 'table:`123`'
$rid = (new RecordId("table", "123withletters"))->toString();
// 'table:123withletters'
$rid = (new RecordId("table", "complex-string"))->toString();
// 'table:`complex-string`'
$rid = (new RecordId("table-name", 123))->toString();
// '`table-name`:123'
```

Objects and Arrays

```php
$rid = (new RecordId("table", ["city" => "London"]))->toString();
// 'table:{ city: "London" }'
$rid = (new RecordId("table", ["London"]))->toString();
// 'table:["London"]'
```

###  Send back string[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#send-back-string)
If you need to send back a Record Id in string format, you can do so with the `StringRecordId` class.
We do not implement the parsing of Record Ids in the PHP SDK, as that would mean that we need to be able to parse any SurrealQL value,   
which comes with a cost. Instead you can send it over as a string with `StringRecordId`, allowing the server to handle the parsing.

```php
new StringRecordId("person:john");
```

  

##  `Geometry`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometry)
When a Geometry is sent back from SurrealDB, be it a `Point`, `Line`, `Polygon`, `MultiPoint`, `MultiLine`, `MultiPolygon` or `Collection`, it will be represented as a derivative of the `Geometry` class.
###  Methods[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#methods)
Below, are all the methods implemented across all geometry derivatives.
####  `->toJSON()`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#-tojson)
Used to convert a geometry to a GeoJSON representation
Signature

```php
Geometry->toJson();
```

Example

```php
$line = new GeometryLine([
    new GeometryPoint([1, 2]),
    new GeometryPoint([3, 4]),
]);

$line->toJson();                    // '{ type: "LineString", coordinates: [ [1, 2], [3, 4] ] }'
json_encode($line);                 // '{ type: "LineString", coordinates: [ [1, 2], [3, 4] ] }'
```

####  `->is()`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#-is)
Used to convert a check if geometry X is exactly equal to geometry Y
Signature

```php
Geometry->is(Geometry $geometry)
```

Example

```php
$point1 = new GeometryPoint([1, 2]);
$point2 = new GeometryPoint([3, 4]);
$line = new GeometryLine([$point1, $point2]);

$point1->is($point1);      // true
$point1->is($point2);      // false
$point1->is($line);        // false

// Checks the inner values, does not need to be the same instance
$duplicate = new GeometryPoint([1, 2]);
$point1->is($duplicate);   // true
```

####  `->clone()`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#-clone)
Used to deeply clone a geometry. Creates a new replica of the original instance, but changing the new instance won't affect the other.
Signature

```php
Geometry->clone()
```

###  Properties[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#properties)
####  `->coordinates`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#-coordinates)
A getter property, representing the coordinates as shown in GeoJSON format for X Geometry
Signature

```php
Geometry.coordinates
```

###  Derivatives[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#derivatives)
####  `GeometryPoint`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrypoint)
A [point](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#point) in space, made up of a long and lat coordinate, automatically converted to a float.
Signature

```php
new GeometryPoint([int|float|Decimal $long, int|float|Decimal $lat]);
```

####  `GeometryLine`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometryline)
A line, made up of two or more points
Signature

```php
new GeometryLine([GeometryPoint, GeometryPoint, ...GeometryPoint[]]);
```

####  `GeometryPolygon`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrypolygon)
A polygon, made up of self-closing lines
**Note** : The lines inside the polygon will automatically be closed if not already, meaning that the last point will be the same as the first.
Signature

```php
new GeometryPolygon([GeometryLine, ...GeometryLine[]]);
```

####  `GeometryMultiPoint`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrymultipoint)
A collection of one or more points
Signature

```php
new GeometryMultiPoint([GeometryPoint, ...GeometryPoint[]]);
```

####  `GeometryMultiLine`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrymultiline)
A collection of one or more lines
Signature

```php
new GeometryMultiLine([GeometryLine, ...GeometryLine[]]);
```

####  `GeometryMultiPolygon`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrymultipolygon)
A collection of one or more polygons
Signature

```php
new GeometryMultiPolygon([GeometryPolygon, ...GeometryPolygon[]]);
```

####  `GeometryCollection`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#geometrycollection)
A collection of one or more `Geometry` derivatives
Signature

```php
new GeometryCollection([Geometry, ...Geometry[]]);
```

  

##  `Decimal`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#decimal)
Because PHP does not support Decimals natively,   
our SDK represents them in a `Decimal` class as a string.   
This means if you want to work with Decimals, you will need to use an external library for this.
Signature

```php
new Decimal(string|float|Decimal $decimal);
```

###  Converting to string[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#converting-to-string)

```php
$decimal = new Decimal("123.456");
decimal->toString(); // "123.456"
```

###  Converting to JSON[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#converting-to-json)
A `Decimal` will be represented as a string in JSON to perserve accuracy

```php
$decimal = new Decimal("123.456");
$decimal->toJson();                  // "123.456"
json_encode(decimal);                // "123.456"
```

  

##  `Table`[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#table)
When you get a table name sent back from SurrealDB, it will be represented as a `Table` class.
Signature

```php
new Table(string $table);
```

###  Converting to string[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#converting-to-string-1)

```php
$table = new Table("table");
$table->toString();              // "table"
```

###  Converting to JSON[](https://surrealdb.com/docs/reference/php/v1/concepts/data-types#converting-to-json-1)
A `Table` will be represented as a string in JSON

```php
$table = new Table("table");
$table->jsonSerializable();      // "table"
json_encode($table);             // "table"
```
