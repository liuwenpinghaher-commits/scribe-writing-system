---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/function"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/function"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/function

Source: https://surrealdb.com/docs/reference/query-language/statements/define/function

The `DEFINE FUNCTION` statement allows you to define custom functions that can be reused throughout a database. When using the `DEFINE FUNCTION` statement, you can define a function that takes one or more arguments and returns a value. You can then call this function in other SurrealQL statements.
Functions can be used to encapsulate logic that you want to reuse in multiple queries. They can also be used to simplify complex queries by breaking them down into smaller, more manageable pieces. They are particularly useful when you have a complex query that you need to run multiple times with different arguments.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/function#requirements)
  * •
You must be authenticated as a root owner or editor, namespace owner or editor, or database owner or editor before you can use the `DEFINE FUNCTION` statement.
  * •
[You must select your namespace and database](https://surrealdb.com/docs/reference/query-language/statements/use) before you can use the `DEFINE FUNCTION` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/function#statement-syntax)
SurrealQL Syntax

```syntax
DEFINE FUNCTION [ OVERWRITE | IF NOT EXISTS ] fn::@name
  ( [ @argument: @type ... ] ) [ -> @type ] {
	[ @query ... ]
	[ RETURN @returned ]
} [ COMMENT @string ] [ PERMISSIONS [ NONE | FULL | WHERE @condition]]
```

##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/function#example-usage)
Below shows how you can define a custom function using the `DEFINE FUNCTION` statement, and how to call it.

```surql
-- It is necessary to prefix the name of your function with "fn::"
-- This indicates that it's a custom function
DEFINE FUNCTION fn::greet($name: string) {
	"Hello, " + $name + "!"
};

-- Returns: "Hello, Tobie!"
RETURN fn::greet("Tobie");
```

To showcase a slightly more complex custom function, this will check if a relation between two nodes exists:

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

##  Optional arguments[](https://surrealdb.com/docs/reference/query-language/statements/define/function#optional-arguments)
If one or more ending arguments have the `option` type, they can be omitted when you run the invoke the function.

```surql
DEFINE FUNCTION fn::last_option($required: number, $optional: option<number>) {
	RETURN {
		required_present: type::is_number($required),
		optional_present: type::is_number($optional),
	}
};

RETURN fn::last_option(1, 2);
-- { required_present: true, optional_present: true }

RETURN fn::last_option(1);
-- { required_present: true, optional_present: false };
```

##  Adding a return value[](https://surrealdb.com/docs/reference/query-language/statements/define/function#adding-a-return-value)
Optionally, the return value of a function can be specified.
For a function that is infallible, a return value is mostly for the sake of readability.

```surql
DEFINE FUNCTION fn::greet($name: string) -> string {
	"Hello, " + $name + "!"
};
```

For a function that is not infallible, specifying a return value can be used to customise error output.

```surql
// Arguments must be of type 'number'
DEFINE FUNCTION fn::combine($one: number, $two: number) -> number {
  $one + $two
};

// Accepts any value but expects the return type 'number'
DEFINE FUNCTION fn::combine_any($one: any, $two: any) -> number {
  $one + $two
};

fn::combine("one", "two");
fn::combine_any("one", "two");
```

While both of these return an error, the output of the second function happens only at the point that it attempts to return the combined arguments to the function.
Output

```surql
-------- Query 1 --------
"Expected `number` but found `'one'`"

-------- Query 2 --------
"Couldn't coerce return value from function `fn::combine_any`: Expected `number` but found `'onetwo'`"
```

The return value of a function can even be a [literal type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals). The following function returns such a type by either returning an object of a certain structure, or a string. In this case this output is used in case an application prefers to return an error as a simple string instead of [throwing](https://surrealdb.com/docs/reference/query-language/statements/throw) an error or returning a NONE value.

```surql
DEFINE FUNCTION fn::age_and_name($user_num: int) -> { age: int, name: string } | string {
    LET $user = type::record("user", $user_num);
    IF $user.exists() {
        $user.{ name, age }
    } ELSE {
        { "Couldn't find user number " + <string>$user_num + "!" }        
    }
};

CREATE user:1 SET name = "Billy", age = 15;

fn::age_and_name(1);
fn::age_and_name(2);
```

Output

```surql
-------- Query 1 --------

{ age: 15, name: 'Billy' }

-------- Query 2 --------

"Couldn't find user number 2!"
```

##  Recursive functions[](https://surrealdb.com/docs/reference/query-language/statements/define/function#recursive-functions)
A function is able to call itself, making it a recursive function. One example of a recursive function is the one below which creates a relation between each and every record passed in.
Consider a situation in which seven person records exist. First, `person:1` will need to be related to the rest of the `person` records, after which there are no more relations to create for it. Following this, the relations for `person:2` and all the other records except for `person:1` will need to be created, and so on.
This can be done in a recursive function by creating all the relations between the first record and the remaining records, after which the function calls itself by passing in all the records except the first. This continues until the function receives less than two records, in which case it ceases calling itself by doing nothing, thereby ending the recursion.

```surql
DEFINE FUNCTION fn::relate_all($records: array<record>) {
  IF $records.len() < 2 {
      -- Don't do anything, ending the recursion
  }  ELSE {
      LET $first = $records[0];
      LET $remainder = $records[1..];
      FOR $counterpart IN $remainder {
          RELATE $first->to->$counterpart;
      };
      fn::relate_all($remainder);
  }
};

CREATE |person:1..8|;

fn::relate_all(SELECT VALUE id FROM person);

SELECT id, ->to->? FROM person;
```

The last query [can be viewed graphically](https://surrealdb.com/blog/whats-new-in-surrealist-3-2#graph-visualisation) inside Surrealist, leading to an output showing a seven-pointed star.
![An image of a seven-pointed star created visually by relating seven records to each other and displayed inside Surrealist's graph view.](https://surrealdb.com/docs/reference/query-language/statements/define/~/assets/img/image/recursive_star.png)
##  Permissions[](https://surrealdb.com/docs/reference/query-language/statements/define/function#permissions)
You can set the permissions for a custom function using the `PERMISSIONS` clause. The `PERMISSIONS` clause is mostly used to restrict who can access a function and what data they can access. It can be set to `NONE`, `FULL`, or `WHERE @condition`.
  * •
`FULL`: When Full permissions are granted [record](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users) users have access to the function. This is the default permission when not specified.
  * •
`NONE`: When this permission is granted, [record](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users) users have no access to the defined function.
  * •
`WHERE @condition`: Permissions are granted to the function based on the specified condition.

Note
The examples below use the [`Surreal Deal Store`](https://surrealdb.com/docs/start#surreal-deal-store---there-is-a-lot-in-store-for-you-recommended) dataset.
###  Using the `FULL` permission[](https://surrealdb.com/docs/reference/query-language/statements/define/function#using-the-full-permission)
The `FULL` permission grants all users access to the function. The following example defines a function that fetches all products from the `product` table and grants the function full permissions to access the data to all users.
###  Using the `NONE` permission[](https://surrealdb.com/docs/reference/query-language/statements/define/function#using-the-none-permission)
The `NONE` permission denies all [record](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users) users access to the function. The following example defines a function that fetches all products from the `product` table

```surql
-- Define a function that fetches all expiration years from the payment_details table and denies access to all none-admin users
DEFINE FUNCTION fn::fetchAllPaymentDetails() {
	SELECT stored_cards.expiry_year FROM payment_details LIMIT 5
} PERMISSIONS NONE;

RETURN fn::fetchAllPaymentDetails();
```

###  Using the `WHERE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/function#using-the-where-clause)
The `WHERE` clause allows you to specify a condition that determines the permissions granted to the function. The condition must evaluate to a boolean value. If the condition evaluates to `true`, the function is granted permissions. If the condition evaluates to `false`, the function is not granted permissions.

```surql
-- Define a function that fetches all products with the condition that only admin users can access it
DEFINE FUNCTION fn::fetchAllProducts() {
	 SELECT * FROM product LIMIT 10
} PERMISSIONS WHERE $auth.admin = true;
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/function#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a function only if it does not already exist. You should use the `IF NOT EXISTS` clause when defining a function in SurrealDB if you want to ensure that the function is only created if it does not already exist. If the function already exists, the `DEFINE FUNCTION` statement will return an error.
It's particularly useful when you want to safely attempt to define a function without manually checking its existence first.
On the other hand, you should not use the `IF NOT EXISTS` clause when you want to ensure that the function definition is updated regardless of whether it already exists. In such cases, you might prefer using the `OVERWRITE` clause, which allows you to define a function and overwrite an existing one if it already exists, ensuring that the latest version of the function definition is always in use

```surql
-- Create a FUNCTION if it does not already exist
DEFINE FUNCTION IF NOT EXISTS fn::example() {};
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/function#using-overwrite-clause)
The `OVERWRITE` clause can be used to define a function and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing user definition. If the user already exists, the `DEFINE FUNCTION` statement will overwrite the existing definition with the new one.

```surql
-- Create a FUNCTION and overwrite if it already exists
DEFINE FUNCTION OVERWRITE fn::example() {};
```

##  Functions as custom middleware[](https://surrealdb.com/docs/reference/query-language/statements/define/function#functions-as-custom-middleware)
Available since: v3.0.0
A `DEFINE FUNCTION` statement can be used to define a function for use as custom middleware. For more details on defining a custom function in this manner, see the [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api#custom-middleware) page.
