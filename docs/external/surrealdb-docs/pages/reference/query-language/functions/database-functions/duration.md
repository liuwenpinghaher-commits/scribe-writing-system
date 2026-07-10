---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration

This page contains built-in functions and constants for converting between numeric and [duration](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations) data.
Note
Since version 3.0.0, the `::from::` functions (e.g. `duration::from::millis()`) now use underscores (e.g. `duration::from_millis()`) to better match the intent of the function and method syntax.
##  Duration functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#duration-functions)  
| Function  | Description  |  
| --- | --- |  
| [`duration::days()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationdays)  | Counts how many days fit in a duration  |  
| [`duration::hours()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationhours)  | Counts how many hours fit in a duration  |  
| [`duration::micros()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmicros)  | Counts how many microseconds fit in a duration  |  
| [`duration::millis()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmillis)  | Counts how many milliseconds fit in a duration  |  
| [`duration::mins()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmins)  | Counts how many minutes fit in a duration  |  
| [`duration::nanos()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationnanos)  | Counts how many nanoseconds fit in a duration  |  
| [`duration::secs()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationsecs)  | Counts how many seconds fit in a duration  |  
| [`duration::weeks()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationweeks)  | Counts how many weeks fit in a duration  |  
| [`duration::years()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationyears)  | Counts how many years fit in a duration  |  
| [`duration::from_days()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_days)  | Converts a numeric amount of days into a duration that represents days  |  
| [`duration::from_hours()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_hours)  | Converts a numeric amount of hours into a duration that represents hours  |  
| [`duration::from_micros()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_micros)  | Converts a numeric amount of microseconds into a duration that represents microseconds  |  
| [`duration::from_millis()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_millis)  | Converts a numeric amount of milliseconds into a duration that represents milliseconds  |  
| [`duration::from_mins()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_mins)  | Converts a numeric amount of minutes into a duration that represents minutes  |  
| [`duration::from_nanos()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_nanos)  | Converts a numeric amount of nanoseconds into a duration that represents nanoseconds  |  
| [`duration::from_secs()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_secs)  | Converts a numeric amount of seconds into a duration that represents seconds  |  
| [`duration::from_weeks()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_weeks)  | Converts a numeric amount of weeks into a duration that represents weeks  |  
##  Duration constants[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#duration-constants)  
| Constant  | Description  |  
| --- | --- |  
| [`duration::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmax)  | Constant representing the greatest possible duration  |  
##  `duration::days`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationdays)
The `duration::days` function counts how many days fit into a duration.
API DEFINITION

```surql
duration::days(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::days(3w);

-- 21
```

  

##  `duration::hours`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationhours)
The `duration::hours` function counts how many hours fit into a duration.
API DEFINITION

```surql
duration::hours(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::hours(3w);

-- 504
```

  

##  `duration::max`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmax)
Available since: v2.3.0
The `duration::max` constant represents the greatest possible duration that can be used.
API DEFINITION

```surql
duration::max -> duration
```

Some examples of the constant in use:

```surql
duration::max;

duration::max + 1ns;

100y IN 0ns..duration::max
```

Output

```surql
-------- Query 1 --------

584942417355y3w5d7h15s999ms999µs999ns

-------- Query 2 --------
'Failed to compute: "584942417355y3w5d7h15s999ms999µs999ns + 1ns", as the operation results in an arithmetic overflow.'

-------- Query 3 --------
true
```

  

##  `duration::micros`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmicros)
The `duration::micros` function counts how many microseconds fit into a duration.
API DEFINITION

```surql
duration::micros(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::micros(3w);

-- 1814400000000
```

  

##  `duration::millis`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmillis)
The `duration::millis` function counts how many milliseconds fit into a duration.
API DEFINITION

```surql
duration::millis(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::millis(3w);

-- 1814400000
```

  

##  `duration::mins`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmins)
The `duration::mins` function counts how many minutes fit into a duration.
API DEFINITION

```surql
duration::mins(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::mins(3w);

-- 30240
```

  

##  `duration::nanos`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationnanos)
The `duration::nanos` function counts how many nanoseconds fit into a duration.
API DEFINITION

```surql
duration::nanos(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::nanos(3w);

-- 1814400000000000
```

  

##  `duration::secs`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationsecs)
The `duration::secs` function counts how many seconds fit into a duration.
API DEFINITION

```surql
duration::secs(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::secs(3w);

-- 1814400
```

  

##  `duration::weeks`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationweeks)
The `duration::weeks` function counts how many weeks fit into a duration.
API DEFINITION

```surql
duration::weeks(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::weeks(3w);

-- 3
```

  

##  `duration::years`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationyears)
The `duration::years` function counts how many years fit into a duration.
API DEFINITION

```surql
duration::years(duration) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::years(300w);

-- 5
```

  

##  `duration::from_days`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_days)
The `duration::from_days` function counts how many years fit into a duration. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_days(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_days(3);

-- 3d
```

  

##  `duration::from_hours`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_hours)
The `duration::from_hours` function converts a numeric amount of hours into a duration that represents hours. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_hours(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_hours(3);

-- 3h
```

  

##  `duration::from_micros`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_micros)
The `duration::from_micros` function converts a numeric amount of microseconds into a duration that represents microseconds. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_micros(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_micros(3);

-- 3μs
```

  

##  `duration::from_millis`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_millis)
The `duration::from_millis` function converts a numeric amount of milliseconds into a duration that represents milliseconds. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_millis(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_millis(3);

-- 3ms
```

  

##  `duration::from_mins`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_mins)
The `duration::from_mins` function converts a numeric amount of minutes into a duration that represents minutes. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_mins(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_mins(3);

-- 3m
```

  

##  `duration::from_nanos`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_nanos)
The `duration::from_nanos` function converts a numeric amount of nanoseconds into a duration that represents nanoseconds. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_nanos(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_nanos(3);

-- 3ns
```

  

##  `duration::from_secs`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_secs)
The `duration::from_secs` function converts a numeric amount of seconds into a duration that represents seconds. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_secs(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_secs(3);

-- 3s
```

  

##  `duration::from_weeks`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationfrom_weeks)
The `duration::from_weeks` function converts a numeric amount of weeks into a duration that represents weeks. The argument must be non-negative; negative values return an error.
API DEFINITION

```surql
duration::from_weeks(number) -> duration
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN duration::from_weeks(3);

-- 3w
```

  
  

##  Method chaining[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#method-chaining)
Method chaining allows functions to be called using the `.` dot operator on a value of a certain type instead of the full path of the function followed by the value.

```surql
-- Traditional syntax
duration::mins(2d6h);

-- Method chaining syntax
2d6h.mins();
```

Response

```surql
3240
```

This is particularly useful for readability when a function is called multiple times.

```surql
-- Traditional syntax
duration::mins(duration::from_millis(98734234));

-- Method chaining syntax
duration::from_millis(98734234).mins();
```

Response

```surql
1645
```
