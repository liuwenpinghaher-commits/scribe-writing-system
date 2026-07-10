---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/api"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/api

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/api

Available since: v3.0.5
The `ALTER API` statement can be used to modify an existing defined [API](https://surrealdb.com/docs/reference/query-language/statements/define/api).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/api#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER API [ IF EXISTS ] @endpoint
  [ FOR any [ @api_config ] [ THEN @expression | DROP THEN ] ]
  [ FOR @http_method, ... [ MIDDLEWARE @function, ... ] [ THEN @expression ] ]
  [ FOR @http_method, ... DROP THEN ]
  [ COMMENT @string | DROP COMMENT ]
```

ALTER APIIFEXISTS@endpointFORany@api_configTHEN@expressionDROPTHENFOR@http_method,@http_methodMIDDLEWARE@function,@functionTHEN@expressionFOR@http_method,@http_methodDROPTHENCOMMENT@stringDROPCOMMENT
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/api#example-usage)

```surql
-- Define a simple API
DEFINE API "/test"
    FOR get
        THEN {
            {
                body: {
                    some: "data"
                }
            };
        };

-- Make a random function
DEFINE FUNCTION fn::feeling_lucky() -> int {
    rand::enum(200, 404)
};

-- Set it as the HTTP status
ALTER API "/test" FOR get THEN {
    {
        status: fn::feeling_lucky(),
        body: {
            some: "data"
        }
    }
};

-- status is either 200 or 404
api::invoke("/test");
```

Possible output

```surql
{
	body: {
		some: 'data'
	},
	headers: {
		"x-surreal-request-id": '95fd0577-5b97-4dc1-b98e-c284f0e36a63'
	},
	request_id: '95fd0577-5b97-4dc1-b98e-c284f0e36a63',
	status: 404
}
```
