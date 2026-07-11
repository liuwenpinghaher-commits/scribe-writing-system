---
title: "https://surrealdb.com/docs/reference/javascript/api/values/duration"
url: "https://surrealdb.com/docs/reference/javascript/api/values/duration"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/duration

Source: https://surrealdb.com/docs/reference/javascript/api/values/duration

The `Duration` class provides time duration values with nanosecond precision and support for human-readable formats like `"5h30m"`.
**Import:**

```ts
import { Duration } from 'surrealdb';
```

**Source:** [value/duration.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/duration.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/duration#constructor)
###  `new Duration(value)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#constructor)
Create a new duration value.
Syntax

```ts
new Duration(duration) // Clone existing
new Duration(string) // Parse human-readable string
new Duration([seconds, nanoseconds]) // From tuple
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `value`  | `Duration | string | [bigint, bigint]`  | Value to create duration from.  |  
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/duration#examples)

```ts
// Parse human-readable durations
const fiveMinutes = new Duration('5m');
const oneHour = new Duration('1h');
const complex = new Duration('2h30m15s');
const precise = new Duration('1s500ms250us125ns');

// From tuple [seconds, nanoseconds]
const duration = new Duration([300n, 0n]); // 5 minutes

// Clone existing
const clone = new Duration(fiveMinutes);
```

##  Supported units[](https://surrealdb.com/docs/reference/javascript/api/values/duration#supported-units)  
| Unit  | Symbol  | Example  |  
| --- | --- | --- |  
| Nanoseconds  | `ns`  | `"500ns"`  |  
| Microseconds  |  `us`, `µs`  | `"250us"`  |  
| Milliseconds  | `ms`  | `"100ms"`  |  
| Seconds  | `s`  | `"30s"`  |  
| Minutes  | `m`  | `"5m"`  |  
| Hours  | `h`  | `"2h"`  |  
| Days  | `d`  | `"7d"`  |  
| Weeks  | `w`  | `"4w"`  |  
| Years  | `y`  | `"1y"`  |  
##  Static methods[](https://surrealdb.com/docs/reference/javascript/api/values/duration#static-methods)
###  `Duration.nanoseconds(ns)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#nanoseconds-static)
Create a duration from a number of nanoseconds.
Syntax

```ts
Duration.nanoseconds(ns)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ns`  | `number | bigint`  | Number of nanoseconds.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns)
`Duration` - Duration representing the given nanoseconds
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example)

```ts
const d = Duration.nanoseconds(500);
```

* * *
###  `Duration.microseconds(µs)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#microseconds-static)
Create a duration from a number of microseconds.
Syntax

```ts
Duration.microseconds(µs)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-2)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `µs`  | `number | bigint`  | Number of microseconds.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-1)
`Duration` - Duration representing the given microseconds
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-1)

```ts
const d = Duration.microseconds(250);
```

* * *
###  `Duration.milliseconds(ms)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#milliseconds-static)
Create a duration from a number of milliseconds.
Syntax

```ts
Duration.milliseconds(ms)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-3)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `ms`  | `number | bigint`  | Number of milliseconds.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-2)
`Duration` - Duration representing the given milliseconds
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-2)

```ts
const d = Duration.milliseconds(1500);
console.log(d.toString()); // '1s500ms'
```

* * *
###  `Duration.seconds(s)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#seconds-static)
Create a duration from a number of seconds.
Syntax

```ts
Duration.seconds(s)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-4)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `s`  | `number | bigint`  | Number of seconds.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-3)
`Duration` - Duration representing the given seconds
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-3)

```ts
const d = Duration.seconds(90);
console.log(d.toString()); // '1m30s'
```

* * *
###  `Duration.minutes(m)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#minutes-static)
Create a duration from a number of minutes.
Syntax

```ts
Duration.minutes(m)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-5)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `m`  | `number | bigint`  | Number of minutes.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-4)
`Duration` - Duration representing the given minutes
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-4)

```ts
const d = Duration.minutes(5);
console.log(d.toString()); // '5m'
```

* * *
###  `Duration.hours(h)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#hours-static)
Create a duration from a number of hours.
Syntax

