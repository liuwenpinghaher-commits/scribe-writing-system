---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations

A `duration` represents a non-negative period of time.
##  Duration units[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations#duration-units)
Durations can be specified in any of the following units:  
| Unit  | Description  |  
| --- | --- |  
| ns  | Nanoseconds  |  
| us  | Microseconds, alternative: µs  |  
| ms  | Milliseconds  |  
| s  | Seconds  |  
| m  | Minutes  |  
| h  | Hours  |  
| d  | Days  |  
| w  | Weeks  |  
| y  | Years  |  
##  Creating and using durations[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations#creating-and-using-durations)
A duration can be composed of any number of duration units.

```surql
1y40w20h;
```

A duration that contains multiple instances of the same unit type will parse as well, combining lesser units into greater units when a maximum value is reached.
For example, a duration that includes `12h` two times will be evaluated as `1d`.

```surql
1d1d12h12h;
-- 3d
```

A duration can also be created by casting a string.

```surql
<duration>"1d1d12h12h";
-- 3d
```

A duration can be zero, but cannot be negative.

```surql
0ns;
0d; -- Evaluates to 0ns
```

The maximum possible duration can be accessed via the const [`duration::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#durationmax), above which a duration cannot be formed.

```surql
duration::max;
-- 584942417355y3w5d7h15s999ms999µs999ns

duration::max + 1ns
-- 'Failed to compute: "584942417355y3w5d7h15s999ms999µs999ns + 1ns", as the operation results in an arithmetic overflow.'
```

Durations can be added to and subtracted from other durations as well as datetimes.

```surql
d'1970-01-01' + 1d;
-- d'1970-01-02T00:00:00Z'

1y - 6w;
46w1d;
```

##  Multiplying and dividing durations[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations#multiplying-and-dividing-durations)
Available since: v3.0.1
A duration can be multiplied and divided by a number.

```surql
1d / 24;
-- 1h

1d * 5.5;
-- 5d12h
```
