---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/api"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/api

Source: https://surrealdb.com/docs/reference/query-language/statements/define/api

Available since: v3.0.0
The `DEFINE API` statements allows a custom endpoint to be created. Each endpoint created by a `DEFINE API` statement is located at the `/api/:namespace/:database/:endpoint_name` path. For example, an endpoint for the path `get_users` for the namespace `my_namespace` and database `my_database` will have the path `/api/my_namespace/my_database/get_users`.
The response is an object with a combination of the following properties:
  * •
`status` - A valid HTTP status code.
  * •
`body` - Any value.
  * •
`headers` - An object of valid header key value pairs. The value of each pair must be a string.
  * •
`context` - An object. 

A defined API has access to a preset parameter called [`$request`](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters#request) which contains the request sent by the caller of the endpoint. The $request parameter may contain values at the following fields: `body`, `headers`, `params`, `method`, `query`, and `context`.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/api#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE API [ OVERWRITE | IF NOT EXISTS ] @endpoint
    [ FOR @HTTP_method, .. ]
    [ MIDDLEWARE @function, .. ]
    [ THEN { @value } ]
    [ PERMISSIONS [ NONE | FULL | @expression ]
```

DEFINEAPIOVERWRITEIFNOTEXISTS@endpointFOR@HTTP_method, ..MIDDLEWARE@function, ..THEN{@value}PERMISSIONSNONEFULL@expression
`DEFINE API` is often used in conjunction with a [capabilities flag](https://surrealdb.com/docs/learn/security/authorization/capabilities) or [environment variable](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables) to disable arbitrary queries, thereby forcing record and anonymous users to interact with the database via API endpoints alone.
##  Quick example[](https://surrealdb.com/docs/reference/query-language/statements/define/api#quick-example)
Defining an API endpoint

```surql
DEFINE API "/test"
    FOR get, post 
        MIDDLEWARE
            api::timeout(1s)
        THEN {
            {
                status: 200,
                body: {
                    request: $request.body,
                    response: "The server works"
                },
                headers: {
                    'last-modified': <string>time::now(),
                    'expires': <string>(time::now() + 4d)
                }
            };
        };
```

An API endpoint can be tested using the [`api::invoke` function](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api), which takes either the path as a single string or the path along with a request body. It can also be tested via [CURL or other means by directly using the endpoint](https://surrealdb.com/docs/reference/rest-api/http-protocol) along with the namespace and database in the headers.

```surql
api::invoke("/test");

api::invoke("/test", {
    body: {
       hi: "please",
        give: "me",
        the: "information"
    }
});
```

Output

```surql
-------- Query --------

{
	body: {
		request: NONE,
		response: 'The server works'
	},
    context: {},
	headers: {
		"access-control-allow-origin": '*',
		expires: '2026-01-24T02:43:50.137321Z',
		"last-modified": '2025-02-20T02:43:50.137326Z'
	},
	status: 200
}

-------- Query --------

{
	body: {
		request: {
			give: 'me',
			hi: 'please',
			the: 'information'
		},
		response: 'The server works'
	},
    context: {},
	headers: {
		"access-control-allow-origin": '*',
		expires: '2025-02-24T02:43:50.137455Z',
		"last-modified": '2026-01-20T02:43:50.137457Z'
	},
	status: 200
}
```

Each HTTP method may appear in at most one `FOR` clause on a `DEFINE API` statement. Overlapping methods — including duplicates inside a comma-separated list — are rejected at define time with a clear error instead of silently routing to only the first matching action.

```surql
-- Error: duplicate `get` across FOR clauses
DEFINE API "/foo"
  FOR get THEN $x
  FOR get THEN $y;
```

##  API paths[](https://surrealdb.com/docs/reference/query-language/statements/define/api#api-paths)
The path of a `DEFINE API` statement can be static, such as `"/test"`, dynamic, or the remainder of a URL.
A dynamic path uses a `:` (colon) followed by a name, which will match on anything passed in at that section of a path.

```surql
DEFINE API OVERWRITE "/test/:anything_goes" FOR get THEN {
    RETURN {
        body: {
            some: "data"
        }
    }
};

api::invoke("/test/this_matches");
api::invoke("/test/same_here");
api::invoke("/test/but/this/wont/match");
```

The first two `api::invoke` calls return the output below, but the third returns nothing as `:anything_goes` only applies to a single path segment.
Output

```surql
{ 
    body: NONE, 
    context: {}, 
    headers: {}, 
    status: 404 
}
```

To match on the remainder of a URL, change the `:` (colon) to a `*` (star).

```surql
DEFINE API OVERWRITE "/test/*anything_goes" FOR get THEN {
    RETURN {
        body: {
            some: "data"
        }
    }
};

api::invoke("/test/this_matches");
api::invoke("/test/same_here");
api::invoke("/test/works/with/multiple/paths/now");
```

All three `api::invoke` calls will now show the following output.
Output

```surql
{
	body: {
		some: 'data'
	},
	context: {},
	headers: {},
	status: 200
};
```

##  Custom middleware[](https://surrealdb.com/docs/reference/query-language/statements/define/api#custom-middleware)
Custom middleware can be used in addition to the functions listed above.
A custom middleware function is defined in the same way as any other [user-defined function](https://surrealdb.com/docs/reference/query-language/statements/define/function).
Each such function automatically receives two arguments:
  * •
An object that will contain the user request.
  * •
A function (a closure) that can be called to get the current state of the response to be returned.

The parameter names `$req` for the first and `$next` for the second are commonly used, though the actual parameter names are of no consequence.
The output of such a function must be an `object`. This is used to pass the response on to the next middleware function, or on to the actual response if there is no middleware left to call.

```surql
DEFINE FUNCTION fn::middleware_function($req: object,
  $next: function) -> object {};
```

These functions can take additional arguments on top of the required two.

```surql
DEFINE FUNCTION fn::middleware_function($req: object,
  $next: function,
  $some_string: string) -> object {};
```

###  Custom middleware examples[](https://surrealdb.com/docs/reference/query-language/statements/define/api#custom-middleware-examples)
Here is an example of an API endpoint without any middleware.

```surql
DEFINE API "/custom_response"
    FOR get
        THEN {
            {
                status: 200,
                body: {
                    num: 1
                }
            };
        };
```

Calling `api::invoke("/custom_response")` will return the following.

```surql
{
	body: {
		num: 1
	},
	context: {},
	headers: {},
	status: 200
};
```

The next example adds a middleware function that does the following:
  * •
Calls the `$next` closure on the `$req` object. This will return the value after `THEN`: the original return value.
  * •
Returns an object in which the `num` field inside `body` is increased by one.

```surql
DEFINE FUNCTION fn::increment_num($req: object,
  $next: function) -> object {
    LET $res = $next($req);
    $res + { body: { num: $res.body.num + 1 } }
};

DEFINE API "/custom_response"
    FOR get
        MIDDLEWARE
            fn::increment_num()
        THEN {
            {
                status: 200,
                body: {
                    num: 1
                }
            };
        };
```

Calling `api::invoke("/custom_response")` will now return a modified output in which `num` is equal to 2.

```surql
{
	body: {
		num: 2
	},
	context: {},
	headers: {},
	status: 200
};
```

Here is an example of the same endpoint with an extra custom middleware function which adds a `called_at` field to the `context` of the response to show when the API endpoint was called. 

```surql
DEFINE FUNCTION fn::start_timer($req: object,
  $next: function,
  $called_at: datetime) -> object {
    LET $res = $next($req);
    $res + { context: { called_at: $called_at }}
};

DEFINE FUNCTION fn::increment_num($req: object,
  $next: function) -> object {
    LET $res = $next($req);
    $res + { body: { num: $res.body.num + 1 } }
};

DEFINE API "/custom_response"
    FOR get
        MIDDLEWARE
            fn::start_timer(time::now()),
            fn::increment_num()
        THEN {
            {
                status: 200,
                body: {
                    num: 1
                }
            };
        };

api::invoke("/custom_response");
```

The output will look something like this.

```surql
{
	body: {
		num: 2
	},
	context: {
		api_called_at: d'2026-01-16T01:49:44.115351Z'
	},
	headers: {},
	status: 200
};
```
