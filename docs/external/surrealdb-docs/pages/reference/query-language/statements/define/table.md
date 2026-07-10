---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/table"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/table

Source: https://surrealdb.com/docs/reference/query-language/statements/define/table

The `DEFINE TABLE` statement allows you to declare your table by name, enabling you to apply strict controls to a table's schema by making it `SCHEMAFULL`, create a foreign table view, and set permissions specifying what operations can be performed on the table.
Note
The fields of a table are not defined using `DEFINE TABLE`, but via individual [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statements.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/table#requirements)
  * •
You must be authenticated as a root owner or editor, namespace owner or editor, or database owner or editor before you can use the `DEFINE TABLE` statement.
  * •
[You must select your namespace and database](https://surrealdb.com/docs/reference/query-language/statements/use) before you can use the `DEFINE TABLE` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/table#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE TABLE [ OVERWRITE | IF NOT EXISTS ] @name
	[ DROP ]
	[ SCHEMAFULL | SCHEMALESS ]
	[ TYPE [ ANY | NORMAL | RELATION [ IN | FROM ] @table [ OUT | TO ] @table [ ENFORCED ]]]
	[ AS SELECT @projections
		FROM @tables
		[ WHERE @condition ]
		[ GROUP [ BY @groups | ALL ] ]
	]
	[ CHANGEFEED @duration [ INCLUDE ORIGINAL ] ]
	[ PERMISSIONS [ NONE | FULL
		| FOR select @expression
		| FOR create @expression
		| FOR update @expression
		| FOR delete @expression
	] ]
    [ COMMENT @string ]
```

DEFINETABLEOVERWRITEIFNOTEXISTS@nameDROPSCHEMAFULLSCHEMALESSTYPEANYNORMALRELATIONINFROM@tableOUTTO@tableENFORCEDASSELECT@projectionsFROM@tablesWHERE@conditionGROUPBY@groupsALLCHANGEFEED@durationINCLUDEORIGINALPERMISSIONSNONEFULLFORselect@expressionFORcreate@expressionFORupdate@expressionFORdelete@expressionCOMMENT@string
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/table#example-usage)
Below shows how you can create a table using the `DEFINE TABLE` statement.

```surql
-- Declare the name of a table.
DEFINE TABLE reading;
```

The following example uses the `DROP` portion of the `DEFINE TABLE` statement. Marking a table as `DROP` disallows creating or updating records.
`DROP` tables are useful in combination with events or foreign (view) tables, as you can compute a record and essentially drop the input.

```surql
-- By marking a table as DROP, you disallow any records to be created or updated.
-- Records that currently exist in the table will not automatically be deleted, you can still remove them manually.
DEFINE TABLE reading DROP;
```

The following expression shows how you can define a `CHANGEFEED` for a table. After creating, updating, and deleting records in the table as usual, using `SHOW CHANGES FOR` will show the changes that have taken place during this time.
If an entry holds a change to an existing record, the diff will show the operation needed to modify the record to the state immediately preceding its current state. In other words, the diff included is a reverse diff.

```surql
-- Define the changefeed and its duration
-- Optionally, append INCLUDE ORIGINAL to include info
-- on the current record before a change took place
DEFINE TABLE reading CHANGEFEED 3d;

-- Create some records in the reading table
CREATE reading SET story = "Once upon a time";
CREATE reading SET story = "there was a database";
UPDATE reading SET is_interesting = true;

-- Replay changes to the reading table since a certain date
-- Must be after the timestamp at which the changefeed began
SHOW CHANGES FOR TABLE reading SINCE d"2025-09-07T01:23:52Z" LIMIT 10;

-- Alternatively, show the changes for the table since a version number
SHOW CHANGES FOR TABLE reading SINCE 0 LIMIT 10;
```

Response without INCLUDE ORIGINAL

```surql
[
	{
		changes: [
			{
				define_table: {
					changefeed: {
						expiry: 3d,
						original: false
					},
					drop: false,
					id: 0,
					kind: {
						kind: 'ANY'
					},
					name: 'reading',
					permissions: {
						create: false,
						delete: false,
						select: false,
						update: false
					},
					schemafull: false
				}
			}
		],
		versionstamp: 116395447100768256
	},
	{
		changes: [
			{
				update: {
					id: reading:bqlejs8fx4phgbo6g5ve,
					story: 'Once upon a time'
				}
			}
		],
		versionstamp: 116395447100833792
	},
	{
		changes: [
			{
				update: {
					id: reading:fa8o65ccxykfxqqz91yo,
					story: 'there was a database'
				}
			}
		],
		versionstamp: 116395447100833793
	},
	{
		changes: [
			{
				update: {
					id: reading:bqlejs8fx4phgbo6g5ve,
					is_interesting: true,
					story: 'Once upon a time'
				}
			},
			{
				update: {
					id: reading:fa8o65ccxykfxqqz91yo,
					is_interesting: true,
					story: 'there was a database'
				}
			}
		],
		versionstamp: 116395447100833794
	}
]
```

Response with INCLUDE ORIGINAL

```surql
[
	{
		changes: [
			{
				define_table: {
					changefeed: {
						expiry: 3d,
						original: true
					},
					drop: false,
					id: 0,
					kind: {
						kind: 'ANY'
					},
					name: 'reading',
					permissions: {
						create: false,
						delete: false,
						select: false,
						update: false
					},
					schemafull: false
				}
			}
		],
		versionstamp: 116395448975818752
	},
	{
		changes: [
			{
				update: {
					id: reading:kypj876yubk4fnnja93b,
					story: 'Once upon a time'
				}
			}
		],
		versionstamp: 116395448975818753
	},
	{
		changes: [
			{
				update: {
					id: reading:0i2qwoi053nmrl4k2wm2,
					story: 'there was a database'
				}
			}
		],
		versionstamp: 116395448975818754
	},
	{
		changes: [
			{
				current: {
					id: reading:0i2qwoi053nmrl4k2wm2,
					is_interesting: true,
					story: 'there was a database'
				},
				update: [
					{
						op: 'remove',
						path: '/is_interesting'
					}
				]
			},
			{
				current: {
					id: reading:kypj876yubk4fnnja93b,
					is_interesting: true,
					story: 'Once upon a time'
				},
				update: [
					{
						op: 'remove',
						path: '/is_interesting'
					}
				]
			}
		],
		versionstamp: 116395448975818755
	}
]
```

##  Schemafull tables[](https://surrealdb.com/docs/reference/query-language/statements/define/table#schemafull-tables)
The following example demonstrates the `SCHEMAFULL` portion of the `DEFINE TABLE` statement. When a table is defined as schemafull, the database strictly enforces any schema definitions that are specified using the `DEFINE TABLE` statement. New fields can not be added to a `SCHEMAFULL` table unless they are defined via the [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statement.
Note
Schemafull tables are implicitly type [`NORMAL`](https://surrealdb.com/docs/reference/query-language/statements/define/table#table-with-specialized-type-clause) tables by default.

```surql
-- Create schemafull user table.
DEFINE TABLE user SCHEMAFULL;

-- Define some fields.
DEFINE FIELD firstName ON TABLE user TYPE string;
DEFINE FIELD lastName ON TABLE user TYPE string;
DEFINE FIELD email ON TABLE user TYPE string
  ASSERT string::is_email($value);
DEFINE INDEX userEmailIndex ON TABLE user COLUMNS email UNIQUE;

-- SEE IT IN ACTION
-- 1: Add a user with all required fields and an undefined one, 'photoURI'.
CREATE user CONTENT {
    firstName: 'Tobie',
    lastName: 'Hitchcock',
    email: 'Tobie.Hitchcock@surrealdb.com',
    photoURI: 'photo/yxCFi22Jw2.webp'
};
-- 2: Statement will not fail but photoURI will be ignored as it is not a
--    defined field.

-- 3: Query the data
SELECT * FROM user;
```

##  Schemaless tables[](https://surrealdb.com/docs/reference/query-language/statements/define/table#schemaless-tables)
The following example demonstrates the `SCHEMALESS` portion of the `DEFINE TABLE` statement. This allows you to explicitly state that the specified table has no schema.

```surql
-- Create schemaless user table.
DEFINE TABLE user SCHEMALESS;

-- Define some fields.
DEFINE FIELD firstName ON TABLE user TYPE string;
DEFINE FIELD lastName ON TABLE user TYPE string;
DEFINE FIELD email ON TABLE user TYPE string
  ASSERT string::is_email($value);
DEFINE INDEX userEmailIndex ON TABLE user COLUMNS email UNIQUE;

-- SEE IT IN ACTION - Example 1
-- 1: Add a user with all required fields and an undefined one.
CREATE user:tobie SET firstName = 'Tobie', lastName = 'Hitchcock', email = 'Tobie.Hitchcock@surrealdb.com', photoURI = 'photo/yxCFi22Jw2.webp';
-- 2: Statement will succeed because user is a SCHEMALESS table.

-- SEE IT IN ACTION - Example 2
-- 1: Add a user with an invalid email address and include a new field that was never defined.
CREATE user:jaime SET firstName = 'Jamie', lastName = 'Hitchcock', email = 'Jamie.Hitchcock', photoURI = 'photo/yxCFi22Jw2.webp';
-- 2: Statement will fail because the value for email was not valid.
```

##  Interaction between fields[](https://surrealdb.com/docs/reference/query-language/statements/define/table#interaction-between-fields)
While a `DEFINE TABLE` statement represents a template for any subsequent records to be created, a `DEFINE FIELD` statement pertains to concrete field data of a record. As such, a `DEFINE FIELD` statement gives access to the record's other fields through their names, as well as the current field through the [`$value`](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters#value) parameter.

```surql
DEFINE TABLE person SCHEMAFULL;

DEFINE FIELD first_name
  ON TABLE person TYPE string ASSERT string::len($value) < 20;
DEFINE FIELD last_name 
  ON TABLE person TYPE string ASSERT string::len($value) < 20;
DEFINE FIELD name      
  ON TABLE person             VALUE first_name + ' ' + last_name;

// Creates a `person` with the name "Bob Bobson"
CREATE person SET first_name = "Bob", last_name = "Bobson";
```

##  Pre-computed table views[](https://surrealdb.com/docs/reference/query-language/statements/define/table#pre-computed-table-views)
In SurrealDB, like in other databases, you can create views. The way you create views is using the `DEFINE TABLE` statement like you would for any other table, then adding the `AS` clause at the end with your `SELECT` query.

```surql
DEFINE TABLE review DROP;
-- Define a table as a view which aggregates data from the review table
DEFINE TABLE avg_product_review TYPE NORMAL AS
SELECT
	count() AS number_of_reviews,
	math::mean(<float> rating) AS avg_review,
	->product.id AS product_id,
	->product.name AS product_name
FROM review
GROUP BY product_id, product_name;

-- Query the projection
SELECT * FROM avg_product_review;
```

There are a few important things which make our views far more powerful than a typical relational database view and a few limitations to keep in mind.
Starting with what makes them powerful. Our pre-computed table views are most similar to event-based, incrementally updating, materialised views. Let's explain what that means.
  * •
Event-based, meaning that when you run add or remove data from the underlying table, in our example, the `review` table, it triggers a matching event on the `avg_product_review` table view.
  * •
Materialised view, meaning that the first time we run the table view query, it will run the query like a normal `SELECT` statement, but then materialise the result. Instead of normal views which behave like bookmarked `SELECT` queries, that just look like tables to the user.
  * •
Incrementally updating, meaning that for any subsequent run, it will listen for the event trigger and perform the most efficient operation possible to always keep the result up to date, instead of just running the `SELECT` statement again.

While this functionality can be replicated in many other databases, it is usually only done by expert users as it can be very complicated to set up and maintain. Therefore, the true power of our pre-computed table views is making this advanced functionality accessible to everyone.
As mentioned though, there are a few limitations to keep in mind.
  * •
First, while subsequent runs are very efficient, the initial run of large analytical queries can be slow and use a lot of resources, because its just a normal `SELECT` statement. Therefore indexing and query optimisation are still very important.
  * •
Second, while both graph relations and record links are supported, the table view update event, only gets triggered based on the table we have in our `FROM` clause. In our case, just the `review` table, not the `product` we are also using in the query. Meaning that if you delete a `review` the `avg_product_review` will reflect that in near real-time. However if you delete a `product`, it will still show up in `avg_product_review`.
  * •
Third, view tables are **read-only**. Since 3.2.0, `CREATE`, `INSERT`, `UPSERT`, `UPDATE`, `DELETE`, and `RELATE` against a view table are rejected — records are computed from the source query only. The one exception is import: rows emitted for a view during export can be re-applied under `OPTION IMPORT`, to allow export → import round-trips to keep working.

Also note that table views are not triggered when importing data.
##  Defining permissions[](https://surrealdb.com/docs/reference/query-language/statements/define/table#defining-permissions)
By default, the permissions on a table will be set to NONE unless otherwise specified.

```surql
CREATE some_table;
DEFINE TABLE some_other_table;

INFO FOR DB;
```

Response

```surql
{
	analyzers: {},
	functions: {},
	models: {},
	params: {},
	scopes: {},
	tables: {
		some_other_table: 'DEFINE TABLE some_other_table TYPE ANY SCHEMALESS PERMISSIONS NONE',
		some_table: 'DEFINE TABLE some_table TYPE ANY SCHEMALESS PERMISSIONS NONE'
	},
	tokens: {},
	users: {}
}
```

The following shows how to set table level `PERMISSIONS` using the `DEFINE TABLE` statement. This allows you to set independent permissions for selecting, creating, updating, and deleting data.

```surql
-- Specify access permissions for the 'post' table
DEFINE TABLE post SCHEMALESS
	PERMISSIONS
		FOR select
			-- Published posts can be selected
			WHERE published = true
			-- A user can select all their own posts
			OR user = $auth.id
		FOR create, update
			-- A user can create or update their own posts
			WHERE user = $auth.id
		FOR delete
			-- A user can delete their own posts
			WHERE user = $auth.id
			-- Or an admin can delete any posts
			OR $auth.admin = true
;
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/table#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a table only if it does not already exist. You should use the `IF NOT EXISTS` clause when defining a table in SurrealDB if you want to ensure that the table is only created if it does not already exist. If the table already exists, the `DEFINE TABLE` statement will return an error.
It's particularly useful when you want to safely attempt to define a table without manually checking its existence first.
On the other hand, you should not use the `IF NOT EXISTS` clause when you want to ensure that the table definition is updated regardless of whether it already exists. In such cases, you might prefer using the `OVERWRITE` clause, which allows you to define a table and overwrite an existing one if it already exists, ensuring that the latest version of the table definition is always in use

```surql
-- Create a TABLE if it does not already exist
DEFINE TABLE IF NOT EXISTS reading;
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/table#using-overwrite-clause)
The `OVERWRITE` clause can be used to define a table and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing table definition. If the table already exists, the `DEFINE TABLE` statement will overwrite the existing table definition with the new one.

```surql
-- Create an TABLE and overwrite if it already exists
DEFINE TABLE OVERWRITE example;
```

##  Table with specialized `TYPE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/table#table-with-specialized-type-clause)
When defining a table in SurrealDB, you can specify the type of data that can be stored in the table. This can be done using the `TYPE` clause, followed by either `ANY`, `NORMAL`, or `RELATION`.
With `TYPE ANY`, you can specify a table to store any type of data, whether it's a normal record or a relational record.
With `TYPE NORMAL`, you can specify a table to only store "normal" records, and not relations. When a table is defined as `TYPE NORMAL`, it will not be able to store relations this can be useful when you want to restrict the type of data that can be stored in a table in schemafull mode.
Finally, with `TYPE RELATION`, you can specify a table to only store relational type content. This can be useful when you want to restrict the type of data that can be stored in a table.

```surql
DEFINE TABLE person TYPE ANY;
DEFINE TABLE person;
```

With `TYPE NORMAL`, you can specify a table to only store "normal" records, and not relations.

```surql
-- Since it's default, we can also omit the TYPE clause
DEFINE TABLE person TYPE NORMAL;
```

With `TYPE RELATION`, you can specify a table to only store relational type content, and restrict what kind of relations can be stored.

```surql
-- Just a RELATION table, no constraints on the type of table
DEFINE TABLE likes TYPE RELATION;

-- Define a relation table, and constrain the type of relation which can be stored
DEFINE TABLE likes TYPE RELATION FROM user TO post;
-- OR use IN and OUT alternatively to FROM and TO
DEFINE TABLE likes TYPE RELATION IN user OUT post;
-- To allow a link to one of a possible set of record types, use the | operator
DEFINE TABLE likes TYPE RELATION FROM user TO post|video;
DEFINE TABLE likes TYPE RELATION IN user OUT post|video;
```

```surql
-- Define a relation table, and constrain the type of relation which can be stored
DEFINE TABLE assigned_to SCHEMAFULL TYPE RELATION IN tag OUT sticky
    PERMISSIONS
        FOR create, select, update, delete
            WHERE in.owner == $auth.id AND out.author == $auth.id;
```

##  Using ENFORCED to ensure that related records exist[](https://surrealdb.com/docs/reference/query-language/statements/define/table#using-enforced-to-ensure-that-related-records-exist)
As relations are represented by standalone tables, they can be constructed before any linked records exist.

```surql
RELATE city:one->road_to->city:two SET
    distance = 12.4,
    slope = 5.4;
```

Output

```surql
[
	{
		distance: 12.4f,
		id: road_to:pacwucj25a056hhs2s5h,
		in: city:one,
		out: city:two,
		slope: 5.4f
	}
]
```

As such, a query on the relation will return nothing until the records it has been defined upon are created.

```surql
SELECT ->road_to->city FROM city;

CREATE city:one, city:two;
SELECT ->road_to->city FROM city;
```

Output

```surql
-------- Query --------

[]

-------- Query --------

[
	{
		"->road_to": {
			"->city": [
				city:two
			]
		}
	},
	{
		"->road_to": {
			"->city": []
		}
	}
]
```

If this behaviour is not desirable, the `ENFORCED` clause can be used on a table of `TYPE RELATION` to disallow a `RELATE` statement from working unless it points to existing data.

```surql
DEFINE TABLE road_to TYPE RELATION IN city OUT city ENFORCED;

RELATE city:one->road_to->city:three SET
    distance = 5.5,
    slope = 30.0;
```

Output

```surql
"The record 'city:one' does not exist"
```

##  Inserting data from undefined fields on a `SCHEMAFULL` table[](https://surrealdb.com/docs/reference/query-language/statements/define/table#inserting-data-from-undefined-fields-on-a-schemafull-table)
Available since: v3.0.0
Previously, an insert into a `SCHEMAFULL` table would work even if extra data was present. The query below shows this behaviour, in which the data inside `unneeded_data` is simply filtered out.

```surql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD user_num ON user TYPE int;

CREATE ONLY user CONTENT { 
    name: "Billy", 
    user_num: 100,
    unneeded_data: {
        some: "other",
        needless: "data"
    }
};
```

Output

```surql
{
    id: user:r38bg4fnp9nurksd06nl,
    name: 'Billy',
    user_num: 100
}
```

While convenient, this led to the possibility of a typo leading to unexpected results.

```surql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD user_num ON user TYPE option<int>;

CREATE ONLY user CONTENT { 
    name: "Billy", 
    User_num: 100 // Note: field is capitalized
};
```

The output shows that the `user` lacks a value for `user_num` even though the query above intended to provide this data.

```surql
{
	id: user:jn4762t7oyure86fe3qk,
	name: 'Billy'
}
```

The same query in SurrealDB 3.0 now returns an error.

```surql
"Found field 'User_num', but no such field exists for table 'user'"
```

To avoid an error when working with data that contains unneeded fields, use `.{}` (the destructuring operator) to pass on only the necessary fields.

```surql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD user_num ON user TYPE int;

CREATE ONLY user CONTENT { 
    name: "Billy", 
    user_num: 100,
    unneeded_data: {
        some: "other",
        needless: "data"
    }
}.{
    -- Only pass on the name and user_num data
    name,
    user_num
};
```
