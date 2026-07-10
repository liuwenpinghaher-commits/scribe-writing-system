---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/config"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/config"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/config

Source: https://surrealdb.com/docs/reference/query-language/statements/define/config

The `DEFINE CONFIG` statement allows you to set external configurations on your database. It can be used to configure API middleware and permissions, or to configure how the database's tables and functions are exposed via the GraphQL API.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/config#requirements)
  * •
You **must** be authenticated as a **root** , **namespace** , or **database** user before you can use the `DEFINE CONFIG GRAPHQL` statement.
  * •
You **must** select your **namespace** and **database** before you can use the `DEFINE CONFIG GRAPHQL` statement.
  * •
You **must** define at least one table in your database for the GraphQL API to function.
  * •
You **must** have started the SurrealDB instance with GraphQL enabled.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/config#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```surql
DEFINE CONFIG [ OVERWRITE | IF NOT EXISTS ]
  ( API
      [ MIDDLEWARE @function(...), ... ]
      PERMISSIONS [ NONE | FULL | @expression ]
  | GRAPHQL
      TABLES [ AUTO | NONE | INCLUDE @table,
        ... | EXCLUDE @table,
        ... ]
      FUNCTIONS [ AUTO | NONE | INCLUDE @function,
        ... | EXCLUDE @function,
        ... ]
      [ DEPTH @integer ]
      [ COMPLEXITY @integer ]
      [ INTROSPECTION NONE ]
  | DEFAULT
      NAMESPACE @namespace
      DATABASE @database
  )
```

DEFINECONFIGOVERWRITEIFNOTEXISTSAPIMIDDLEWARE@expression, ..PERMISSIONSNONEFULL@expressionGRAPHQLAUTONONETABLESAUTONONEINCLUDEtable1, table2, ...FUNCTIONSAUTONONEINCLUDE[function1, function2, ...]EXCLUDE[function1, function2, ...]
##  DEFINE CONFIG API[](https://surrealdb.com/docs/reference/query-language/statements/define/config#define-config-api)
The `DEFINE CONFIG API` statement can be used to set middleware and permissions in order to alter the behaviour of the database for guest and [record users](https://surrealdb.com/docs/reference/query-language/statements/define/access/record). This middleware can be used in cases such as rate limiting on the query language and setting how many resources a client can read or alter at a time.
`DEFINE CONFIG API` is often used in conjunction with a [flag](https://surrealdb.com/docs/learn/security/authorization/capabilities) or [environment variable](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables) to disable arbitrary queries, thereby forcing record and anonymous users to interact with the database via API endpoints alone.
The following is an example of a `DEFINE CONFIG` statement that includes a timeout and a single header in the responses of all API endpoints.

```surql
DEFINE CONFIG API
    MIDDLEWARE 
        api::timeout(10s),
        api::res::headers({
            'Access-Control-Allow-Origin': '*'
        });
```

To set the actual API endpoints and their middleware, a `DEFINE API` statement is used for each endpoint. For more details and examples, see the pages for [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) and [API functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api).
The behaviour of API endpoints can be tested using the `api::invoke` method, or through a regular HTTP call to the endpoint that [includes the namespace and database name](https://surrealdb.com/docs/reference/rest-api/http-protocol#custom-endpoint-at-apinsdbendpoint).
This next example uses `DEFINE CONFIG` to set a single response header, followed by two endpoints that return different output.

```surql
DEFINE CONFIG API
    MIDDLEWARE 
        api::res::headers({
            'Access-Control-Allow-Origin': '*'
        });

DEFINE API "/test" FOR get THEN {};
DEFINE API "/test2" FOR get THEN {
    {
        body: {
            some: "data"
        }
    }
};

api::invoke("/test");
api::invoke("/test2");
```

The query shows that the endpoints return a combination of the `DEFINE CONFIG` middleware and the response object set in the `DEFINE API` statements.

```surql
-------- Query --------

{
  body: NONE,
  context: {},
	headers: {
		"access-control-allow-origin": '*'
	},
	status: 200
}

-------- Query --------

{
	body: {
		some: 'data'
	},
  context: {},
	headers: {
		"access-control-allow-origin": '*'
	},
	status: 200
}
```

Note that the middleware and permissions inside individual `DEFINE API` statements will override the middleware in a `DEFINE CONFIG API` statement. In the following example, the default `10s` timeout is set to a single microsecond for the `"/test"` endpoint, giving the intended query no time to complete.

```surql
DEFINE CONFIG API
    MIDDLEWARE 
        api::timeout(10s),
        api::res::headers({
            'Access-Control-Allow-Origin': '*'
        });

