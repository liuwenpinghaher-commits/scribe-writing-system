---
title: "https://surrealdb.com/docs/reference/javascript/api/values/datetime"
url: "https://surrealdb.com/docs/reference/javascript/api/values/datetime"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/datetime

Source: https://surrealdb.com/docs/reference/javascript/api/values/datetime

The `DateTime` class provides datetime values with nanosecond precision, extending the abstract `Value` class to match SurrealDB's datetime type.
**Import:**

```ts
import { DateTime } from 'surrealdb';
```

**Source:** [value/datetime.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/datetime.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#constructor)
###  `new DateTime(value?)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#constructor)
Create a new datetime value.
Syntax

```ts
new DateTime() // Current time
new DateTime(datetime) // Clone existing
new DateTime(date) // From JavaScript Date
new DateTime(string) // Parse ISO string
new DateTime(number | bigint) // From timestamp
new DateTime([seconds, nanoseconds]) // From tuple
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | `DateTime | Date | string | number | bigint | [bigint, bigint]`  | Value to create datetime from. If omitted, uses current time.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#examples)

```ts
// Current time
const now = new DateTime();

// From JavaScript Date
const date = new DateTime(new Date());

// Parse ISO string
const parsed = new DateTime('2024-01-15T12:00:00Z');

// From Unix timestamp (seconds)
const fromTimestamp = new DateTime(1705320000);

// From tuple [seconds, nanoseconds]
const precise = new DateTime([1705320000n, 500000000n]);

// Clone existing
const clone = new DateTime(now);
```

##  Static methods[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#static-methods)
###  `DateTime.now()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#now)
Get the current datetime with nanosecond precision.
Syntax

```ts
DateTime.now()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns)
`DateTime` - Current datetime
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example)

```ts
const now = DateTime.now();
console.log(now.toString()); // '2024-01-15T12:30:45.123456789Z'

// Use in queries
await db.create(new Table('events')).content({
    name: 'Meeting',
    timestamp: DateTime.now()
});
```

* * *
###  `DateTime.epoch()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#epoch)
Returns a `DateTime` representing the Unix epoch (1970-01-01T0000Z).
Syntax

```ts
DateTime.epoch()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-1)
`DateTime` - Unix epoch datetime
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-1)

```ts
const epoch = DateTime.epoch();
console.log(epoch.toString()); // '1970-01-01T00:00:00.000000000Z'
console.log(epoch.seconds); // 0
```

* * *
###  `DateTime.fromEpochNanoseconds(ns)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#fromepochnanoseconds)
Create a `DateTime` from a nanosecond timestamp since Unix epoch.
Syntax

```ts
DateTime.fromEpochNanoseconds(ns)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ns`  | `number | bigint`  | Nanoseconds since Unix epoch.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-2)
`DateTime` - Datetime from the nanosecond timestamp
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-2)

```ts
const dt = DateTime.fromEpochNanoseconds(1705320000123456789n);
console.log(dt.toString()); // '2024-01-15T12:00:00.123456789Z'
```

* * *
###  `DateTime.fromEpochMicroseconds(µs)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#fromepochmicroseconds)
Create a `DateTime` from a microsecond timestamp since Unix epoch.
Syntax

```ts
DateTime.fromEpochMicroseconds(µs)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `µs`  | `number | bigint`  | Microseconds since Unix epoch.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-3)
`DateTime` - Datetime from the microsecond timestamp
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-3)

```ts
const dt = DateTime.fromEpochMicroseconds(1705320000123456n);
console.log(dt.toString()); // '2024-01-15T12:00:00.123456000Z'
```

* * *
###  `DateTime.fromEpochMilliseconds(ms)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#fromepochmilliseconds)
Create a `DateTime` from a millisecond timestamp since Unix epoch.
Syntax

```ts
DateTime.fromEpochMilliseconds(ms)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ms`  | `number | bigint`  | Milliseconds since Unix epoch.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-4)
`DateTime` - Datetime from the millisecond timestamp
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-4)

