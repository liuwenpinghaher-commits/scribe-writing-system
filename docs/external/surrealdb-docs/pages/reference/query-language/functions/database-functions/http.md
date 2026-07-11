---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/http"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/http"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/http

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/http

These functions can be used when opening and submitting remote web requests, and webhooks.  
| Function  | Description  |  
| --- | --- |  
| [`http::head()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httphead)  | Perform a remote HTTP HEAD request  |  
| [`http::get()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpget)  | Perform a remote HTTP GET request  |  
| [`http::put()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpput)  | Perform a remote HTTP PUT request  |  
| [`http::post()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httppost)  | Perform a remote HTTP POST request  |  
| [`http::patch()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httppatch)  | Perform a remote HTTP PATCH request  |  
| [`http::delete()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpdelete)  | Perform a remote HTTP DELETE request  |  
##  Response encoding and errors[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#response-encoding-and-errors)
Failed requests return descriptive errors with the relevant HTTP status code when the remote server provides one.
Response bodies encode SurrealQL values as follows:
  * •
**Bytes** , sent as raw bytes (not base64- or JSON-encoded).
  * •
**Strings** , sent as raw strings.
  * •
**Other values** (numbers, arrays, objects, booleans, and so on), JSON-encoded.

SurrealDB does not add `Content-Type: application/octet-stream` automatically when the body contains byte values. You can set this header yourself if a client requires it.
##  `http::head`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httphead)
The `http::head` function performs a remote HTTP `HEAD` request. The first parameter is the URL of the remote endpoint. If the response does not return a `2XX` status code, then the function will fail and return the error.
API DEFINITION

```surql
http::head(string) -> null
```

If an object is given as the second argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::head(string, $headers: object) -> null
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN http::head('https://surrealdb.com');

null
```

To specify custom headers with the HTTP request, pass an object as the second argument:

```surql
RETURN http::head('https://surrealdb.com', {
	'x-my-header': 'some unique string'
});

null
```

  

##  `http::get`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpget)
The `http::get` function performs a remote HTTP `GET` request. The first parameter is the URL of the remote endpoint. If the response does not return a 2XX status code, then the function will fail and return the error. 
If the remote endpoint returns an `application/json content-type`, then the response is parsed and returned as a value, otherwise the response is treated as text.
API DEFINITION

```surql
http::get(string) -> value
```

If an object is given as the second argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::get(string, $headers: object) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN http::get('https://surrealdb.com');

-- The HTML code is returned
```

To specify custom headers with the HTTP request, pass an object as the second argument:

```surql
RETURN http::get('https://surrealdb.com', {
	'x-my-header': 'some unique string'
});

-- The HTML code is returned
```

  

##  `http::put`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpput)
The `http::put` function performs a remote HTTP `PUT` request. The first parameter is the URL of the remote endpoint, and the second parameter is the value to use as the request body, which will be converted to JSON. If the response does not return a `2XX` status code, then the function will fail and return the error. If the remote endpoint returns an `application/json` content-type, then the response is parsed and returned as a value, otherwise the response is treated as text.
API DEFINITION

```surql
http::put(string, $body: object) -> value
```

If an object is given as the third argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::put(string, $body: object, $headers: object) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:
Request without headers

```surql
RETURN http::put('https://jsonplaceholder.typicode.com/posts/1', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: 'eburras1q'
  }
});
```

Request with headers

```surql
RETURN http::put('https://jsonplaceholder.typicode.com/posts/1', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: 'eburras1q'
  }
}, {
  'Authorization': 'Bearer your-token-here',
  'Content-Type': 'application/json',
  'x-custom-header': 'custom-value'
});
```

Response

```surql
{
	body: 'This is some awesome thinking!',
	id: 1,
	postId: 100,
	user: {
		id: 63,
		username: 'eburras1q'
	}
}
```

  

##  `http::post`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httppost)
The `http::post` function performs a remote HTTP `POST` request. The first parameter is the URL of the remote endpoint, and the second parameter is the value to use as the request body, which will be converted to JSON. If the response does not return a `2XX` status code, then the function will fail and return the error. If the remote endpoint returns an `application/json` content-type, then the response is parsed and returned as a value, otherwise the response is treated as text.
API DEFINITION

```surql
http::post(string, $body: object) -> value
```

If an object is given as the third argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::post(string, $body: object, $headers: object) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:
Request without headers

```surql
RETURN http::post('https://jsonplaceholder.typicode.com/posts/', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: "eburras1q"
  }
});
```

Request with headers

```surql
RETURN http::post('https://jsonplaceholder.typicode.com/posts/', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: "eburras1q"
  }
}, {
  'Authorization': 'Bearer your-token-here',
  'Content-Type': 'application/json',
  'x-custom-header': 'custom-value'
});
```

Response

```surql
{
	body: 'This is some awesome thinking!',
	id: 101,
	postId: 100,
	user: {
		id: 63,
		username: 'eburras1q'
	}
}
```

  

##  `http::patch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httppatch)
The `http::patch` function performs a remote HTTP `PATCH` request. The first parameter is the URL of the remote endpoint, and the second parameter is the value to use as the request body, which will be converted to JSON. If the response does not return a `2XX` status code, then the function will fail and return the error. If the remote endpoint returns an `application/json` content-type, then the response is parsed and returned as a value, otherwise the response is treated as text.
API DEFINITION

```surql
http::patch(string, $body: object) -> value
```

If an object is given as the third argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::patch(string, $body: object, $headers: object) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:
Request without headers

```surql
RETURN http::patch('https://jsonplaceholder.typicode.com/posts/1', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: "eburras1q"
  }
});
```

Setting the request headers

```surql
RETURN http::patch('https://jsonplaceholder.typicode.com/posts/1', {
  id: 1,
  body: "This is some awesome thinking!",
  postId: 100,
  user: {
    id: 63,
    username: "eburras1q"
  }
}, {
  'Authorization': 'Bearer your-token-here',
  'Content-Type': 'application/json',
  'x-custom-header': 'custom-value'
});
```

RESPONSE

```surql
{
	body: 'This is some awesome thinking!',
	id: 1,
	postId: 100,
	title: 'sunt aut facere repellat provident occaecati excepturi optio reprehenderit',
	user: {
		id: 63,
		username: 'eburras1q'
	},
	userId: 1
}
```

  

##  `http::delete`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http#httpdelete)
The `http::delete` function performs a remote HTTP `DELETE` request. The first parameter is the URL of the remote endpoint, and the second parameter is the value to use as the request body, which will be converted to JSON. If the response does not return a `2XX` status code, then the function will fail and return the error. If the remote endpoint returns an `application/json` content-type, then the response is parsed and returned as a value, otherwise the response is treated as text.
API DEFINITION

```surql
http::delete(string) -> value
```

If an object is given as the second argument, then this can be used to set the request headers.
API DEFINITION

```surql
http::delete(string, $headers: object) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN http::delete('https://jsonplaceholder.typicode.com/posts/1');

{}
```

To specify custom headers with the HTTP request, pass an object as the second argument:

```surql
RETURN http::delete('https://jsonplaceholder.typicode.com/posts/1', {
	'x-my-header': 'some unique string'
});

{}
```