DEFINE API OVERWRITE "/test"
    FOR get 
        MIDDLEWARE
            api::timeout(1µs)
        THEN {
            RETURN {
                status: 200,
                body: { 
                    data: (SELECT * FROM person),
                    however: "This will probably never return because
                      the timeout is 1 microsecond"
                }
            };
        };

api::invoke("/test");
```

Output

```surql
'The query was not executed because it exceeded the timeout: 1µs'
```

##  DEFINE CONFIG GRAPHQL[](https://surrealdb.com/docs/reference/query-language/statements/define/config#define-config-graphql)
The configuration set using the `DEFINE CONFIG GRAPHQL` is essential for enabling GraphQL functionality in your database, specifying which tables and functions should be included or excluded from the GraphQL schema.
The GraphQL configuration defined using this statement dictates how clients interact with your database through GraphQL queries and mutations.
###  Important notes[](https://surrealdb.com/docs/reference/query-language/statements/define/config#important-notes)
  * •
The `DEFINE CONFIG GRAPHQL` statement **must** be executed before any GraphQL queries can be made.
  * •
If you attempt to use the GraphQL API without defining the configuration, you will receive a `NotConfigured` error.
  * •
If no tables are defined in the database, you will receive an error stating "No tables found in database" when attempting to use the GraphQL API.

###  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-usage)

```surql
-- Define GraphQL configuration
DEFINE CONFIG GRAPHQL AUTO;
```

The above statement will automatically include all tables and functions in the GraphQL schema, and show up in the database as `DEFINE CONFIG GRAPHQL TABLES AUTO FUNCTIONS AUTO`.
###  `TABLES` configuration[](https://surrealdb.com/docs/reference/query-language/statements/define/config#tables-configuration)
The `TABLES` clause in the `DEFINE CONFIG GRAPHQL` statement specifies how tables are exposed via GraphQL. There are four options for the `TABLES` configuration:
  * •
`AUTO`: Automatically include all tables in the GraphQL schema.
  * •
`NONE`: Do not include any tables in the GraphQL schema.
  * •
`INCLUDE`: Specify a list of tables to include in the GraphQL schema.
  * •
`EXCLUDE`: Specify a list of tables to exclude from the GraphQL schema.

####  `AUTO`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#auto)
When you specify `TABLES AUTO`, all tables in the database are automatically included in the GraphQL schema.

```surql
DEFINE CONFIG GRAPHQL TABLES AUTO;
```

####  `NONE`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#none)
When you specify `TABLES NONE`, no tables are included in the GraphQL schema.

```surql
DEFINE CONFIG GRAPHQL TABLES NONE;
```

####  `INCLUDE`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#include)
You can specify a list of tables to include in the GraphQL schema using the `INCLUDE` clause. The list of tables is specified as a comma-separated list without brackets.

```surql
DEFINE CONFIG GRAPHQL TABLES INCLUDE user, post, comment;
```

Note
The `EXCLUDE` option for `TABLES` is currently not implemented.
###  `FUNCTIONS` configuration[](https://surrealdb.com/docs/reference/query-language/statements/define/config#functions-configuration)
The `FUNCTIONS` clause in the `DEFINE CONFIG GRAPHQL` statement specifies how functions are exposed via GraphQL. There are four options for the `FUNCTIONS` configuration:
  * •
`AUTO`: Automatically include all functions in the GraphQL schema.
  * •
`NONE`: Do not include any functions in the GraphQL schema.
  * •
`INCLUDE`: Specify a list of functions to include in the GraphQL schema.
  * •
`EXCLUDE`: Specify a list of functions to exclude from the GraphQL schema.

####  `AUTO`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#auto-1)
When you specify `FUNCTIONS AUTO`, all functions in the database are automatically included in the GraphQL schema.

```surql
DEFINE CONFIG GRAPHQL FUNCTIONS AUTO;
```

####  `NONE`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#none-1)
When you specify `FUNCTIONS NONE`, no functions are included in the GraphQL schema.

```surql
DEFINE CONFIG GRAPHQL FUNCTIONS NONE;
```

####  `INCLUDE`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#include-1)
You can specify a list of functions to include in the GraphQL schema using the `INCLUDE` clause. The list of functions is specified as a comma-separated list enclosed in square brackets `[]`.

```surql
DEFINE CONFIG GRAPHQL FUNCTIONS INCLUDE [getUser,
  listPosts,
  searchComments];