```ts
const dt = DateTime.fromEpochMilliseconds(1705320000123);
console.log(dt.toString()); // '2024-01-15T12:00:00.123000000Z'
```

* * *
###  `DateTime.fromEpochSeconds(s)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#fromepochseconds)
Create a `DateTime` from a second timestamp since Unix epoch.
Syntax

```ts
DateTime.fromEpochSeconds(s)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `s`  | `number | bigint`  | Seconds since Unix epoch.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-5)
`DateTime` - Datetime from the second timestamp
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-5)

```ts
const dt = DateTime.fromEpochSeconds(1705320000);
console.log(dt.toString()); // '2024-01-15T12:00:00.000000000Z'
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#instance-methods)
###  `.toDate()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#todate)
Convert to JavaScript Date object.
Syntax

```ts
datetime.toDate()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-6)
`Date` - JavaScript Date (millisecond precision)
Warning
JavaScript Date only supports millisecond precision. Nanosecond precision is lost in conversion.
Note
`DateTime` does not extend JavaScript's `Date`. To use `Date` methods like `.getFullYear()`, `.getMonth()`, `.getDate()`, `.getHours()`, etc., first call `.toDate()`.
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-6)

```ts
const dt = DateTime.now();
const jsDate = dt.toDate();

// Use with JavaScript APIs
const formatted = jsDate.toLocaleDateString();

// Access Date component methods via .toDate()
console.log(jsDate.getFullYear());  // 2024
console.log(jsDate.getMonth());     // 0 (January)
console.log(jsDate.getDate());      // 15
console.log(jsDate.getHours());     // 12
console.log(jsDate.getMinutes());   // 30
console.log(jsDate.getSeconds());   // 45
```

* * *
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#tostring)
Convert to ISO 8601 string with full nanosecond precision.
Syntax

```ts
datetime.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-7)
`string` - ISO 8601 formatted string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-7)

```ts
const dt = DateTime.now();
console.log(dt.toString());
// '2024-01-15T12:30:45.123456789Z'
```

* * *
###  `.toISOString()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#toisostring)
Convert to ISO 8601 string (alias for `.toString()`).
Syntax

```ts
datetime.toISOString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-8)
`string` - ISO 8601 formatted string
* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#tojson)
Serialize for JSON.
Syntax

```ts
datetime.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-9)
`string` - ISO string for JSON serialization
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-8)

```ts
const dt = DateTime.now();
console.log(JSON.stringify({ timestamp: dt }));
// {"timestamp":"2024-01-15T12:30:45.123456789Z"}
```

* * *
###  `.toCompact()`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#tocompact)
Returns the datetime as a compact tuple of seconds and nanoseconds since Unix epoch.
Syntax

```ts
datetime.toCompact()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-10)
`[bigint, bigint]` - Tuple of `[seconds, nanoseconds]`
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-9)

```ts
const dt = new DateTime('2024-01-15T12:00:00.500000000Z');
const [secs, nanos] = dt.toCompact();
console.log(secs);  // 1705320000n
console.log(nanos); // 500000000n

// Round-trip via constructor
const restored = new DateTime([secs, nanos]);
console.log(dt.equals(restored)); // true
```

* * *
###  `.add(duration)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#add)
Add a duration to the datetime.
Syntax

```ts
datetime.add(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Duration to add.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-11)
`DateTime` - New datetime with duration added
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-10)

```ts
import { Duration } from 'surrealdb';

const now = DateTime.now();
const later = now.add(Duration.parse('1h30m'));
const tomorrow = now.add(Duration.parse('24h'));
```

* * *
###  `.sub(duration)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#sub)
Subtract a duration from the datetime.
Syntax

