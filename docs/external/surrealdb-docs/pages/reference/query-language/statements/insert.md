---
title: "https://surrealdb.com/docs/reference/query-language/statements/insert"
url: "https://surrealdb.com/docs/reference/query-language/statements/insert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/insert

Source: https://surrealdb.com/docs/reference/query-language/statements/insert

The `INSERT` statement can be used to insert or update data into the database, using the same statement syntax as the traditional SQL Insert statement.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/insert#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
INSERT [ RELATION ] [ IGNORE ] INTO @what
	[ @value
	  | (@fields) VALUES (@values)
		[ ON DUPLICATE KEY UPDATE @field = @value ... ]
	]
	[ RETURN NONE | RETURN BEFORE | RETURN AFTER | RETURN DIFF | RETURN @statement_param, ... | RETURN VALUE @statement_param ]
;
```

INSERTRELATIONIGNOREINTO@what@value(@fields)VALUES(@values)ON DUPLICATE KEY UPDATE@field = @value ...RETURNNONEBEFOREAFTERDIFF@statement_param, ...VALUE@statement_param;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/insert#example-usage)
The following query shows example usage of this statement.

```surql
INSERT INTO company {
	name: 'SurrealDB',
	founded: "2021-09-10",
	founders: [person:tobie, person:jaime],
	tags: ['big data', 'database']
};
```

Records can also be inserted by using the `VALUES` keyword. This keyword is preceded by the name of the fields in question, and followed by comma-separated values matching the number of fields specified.

```surql
-- Insert a single record
INSERT INTO
	company (name, founded)
	VALUES  ('SurrealDB', '2021-09-10');

-- Insert multiple records
INSERT INTO
	company (name, founded)
	VALUES  ('Acme Inc.', '1967-05-03'), ('Apple Inc.', '1976-04-01');
```

It is possible to update records which already exist or violate a unique index by specifying an `ON DUPLICATE KEY UPDATE` clause. This clause also allows incrementing and decrementing numeric values, and adding or removing values from arrays. To increment a numeric value, or to add an item to an array, use the `+=` operator. To decrement a numeric value, or to remove an value from an array, use the `-=` operator.

```surql
INSERT INTO product (name, url) VALUES ('Salesforce', 'salesforce.com') ON DUPLICATE KEY UPDATE tags += 'crm';
```

Field names inside `ON DUPLICATE KEY UPDATE` refer to the fields of the existing record. To access the fields of the new record that was attempted to be inserted, prefix the field name with [`$input`](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters#input):

```surql
INSERT INTO city (id, population, at_year) VALUES ("Calgary", 1665000, 2024)
ON DUPLICATE KEY UPDATE
	population = $input.population,
	at_year = $input.at_year;
```

An example of `ON DUPLICATE KEY UPDATE` when a unique key is encountered shows the same behaviour as that with a duplicate record:

```surql
DEFINE FIELD data_for ON user_data TYPE record<user>;
DEFINE INDEX one_user ON user_data FIELDS data_for UNIQUE;

INSERT INTO user_data {
    data_for: user:one,
    some: "data"
} ON DUPLICATE KEY UPDATE times_updated += 1, last_edited = time::now();

INSERT INTO user_data {
    data_for: user:one,
    some_more: "data"
} ON DUPLICATE KEY UPDATE times_updated += 1, last_edited = time::now();
```

Output

```surql
-------- Query --------

[
	{
		for: user:one,
		id: user_data:kp78dubsxmp4f04x0de3,
		some: 'data'
	}
]

-------- Query --------

[
	{
		for: user:one,
		id: user_data:kp78dubsxmp4f04x0de3,
		last_edited: d'2025-07-14T05:15:52.146Z',
		some: 'data',
		times_updated: 1
	}
]
```

Using the insert statement, it is possible to copy records easily between tables. The records being copied will have the same id in the new table, but the record id will signify the new table name.

```surql
INSERT INTO recordings_san_francisco (SELECT * FROM temperature
  WHERE city = 'San Francisco');
```

Furthermore, it is possible to perform a bulk insert in a single query. The `@what` part of the syntax can be either a single object or an array of objects.

```surql
INSERT INTO person [
   { id: "jaime", name: "Jaime", surname: "Morgan Hitchcock" },
   { id: "tobie", name: "Tobie", surname: "Morgan Hitchcock" },
];
```

###  Ignoring duplicates[](https://surrealdb.com/docs/reference/query-language/statements/insert#ignoring-duplicates)
While attempting to insert one or more records via the `INSERT` statement, if the record ID is already present in the table, the query will encounter an error and fail. If the `IGNORE` clause is supplied, records with an already existing or duplicate ID will be silently ignored.

```surql
INSERT IGNORE INTO person [
   { id: "jaime", name: "Jaime", surname: "Morgan Hitchcock" },
   { id: "tobie", name: "Tobie", surname: "Morgan Hitchcock" },

   { id: "jaime", name: "Jaime", surname: "Morgan Hitchcock" }, -- will not throw an error
];
```

###  Return values[](https://surrealdb.com/docs/reference/query-language/statements/insert#return-values)
By default, the `INSERT` statement returns the record once it has been inserted. To change what is returned, we can use the `RETURN` clause, specifying either `NONE`, `BEFORE`, `AFTER`, `DIFF`, or a comma-separated list of specific fields to return.
`RETURN NONE` can be useful to avoid excess output:

```surql
-- Insert a record and return nothing
INSERT INTO company {
	name: 'SurrealDB',
	founded: "2021-09-10",
	founders: [person:tobie, person:jaime],
	tags: ['big data', 'database']
} RETURN NONE;
```

`RETURN DIFF` returns the changeset diff:

```surql
-- Insert a record and return the diff
INSERT INTO company {
	name: 'SurrealDB',
	founded: "2021-09-10",
	founders: [person:tobie, person:jaime],
	tags: ['big data', 'database']
} RETURN DIFF;
```

Response

```surql
-------- Query 1 --------