```

####  `EXCLUDE`[](https://surrealdb.com/docs/reference/query-language/statements/define/config#exclude)
You can specify a list of functions to exclude from the GraphQL schema using the `EXCLUDE` clause. The list of functions is specified as a comma-separated list enclosed in square brackets `[]`.

```surql
DEFINE CONFIG GRAPHQL FUNCTIONS EXCLUDE [debugFunction, testFunction];
```

###  Using the `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/config#using-the-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define the GraphQL configuration only if it does not already exist. This is useful when you want to ensure that the configuration is only created if it does not already exist, preventing errors due to duplicate definitions.

```surql
-- Define GraphQL configuration only if it does not already exist
DEFINE CONFIG GRAPHQL IF NOT EXISTS TABLES AUTO FUNCTIONS AUTO;
```

###  Using the `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/config#using-the-overwrite-clause)
The `OVERWRITE` clause can be used to redefine the GraphQL configuration, overwriting any existing configuration. This is useful when you want to update or modify the existing GraphQL configuration.

```surql
-- Redefine GraphQL configuration, overwriting existing configuration
DEFINE CONFIG OVERWRITE GRAPHQL TABLES INCLUDE user,
  post FUNCTIONS NONE;
```

###  Examples[](https://surrealdb.com/docs/reference/query-language/statements/define/config#examples)
####  Example 1: Include specific tables and functions[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-1-include-specific-tables-and-functions)
This example defines a GraphQL configuration that includes specific tables and functions.

```surql
DEFINE CONFIG GRAPHQL TABLES INCLUDE user,
  post FUNCTIONS INCLUDE [getUser,
  listPosts];
```

####  Example 2: Automatically include all tables and functions[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-2-automatically-include-all-tables-and-functions)
This example defines a GraphQL configuration that automatically includes all tables and functions.

```surql
DEFINE CONFIG GRAPHQL TABLES AUTO FUNCTIONS AUTO;
```

####  Example 3: Exclude specific functions[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-3-exclude-specific-functions)
This example defines a GraphQL configuration that includes all functions except specific ones.

```surql
DEFINE CONFIG GRAPHQL FUNCTIONS EXCLUDE [debugFunction, testFunction];
```

###  Error handling[](https://surrealdb.com/docs/reference/query-language/statements/define/config#error-handling)
####  NotConfigured Error[](https://surrealdb.com/docs/reference/query-language/statements/define/config#notconfigured-error)
If you attempt to access the GraphQL endpoint without defining the GraphQL configuration, you will receive a `NotConfigured` error.
Error Response

```surql
{
  "error": "NotConfigured: GraphQL endpoint is not configured. Please
    define the GraphQL configuration using DEFINE CONFIG GRAPHQL."
}
```

Execute the `DEFINE CONFIG GRAPHQL` statement to define the GraphQL configuration.

```surql
-- Define GraphQL configuration
DEFINE CONFIG GRAPHQL TABLES AUTO FUNCTIONS AUTO;
```

