---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/api"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/api"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/api

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/api

| Function  | Description  |  
| --- | --- |  
| [`api::invoke()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiinvoke)  | Invokes an `/api` endpoint and returns the result  |  
| [`api::timeout()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apitimeout)  | Middleware to set a timeout for requests made to a defined API endpoint  |  
| [`api::req::body()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apireqbody)  | Middleware to set the body type for an API endpoint request  |  
| [`api::res::body()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresbody)  | Middleware to set the body type for an API endpoint response  |  
| [`api::res::header()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresheader)  | Middleware to add a single header to an API endpoint response  |  
| [`api::res::headers()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresheaders)  | Middleware to adds multiple headers to an API endpoint response  |  
| [`api::res::status()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresstatus)  | Middleware to set the status for an API endpoint response  |  
| [`Custom middleware`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#custom-middleware)  | Middleware to set the status for an API endpoint response  |  
##  Overview[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#overview)
API functions are passed in as middleware inside a [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) or [`DEFINE CONFIG API`](https://surrealdb.com/docs/reference/query-language/statements/define/config) statement and called a request is received.
The only API function intended for use in regular queries is the [`api::invoke`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiinvoke) function, which is used to test API endpoints instead of as middleware.
The signatures for all other functions are presented here are from the point of view of the user. For example, the `api::timeout` function takes a single duration.

```surql
api::timeout(duration)
```

In practice, two extra arguments are passed in to these functions unseen to the user, making this the true signature.

```surql
api::timeout($req: object, $next: function, $duration: duration)
```

For more details on how this works, see [this section](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#structure-of-api-functions) on this page.
##  `api::invoke`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiinvoke)
API DEFINITION

```surql
api::invoke($path: string, $options: option<object>) -> object
```

The `api::invoke` function invokes a custom `/api` endpoint defined using a `DEFINE API` statement. While a `DEFINE API` statement creates an API endpoint at the `/api/:namespace/:database/:endpoint` path, this function is called when a namespace and database have already been decided, necessitating only the final path (such as `"/test"`) for it to be invoked.
The following two examples of the function assume that this `DEFINE API` statement has been used to set up the `"/test"` endpoint.
Define API endpoint

```surql
DEFINE API "/test"
    FOR get 
        MIDDLEWARE
            api::timeout(1s)
        THEN {
            {
                status: 404,
                body: $request.body,
                headers: { the_time_is_now: <string>time::now() }
            };
        };
```

Calling the `api::invoke` function with just a path:
Use defined endpoint

```surql
api::invoke("/test");
```

Output

```surql
{
	body: NONE,
    context: {},
	headers: {
		the_time_is_now: '2025-12-25T11:49:30.732Z'
	},
	status: 404
}
```

Calling the `api::invoke` function with a path and an object containing a body and headers:

```surql
api::invoke("/test", {
    body: <bytes> '{ "a": true }',
    headers: {
        "Content-Type": "application/json",
        Accept: "application/cbor",
    }
});
```

Output

```surql
{
	body: b"7B202261223A2074727565207D",
    context: {},
	headers: {
		the_time_is_now: '2025-12-25T11:51:18.910Z'
	},
	status: 404
}
```

For more information and examples, see the page for the `DEFINE API` statement.
##  `api::timeout`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apitimeout)
The `api::timeout` function sets the maximum timeout for a request.
API DEFINITION

```surql
api::timeout($timeout: duration)
```

The following example will always return an error because the
Example

```surql
DEFINE API "/exceeds_timeout"
    FOR get 
        MIDDLEWARE
            api::timeout(1ns)
        THEN {
            sleep 1ns;
            {}
        };
```

##  `api::req::body`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apireqbody)
API DEFINITION

```surql
api::req::body($path: string, $strategy: option<string>)
```

This function sets the strategy (the input format) for the endpoint. It can take one of the following strings:
  * •
'auto'
  * •
'json'
  * •
'cbor'
  * •
'flatbuffers'
  * •
'plain'
  * •
'bytes'
  * •
'native'

The following example shows an endpoint for each of these strategies, followed by an invocation for each that matches it.

```surql
DEFINE API "/body/json" FOR post
    MIDDLEWARE api::req::body("json")
    THEN {{ body: { parsed: $request.body } }};

DEFINE API "/body/cbor" FOR post
    MIDDLEWARE api::req::body("cbor")
    THEN {{ body: { parsed: $request.body } }};

DEFINE API "/body/plain" FOR post
    MIDDLEWARE api::req::body("plain")
    THEN {{ body: { parsed: $request.body } }};

DEFINE API "/body/bytes" FOR post
    MIDDLEWARE api::req::body("bytes")
    THEN {{ body: { parsed: $request.body } }};

DEFINE API "/body/native" FOR post
    MIDDLEWARE api::req::body("native")
    THEN {{ body: { parsed: $request.body } }};

DEFINE API "/body/auto" FOR post
    MIDDLEWARE api::req::body("auto")
    THEN {{ body: { parsed: $request.body } }};

api::invoke("/body/json", {
    method: "post",
    headers: { "content-type": "application/json" },
    body: <bytes>'{"name":"billy","billys_number":753}'
});

api::invoke("/body/cbor", {
    method: "post",
    headers: { "content-type": "application/cbor" },
    body: encoding::cbor::encode('CBOR!!')
});

api::invoke("/body/plain", {
    method: "post",
    headers: { "content-type": "text/plain" },
    body: <bytes>'plain text content'
});

api::invoke("/body/bytes", {
    method: "post",
    headers: { "content-type": "application/octet-stream" },
    body: <bytes>'raw bytes'
});

api::invoke("/body/native", {
    method: "post",
    headers: { "content-type": "application/vnd.surrealdb.native" },
    body: { native: "format" }
});

api::invoke("/body/auto", {
    method: "post",
    headers: { "content-type": "application/json" },
    body: <bytes>'{"auto":"json"}'
});

api::invoke("/body/auto", {
    method: "post",
    body: <bytes>'some data'
});
```

##  `api::res::body`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresbody)
API DEFINITION

```surql
api::res::body($path: string, $strategy: option<string>)
```

```surql
DEFINE API "/serialize_json"
    FOR get
        MIDDLEWARE
            api::res::body("json")
        THEN {
            {
                status: 200,
                body: {
                    message: "Hello"
                }
            };
        };

api::invoke("/serialize_json").{
    body: <string>body, -- Cast response bytes into string
    headers,
    status
};
```

Response

```surql
{ 
    body: '{"message":"Hello"}', 
    headers: { "access-control-allow-origin": '*',
      "content-type": 'application/json' }
    status: 200 
}
```

##  `api::res::header`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresheader)
The `api::res::header` function sets a single header for a response.
API DEFINITION

```surql
api::res::header($header_name: string, $val: value)
```

Example

```surql
DEFINE API "/test"
  FOR get 
    MIDDLEWARE
      api::res::header("country-origin", "CA")
    THEN {
      {
        status: 200,
        headers: {
          "requested-at": <string>time::now()
        },
        body: SELECT * FROM person
      };
    };
```

##  `api::res::headers`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresheaders)
The `api::res::headers` function takes an object to set the headers for a response.
API DEFINITION

```surql
api::res::headers($headers: object)
```

Example

```surql
DEFINE API "/test"
    FOR get 
        MIDDLEWARE
            api::res::headers({
                "country-origin": "CA",
                "language": "FR"
            })
        THEN {
            {
                status: 200,
                headers: {
                    "requested-at": <string>time::now()
                },
                body: SELECT * FROM person
            };
        };
```

##  `api::res::status`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#apiresstatus)
API DEFINITION

```surql
api::res::status($http_code: int)
```

The `api::res::status` function adds a status to the response of an API endpoint.

```surql
DEFINE API "/always_ok"
    FOR get
        MIDDLEWARE
            api::res::status(200)
        THEN {
            {
                status: 404,
                body: {
                    some: "data"
                }
            };
        };

api::invoke("/always_ok");
```

Response

```surql
{ 
    body: {some: 'data'}, 
    context: {}, 
    headers: {}, 
    status: 200 
}
```

Setting an invalid HTTP status will result in an error.

```surql
DEFINE API "/status/invalid-low"
    FOR get
        MIDDLEWARE
            api::res::status(99)
        THEN {
            RETURN {
                status: 200,
                body: {}
            };
        };

api::invoke("/status/invalid-low");
```

Response

```surql
'Invalid HTTP status code: 99. Must be between 100 and 599'
```

##  Custom middleware[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#custom-middleware)
A `DEFINE FUNCTION` statement can be used to define a function for use as custom middleware. For more details on defining a custom function in this manner, see the [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api#custom-middleware) page.
##  Structure of API functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api#structure-of-api-functions)
An API function can technically be called in the same way as any other function, as long as the first argument is an object and the second argument is a closure that returns an object. After a `MIDDLEWARE` clause these arguments will be automatically filled, but dummy arguments can be passed in for practice or testing.

```surql
api::res::body({}, || {}, "json").{
    body: <string>body,
    context,
    headers,
    status
};

-- Returns:
{
	body: 'null',
	context: {},
	headers: {
		"content-type": 'application/json'
	},
	status: 200
};

api::res::body({}, || {}, "jsonnn").{
    body: <string>body,
    context,
    headers,
    status
};

-- Returns:
'Failed to decode BodyStrategy, no variants matched'
```
