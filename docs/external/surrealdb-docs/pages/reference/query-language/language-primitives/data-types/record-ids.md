---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids

Note
SurrealDB does not eagerly convert a string into a record. An [implicit `r` prefix or cast](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/casting#casting-vs-affixes) is required instead.
SurrealDB record IDs are composed of a table name and a record identifier separated by a `:` in between, allowing for a simple and consistent way to reference records across the database. Record IDs are used to uniquely identify records within a table, to [query](https://surrealdb.com/docs/reference/query-language/statements/select), [update](https://surrealdb.com/docs/reference/query-language/statements/update), and [delete](https://surrealdb.com/docs/reference/query-language/statements/delete) records, and serve as [links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links) from one record to another.
Record IDs can be constructed from a number of ways, including [alphanumeric text](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#text-record-ids), complex Unicode text and symbols, [numbers](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#numeric-record-ids), arrays, objects, [built-in ID generation functions](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#random-ids), and [a function to generate an ID from values](https://surrealdb.com/docs/reference/query-language/functions/database-functions/type#typerecord).
All of the following are examples of valid record IDs in SurrealQL.

```surql
company:surrealdb
company:w6xb3izpgvz4n0gow6q7
reaction:`🤪`
weather:['London', d'2025-02-14T01:52:50.375Z']
```

As all record IDs are unique, trying to create a new record with an existing record ID will return an error. To create a record or modify it if the ID already exists, use an [`UPSERT`](https://surrealdb.com/docs/reference/query-language/statements/upsert) statement or an [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert#example-usage) statement with an `ON DUPLICATE KEY UPDATE` clause.
##  Types of record IDs[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#types-of-record-ids)
###  Random IDs[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#random-ids)
When you [create a record](https://surrealdb.com/docs/reference/query-language/statements/create) without specifying the full ID, a random identifier is assigned after the table name. This differs from the traditional default of auto-increment or serial IDs that many developers are used to.

```surql
CREATE company;
```

Output

```surql
[
	{
		id: company:ezs644u19mae2p68404j
	}
]
```

Record IDs can be generated with a number of built-in ID generation functions, which are cryptographically secure and suitable for dispersion across a distributed datastore. These include a 20 digit alphanumeric ID (the default), sequentially incrementing and temporally sortable ULID Record identifiers, and UUID version 7 Record identifiers.

```surql
// Generate a random record ID 20 characters in length
// Charset: `abcdefghijklmnopqrstuvwxyz0123456789`
CREATE temperature:rand() SET time = time::now(), celsius = 37.5;
// Identical to the above CREATE statement, because
// :rand() is the default random ID format
CREATE temperature SET time = time::now(), celsius = 37.5;

// Generate a ULID-based record ID
CREATE temperature:ulid() SET time = time::now(), celsius = 37.5;
// Generate a UUIDv7-based record ID
CREATE temperature:uuid() SET time = time::now(), celsius = 37.5;
```

###  Text record IDs[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#text-record-ids)
Text record IDs can contain letters, numbers and `_` characters.

```surql
CREATE company:surrealdb SET name = 'SurrealDB';
CREATE user_version_2025 SET name = 'Alucard';
```

To create a record ID with complex characters, use ``` (backticks) around the table name and/or record identifier.

```surql
CREATE article:`8424486b-85b3-4448-ac8d-5d51083391c7` SET
    time = time::now(),
    author = person:tobie;

CREATE `Artykuł`:100 SET
    author = person:`Lech_Wałęsa`;
```

The parts of record IDs with complex characters will display enclosed by ``` backticks.
Output

```surql
-------- Query --------

[
	{
		author: person:tobie,
		id: article:`8424486b-85b3-4448-ac8d-5d51083391c7`,
		time: d'2025-02-18T01:48:46.364Z'
	}
]

-------- Query --------

[
	{
		author: person:`Lech_Wałęsa`,
		id: `Artykuł`:100
	}
]
```

###  Numeric record IDs[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#numeric-record-ids)
If you create a record ID with a number as a string, it will be stored with ``` backticks to differentiate it from a number.

```surql
CREATE article SET id = 10;
CREATE article SET id = "10";
CREATE article SET id = "article10";
SELECT VALUE id FROM article;
```

As the record ID `article:10` is different from `article:`10` `, no errors are returned when creating and both records turn up in the output of the `SELECT` statement. Meanwhile, the article with the identifier `article10` does not use backticks as there is no `article10` number to differentiate it from.
Output

```surql
[
	article:10,
	article:`10`,
    article:article10
]
```

If a numeric value is specified without any decimal point suffix and is within the range `-9223372036854775808` to `9223372036854775807` then the value will be parsed, stored, and treated as a 64-bit signed integer.
Any numeric numbers outside of the range of a signed 64-bit integer will be stored as a string.

```surql
/**[test]

[[test.results]]
value = "[{ celsius: 37.5f, id: temperature:17493, time: d'2025-10-03T01:09:50.155406Z' }]"

[[test.results]]
value = "[{ events: ['Galactic senate convenes', 'Mr. Bean still waits in a field'], id: year:⟨29878977097987987979232⟩ }]"

*/

CREATE temperature:17493 SET time = time::now(), celsius = 37.5;
CREATE year:29878977097987987979232 SET
    events = [
        "Galactic senate convenes",
        "Mr. Bean still waits in a field"
    ];
```

Output

```surql
-------- Query --------

[
	{
		celsius: 37.5f,
		id: temperature:17493,
		time: d'2025-02-17T06:21:08.911Z'
	}
]

-------- Query s--------

[
	{
		events: [
			'Galactic senate convenes',
			'Mr. Bean still waits in a field'
		],
		id: year:`29878977097987987979232`
	}
]
```

###  Array-based record IDs[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#array-based-record-ids)
Record IDs can be constructed out of arrays and even objects. This sort of record ID is most used when you have a field or two that will be used to look up records inside a [record range](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges), which is extremely performant. This is in contrast to using a `WHERE` clause to filter, which involves a table scan.
Records in SurrealDB can store arrays of values, including other nested arrays or objects within them. Different types of values can be stored within the same array, unless defined otherwise.

```surql
/**[test]

[[test.results]]
value = "[{ conditions: 'cloudy', id: weather:['London', d'2025-02-13T05:00:00Z'], temperature: 5.7f }]"

*/

CREATE weather:['London', d'2025-02-13T05:00:00Z'] SET
    temperature = 5.7,
    conditions = "cloudy";
```

Output

```surql
[
	{
		conditions: 'cloudy',
		id: weather:[
			'London',
			d'2025-02-13T05:00:00Z'
		],
		temperature: 5.7f
	}
]
```

###  Why record ranges are performant[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#why-record-ranges-are-performant)
The main reason why record ranges are so performant is simply because the database knows ahead of time in which area to look for records in a query, and therefore has a smaller "surface area" to work in.
This can be demonstrated by seeing what happens when a single record range query encompasses all of the records in a database. The example below creates 10,000 `player` records that have an array-based record ID that begins with `'mage'`, allowing them to be used in a record range query, as well as a field called `class` that is also `'mage'`, which will be used in a `WHERE` clause to compare performance.
Interestingly, in this case a record range query is only somewhat more performant. This is because both queries end up iterating over 10,000 records, with the only difference being that the query with a `WHERE` clause also checks to see if the value of the `class` field is equal to `'mage'`.

```surql
FOR $_ IN 0..10000 {
    CREATE player:['mage', rand::id()] SET class = 'mage';
};

LET $_ = SELECT * FROM player:['mage', NONE]..['mage', ..];
LET $_ = SELECT * FROM player WHERE class = 'mage';
```

If the number of `player` records is extended to a larger number of classes, however, the difference in performance will be much larger. In this case the record range query is still only iterating a relatively small surface area of 10,000 records, while the second one has ten times this number to go through in addition to the `WHERE` clause on top.

```surql
FOR $_ IN 0..10000 {
  CREATE player:['mage', rand::id()] SET class = 'mage';
  CREATE player:['barbarian', rand::id()] SET class = 'barbarian';
  CREATE player:['rogue', rand::id()]     SET class = 'rogue';
  CREATE player:['bard', rand::id()]      SET class = 'bard';
  CREATE player:['sage', rand::id()]      SET class = 'sage';
  CREATE player:['psionic', rand::id()]   SET class = 'psionic';
  CREATE player:['thief', rand::id()]     SET class = 'thief';
  CREATE player:['paladin', rand::id()]   SET class = 'paladin';
  CREATE player:['ranger', rand::id()]    SET class = 'ranger';
  CREATE player:['cleric', rand::id()]    SET class = 'cleric';
};

LET $_ = SELECT * FROM player:['mage', NONE]..['mage', ..];
LET $_ = SELECT * FROM player WHERE class = 'mage';
```

###  IDs made with parameters and function calls[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#ids-made-with-parameters-and-function-calls)
Parameters and function calls can be used inside array- and object-based record IDs in the same way as on standalone arrays and objects.

```surql
/**[test]

[[test.results]]
value = "NONE"

[[test.results]]
value = "[{ conditions: 'cloudy', id: weather:['Seoul', d'2025-10-03T01:11:38.204589Z'], temperature: -2.3f }]"
skip-datetime = true

[[test.results]]
value = "[{ conditions: 'cloudy', id: weather:['London', d'2025-10-03T01:11:38.204961Z'], temperature: 5.3f }]"
skip-datetime = true

*/

LET $now = time::now();

CREATE weather:['Seoul', $now] SET
    temperature = -2.3,
    conditions = "cloudy";

CREATE weather:['London', time::now()] SET
    temperature = 5.3,
    conditions = "cloudy";
```

To create a record that uses a parameter or function call as its entire record identifier, the [`type::record()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/type#typerecord) function can be used. (Note: this function was known as `type::thing()` before SurrealDB 3.0)

```surql
/**[test]

[[test.results]]
value = "NONE"

[[test.results]]
value = "[{ city: 'London', id: weather:⟨2025-10-03T01:13:14.238633Z⟩ }]"
skip-record-id-key = true

*/

LET $now = time::now();

CREATE type::record("weather", $now) SET city = 'London';
```

Output

```surql
[
	{
		city: 'London',
		id: weather:`2025-02-18T02:30:08.563Z`
	}
]
```

##  Defining record IDs in a schema[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#defining-record-ids-in-a-schema)
The type name of a record ID is `record`, which by default allows any sort of record. This type can be set inside a [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statement.

```surql
/**[test]

[[test.results]]
value = "NONE"

[[test.results]]
value = "NONE"

[[test.results]]
value = "[{ friends: [person:one, person:two], id: person:663uogu8gnw31irybeer, possessions: [book:one, house:one] }]"
skip-record-id-key = true

*/

DEFINE FIELD possessions ON TABLE person TYPE option<array<record>>;
DEFINE FIELD friends ON TABLE person TYPE option<array<record<person>>>;

CREATE person SET
    possessions = [ book:one, house:one],
    friends = [ person:one, person:two ];
```

Be sure to use just `record` instead of `record`, as `` here would imply actual records of a table called `any`.

```surql
/**[test]

[[test.results]]
value = "NONE"

[[test.results]]
match = "$error = "Couldn't coerce value for field `possessions` of `person:*`: Expected `none | array<record<any>>` but found `[book:one, house:one]`""
error = true

[[test.results]]
value = "[{ id: person:u6qd2t4ij2h45bkf2gk4, possessions: [any:one, any:two] }]"
skip-record-id-key = true

*/

DEFINE FIELD possessions ON TABLE person TYPE option<array<record<any>>>;

-- Won't work, 'book' and 'house' are not of table 'any'
CREATE person SET
    possessions = [ book:one, house:one ];

-- Actually expects this, which is probably
-- not what the DEFINE FIELD intended
CREATE person SET
    possessions = [ any:one, any:two ];
```

##  Record ranges[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#record-ranges)
SurrealDB supports the ability to query a range of records, using the record ID. Record ID range queries retrieve records using the natural sorting order of the record IDs, making a table scan unnecessary. These range queries can be used to query a range of records in a timeseries context.

```surql
-- Select all person records with IDs between the given range
SELECT * FROM person:1..1000;

-- Select all records for a particular location, inclusive
SELECT * FROM temperature:['London', NONE]..=['London', ..];

-- Select all temperature records with IDs less than a maximum value
SELECT * FROM temperature:..['London', '2022-08-29T08:09:31'];

-- Select all temperature records with IDs greater than a minimum value
SELECT * FROM temperature:['London', '2022-08-29T08:03:39']..;

-- Select all temperature records with IDs between the specified range
SELECT * FROM temperature:['London', '2022-08-29T08:03:39']..['London', '2022-08-29T08:09:31'];
```

The following example shows the difference in performance between a regular query that uses a `WHERE` clause and a record range scan.

```surql
FOR $num IN 0..=100000 {
  CREATE person SET id = $num, num = $num  
};

-- Assign the output to an unused parameter
-- to avoid excessive output
LET $_ = SELECT * FROM person WHERE num IN 0..=1000;
LET $_ = SELECT * FROM person:0..=1000;
```

##  Limitations[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#limitations)
At present, the `VALUE` clause cannot be used inside a [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statement.

```surql
/**[test]

[[test.results]]
error = "'Cannot use the `VALUE` keyword on the `id` field.'"

*/

DEFINE FIELD id ON user VALUE rand::int(1, 1000000000) READONLY;
```

Output

```surql
[
	{
		id: user:9ixn3oei6o532c2qyixa
	}
]
```

To achieve the desired behaviour, the `id` field can be set inside the statement to create the record.

```surql
/**[test]

[[test.results]]
value = "[{ id: user:639167349 }]"
skip-record-id-key = true

*/

CREATE user SET id = rand::int(1, 1000000000);
```

##  Learn more[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids#learn-more)
Learn more about record IDs [in this blogpost](https://surrealdb.com/blog/the-life-changing-magic-of-surrealdb-record-ids#the-performance-at-scale) and on this [youtube video](https://www.youtube.com/watch?v=c0cqmWRYP8c).
