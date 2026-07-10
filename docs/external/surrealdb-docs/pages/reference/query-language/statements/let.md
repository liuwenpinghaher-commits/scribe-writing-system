---
title: "https://surrealdb.com/docs/reference/query-language/statements/let"
url: "https://surrealdb.com/docs/reference/query-language/statements/let"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/let

Source: https://surrealdb.com/docs/reference/query-language/statements/let

The `LET` statement allows you to create parameters to store any value, including the results of queries or the outputs of expressions. These parameters can then be referenced throughout your SurrealQL code, making your queries more dynamic and reusable.
##  Syntax[](https://surrealdb.com/docs/reference/query-language/statements/let#syntax)
The syntax for the `LET` statement is straightforward. The parameter name is prefixed with a `$` symbol.
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
LET $parameter [: @type_name] = @value;
```

LET$@parameter:@type_name=@value;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/let#example-usage)
###  Basic parameter assignment[](https://surrealdb.com/docs/reference/query-language/statements/let#basic-parameter-assignment)
You can use the `LET` statement to store simple values or query results. For example, storing a string value and then using it in a `CREATE` statement:

```surql
-- Define the parameter
LET $name = "tobie";
-- Use the parameter
CREATE person SET name = $name;
```

###  Storing query results[](https://surrealdb.com/docs/reference/query-language/statements/let#storing-query-results)
The `LET` statement is also useful for storing the results of a query, which can then be used in subsequent operations:

```surql
-- Define the parameter
LET $adults = SELECT * FROM person WHERE age > 18;
-- Use the parameter
UPDATE $adults SET adult = true;
```

###  Conditional logic with `IF ELSE`[](https://surrealdb.com/docs/reference/query-language/statements/let#conditional-logic-with-if-else)
SurrealQL allows you to define parameters based on conditional logic using `IF ELSE` statements:

```surql
LET $num = 10;

LET $num_type =
         IF type::is_int($num)     { "integer" }
    ELSE IF type::is_decimal($num) { "decimal" }
    ELSE IF type::is_float($num)   { "float"   };

RETURN $num_type;
-- 'integer'
```

##  Anonymous functions[](https://surrealdb.com/docs/reference/query-language/statements/let#anonymous-functions)
You can define anonymous functions also known as closures using the `LET` statement. These functions can be used to encapsulate reusable logic and can be called from within your queries. Learn more about [anonymous functions](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) in the Data model section.
##  Pre-defined and protected parameters[](https://surrealdb.com/docs/reference/query-language/statements/let#pre-defined-and-protected-parameters)
SurrealDB comes with [pre-defined parameters](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters) that are accessible in any context. However, parameters created using `LET` are not accessible within the scope of these pre-defined parameters.
Furthermore, some pre-defined parameters are protected and cannot be overwritten using `LET`:

```surql
LET $before = "Before!";

-- Returns ["Before!"];
RETURN $before;

-- Returns the `person` records before deletion
DELETE person RETURN $before;

-- Returns "Before!" again
RETURN $before;
```

Attempting to redefine protected parameters will result in an error:

```surql
LET $auth = 1;
LET $session = 10;
```

Output

```surql
-------- Query 1 --------

"'auth' is a protected variable and cannot be set"

-------- Query 2 --------

"'session' is a protected variable and cannot be set"
```

##  Typed LET statements[](https://surrealdb.com/docs/reference/query-language/statements/let#typed-let-statements)
Type safety in a `LET` statement can be ensured by adding a `:` (a colon) and the type name after the `LET` keyword.

```surql
LET $number: int = "9";
```

Output

```surql
"Tried to set `$number`, but couldn't coerce value: Expected `int` but found `'9'`"
```

###  Typed literal statements[](https://surrealdb.com/docs/reference/query-language/statements/let#typed-literal-statements)
Multiple possible types can be specified in a `LET` statement by adding a `|` (vertical bar) in between each possible type.

```surql
LET $number: int | string = "9";
```

Even complex types such as objects can be included in a typed `LET` statement.

```surql
LET $error_info: 
  string | { error: string } = 
  { 
    error: "Something went wrong plz help" 
  };
```

For more information on this pattern, see the page on [literals](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals).
##  Conclusion[](https://surrealdb.com/docs/reference/query-language/statements/let#conclusion)
The `LET` statement in SurrealDB is versatile, allowing you to store values, results from subqueries, and even define anonymous functions. Understanding how to use `LET` effectively can help you write more concise, readable, and maintainable queries.