```ts
Duration.hours(h)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-6)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `h`  | `number | bigint`  | Number of hours.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-5)
`Duration` - Duration representing the given hours
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-5)

```ts
const d = Duration.hours(2);
console.log(d.toString()); // '2h'
```

* * *
###  `Duration.days(d)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#days-static)
Create a duration from a number of days.
Syntax

```ts
Duration.days(d)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-7)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `d`  | `number | bigint`  | Number of days.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-6)
`Duration` - Duration representing the given days
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-6)

```ts
const d = Duration.days(7);
console.log(d.toString()); // '1w'
```

* * *
###  `Duration.weeks(w)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#weeks-static)
Create a duration from a number of weeks.
Syntax

```ts
Duration.weeks(w)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-8)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `w`  | `number | bigint`  | Number of weeks.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-7)
`Duration` - Duration representing the given weeks
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-7)

```ts
const d = Duration.weeks(4);
console.log(d.toString()); // '4w'
```

* * *
###  `Duration.years(y)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#years-static)
Create a duration from a number of years.
Syntax

```ts
Duration.years(y)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-9)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `y`  | `number | bigint`  | Number of years.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-8)
`Duration` - Duration representing the given years
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-8)

```ts
const d = Duration.years(1);
console.log(d.toString()); // '1y'
```

* * *
###  `Duration.parseFloat(input)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parsefloat)
Parse a duration from a float string with a unit suffix.
Syntax

```ts
Duration.parseFloat(input)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-10)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `input`  | `string`  |  A float string with a unit suffix (e.g., `"1.5s"`).  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-9)
`Duration` - Parsed duration
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-9)

```ts
const d = Duration.parseFloat('1.5s');
console.log(d.milliseconds); // 1500n
```

* * *
###  `Duration.measure()`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#measure)
Returns a function that, when called, returns the elapsed `Duration` since the call to `Duration.measure()`.
Syntax

```ts
Duration.measure()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-10)
`() => Duration` - A function that returns the elapsed duration
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-10)

```ts
const elapsed = Duration.measure();

// ... perform some operation ...

const duration = elapsed();
console.log('Operation took:', duration.toString());
```

##  Property getters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#property-getters)
Property getters for accessing the total duration in specific units. All return `bigint`.  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `nanoseconds`  | `bigint`  | Total nanoseconds  |  
| `microseconds`  | `bigint`  | Total microseconds  |  
| `milliseconds`  | `bigint`  | Total milliseconds  |  
| `seconds`  | `bigint`  | Whole seconds  |  
| `minutes`  | `bigint`  | Total whole minutes  |  
| `hours`  | `bigint`  | Total whole hours  |  
| `days`  | `bigint`  | Total whole days  |  
| `weeks`  | `bigint`  | Total whole weeks  |  
| `years`  | `bigint`  | Total whole years  |  
###  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/duration#examples-1)

```ts
const duration = new Duration('2h30m');

console.log(duration.hours);        // 2n
console.log(duration.minutes);      // 150n
console.log(duration.seconds);      // 9000n
console.log(duration.milliseconds); // 9000000n
console.log(duration.nanoseconds);  // 9000000000000n
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/duration#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#tostring)
Convert to human-readable string.
Syntax

```ts
duration.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-11)
`string` - Human-readable duration string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-11)

```ts
const duration = new Duration('2h30m15s');
console.log(duration.toString()); // '2h30m15s'
```

* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#tojson)
Serialize for JSON.
Syntax

```ts
duration.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-12)
`string` - Duration string for JSON
* * *
###  `.toCompact()`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#tocompact)
Convert to a compact tuple representation.
Syntax

```ts
duration.toCompact()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-13)
`[bigint, bigint] | [bigint] | []` - Compact representation: `[seconds, nanoseconds]`, `[seconds]` if nanoseconds is zero, or `[]` for a zero duration.
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-12)

```ts
const d = new Duration('5m30s');
console.log(d.toCompact()); // [330n, 0n] or [330n]
```

* * *
###  `.add(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#add)
Add another duration.
Syntax

