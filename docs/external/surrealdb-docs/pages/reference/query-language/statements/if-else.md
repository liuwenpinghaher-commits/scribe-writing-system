---
title: "https://surrealdb.com/docs/reference/query-language/statements/if-else"
url: "https://surrealdb.com/docs/reference/query-language/statements/if-else"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/if-else

Source: https://surrealdb.com/docs/reference/query-language/statements/if-else

The `IF ELSE` statement can be used as a main statement, or within a parent statement, to return a value depending on whether a condition, or a series of conditions match. The statement allows for multiple `ELSE IF` expressions, and a final `ELSE` expression, with no limit to the number of `ELSE IF` conditional expressions.
Note
As [THROW](https://surrealdb.com/docs/reference/query-language/statements/throw), [CONTINUE](https://surrealdb.com/docs/reference/query-language/statements/continue), and [BREAK](https://surrealdb.com/docs/reference/query-language/statements/break) do not return an expression, they must be inside a separate code block inside an `IF ELSE` statement.
An `IF ELSE` syntax uses `{}` to open up a code block on each condition check which will be run when it evaluates as [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
SyntaxRailroad Diagram
Modern syntax

```surql
IF @condition { @expression; .. }
   [ ELSE IF @condition { @expression; .. } ] ...
   [ ELSE { @expression; .. } ]
```

IF@condition{@expression; ..}ELSEIF@condition{@expression; ..}ELSE{@expression; ..}
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/if-else#example-usage)
###  Basic usage[](https://surrealdb.com/docs/reference/query-language/statements/if-else#basic-usage)
The following queries show example usage of this statement.
The smallest possible `IF THEN` statement simply does something when a condition is true, and nothing otherwise.

```surql
IF 9 = 9 { 'Nine is indeed nine' };
```

As the last line of a scope is its return value, the `RETURN` keyword can also be placed before the entire `IF THEN` statement. This is particularly convenient in long `IF ELSE` chains to avoid using the `RETURN` keyword at the end of every check for a condition.

```surql
LET $num = 100;

RETURN IF $num < 0 {
    "Negative"
} ELSE IF $num = 0 {
    "Zero"
} ELSE IF $num = 13 {
    "Thirteen"
} ELSE {
    "Positive uninteresting number"
};
```

The `RETURN` keyword can even be omitted, as the output at each point is the output of the entire expression if evaluated as truthy.

```surql
LET $num = 100;

IF $num < 0 {
    "Negative"
} ELSE IF $num = 0 {
    "Zero"
} ELSE IF $num = 13 {
    "Thirteen"
} ELSE {
    "Positive uninteresting number"
};
```

The `THROW` keyword inside `{}` braces can be used to break out of an `IF ELSE` statement early.

```surql
LET $badly_formatted_datetime = "2024-04TT08:08:08Z";

IF !type::is_datetime($badly_formatted_datetime) {
    THROW "Whoops, that isn't a real datetime"
};
```

Response

```surql
"An error occurred: Whoops, that isn't a real datetime"
```

`ELSE IF` branches and a final `ELSE` can be added into an `IF ELSE` statement:

```surql
RETURN
    IF $access = "admin" { (SELECT * FROM account) }
    ELSE IF $access = "user"  { (SELECT * FROM $auth.account) }
    ELSE { THROW "Access method hasn't been defined!" };
```

###  Advanced usage[](https://surrealdb.com/docs/reference/query-language/statements/if-else#advanced-usage)
The output of an `IF ELSE` statement can be assigned to a parameter:

```surql
LET $num = 9;

LET $odd_even = 
    IF $num % 2 = 0 { "even" } 
    ELSE { "odd" };
```

If-else statements can also be used as subqueries within other statements.

```surql
UPSERT person SET railcard =
    IF age <= 10 { 'junior' }
    ELSE IF age <= 21 { 'student' }
    ELSE IF age >= 65 { 'senior' }
    ELSE { NULL };
```

You can also have nested conditions:

```surql
IF $access = 'admin'
	{
        CREATE admin_user_event SET 
            time = time::now(),
            info = "Admin user activity registered";
		SELECT * FROM admin_data WHERE access_level = 'full';
	}
ELSE IF $access = 'user'
	{
		IF $auth.role = 'premium'
			{
                CREATE premium_user_event SET 
                    time = time::now(),
                    info = "Premium user activity registered";

				IF $auth.subscription_status = 'active'
					{ SELECT * FROM premium_user_data WHERE active = 1 }
				ELSE IF $auth.subscription_status = 'trial'
					{ SELECT * FROM trial_user_data }
				ELSE
					{ SELECT * FROM basic_user_data }
			}
		ELSE IF $auth.role = 'standard'
			{ SELECT * FROM standard_user_data WHERE region = 'US' }
		ELSE IF $auth.role = 'standard' AND $auth.subscription_status = 'active'
			{ SELECT * FROM standard_user_data WHERE region = 'EU' }
		ELSE
			{ SELECT * FROM unauthorized_user_data }
	}
ELSE
	{ SELECT * FROM unknown_access_data };
```