####  "No tables found" error[](https://surrealdb.com/docs/reference/query-language/statements/define/config#no-tables-found-error)
If you have defined the GraphQL configuration but no tables are defined in the database, you will receive an error stating "No tables found in database" when attempting to use the GraphQL API. You can fix this by defining at least one table in your database using the [`DEFINE TABLE`](https://surrealdb.com/docs/reference/query-language/statements/define/table) statement.
Error Response

```surql
{
  "error": "No tables found in database. Please define at least one
    table to use the GraphQL API."
}
```

**Solution** : Define at least one table in your database.

```surql
DEFINE TABLE foo SCHEMAFUL;
DEFINE FIELD val ON foo TYPE int;
CREATE foo:1 SET val = 42;
```

###  Authentication errors when accessing data via GraphQL[](https://surrealdb.com/docs/reference/query-language/statements/define/config#authentication-errors-when-accessing-data-via-graphql)
**Cause** : Insufficient permissions or incorrect authentication credentials.
**Solution** : Ensure you are authenticated as a user with the necessary permissions and that the permissions on tables and fields are correctly configured.
####  Authentication and permissions[](https://surrealdb.com/docs/reference/query-language/statements/define/config#authentication-and-permissions)
  * •
The GraphQL API respects SurrealDB's authentication and permission model.
  * •
You must authenticate using the appropriate credentials to access data via GraphQL.
  * •
Permissions set on tables and fields will affect the data accessible through the GraphQL API.
  * •
If you attempt to access data without sufficient permissions, you will receive an authentication error.

####  Example: Basic authentication[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-basic-authentication)

```surql
-- Define a user with access permissions
DEFINE USER my_user ON DATABASE PASSWORD 'my_password';
DEFINE ACCESS user ON DATABASE TYPE RECORD
  SIGNUP ( CREATE user SET email = $email,
    pass = crypto::argon2::generate($pass) )
  SIGNIN ( SELECT * FROM user WHERE email = $email
    AND crypto::argon2::compare(pass, $pass) )
  DURATION FOR SESSION 60s, FOR TOKEN 1d;

-- Define a table with permissions
DEFINE TABLE foo SCHEMAFUL PERMISSIONS FOR select
  WHERE $auth.email = email;
DEFINE FIELD email ON foo TYPE string;
DEFINE FIELD val ON foo TYPE int;

-- Insert data
CREATE foo:1 SET val = 42, email = "user@example.com";
CREATE foo:2 SET val = 43, email = "other@example.com";
```

When querying the GraphQL API as `user@example.com`, only the records where `email = "user@example.com"` will be accessible due to the permissions set.
###  Examples[](https://surrealdb.com/docs/reference/query-language/statements/define/config#examples-1)
####  Example 1: Defining GraphQL configuration and fetching data[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-1-defining-graphql-configuration-and-fetching-data)

```surql
-- Define GraphQL configuration to include all tables automatically
DEFINE CONFIG GRAPHQL TABLES AUTO;

-- Define a table and insert data
DEFINE TABLE foo SCHEMAFUL;
DEFINE FIELD val ON foo TYPE int;
CREATE foo:1 SET val = 42;
CREATE foo:2 SET val = 43;
```

Now, you can fetch data via GraphQL:

```graphql
query {
  foo {
    id
    val
  }
}
```

**Response:**

```json
{
  "data": {
    "foo": [
      {
        "id": "foo:1",
        "val": 42
      },
      {
        "id": "foo:2",
        "val": 43
      }
    ]
  }
}
```

####  Example 2: Including Specific Tables[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-2-including-specific-tables)

```surql
-- Define GraphQL configuration to include only specific tables
DEFINE CONFIG OVERWRITE GRAPHQL TABLES INCLUDE foo;
```

When querying the GraphQL schema, only the included tables will be available.
####  Example 3: Using limit, start, order, and filter in GraphQL queries[](https://surrealdb.com/docs/reference/query-language/statements/define/config#example-3-using-limit-start-order-and-filter-in-graphql-queries)
You can use `limit`, `start`, `order`, and `filter` in your GraphQL queries to control the data returned.
#####  Limit[](https://surrealdb.com/docs/reference/query-language/statements/define/config#limit)

```graphql
query {
  foo(limit: 1) {
    id
    val
  }
}
```

#####  Start[](https://surrealdb.com/docs/reference/query-language/statements/define/config#start)

```graphql
query {
  foo(start: 1) {
    id
    val
  }
}
```

#####  Order[](https://surrealdb.com/docs/reference/query-language/statements/define/config#order)

```graphql
query {
  foo(order: { desc: val }) {
    id
    val
  }
}
```

#####  Filter[](https://surrealdb.com/docs/reference/query-language/statements/define/config#filter)

```graphql
query {
  foo(filter: { val: { eq: 42 } }) {
    id
    val
  }
}
```

###  More information[](https://surrealdb.com/docs/reference/query-language/statements/define/config#more-information)
The `DEFINE CONFIG GRAPHQL` statement is essential for enabling and configuring the GraphQL API in SurrealDB. By specifying which tables and functions are included or excluded, you can fine-tune the GraphQL schema to match your application's needs.
  * •
**Authentication** : Ensure you are authenticated with the appropriate credentials.
  * •
**Permissions** : Set up permissions on tables and fields to control access via GraphQL.
  * •
**Configuration** : The GraphQL configuration must be defined before using the GraphQL API.
  * •
**Error Handling** : Be aware of possible errors when the configuration is missing or incomplete.

Important
Always ensure you have the necessary permissions and have selected the appropriate namespace and database before using the `DEFINE CONFIG GRAPHQL` statement.
##  Summary[](https://surrealdb.com/docs/reference/query-language/statements/define/config#summary)
  * •
Use `DEFINE CONFIG GRAPHQL` to enable and configure the GraphQL API.
  * •
Define your tables and set up permissions to control data access.
  * •
Use the `OVERWRITE` and `IF NOT EXISTS` clauses as needed to manage your configuration.
  * •
Always authenticate with appropriate credentials when accessing the GraphQL API.
  * •
Utilize GraphQL query features like `limit`, `start`, `order`, and `filter` to control the data returned.

By following these guidelines, you can effectively use the `DEFINE CONFIG GRAPHQL` statement to configure and interact with your SurrealDB database via GraphQL.
