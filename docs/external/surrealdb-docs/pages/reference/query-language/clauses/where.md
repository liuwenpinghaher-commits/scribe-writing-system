---
title: "https://surrealdb.com/docs/reference/query-language/clauses/where"
url: "https://surrealdb.com/docs/reference/query-language/clauses/where"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/clauses/where

Source: https://surrealdb.com/docs/reference/query-language/clauses/where

The `WHERE` clause can be used to specify a condition that acts as a filter. You can use the `WHERE` clause to either filter the result of the FROM clause in a `SELECT` statement or specify which rows to operate on in an `UPDATE`, `MERGE`, or `DELETE` statement.
It can also be used in special cases when working with conditions in [`DEFINE FUNCTION`](https://surrealdb.com/docs/reference/query-language/statements/define/function) statements or when asserting access control in [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) & [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statements.
##  Syntax[](https://surrealdb.com/docs/reference/query-language/clauses/where#syntax)
Clause Syntax

```syntax
STATEMENT
    [WHERE condition;]

```

##  Conditional record selection[](https://surrealdb.com/docs/reference/query-language/clauses/where#conditional-record-selection)
The most common use case for the `WHERE` clause is to filter the result of the `SELECT` statement. It is particularly useful when you want to select a subset of records from a table based on a condition.

```surql
SELECT @fields FROM <TABLE_NAME> WHERE <CONDITION> = <VALUE>;
```

When fetching records from a table, the `WHERE` clause is used to filter the records that are returned.
##  Conditional record alteration[](https://surrealdb.com/docs/reference/query-language/clauses/where#conditional-record-alteration)
The `WHERE` clause can also be used to specify which records to operate on in an `UPDATE`, `MERGE`, or `DELETE` statement.

```surql
UPDATE [TABLE_NAME] SET [FIELDS] WHERE [CONDITION] = [VALUE];
```

##  Setting conditions in `DEFINE FUNCTION` statements[](https://surrealdb.com/docs/reference/query-language/clauses/where#setting-conditions-in-define-function-statements)

```surql
-- Define a function that checks if a relation exists between two nodes
DEFINE FUNCTION fn::relation_exists(
	$in: record,
	$tb: string,
	$out: record
) {
	-- Check if a relation exists between the two nodes.
	LET $results = SELECT VALUE id FROM type::table($tb) WHERE in = $in
	  AND out = $out;
	-- Return true if a relation exists, false otherwise
    RETURN array::len($results) > 0;
};
```

##  Setting permissions conditions in `DEFINE TABLE` statements [](https://surrealdb.com/docs/reference/query-language/clauses/where#setting-permissions-conditions-in-define-table-statements)
The `WHERE` clause can be used to specify the conditions for the permissions of a table and based on the conditions, the permissions are applied to the table CRUD operations.

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

```surql
-- Define a relation table, and constrain the type of relation which can be stored
DEFINE TABLE assigned_to SCHEMAFULL TYPE RELATION IN tag OUT sticky
    PERMISSIONS
        FOR create, select, update, delete
            WHERE in.owner == $auth.id AND out.author == $auth.id;
```
