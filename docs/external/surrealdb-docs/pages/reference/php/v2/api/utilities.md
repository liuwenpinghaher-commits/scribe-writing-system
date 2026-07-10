---
title: "https://surrealdb.com/docs/reference/php/v2/api/utilities"
url: "https://surrealdb.com/docs/reference/php/v2/api/utilities"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/api/utilities

Source: https://surrealdb.com/docs/reference/php/v2/api/utilities

This page covers the supporting types used across the SDK: bound queries, driver-wide options, and the enums that statements accept.
##  `BoundQuery`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery)
A parameter-bound SurrealQL fragment: the query text plus the values bound to generated placeholders. The query builders compile to a `BoundQuery`, and you can build one by hand.
**Namespace:** `SurrealDB\SDK\Query\BoundQuery`
Constructor

```php
new BoundQuery(string $query = '', array $bindings = [])
```
  
| Method  | Description  |  
| --- | --- |  
| `bind(mixed $value): string`  | Bind a value and return its generated placeholder, such as `$bind_0`  |  
| `append(BoundQuery\|string $sql, array $bindings = []): self`  | Append SurrealQL or another `BoundQuery`, merging bindings  |  

```php
use SurrealDB\SDK\Query\BoundQuery;

$query = new BoundQuery('SELECT * FROM person WHERE age > $min', ['min' => 18]);
$results = $db->query($query);
```

You can pass a `BoundQuery` to a builder's `where()` to keep dynamic values parameterised.

```php
$db->select(new Table('person'))
    ->where(new BoundQuery('age > $min', ['min' => 18]))
    ->execute();
```

##  `DriverOptions`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#driveroptions)
Driver-wide configuration passed to the `Surreal` constructor. Every field has a default, so `new Surreal()` works without arguments.
**Namespace:** `SurrealDB\SDK\Connection\DriverOptions`  
| Option  | Type  | Default  | Description  |  
| --- | --- | --- | --- |  
| `format`  | `CodecEnum`  | `JSON`  | The wire format  |  
| `codec`  | `?Codec`  | derived from `format`  | A custom serialiser and deserialiser  |  
| `events`  | `?EventDispatcherInterface`  | new dispatcher  | PSR-14 dispatcher for [domain events](https://surrealdb.com/docs/reference/php/v2/concepts/events)  |  
| `logger`  | `?LoggerInterface`  | null logger  | PSR-3 logger; enables the [logging middleware](https://surrealdb.com/docs/reference/php/v2/concepts/middleware#logging)  |  
| `tracer`  | `?Tracer`  | no-op tracer  | Tracing backend; enables [telemetry](https://surrealdb.com/docs/reference/php/v2/concepts/observability)  |  
| `meter`  | `?Meter`  | no-op meter  | Metrics backend; enables [telemetry](https://surrealdb.com/docs/reference/php/v2/concepts/observability)  |  
| `httpClient`  | `?ClientInterface`  | discovered  | PSR-18 HTTP client  |  
| `requestFactory`  | `?RequestFactoryInterface`  | discovered  | PSR-17 request factory  |  
| `streamFactory`  | `?StreamFactoryInterface`  | discovered  | PSR-17 stream factory  |  
| `scheduler`  | `?Scheduler`  | sync scheduler  | Synchronous or async scheduler  |  
| `engines`  | `?array`  | `null`  | Engine factory overrides keyed by URL scheme  |  
| `webSocketClientFactory`  | `?Closure`  | `null`  | Override the WebSocket client  |  
| `webSocketTransportFactory`  | `?Closure`  | `null`  | Swap the entire WebSocket transport  |  
| `httpTransportFactory`  | `?Closure`  | `null`  | Swap the entire HTTP transport  |  
| `middleware`  | `list<MiddlewareInterface>`  | `[]`  | Extra [middleware](https://surrealdb.com/docs/reference/php/v2/concepts/middleware) appended to the pipeline  |  
| `pingInterval`  | `int`  | `30`  | WebSocket ping interval in seconds  |  
The `engines` and `*Factory` options are the transport-level extension seams. The [runtime presets](https://surrealdb.com/docs/reference/php/v2/concepts/runtimes) configure them for you, so you only set them when supplying a transport of your own.

```php
use SurrealDB\SDK\Surreal;
use SurrealDB\SDK\Connection\DriverOptions;
use SurrealDB\SDK\Enum\CodecEnum;

$db = new Surreal(new DriverOptions(format: CodecEnum::CBOR));
```

##  `CodecEnum`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#codecenum)
The wire format used to serialise values.
**Namespace:** `SurrealDB\SDK\Enum\CodecEnum`
  * •
`CodecEnum::JSON` is the zero-dependency default.
  * •
`CodecEnum::CBOR` is a compact binary format that preserves more type information.

###  Custom codecs[](https://surrealdb.com/docs/reference/php/v2/api/utilities#custom-codecs)
A `Codec` pairs a serialiser with a deserialiser. The built-in pairs are `Codec::json()` and `Codec::cbor()`, selected from the `format` option. To customise serialisation, implement `SurrealDB\SDK\Codec\SerializerInterface` and `SurrealDB\SDK\Codec\DeserializerInterface`, wrap them in a `Codec`, and pass it as the `codec` option.

```php
use SurrealDB\SDK\Codec\Codec;
use SurrealDB\SDK\Connection\DriverOptions;
use SurrealDB\SDK\Enum\CodecEnum;

$db = new Surreal(new DriverOptions(
    format: CodecEnum::CBOR,
    codec: new Codec(new MySerializer(), new MyDeserializer()),
));
```

The codec must agree with the `format`: a `CBOR` format requires a CBOR-compatible codec, and a `JSON` format requires a JSON-compatible one. Mixing them throws a `ConfigurationException`.
##  `Output`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#output)
The `RETURN` clause variants accepted by mutating statements.
**Namespace:** `SurrealDB\SDK\Enum\Output`
**Values:** `NONE`, `NULL_`, `DIFF`, `BEFORE`, `AFTER`

```php
use SurrealDB\SDK\Enum\Output;

$db->create(new RecordId('person', 'tobie'))
    ->content(['name' => 'Tobie'])
    ->output(Output::AFTER)
    ->execute();
```

##  `Endpoint`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#endpoint)
A parsed, normalised endpoint. `connect()` accepts a string and parses it for you, but you can build one explicitly with `Endpoint::parse()`. Remote schemes (`ws`, `wss`, `http`, `https`) get a `/rpc` suffix when one is missing.
**Namespace:** `SurrealDB\SDK\Connection\Endpoint`

```php
use SurrealDB\SDK\Connection\Endpoint;

$endpoint = Endpoint::parse('ws://127.0.0.1:8000'); // path becomes /rpc
$db->connect($endpoint);
```

##  `Features`[](https://surrealdb.com/docs/reference/php/v2/api/utilities#features)
A catalogue of features with the server version each requires. Pass one to [`isFeatureSupported()`](https://surrealdb.com/docs/reference/php/v2/api/core#isfeaturesupported).
**Namespace:** `SurrealDB\SDK\Protocol\Features`

```php
Features::liveQueries();
Features::transactions();
Features::sessions();
Features::refreshTokens();
Features::surrealMl();
```

##  See also[](https://surrealdb.com/docs/reference/php/v2/api/utilities#see-also)
  * •
[Core classes](https://surrealdb.com/docs/reference/php/v2/api/core) for the `Surreal` entry point
  * •
[Query builders](https://surrealdb.com/docs/reference/php/v2/api/query-builders) for the fluent statement API
  * •
[Executing queries](https://surrealdb.com/docs/reference/php/v2/concepts/executing-queries) for the guide
