---
title: "https://surrealdb.com/docs/reference/javascript/concepts/codecs"
url: "https://surrealdb.com/docs/reference/javascript/concepts/codecs"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/codecs

Source: https://surrealdb.com/docs/reference/javascript/concepts/codecs

Record IDs, nanosecond datetimes, decimals, and durations do not survive a round trip through plain JSON or untagged CBOR unchanged. SQON (SurrealQL Object Notation) is the wire format SurrealDB uses for these types. The [`@surrealdb/sqon`](https://www.npmjs.com/package/@surrealdb/sqon) package ships the codecs that convert between JavaScript value instances and that format.
When you use the `surrealdb` SDK over WebSocket or HTTP, those codecs run automatically on every request and response. You can also import them on their own if you are building a custom client, middleware, or data pipeline and do not need the full driver.
##  Available codecs[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#available-codecs)
Two codecs are fully implemented today:  
| Codec  | Wire format  | When to use  |  
| --- | --- | --- |  
| `CborCodec`  |  `Uint8Array`(CBOR with SurrealDB tags)  | RPC transport to SurrealDB - WebSocket and HTTP engines encode every request and decode every response with CBOR  |  
| `JsonCodec`  | Plain object tree (SQON JSON)  | JSON-safe interchange - logging, caching, REST APIs, or any environment where binary CBOR is impractical  |  
Both codecs represent the same values. If you encode with one and decode with the other, types are preserved as long as you decode back into the matching value classes.
Note
`FlatBufferCodec` is exported for forward compatibility but is not implemented in this version.
##  Why you need a codec[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#why-you-need-a-codec)
Without one, SurrealDB-specific types get flattened or misread on the way in or out:
  * •
A `RecordId` can turn into a plain string and lose its table
  * •
A `Decimal` can be rounded by JavaScript's `number` type
  * •
`none` can be confused with a missing JSON field or with `null`
  * •
Datetimes can drop from nanoseconds to milliseconds

That is why query results come back as `DateTime`, `RecordId`, and the other value classes: the CBOR codec decodes every inbound RPC message before your code sees it.
##  Using codecs with the SDK[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#using-codecs-with-the-sdk)
A new `Surreal` instance registers default codecs. WebSocket and HTTP engines use `CborCodec` for RPC traffic, so you normally never call a codec yourself.
Pass `codecOptions` in the driver options to change decoding behaviour:

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal({
    codecOptions: {
        useNativeDates: true,
    },
});
```

With `useNativeDates` set, datetimes decode as native `Date` objects instead of `DateTime`. You lose nanosecond precision, which is the trade-off if the rest of your code expects `Date`.
You can replace the default codec factories when you need custom encode or decode logic:

```ts
import { CborCodec, JsonCodec, type CodecOptions } from '@surrealdb/sqon';
import { Surreal } from 'surrealdb';

const db = new Surreal({
    codecOptions: {
        valueDecodeVisitor: (value) => {
            // Transform decoded values before they reach your application
            return value;
        },
    },
    codecs: {
        cbor: (options: CodecOptions) => new CborCodec(options),
        json: (options: CodecOptions) => new JsonCodec(options),
    },
});
```

##  Using codecs standalone[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#using-codecs-standalone)
Install `@surrealdb/sqon` when you only need serialisation and not the database client:

```sh
bun add @surrealdb/sqon
```

###  CBOR codec[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#cbor-codec)
`CborCodec` outputs compact binary. Reach for it when you speak SurrealDB's RPC protocol or want a small, type-safe binary payload.

```ts
import { CborCodec, RecordId, Decimal, Duration } from '@surrealdb/sqon';

const codec = new CborCodec({
	// optional options
});

const payload = {
    id: new RecordId('order', 42),
    total: new Decimal('99.95'),
    sla: Duration.parse('24h'),
};

const bytes = codec.encode(payload);
const restored = codec.decode<typeof payload>(bytes);

console.log(restored.id instanceof RecordId); // true
console.log(restored.total instanceof Decimal); // true
```

The CBOR layout uses SurrealDB's tagged values. See the [CBOR protocol reference](https://surrealdb.com/docs/reference/rest-api/cbor-protocol) for the tag list.
###  JSON codec[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#json-codec)
`JsonCodec` builds a JSON-safe object tree in SQON JSON notation. Typed values sit inside wrapper objects such as `$recordId`, `$datetime`, and `$decimal`:

```ts
import { JsonCodec, RecordId, DateTime } from '@surrealdb/sqon';

const codec = new JsonCodec({
	// optional options
});

const value = {
    created: DateTime.parse('2024-01-15T12:00:00.123456789Z'),
    author: new RecordId('user', 'tobie'),
};

const sqonJson = codec.encode(value);
```

```json
{
    "created": { "$datetime": "2024-01-15T12:00:00.123456789Z" },
    "author": { "$recordId": { "tb": "user", "id": "tobie" } }
}
```

Decode the structure back to value instances:

```ts
const restored = codec.decode<typeof value>(sqonJson);
console.log(restored.author instanceof RecordId); // true
```

`JsonCodec` fits logging, browser storage, and anything that only accepts JSON/text such as LLMs. `CborCodec` fits talking to SurrealDB directly and cases where size and binary safety matter.
##  Choosing a codec[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#choosing-a-codec)  
| Scenario  | Recommended codec  |  
| --- | --- |  
| WebSocket or HTTP RPC to SurrealDB  |  `CborCodec`(used automatically by the SDK)  |  
| Storing query results in a JSON document store  |  `JsonCodec`or `jsonify()`for string representations  |  
| Logging or debugging typed values  |  `JsonCodec`or `jsonify()`  |  
| Custom RPC client implementation  | `CborCodec`  |  
|  Browser storage ( `localStorage`, IndexedDB as JSON)  | `JsonCodec`  |  
For a plain string form (good for display or simple serialisation), [`jsonify()`](https://surrealdb.com/docs/reference/javascript/concepts/utilities#jsonifying-query-results) converts value instances to SurrealQL strings without the SQON JSON wrappers.
##  Codec options[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#codec-options)
Both codecs accept a shared `CodecOptions` object:  
| Option  | Description  |  
| --- | --- |  
| `useNativeDates`  |  Decode datetimes as native `Date`instead of `DateTime`(loses nanosecond precision)  |  
| `valueEncodeVisitor`  | Custom function applied to each value before encoding  |  
| `valueDecodeVisitor`  | Custom function applied to each value after decoding  |  
Use `valueEncodeVisitor` and `valueDecodeVisitor` to map values to your own types, or to strip fields before encoding.
##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/codecs#learn-more)
  * •
[CBOR protocol reference](https://surrealdb.com/docs/reference/rest-api/cbor-protocol) for the full CBOR tag specification
  * •
[Value types](https://surrealdb.com/docs/reference/javascript/concepts/value-types) for the value classes codecs operate on
  * •
[Utilities](https://surrealdb.com/docs/reference/javascript/concepts/utilities) for `jsonify()` and other SQON helpers
  * •
[`@surrealdb/sqon` on npm](https://www.npmjs.com/package/@surrealdb/sqon) for standalone installation
