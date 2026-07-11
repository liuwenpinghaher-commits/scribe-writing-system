---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand

These functions can be used when generating random data values.
Note
For functions that take a lower and upper bound (`rand::float`, `rand::int`, `rand::duration`, `rand::time`, `rand::id`, `rand::string`), the **first argument is the minimum** and the **second is the maximum**. If the minimum is greater than the maximum, an error is returned. Length and bound arguments must be non-negative; negative values return an error.  
| Function  | Description  |  
| --- | --- |  
| [`rand()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#rand)  | Generates and returns a random floating point number  |  
| [`rand::bool()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randbool)  | Generates and returns a random boolean  |  
| [`rand::duration()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randduration)  | Generates and returns a random duration  |  
| [`rand::enum()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randenum)  | Randomly picks a value from the specified values  |  
| [`rand::float()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randfloat)  | Generates and returns a random floating point number  |  
| [`rand::id()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randid)  | Generates and returns a random id  |  
| [`rand::int()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randint)  | Generates and returns a random integer  |  
| [`rand::string()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randstring)  | Generates and returns a random string  |  
| [`rand::time()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randtime)  | Generates and returns a random datetime  |  
| [`rand::uuid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randuuid)  | Generates and returns a random UUID  |  
| [`rand::uuid::v4()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randuuidv4)  | Generates and returns a random Version 4 UUID  |  
| [`rand::ulid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randulid)  | Generates and returns a random ULID  |  
##  `rand`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#rand)
The rand function generates a random [`float`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#floating-point-numbers), between 0 and 1.
API DEFINITION

```surql
rand() -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand();

0.7062321084863658
```

The following example shows this function being used in a [`SELECT`](https://surrealdb.com/docs/reference/query-language/statements/select) statement with an `ORDER BY` clause:

```surql
SELECT * FROM [{ age: 33 }, { age: 45 }, { age: 39 }] ORDER BY rand();

[
	{
		age: 45
	},
	{
		age: 39
	},
	{
		age: 33
	}
]
```

  

##  `rand::bool`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randbool)
The rand::bool function generates a random [`boolean`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans) value.
API DEFINITION

```surql
rand::bool() -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::bool();

true
```

  

##  `rand::duration`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randduration)
Available since: v2.3.0
The rand::duration function generates a random [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) value between two `duration` arguments.
API DEFINITION

```surql
rand::duration($from: duration, $to: duration) -> duration
```

Some examples of the function in use:

```surql
rand::duration(1ns, 1ms);

rand::duration(0ns, duration::max);
```

Output

```surql
-------- Query 1 --------
435µs884ns

-------- Query 2 --------
405337457164y36w2d5h54m8s16ms76µs191ns
```

  

##  `rand::enum`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randenum)
The `rand::enum` function generates a random value, from a multitude of values.
API DEFINITION

```surql
rand::enum(value...) -> any
rand::enum(array<value>) -> any
```

The argument to this function can take either comma-separated values or an array of values.

```surql
rand::enum('one', 'two', 3, 4.15385, 'five', true);
rand::enum(['one', 'two', 3, 4.15385, 'five', true]);

"five"
```

As nested values are not combined at greater levels of depth, the following example will return either `[8, 9]` or `[10, 11]`, but never an individual number.

```surql
RETURN rand::enum([
    [8,9],
    [10,11]
]);
```

  

##  `rand::float`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randfloat)
The `rand::float` function generates a random [`float`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#floating-point-numbers), between `0` and `1`.
API DEFINITION

```surql
rand::float() -> float
```

If two numbers are provided, the function generates a random [`float`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#floating-point-numbers) between them (inclusive of the bounds). The first argument is the **minimum** and the second is the **maximum**.
API DEFINITION

```surql
rand::float($from: number, $to: number) -> float
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::float();

0.7812733136200293
```

```surql
RETURN rand::float(10, 15);

11.305355983514927
```

  

##  `rand::id`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randid)
Note
This function was known as `rand::guid` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `rand::id` function generates a random alphanumeric ID, defaulting to a length of 20 characters.
API DEFINITION

```surql
rand::id() -> string
```

If a number is provided, then the function generates a random ID with a specific length.
API DEFINITION

```surql
rand::id(number) -> string
```

If a second number is provided, the function generates a random id with a length between the two numbers. The first argument is the **minimum** length and the second is the **maximum**. Both must be non-negative.
API DEFINITION

```surql
rand::id($min_len: int, $max_len: int) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:
Default 20-char random id

```surql
RETURN rand::id();

'4uqmrmtjhtjeg77et0dl'
```

A 10-char random id

```surql
RETURN rand::id(10);

'f3b6cjh0nt'
```

A random id with a length between 1 and 9 chars

```surql
RETURN rand::id(1, 9);

'894bqt4lp'
```

This function is used for default record ID keys in SurrealDB, and can be overridden to use a ULID or UUID instead by affixing `:ulid()` and `:uuid()` after the table name, respectively.

```surql
CREATE 
  person,
  person:ulid(),
  person:uuid()
-- Return only id values for nicer output
RETURN VALUE id;
```

Output:

```surql
[
	person:o9s1sl3ivckuxo0kglix,
	person:01K7JRP6KVAQGN2THR2T13X9WP,
	person:u'0199e58b-1a7b-7880-ad5b-01671678c11f'
]
```

  

##  `rand::int`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randint)
The `rand::int` function generates a random int.
API DEFINITION

```surql
rand::int() -> int
```

If two numbers are provided, the function generates a random int between them (inclusive). The first argument is the **minimum** and the second is the **maximum**.
API DEFINITION

```surql
rand::int($from: int, $to: int) -> int
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::int();

6841551695902514727
```

```surql
RETURN rand::int(10, 15);

13
```

  

##  `rand::string`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randstring)
The `rand::string` function generates a random string, with 32 characters.
API DEFINITION

```surql
rand::string() -> string
```

The `rand::string` function generates a random string, with a specific length.
API DEFINITION

```surql
rand::string(number) -> string
```

If two numbers are provided, the function generates a random string with a length between the two numbers. The first argument is the **minimum** length and the second is the **maximum**. Both must be non-negative.
API DEFINITION

```surql
rand::string($from: int, $to: int) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::string();

"N8Q86mklN6U7kv0A2XCRh5UlpQMSvdoT"
```

```surql
RETURN rand::string(15);

"aSCtrfJj4pSJ7Xq"
```

```surql
RETURN rand::string(10, 15);

"rEUWFUMcx0YH"
```

  

##  `rand::time`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randtime)
The `rand::time` function generates a random [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes).
API DEFINITION

```surql
rand::time() -> datetime
rand::time($from: datetime|number, $to: datetime|number) -> datetime
```

The `rand::time` function generates a random [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes), either a completely random datetime when no arguments are passed in, or between two bounds. With two arguments, the first is the **earliest** bound and the second is the **latest** (each may be a unix timestamp or a `datetime`).

```surql
RETURN rand::time();

-- d'1327-07-12T01:00:32Z'

RETURN rand::time(198371, 1223138713);

-- d'1991-01-13T23:27:17Z'
```

Available since: v2.2.0
This function can take two datetimes, returning a random datetime in between the least and greatest of the two.

```surql
RETURN rand::time(d'1970-01-01', d'2000-01-01');

-- d'1999-05-29T17:02:16Z"
```

Available since: v2.3.0
Either of the arguments of this function can be either a number or a datetime.

```surql
RETURN rand::time(0, d'1990-01-01');

-- d'1986-11-17T15:06:01Z'
```

As of this version, this function returns a datetime between 0000-01-01T0000Z and 9999-12-31T2359Z. Before this, the function returned a random datetime between 1970-01-01T0000Z (0 seconds after the UNIX epoch) and +262142-12-31T2359Z (the maximum possible value for a `datetime`).
##  `rand::uuid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randuuid)
The `rand::uuid` function generates a random Version 7 UUID.
API DEFINITION

```surql
rand::uuid() -> uuid
rand::uuid(datetime) -> uuid
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::uuid();

[u"e20b2836-e689-4643-998d-b17a16800323"]
```

The `rand::uuid` function can also generate a random UUID from a datetime.

```surql
RETURN rand::uuid(d"2021-09-07T04:27:53Z");
```

Note that a UUID has a precision of one millisecond, and thus one converted back to a datetime will truncate nanosecond precision.

```surql
LET $now = time::now();
[$now, time::from_uuid(rand::uuid($now))];

-- Output:
[
	d'2026-01-29T02:14:10.057075Z',
	d'2026-01-29T02:14:10.057Z'
]
```

The `rand::uuid` function can also be called using its alias `rand::uuid::v7`.
  

##  `rand::uuid::v4`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randuuidv4)
The `rand::uuid::v4` function generates a random version 4 UUID.
API DEFINITION

```surql
rand::uuid::v4() -> uuid
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::uuid::v4();

[u"4def23a5-a847-4934-8dad-c64ccc48921b"]
```

  

##  `rand::ulid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randulid)
The `rand::ulid` function generates a random ULID.
API DEFINITION

```surql
rand::ulid() -> uuid
rand::ulid(datetime) -> uuid
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::ulid();

[u"01H9QDG81Q7SB33RXB7BEZBK7G"]
```

The `rand::ulid` function can also generate a random ULID from a datetime type.
The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN rand::ulid(d"2021-09-07T04:27:53Z");
```

Note that a ULID has a precision of one millisecond, and thus one converted back to a datetime will truncate nanosecond precision.

```surql
LET $now = time::now();
[$now, time::from_ulid(rand::ulid($now))];

-- Output:
[
	d'2026-01-29T02:14:10.057075Z',
	d'2026-01-29T02:14:10.057Z'
]
```
