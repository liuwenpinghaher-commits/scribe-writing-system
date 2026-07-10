---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/time"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/time"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/time

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/time

This page contains built-in functions and constants for working with and manipulating [datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) values.
Note
Since version 3.0.0-beta, the `::from::` functions (e.g. `time::from::millis()`) now use underscores (e.g. `time::from_millis()`) to better match the intent of the function and method syntax.
Many time functions take an `option` in order to return certain values from a datetime such as its hours, minutes, day of the year, and so in. If no argument is present, the current datetime will be extracted and used. As such, all of the following function calls are valid and will not return an error.

```surql
time::hour(d'2024-09-04T00:32:44.107Z');
time::hour();

time::minute(d'2024-09-04T00:32:44.107Z');
time::minute();

time::yday(d'2024-09-04T00:32:44.107Z');
time::yday();
```

##  Time functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#time-functions)  
| Function  | Description  |  
| --- | --- |  
| [`time::ceil()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeceil)  | Raises a datetime to the nearest multiple of duration from the Unix epoch  |  
| [`time::day()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeday)  | Extracts the day as a number from a datetime or current datetime  |  
| [`time::floor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefloor)  | Truncates a datetime to the nearest lower multiple of duration from the Unix epoch  |  
| [`time::format()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeformat)  | Outputs a datetime according to a specific format  |  
| [`time::group()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timegroup)  | Groups a datetime by a particular time interval  |  
| [`time::hour()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timehour)  | Extracts the hour as a number from a datetime or current datetime  |  
| [`time::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemax)  | Returns the greatest datetime from an array  |  
| [`time::micros()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemicros)  | Extracts the microseconds as a number from a datetime or current datetime  |  
| [`time::millis()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemillis)  | Extracts the milliseconds as a number from a datetime or current datetime  |  
| [`time::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemin)  | Returns the least datetime from an array  |  
| [`time::minute()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeminute)  | Extracts the minutes as a number from a datetime or current datetime  |  
| [`time::month()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemonth)  | Extracts the month as a number from a datetime or current datetime  |  
| [`time::nano()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timenano)  | Returns the number of nanoseconds since the UNIX epoch until a datetime or current datetime  |  
| [`time::now()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timenow)  | Returns the current datetime  |  
| [`time::round()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeround)  | Rounds a datetime to the nearest multiple of a specific duration  |  
| [`time::second()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timesecond)  | Extracts the second as a number from a datetime or current datetime  |  
| [`time::timezone()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timetimezone)  | Returns the current local timezone offset in hours  |  
| [`time::unix()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeunix)  | Returns the number of seconds since the UNIX epoch  |  
| [`time::wday()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timewday)  | Extracts the week day as a number from a datetime or current datetime  |  
| [`time::week()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeweek)  | Extracts the week as a number from a datetime or current datetime  |  
| [`time::yday()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeyday)  | Extracts the yday as a number from a datetime or current datetime  |  
| [`time::year()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeyear)  | Extracts the year as a number from a datetime or current datetime  |  
| [`time::is_leap_year()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeisleap_year)  | Checks if given datetime is a leap year  |  
| [`time::from_micros()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_micros)  | Calculates a datetime based on the microseconds since 1 January 1970 000 UTC.  |  
| [`time::from_millis()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_millis)  | Calculates a datetime based on the milliseconds since 1 January 1970 000 UTC.  |  
| [`time::from_nanos()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_nanos)  | Calculates a datetime based on the nanoseconds since 1 January 1970 000 UTC.  |  
| [`time::from_secs()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_secs)  | Calculates a datetime based on the seconds since 1 January 1970 000 UTC.  |  
| [`time::from_unix()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_unix)  | Calculates a datetime based on the seconds since 1 January 1970 000 UTC.  |  
| [`time::from_ulid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_ulid)  | Calculates a datetime based on the ULID.  |  
| [`time::from_uuid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_uuid)  | Calculates a datetime based on the UUID.  |  
| [`time::set_year()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_year)  | Sets the year value of a datetime.  |  
| [`time::set_month()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_month)  | Sets the year value of a datetime.  |  
| [`time::set_day()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_day)  | Sets the year value of a datetime.  |  
| [`time::set_hour()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_hour)  | Sets the year value of a datetime.  |  
| [`time::set_minute()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_minute)  | Sets the year value of a datetime.  |  
| [`time::set_second()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_second)  | Sets the year value of a datetime.  |  
| [`time::set_nanosecond()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_nanosecond)  | Sets the year value of a datetime.  |  
##  Time constants[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#time-constants)  
| Constant  | Description  |  
| --- | --- |  
| [`time::epoch`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeepoch)  | Constant datetime representing the UNIX epoch  |  
| [`time::maximum`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemaximum)  | Constant representing the greatest possible datetime  |  
| [`time::minimum`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeminimum)  | Constant representing the least possible datetime  |  
##  `time::ceil`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeceil)
The `time::floor` function raises a datetime to the nearest multiple of duration from the Unix epoch (January 1, 1970).
API DEFINITION

```surql
time::ceil(datetime, $ceiling: duration) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $now = d'2024-08-30T02:22:50.231631Z';

RETURN [
  time::ceil($now, 1h),
  time::ceil($now, 1w)
];
```

Output

```surql
[
	d'2024-08-30T03:00:00Z',
	d'2024-09-05T00:00:00Z'
]
```

###  Implementation details[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#implementation-details)
Since this function raises a datetime to the next multiple of duration from the Unix epoch, this means for example that:
  * •
time::ceil(now, 18d) rounds up from the nearest multiple of 18 days since epoch
  * •
time::ceil(now, 17d) rounds up from the nearest multiple of 17 days since epoch

Each call uses a different modular base, so the truncation points land at different offsets that may not be sequential. For example, for October 23, 2023 (day ~19,653 since epoch):
  * •
19653 / 18 = 1091.83… → 1092 × 18 = day 19,656 → Oct 26
  * •
19653 / 17 = 1156.05… → 1157 × 17 = day 19,669 → Nov 08
  * •
19653 / 16 = 1228.31… → 1229 × 16 = day 19,664 → Nov 03
  * •
19653 / 15 = 1310.20… → 1311 × 15 = day 19,665 → Nov 04

```surql
LET $now = d'2023-10-23T09:12:53Z';

time::ceil($now, 18d); -- d'2023-10-26T00:00:00Z'
time::ceil($now, 17d); -- d'2023-11-08T00:00:00Z'
time::ceil($now, 16d); -- d'2023-11-03T00:00:00Z'
time::ceil($now, 15d); -- d'2023-11-04T00:00:00Z'
```

To use this function to raise to midnight of the next day, the duration values above can be subtracted from the datetime first, followed by `1d` for the ceiling.

```surql
LET $now = d'2023-10-23T09:12:53Z';

time::ceil($now - 18d, 1d); -- d'2023-10-06T00:00:00Z'
time::ceil($now - 17d, 1d); -- d'2023-10-07T00:00:00Z'
time::ceil($now - 16d, 1d); -- d'2023-10-08T00:00:00Z'
time::ceil($now - 15d, 1d); -- d'2023-10-09T00:00:00Z'
```

##  `time::day`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeday)
The `time::day` function extracts the day as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::day(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::day(d"2021-11-01T08:30:17+00:00");

-- 1
```

  

##  `time::epoch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeepoch)
The `time::epoch` constant returns the `datetime` for the UNIX epoch (1 January 1970).

```surql
// Return the const
RETURN time::epoch;
-- d'1970-01-01T00:00:00Z'

// Define field using the const
DEFINE FIELD since_epoch ON event COMPUTED time::now().floor(1d) - time::epoch;
CREATE ONLY event:one SET information = "Something happened";
-- { id: event:one, information: 'Something happened', since_epoch: 55y42w6d }
```

  

##  `time::floor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefloor)
The `time::floor` function truncates a datetime to the nearest lower multiple of duration from the Unix epoch (January 1, 1970).
API DEFINITION

```surql
time::floor(datetime, $floor: duration) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::floor(d"2021-11-01T08:30:17+00:00", 1w);

-- d'2021-10-28T00:00:00Z'
```

###  Implementation details[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#implementation-details-1)
Since this function truncates a datetime to the nearest lower multiple of duration from the Unix epoch, this means for example that:
  * •
time::floor(now, 18d) rounds down to the nearest multiple of 18 days since epoch
  * •
time::floor(now, 17d) rounds down to the nearest multiple of 17 days since epoch

Each call uses a different modular base, so the truncation points land at different offsets that may not be sequential. For example, for October 23, 2023 (day ~19,653 since epoch):
  * •
19653 / 18 = 1091.83… → 1091 × 18 = day 19,638 → Oct 8
  * •
19653 / 17 = 1156.05… → 1156 × 17 = day 19,652 → Oct 22
  * •
19653 / 16 = 1228.31… → 1228 × 16 = day 19,648 → Oct 18
  * •
19653 / 15 = 1310.20… → 1310 × 15 = day 19,650 → Oct 20

```surql
LET $now = d'2023-10-23T09:12:53Z';

time::floor($now, 18d); -- d'2023-10-08T00:00:00Z'
time::floor($now, 17d); -- d'2023-10-22T00:00:00Z'
time::floor($now, 16d); -- d'2023-10-18T00:00:00Z'
time::floor($now, 15d); -- d'2023-10-20T00:00:00Z'
```

To use this function to truncate to the day, the duration values above can be subtracted from the datetime first, followed by `1d` for the floor.

```surql
LET $now = d'2023-10-23T09:12:53Z';

time::floor($now - 18d, 1d); -- d'2023-10-05T00:00:00Z'
time::floor($now - 17d, 1d); -- d'2023-10-06T00:00:00Z'
time::floor($now - 16d, 1d); -- d'2023-10-07T00:00:00Z'
time::floor($now - 15d, 1d); -- d'2023-10-08T00:00:00Z'
```

  

##  `time::format`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeformat)
The `time::format` function outputs a datetime as a string according to a specific format.
API DEFINITION

```surql
time::format(datetime, $format: string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::format(d"2021-11-01T08:30:17+00:00", "%Y-%m-%d");
```

```surql
'2021-11-01'
```

[View all format options](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/formatters)
  

##  `time::group`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timegroup)
The `time::group` function reduces and rounds a datetime down to a particular time interval.
API DEFINITION

```surql
time::group(datetime, $group_by: 'year'|'month'|'day'|'hour'|'minute'|'second') -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::group(d"2021-11-01T08:30:17+00:00", "year");

d'2021-01-01T00:00:00Z'
```

  

##  `time::hour`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timehour)
The `time::hour` function extracts the hour as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::hour(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::hour(d"2021-11-01T08:30:17+00:00");

-- 8
```

  

##  `time::max`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemax)
The `time::max` function returns the greatest datetime from an array of datetimes.
API DEFINITION

```surql
time::max(array<datetime>) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::max([ d"1987-06-22T08:30:45Z", d"1988-06-22T08:30:45Z" ])

-- d'1988-06-22T08:30:45Z'
```

See also:
  * •
[`array::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymax), which extracts the greatest value from an array of values
  * •
[`math::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmax), which extracts the greatest number from an array of numbers

  

##  `time::maximum`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemaximum)
Available since: v2.3.0
The `time::maximum` constant returns the greatest possible datetime that can be used.
API DEFINITION

```surql
time::maximum -> datetime
```

Some examples of the constant in use:

```surql
time::maximum;

time::maximum + 1ns;

time::now() IN time::minimum..time::maximum;
```

Output

```surql
-------- Query 1 --------

d'+262142-12-31T23:59:59.999Z'

-------- Query 2 --------

"Failed to compute: \"1ns + d'+262142-12-31T23:59:59.999999999Z'\", as the operation results in an arithmetic overflow."

-------- Query 3 --------

true
```

  

##  `time::micros`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemicros)
The `time::micros` function extracts the microseconds as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::micros(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::micros(d"1987-06-22T08:30:45Z");

-- 551349045000000
```

  

##  `time::millis`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemillis)
The `time::millis` function extracts the milliseconds as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::millis(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::millis(d"1987-06-22T08:30:45Z");

-- 551349045000
```

  

##  `time::min`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemin)
The `time::min` function returns the least datetime from an array of datetimes.
API DEFINITION

```surql
time::min(array<datetime>) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::min([ d"1987-06-22T08:30:45Z", d"1988-06-22T08:30:45Z" ]);

-- d'1987-06-22T08:30:45Z'
```

See also:
  * •
[`array::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymin), which extracts the least value from an array of values
  * •
[`math::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmin), which extracts the least number from an array of numbers

  

##  `time::minimum`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeminimum)
Available since: v2.3.0
The `time::minimum` constant returns the least possible datetime that can be used.
API DEFINITION

```surql
time::minimum -> datetime
```

Some examples of the constant in use:

```surql
time::minimum;

time::now() IN time::minimum..time::maximum;
```

Output

```surql
-------- Query 1 --------

d'-262143-01-01T00:00:00Z'

-------- Query 2 --------

true
```

  

##  `time::minute`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeminute)
The `time::minute` function extracts the minutes as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::minute(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::minute(d"2021-11-01T08:30:17+00:00");

-- 30
```

  

##  `time::month`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemonth)
The `time::month` function extracts the month as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::month(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::month(d"2021-11-01T08:30:17+00:00");

-- 11
```

  

##  `time::nano`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timenano)
The `time::nano` function returns a datetime as an integer representing the number of nanoseconds since the UNIX epoch until a datetime, or the current date if no datetime argument is present.
API DEFINITION

```surql
time::nano(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::nano(d"2021-11-01T08:30:17+00:00");

-- 1635755417000000000
```

  

##  `time::now`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timenow)
The `time::now` function returns the current datetime as an ISO8601 timestamp.
API DEFINITION

```surql
time::now() -> datetime
```

  

##  `time::round`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeround)
The `time::round` function rounds a datetime up by a specific duration.
API DEFINITION

```surql
time::round(datetime, $round_to: duration) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::round(d"2021-11-01T08:30:17+00:00", 1w);

-- d'2021-11-04T00:00:00Z'
```

  

##  `time::second`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timesecond)
The `time::second` function extracts the second as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::second(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::second(d"2021-11-01T08:30:17+00:00");

-- 17
```

  

##  `time::timezone`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timetimezone)
The `time::timezone` function returns the current local timezone offset in hours.
API DEFINITION

```surql
time::timezone() -> string
```

  

##  `time::unix`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeunix)
The `time::unix` function returns a datetime as an integer representing the number of seconds since the UNIX epoch until a certain datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::unix(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::unix(d"2021-11-01T08:30:17+00:00");

-- 1635755417
```

  

##  `time::wday`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timewday)
The `time::wday` function extracts the week day as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::wday(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::wday(d"2021-11-01T08:30:17+00:00");

-- 1
```

  

##  `time::week`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeweek)
The `time::week` function extracts the week as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::week(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::week(d"2021-11-01T08:30:17+00:00");

-- 44
```

  

##  `time::yday`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeyday)
The `time::yday` function extracts the day of the year as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::yday(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::yday(d"2021-11-01T08:30:17+00:00");

-- 305
```

  

##  `time::year`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeyear)
The `time::year` function extracts the year as a number from a datetime, or from the current date if no datetime argument is present.
API DEFINITION

```surql
time::year(option<datetime>) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::year(d"2021-11-01T08:30:17+00:00");

-- 2021
```

  

##  `time::is_leap_year()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeis_leap_year)
The `time::is_leap_year()` function Checks if given datetime is a leap year.
API DEFINITION

```surql
time::is_leap_year(datetime) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
-- Checks with current datetime if none is passed
RETURN time::is_leap_year();

RETURN time::is_leap_year(d"1987-06-22T08:30:45Z");
-- false

RETURN time::is_leap_year(d"1988-06-22T08:30:45Z");
-- true

-- Using function via method chaining
RETURN d'2024-09-03T02:33:15.349397Z'.is_leap_year();
-- true
```

##  `time::from_micros`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_micros)
The `time::from_micros` function calculates a datetime based on the microseconds since 1 January 1970 000 UTC.
API DEFINITION

```surql
time::from_micros(number) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_micros(1000000);

-- d'1970-01-01T00:00:01Z'
```

  

##  `time::from_millis`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_millis)
The `time::from_millis` function calculates a datetime based on the milliseconds since 1 January 1970 000 UTC.
API DEFINITION

```surql
time::from_millis(number) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_millis(1000);

-- d'1970-01-01T00:00:01Z'
```

  

##  `time::from_nanos`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_nanos)
The `time::from_nanos` function calculates a datetime based on the nanoseconds since 1 January 1970 000 UTC.
API DEFINITION

```surql
time::from_nanos(number) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_nanos(1000000);

-- d'1970-01-01T00:00:00.001Z'
```

  

##  `time::from_secs`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_secs)
The `time::from_secs` function calculates a datetime based on the seconds since 1 January 1970 000 UTC.
API DEFINITION

```surql
time::from_secs(number) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_secs(1000);

-- d'1970-01-01T00:16:40Z'
```

  

##  `time::from_unix`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_unix)
The `time::from_unix` function calculates a datetime based on the seconds since 1 January 1970 000 UTC.
API DEFINITION

```surql
time::from_unix(number) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_unix(1000);

-- d'1970-01-01T00:16:40Z'
```

  

##  `time::from_ulid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_ulid)
The `time::from_ulid` function calculates a datetime based on the ULID.
API DEFINITION

```surql
time::from_ulid(ulid) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_ulid("01JH5BBTK9FKTGSDXHWP5YP9TQ");

-- d'2025-01-09T10:57:03.593Z'
```

As a ULID is only precise up to the millisecond, a conversion from a ULID to a timestamp will truncate nanosecond precision.

```surql
LET $now = time::now();
[$now, time::from_ulid(rand::ulid($now))];

-- Output:
[
	d'2026-01-29T02:07:06.494218Z',
	d'2026-01-29T02:07:06.494Z'
]
```

  

##  `time::from_uuid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timefrom_uuid)
The `time::from_uuid` function calculates a datetime based on the UUID.
API DEFINITION

```surql
time::from_uuid(uuid) -> datetime
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN time::from_uuid(u'01944ab6-c1e5-7760-ab6a-127d37eb1b94');

-- d'2025-01-09T10:57:58.757Z'
```

As a UUID is only precise up to the millisecond, a conversion from a UUID to a timestamp will truncate nanosecond precision.

```surql
LET $now = time::now();
[$now, time::from_uuid(rand::uuid($now))];

-- Output:
[
	d'2026-01-29T02:12:13.848476Z',
	d'2026-01-29T02:12:13.848Z'
]
```

  

##  `time::set_year`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_year)
Available since: v3.0.2
The `time::set_year` function sets the year value of a datetime.
API DEFINITION

```surql
time::set_year(datetime, $year: integer) -> datetime
```

Example:

```surql
d'1970-01-01T00:00:00.500000005Z'.set_year(2026);
-- Output
d'2026-01-01T00:00:00.500000000Z'
```

##  `time::set_month`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_month)
Available since: v3.0.2
The `time::set_month` function sets the month value of a datetime.
API DEFINITION

```surql
time::set_month(datetime, $month: integer) -> datetime
```

Example:

```surql
d'1970-01-01T00:00:00.500000005Z'.set_month(9);
-- Output
d'1970-09-01T00:00:00.500000005Z'
```

##  `time::set_day`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_day)
Available since: v3.0.2
The `time::set_day` function sets the day value of a datetime.
API DEFINITION

```surql
time::set_day(datetime, $day: integer) -> datetime
```

Example:

```surql
d'1970-01-01T00:00:00.500000005Z'.set_day(10);
-- Output
d'1970-01-10T00:00:00.500000005Z'
```

##  `time::set_hour`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_hour)
Available since: v3.0.2
The `time::set_hour` function sets the hour value of a datetime.
API DEFINITION

```surql
time::set_hour(datetime, $hour: integer) -> datetime
```

Example:

```surql
d'1970-01-01T00:00:00.500000005Z'.set_hour(10);
-- Output
d'1970-01-01T10:00:00.500000005Z'
```

##  `time::set_minute`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_minute)
Available since: v3.0.2
The `time::set_minute` function sets the minute value of a datetime.
API DEFINITION

```surql
time::set_minute(datetime, $minute: integer) -> datetime
```

Example:

```surql
d'1970-01-01T10:00:00.500000005Z'.set_minute(55);
-- Output
d'1970-01-01T10:55:00.500000005Z'
```

##  `time::set_second`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_second)
Available since: v3.0.2
The `time::set_second` function sets the second value of a datetime.
API DEFINITION

```surql
time::set_second(datetime, $second: integer) -> datetime
```

Example:

```surql
d'1970-01-01T10:00:00.500000005Z'.set_second(30);
-- Output
d'1970-01-01T10:00:30.500000005Z'
```

##  `time::set_nanosecond`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timeset_nanosecond)
Available since: v3.0.2
The `time::set_nanosecond` function sets the nanosecond value of a datetime.
API DEFINITION

```surql
time::set_nanosecond(datetime, $nanosecond: integer) -> datetime
```

Example:

```surql
d'1970-01-01T10:00:00.500000005Z'.set_nanosecond(3535);
-- Output
d'1970-01-01T10:00:00.000003535Z'
```

Since nanoseconds are not needed in a datetime, setting the nanoseconds of a datetime to 0 can be used to make a datetime look cleaner.

```surql
d'1970-01-01T00:00:00.500000000Z'.set_nanosecond(0);
d'1970-01-01T00:00:00Z' -- output
```
