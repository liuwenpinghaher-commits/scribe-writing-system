---
title: "https://surrealdb.com/docs/reference/javascript/api/values/uuid"
url: "https://surrealdb.com/docs/reference/javascript/api/values/uuid"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/uuid

Source: https://surrealdb.com/docs/reference/javascript/api/values/uuid

The `Uuid` class provides universally unique identifiers (UUIDs) with support for UUID v4 (random) and UUID v7 (time-ordered) generation.
**Import:**

```ts
import { Uuid } from 'surrealdb';
```

**Source:** [value/uuid.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/uuid.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#constructor)
###  `new Uuid(value)`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#constructor)
Create a UUID from an existing value.
Syntax

```ts
new Uuid(uuid) // Clone existing
new Uuid(string) // Parse from string
new Uuid(bytes) // From binary representation
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | `Uuid | string | ArrayBuffer | Uint8Array`  | Value to create UUID from.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#examples)

```ts
// Parse from string
const uuid = new Uuid('550e8400-e29b-41d4-a716-446655440000');

// From binary
const bytes = new Uint8Array([/* 16 bytes */]);
const uuid = new Uuid(bytes);

// Clone existing
const copy = new Uuid(uuid);
```

##  Static methods[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#static-methods)
###  `Uuid.v4()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#v4)
Generate a random UUID v4.
Syntax

```ts
Uuid.v4()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns)
`Uuid` - Random UUID v4
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#example)

```ts
const randomId = Uuid.v4();
console.log(randomId.toString());
// '550e8400-e29b-41d4-a716-446655440000'

// Use as record ID
const userId = new RecordId('users', Uuid.v4());
await db.create(userId).content(userData);
```

* * *
###  `Uuid.v7()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#v7)
Generate a time-ordered UUID v7.
Syntax

```ts
Uuid.v7()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-1)
`Uuid` - Time-ordered UUID v7
> !NOTE: Tip  
>  UUID v7 includes a timestamp component, making it sortable by creation time. This is useful for time-series data and maintaining chronological order.
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#example-1)

```ts
const timeOrderedId = Uuid.v7();

// Sequential v7 UUIDs are sortable
const id1 = Uuid.v7();
// ... time passes ...
const id2 = Uuid.v7();

// id1 < id2 (lexicographically)
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#tostring)
Convert to string representation.
Syntax

```ts
uuid.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-2)
`string` - UUID string in standard format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#example-2)

```ts
const uuid = Uuid.v4();
console.log(uuid.toString());
// '550e8400-e29b-41d4-a716-446655440000'
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#tojson)
Serialize for JSON.
Syntax

```ts
uuid.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-3)
`string` - UUID string
* * *
###  `.toUint8Array()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#touint8array)
Get the binary representation as Uint8Array.
Syntax

```ts
uuid.toUint8Array()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-4)
`Uint8Array` - 16-byte binary representation
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#example-3)

```ts
const uuid = Uuid.v4();
const bytes = uuid.toUint8Array();
console.log(bytes.length); // 16
```

* * *
###  `.toBuffer()`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#tobuffer)
Get the binary representation as ArrayBuffer.
Syntax

```ts
uuid.toBuffer()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-5)
`ArrayBufferLike` - Binary representation
* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#equals)
Check if two UUIDs are equal.
Syntax