```ts
duration.add(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-11)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Duration`  | Duration to add.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-14)
`Duration` - Sum of durations
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-13)

```ts
const base = new Duration('1h');
const extra = new Duration('30m');
const total = base.add(extra);
console.log(total.toString()); // '1h30m'
```

* * *
###  `.sub(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#sub)
Subtract another duration.
Syntax

```ts
duration.sub(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-12)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `Duration`  | Duration to subtract.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-15)
`Duration` - Difference of durations
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-14)

```ts
const total = new Duration('2h');
const part = new Duration('30m');
const remaining = total.sub(part);
console.log(remaining.toString()); // '1h30m'
```

* * *
###  `.mul(factor)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#mul)
Multiply a duration by a scalar.
Syntax

```ts
duration.mul(factor)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-13)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `factor`  | `number | bigint`  | Scalar to multiply by.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-16)
`Duration` - Scaled duration
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-15)

```ts
const base = new Duration('30m');
const doubled = base.mul(2);
console.log(doubled.toString()); // '1h'
```

* * *
###  `.div(divisor)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#div)
Divide a duration. Overloaded: dividing by a `Duration` returns the ratio as `bigint`, dividing by a number returns a new `Duration`.
Syntax

```ts
duration.div(divisor: Duration)       // Returns bigint (ratio)
duration.div(divisor: number | bigint) // Returns Duration
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-14)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `divisor`  | `Duration | number | bigint`  | Duration for ratio, or scalar for division.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-17)
`bigint` when dividing by a `Duration`, `Duration` when dividing by a number or bigint.
####  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/duration#examples-2)

```ts
const total = new Duration('2h');
const unit = new Duration('30m');

// Ratio: how many 30m intervals in 2h?
const ratio = total.div(unit); // 4n

// Scalar division
const half = total.div(2);
console.log(half.toString()); // '1h'
```

* * *
###  `.mod(mod)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#mod)
Get the remainder after dividing by another duration.
Syntax

```ts
duration.mod(mod)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/duration#parameters-15)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `mod`  | `Duration`  | Duration to divide by.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-18)
`Duration` - Remainder after division
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/duration#example-16)

```ts
const total = new Duration('2h20m');
const interval = new Duration('1h');
const remainder = total.mod(interval);
console.log(remainder.toString()); // '20m'
```

* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/duration#equals)
Check if two durations are equal.
Syntax

```ts
duration.equals(other)
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/duration#returns-19)
`boolean` - True if equal
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/values/duration#complete-examples)
###  Timeouts and expiration[](https://surrealdb.com/docs/reference/javascript/api/values/duration#timeouts-and-expiration)

```ts
import { Surreal, Duration, DateTime, Table } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Set session timeout
const session = await db.create(new Table('sessions')).content({
    user: userId,
    created_at: DateTime.now(),
    timeout: new Duration('24h')
});
```

###  Query timeouts[](https://surrealdb.com/docs/reference/javascript/api/values/duration#query-timeouts)

```ts
// Set timeout on queries
const users = await db.select(new Table('users'))
    .timeout(new Duration('5s'));

// Timeout on complex query
const result = await db.query(`
    SELECT * FROM complex_view
`).timeout(new Duration('30s')).collect();
```

###  Rate limiting[](https://surrealdb.com/docs/reference/javascript/api/values/duration#rate-limiting)

```ts
// Define rate limit window
const rateLimit = {
    window: new Duration('1m'),
    maxRequests: 100
};

// Store rate limit data
await db.create(new Table('rate_limits')).content({
    user: userId,
    window: rateLimit.window,
    requests: 1,
    window_start: DateTime.now()
});
```

###  Scheduled tasks[](https://surrealdb.com/docs/reference/javascript/api/values/duration#scheduled-tasks)

```ts
// Schedule task with delay
const task = await db.create(new Table('tasks')).content({
    name: 'Send email',
    delay: new Duration('5m'),
    created_at: DateTime.now()
});
```

###  Cache TTL[](https://surrealdb.com/docs/reference/javascript/api/values/duration#cache-ttl)