```ts
datetime.sub(duration)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `duration`  | [Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration)  | Duration to subtract.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-12)
`DateTime` - New datetime with duration subtracted
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-11)

```ts
const now = DateTime.now();
const earlier = now.sub(Duration.parse('1h'));
const yesterday = now.sub(Duration.parse('24h'));
```

* * *
###  `.diff(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#diff)
Calculate the duration between two datetimes.
Syntax

```ts
datetime.diff(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `DateTime`  | The other datetime to calculate the difference from.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-13)
[`Duration`](https://surrealdb.com/docs/reference/javascript/api/values/duration) - Duration between the two datetimes
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-12)

```ts
const start = new DateTime('2024-01-15T12:00:00Z');
const end = new DateTime('2024-01-15T14:30:00Z');

const elapsed = end.diff(start);
console.log(elapsed.toString()); // '2h30m'
```

* * *
###  `.compare(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#compare)
Compare two datetimes for ordering.
Syntax

```ts
datetime.compare(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#parameters-8)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `DateTime`  | The datetime to compare against.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-14)
`number` - Returns `-1` if this datetime is before `other`, `0` if equal, `1` if after
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#example-13)

```ts
const a = new DateTime('2024-01-15T12:00:00Z');
const b = new DateTime('2024-01-16T12:00:00Z');

console.log(a.compare(b)); // -1
console.log(b.compare(a)); // 1
console.log(a.compare(a)); // 0

// Useful for sorting
const dates = [b, a];
dates.sort((x, y) => x.compare(y));
```

* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#equals)
Check if two datetimes are equal (including nanosecond precision).
Syntax

```ts
datetime.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#returns-15)
`boolean` - True if equal
##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#properties)
###  `nanoseconds`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#nanoseconds)
Total nanoseconds since Unix epoch.
**Type:** `bigint`

```ts
const dt = new DateTime('2024-01-15T12:00:00.123456789Z');
console.log(dt.nanoseconds); // 1705320000123456789n
```

* * *
###  `microseconds`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#microseconds)
Total microseconds since Unix epoch.
**Type:** `bigint`

```ts
const dt = new DateTime('2024-01-15T12:00:00.123456789Z');
console.log(dt.microseconds); // 1705320000123456n
```

* * *
###  `milliseconds`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#milliseconds)
Total milliseconds since Unix epoch.
**Type:** `number`

```ts
const dt = new DateTime('2024-01-15T12:00:00.123456789Z');
console.log(dt.milliseconds); // 1705320000123
```

* * *
###  `seconds`[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#seconds)
Seconds since Unix epoch.
**Type:** `number`

```ts
const dt = new DateTime('2024-01-15T12:00:00.123456789Z');
console.log(dt.seconds); // 1705320000
```

##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#complete-examples)
###  Event timestamps[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#event-timestamps)

```ts
import { Surreal, DateTime, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Create event with timestamp
const event = await db.create(new Table('events')).content({
    name: 'User Login',
    user: new RecordId('users', 'john'),
    timestamp: DateTime.now(),
    ip: '192.168.1.1'
});

console.log('Event created at:', event.timestamp.toString());
```

###  Date arithmetic[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#date-arithmetic)

```ts
import { DateTime, Duration } from 'surrealdb';

const now = DateTime.now();

// Add time
const future = now.add(Duration.parse('7d')); // One week later
const meeting = now.add(Duration.parse('2h30m')); // Meeting in 2.5 hours

// Subtract time
const past = now.sub(Duration.parse('30d')); // 30 days ago
const recentCutoff = now.sub(Duration.parse('1h')); // Last hour
```

###  Query with date ranges[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#query-with-date-ranges)

```ts
const startDate = new DateTime('2024-01-01T00:00:00Z');
const endDate = new DateTime('2024-12-31T23:59:59Z');

const events = await db.query(`
    SELECT * FROM events 
    WHERE timestamp >= $start AND timestamp <= $end
`, {
    start: startDate,
    end: endDate
}).collect();
```

###  Time-series data[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#time-series-data)

```ts
// Record metrics with precise timestamps
async function recordMetric(name: string, value: number) {
    await db.create(new Table('metrics')).content({
        name,
        value,
        timestamp: DateTime.now()
    });
}

await recordMetric('cpu_usage', 45.2);
await recordMetric('memory_usage', 78.1);

// Query recent metrics
const recent = await db.query(`
    SELECT * FROM metrics 
    WHERE timestamp > $cutoff
    ORDER BY timestamp DESC
`, {
    cutoff: DateTime.now().sub(Duration.parse('5m'))
}).collect();
```

###  Conversion examples[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#conversion-examples)

```ts
// From JavaScript Date
const jsDate = new Date('2024-01-15T12:00:00Z');
const dt = new DateTime(jsDate);

// To JavaScript Date
const backToJS = dt.toDate();

// From Unix timestamp
const fromTimestamp = new DateTime(1705320000);

// Get Unix timestamp in milliseconds
const timestamp = dt.milliseconds;

// Parse from string
const parsed = new DateTime('2024-01-15T12:00:00.123456789Z');

// Convert to string
const isoString = dt.toString();

// From epoch helpers
const fromNs = DateTime.fromEpochNanoseconds(1705320000123456789n);
const fromMs = DateTime.fromEpochMilliseconds(1705320000123);
const fromSecs = DateTime.fromEpochSeconds(1705320000);
```

###  Scheduled tasks[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#scheduled-tasks)

```ts
// Schedule future task
const scheduledFor = DateTime.now().add(Duration.parse('1h'));

await db.create(new Table('tasks')).content({
    name: 'Send reminder',
    scheduled_for: scheduledFor,
    status: 'pending'
});

// Find overdue tasks
const now = DateTime.now();
const overdue = await db.query(`
    SELECT * FROM tasks 
    WHERE scheduled_for < $now 
    AND status = 'pending'
`, { now }).collect();
```

###  Expiration handling[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#expiration-handling)

```ts
// Set expiration time
const session = await db.create(new Table('sessions')).content({
    user: userId,
    created_at: DateTime.now(),
    expires_at: DateTime.now().add(Duration.parse('24h'))
});

// Check if expired
function isExpired(expiresAt: DateTime): boolean {
    return DateTime.now().milliseconds > expiresAt.milliseconds;
}

if (isExpired(session.expires_at)) {
    await db.delete(session.id);
}
```

###  Timezone handling[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#timezone-handling)

```ts
// DateTime is always stored in UTC
const utcTime = DateTime.now();

// Convert to local time for display
const localDate = utcTime.toDate();
const localString = localDate.toLocaleString();

console.log('UTC:', utcTime.toString());
console.log('Local:', localString);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#best-practices)
###  1. Use DateTime for database timestamps[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#1-use-datetime-for-database-timestamps)

```ts
// Good: Nanosecond precision preserved
await db.create(new Table('logs')).content({
    timestamp: DateTime.now(),
    message: 'Event occurred'
});

// Avoid: JavaScript Date (millisecond precision only)
await db.create(new Table('logs')).content({
    timestamp: new Date(),
    message: 'Event occurred'
});
```

###  2. Be aware of precision loss[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#2-be-aware-of-precision-loss)

```ts
// Good: Keep as DateTime for precision
const dt = DateTime.now();
const stored = dt.toString(); // Preserves nanoseconds

// Caution: Loses nanosecond precision
const jsDate = dt.toDate(); // Only milliseconds
```

###  3. Use Duration for time arithmetic[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#3-use-duration-for-time-arithmetic)

```ts
// Good: Type-safe duration arithmetic
const future = now.add(Duration.parse('1h'));

// Avoid: Manual millisecond math
const future2 = DateTime.fromEpochMilliseconds(now.milliseconds + 3600000);
```

###  4. Store as DateTime, display as localized[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#4-store-as-datetime-display-as-localized)

```ts
// Store in UTC using DateTime
const timestamp = DateTime.now();
await db.create(table).content({ created_at: timestamp });

// Display in user's timezone
const localDisplay = timestamp.toDate().toLocaleString('en-US', {
    timeZone: 'America/New_York'
});
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/datetime#see-also)
  * •
[Duration](https://surrealdb.com/docs/reference/javascript/api/values/duration) - Time duration values
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using DateTime in queries
  * •
[SurrealQL datetimes](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) - Database datetime type