```ts
uuid.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#returns-6)
`boolean` - True if equal
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#complete-examples)
###  Session management[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#session-management)

```ts
import { Surreal, Uuid, RecordId, DateTime, Duration, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create session with UUID
const sessionId = Uuid.v4();
const session = await db.create(new RecordId('sessions', sessionId))
    .content({
        user: userId,
        created_at: DateTime.now(),
        expires_at: DateTime.now().plus(new Duration('24h')),
        ip_address: '192.168.1.1'
    });

console.log('Session ID:', sessionId.toString());
```

###  Time-ordered records[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#time-ordered-records)

```ts
// Use v7 for time-series data
const events = [];

for (let i = 0; i < 100; i++) {
    const eventId = Uuid.v7();
    
    await db.create(new RecordId('events', eventId)).content({
        type: 'user_action',
        timestamp: DateTime.now(),
        data: { action: 'click', target: 'button' }
    });
    
    events.push(eventId);
}

// Events are naturally sorted by creation time
```

###  Unique identifiers[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#unique-identifiers)

```ts
// Generate unique IDs for various purposes
const requestId = Uuid.v4();
const correlationId = Uuid.v4();
const traceId = Uuid.v7(); // Time-ordered for distributed tracing

await db.create(new Table('requests')).content({
    id: requestId,
    correlation_id: correlationId,
    trace_id: traceId,
    timestamp: DateTime.now()
});
```

###  API keys[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#api-keys)

```ts
// Generate API keys
function generateApiKey(): string {
    return `api_${Uuid.v4().toString().replace(/-/g, '')}`;
}

const apiKey = generateApiKey();
console.log(apiKey); // 'api_550e8400e29b41d4a716446655440000'

await db.create(new Table('api_keys')).content({
    key: apiKey,
    user: userId,
    created_at: DateTime.now()
});
```

###  Distributed system IDs[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#distributed-system-ids)

```ts
// Use UUID v7 for distributed systems (sortable)
class IdGenerator {
    static generateOrderId(): Uuid {
        return Uuid.v7(); // Time-ordered
    }
    
    static generateTransactionId(): Uuid {
        return Uuid.v7(); // Time-ordered
    }
    
    static generateRandomId(): Uuid {
        return Uuid.v4(); // Random
    }
}

const orderId = IdGenerator.generateOrderId();
const txnId = IdGenerator.generateTransactionId();
```

###  File upload tracking[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#file-upload-tracking)

```ts
// Track file uploads with UUIDs
async function uploadFile(file: File): Promise<string> {
    const uploadId = Uuid.v4();
    
    await db.create(new RecordId('uploads', uploadId)).content({
        filename: file.name,
        size: file.size,
        mime_type: file.type,
        uploaded_at: DateTime.now(),
        status: 'processing'
    });
    
    return uploadId.toString();
}
```

###  Parsing and validation[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#parsing-and-validation)

```ts
// Parse UUID from user input
function validateUuid(input: string): Uuid | null {
    try {
        return new Uuid(input);
    } catch (error) {
        console.error('Invalid UUID format');
        return null;
    }
}

const userInput = '550e8400-e29b-41d4-a716-446655440000';
const uuid = validateUuid(userInput);

if (uuid) {
    const record = await db.select(new RecordId('items', uuid));
}
```

###  Batch ID generation[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#batch-id-generation)

```ts
// Generate multiple UUIDs
function generateBatchIds(count: number, useV7 = false): Uuid[] {
    const ids: Uuid[] = [];
    
    for (let i = 0; i < count; i++) {
        ids.push(useV7 ? Uuid.v7() : Uuid.v4());
    }
    
    return ids;
}

const randomIds = generateBatchIds(100); // 100 random UUIDs
const sortableIds = generateBatchIds(100, true); // 100 time-ordered UUIDs
```

##  UUID v4 vs UUID v7[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#uuid-v4-vs-uuid-v7)
###  UUID v4 (random)[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#uuid-v4-random)
  * •
**Pros:** Truly random, no predictability
  * •
**Cons:** Not sortable, no time information
  * •
**Use when:** You need unpredictable, secure IDs

```ts
const randomId = Uuid.v4();
```

###  UUID v7 (time-ordered)[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#uuid-v7-time-ordered)
  * •
**Pros:** Sortable, includes timestamp, better for database indexes
  * •
**Cons:** Slightly predictable (timestamp component)
  * •
**Use when:** You need sortable IDs or time-series data

```ts
const timeOrderedId = Uuid.v7();
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#best-practices)
###  1. Choose the right version[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#1-choose-the-right-version)

```ts
// Good: v7 for time-series and events
const eventId = Uuid.v7();

// Good: v4 for security tokens
const token = Uuid.v4();
```

###  2. Use with RecordId[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#2-use-with-recordid)

```ts
// Good: UUID as record ID
const userId = new RecordId('users', Uuid.v7());

// Good: Provides uniqueness and sortability
await db.create(userId).content(userData);
```

###  3. Validate user input[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#3-validate-user-input)

```ts
// Good: Validate before use
try {
    const uuid = new Uuid(userInput);
    await processUuid(uuid);
} catch (error) {
    return { error: 'Invalid UUID format' };
}
```

###  4. Store as UUID type[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#4-store-as-uuid-type)

```ts
// Good: Store as UUID
await db.create(table).content({
    session_id: Uuid.v4()
});

// Avoid: Store as string
await db.create(table).content({
    session_id: Uuid.v4().toString()
});
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/uuid#see-also)
  * •
[RecordId](https://surrealdb.com/docs/reference/javascript/api/values/record-id) - Record identifiers
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using Uuid in queries
  * •
[SurrealQL UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) - Database UUID type