```ts
// Set cache entry with TTL
const cacheEntry = await db.create(new Table('cache')).content({
    key: 'user:123',
    value: userData,
    ttl: new Duration('1h'),
    cached_at: DateTime.now()
});

// Check if cache is still valid
function isCacheValid(entry: typeof cacheEntry): boolean {
    const elapsed = DateTime.now().milliseconds - entry.cached_at.milliseconds;
    return elapsed < entry.ttl.milliseconds;
}
```

###  Performance measurement[](https://surrealdb.com/docs/reference/javascript/api/values/duration#performance-measurement)

```ts
// Measure operation duration
const elapsed = Duration.measure();

// ... perform operation ...

const duration = elapsed();
console.log('Operation took:', duration.toString());
```

###  Conversion examples[](https://surrealdb.com/docs/reference/javascript/api/values/duration#conversion-examples)

```ts
// Parse from string
const duration = new Duration('2h30m');

// Access as different units
const ms = duration.milliseconds; // 9000000n
const secs = duration.seconds;    // 9000n
const mins = duration.minutes;    // 150n
const hrs = duration.hours;       // 2n

// Back to string
const str = duration.toString(); // '2h30m'

// Arithmetic
const doubled = duration.add(duration);
console.log(doubled.toString()); // '5h'
```

###  Complex durations[](https://surrealdb.com/docs/reference/javascript/api/values/duration#complex-durations)

```ts
// Very precise timing
const precise = new Duration('1s500ms250us125ns');

// Multiple units
const complex = new Duration('1d2h30m15s');

// Arithmetic
const extended = complex.add(new Duration('12h'));
console.log(extended.toString()); // '1d14h30m15s'
```

###  Static factory methods[](https://surrealdb.com/docs/reference/javascript/api/values/duration#static-factory-methods)

```ts
// Create durations from numeric values
const timeout = Duration.seconds(30);
const cacheTTL = Duration.hours(1);
const retryDelay = Duration.milliseconds(500);
const oneWeek = Duration.weeks(1);

// Useful when values come from config or computation
const maxRetries = 3;
const backoff = Duration.seconds(2).mul(maxRetries);
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/values/duration#best-practices)
###  1. Use human-readable formats[](https://surrealdb.com/docs/reference/javascript/api/values/duration#1-use-human-readable-formats)

```ts
// Good: Clear intent
const timeout = new Duration('30s');
const cacheTTL = new Duration('1h');

// Avoid: Raw numbers
const timeout = new Duration([30n, 0n]);
```

###  2. Use Duration for time arithmetic[](https://surrealdb.com/docs/reference/javascript/api/values/duration#2-use-duration-for-time-arithmetic)

```ts
// Good: Type-safe duration arithmetic
const base = new Duration('1h');
const extended = base.add(new Duration('30m'));

// Good: Use static factories for computed values
const delay = Duration.seconds(retryCount * 2);
```

###  3. Store durations in database[](https://surrealdb.com/docs/reference/javascript/api/values/duration#3-store-durations-in-database)

```ts
// Good: Store as Duration for type safety
await db.create(table).content({
    timeout: new Duration('24h')
});

// Avoid: Store as number
await db.create(table).content({
    timeout: 86400000 // What unit is this?
});
```

###  4. Use appropriate units[](https://surrealdb.com/docs/reference/javascript/api/values/duration#4-use-appropriate-units)

```ts
// Good: Use largest appropriate unit
const oneDay = new Duration('1d');
const oneWeek = new Duration('1w');

// Avoid: Unnecessary smaller units
const oneDay = new Duration('24h');
const oneWeek = new Duration('168h');
```

###  5. Use duration.measure() for timing[](https://surrealdb.com/docs/reference/javascript/api/values/duration#5-use-durationmeasure-for-timing)

```ts
// Good: Built-in measurement
const elapsed = Duration.measure();
await performOperation();
console.log('Took:', elapsed().toString());
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/duration#see-also)
  * •
[DateTime](https://surrealdb.com/docs/reference/javascript/api/values/datetime) - Datetime values
  * •
[Data types overview](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Using Duration in queries
  * •
[SurrealQL durations](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations) - Database duration type