[
	[
		{
			op: 'replace',
			path: '/',
			value: {
				founded: '2021-09-10',
				founders: [
					person:tobie,
					person:jaime
				],
				id: company:hu5o1wqbo29t10engbeo,
				name: 'SurrealDB',
				tags: [
					'big data',
					'database'
				]
			}
		}
	]
]
```

`RETURN BEFORE` inside a `INSERT` statement is essentially a synonym for `RETURN NONE`, while `RETURN AFTER` is the default behaviour for `INSERT`.

```surql
-- Before insert will always return NONE as it is the same as the record being inserted
INSERT INTO company {
	name: 'SurrealDB',
	founded: "2021-09-10",
	founders: [person:tobie, person:jaime],
	tags: ['big data', 'database']
} RETURN BEFORE;
```

```surql
-- Return the record after creation
INSERT INTO company {
	name: 'SurrealDB',
	founded: "2021-09-10",
	founders: [person:tobie, person:jaime],
	tags: ['big data', 'database']
} RETURN AFTER;
```

You can also return specific fields from a created record, the value of a single field using `VALUE`, as well as ad-hoc fields to modify the output as needed.

```surql
INSERT INTO person {
    age: 46,
    username : "john-smith",
    interests : ['skiing', 'music'] }
RETURN
    age,
    interests,
    age + 1 AS age_next_year;

INSERT INTO planet [
	{
		name: 'Venus',
        surface_temp: 462,
        temp_55_km_up: 27
	},
	{
		name: 'Earth',
        surface_temp: 15,
        temp_55_km_up: -55
	}
] RETURN VALUE temp_55_km_up;
```

Response

```surql
-------- Query --------

[
	{
		age: 46,
		age_next_year: 47,
		interests: [
			'skiing',
			'music'
		]
	}
]

-------- Query --------

[
	27,
	-55
]
```

##  Bulk insert[](https://surrealdb.com/docs/reference/query-language/statements/insert#bulk-insert)
The `INSERT` statement supports bulk insert, which allows multiple records to be inserted in a single query. The `@what` part of the syntax can be either a single object or an array of objects.

```surql
INSERT INTO person [
   { id: "jaime", name: "Jaime", surname: "Morgan Hitchcock" },
   { id: "tobie", name: "Tobie", surname: "Morgan Hitchcock" },
   -- ... 1000 more records
];
```

##  Insert relation tables[](https://surrealdb.com/docs/reference/query-language/statements/insert#insert-relation-tables)
The `INSERT` statement can also be used to add records into relation tables. The `@what` part of the syntax can be either a single object or an array of objects.
Learn more about creating relationships between tables in the [RELATE](https://surrealdb.com/docs/reference/query-language/statements/relate) statement. For example:

```surql
-- Insert records into the person table
INSERT INTO person [
	{ id: 1 },
	{ id: 2 },
	{ id: 3 },
];
-- Insert a single relation
INSERT RELATION INTO likes {
	in: person:1,
	id: 'object',
	out: person:2,
};

-- Insert multiple relations
INSERT RELATION INTO likes [
	{
		in: person:1,
		id: 'array',
		out: person:2,
	},
	{
		in: person:2,
		id: 'array_two',
		out: person:3,
	}
];

-- Insert a relation and return the value of the likes field
INSERT RELATION INTO likes (in, id, out)
	VALUES (person:1, 'values', person:2);

-- Select the value of the likes field
SELECT VALUE ->likes FROM person;

```

Available since: v3.1.5
When `INSERT RELATION` specifies an explicit edge `id` that already exists, SurrealDB returns a record-exists error instead of updating the edge in place. You can use `ON DUPLICATE KEY UPDATE` to merge into the existing relation, in the same way as a normal [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert#example-usage):

```surql
CREATE person:one, post:one;

INSERT RELATION INTO likes {
  in: person:one,
  out: post:one,
  id: [person:one, post:one],
  note: 'first',
};

INSERT RELATION INTO likes {
  in: person:one,
  out: post:one,
  id: [person:one, post:one],
  note: 'second',
};

INSERT RELATION INTO likes {
  in: person:one,
  out: post:one,
  id: [person:one, post:one],
  note: 'third',
} ON DUPLICATE KEY UPDATE note = 'updated';
```
