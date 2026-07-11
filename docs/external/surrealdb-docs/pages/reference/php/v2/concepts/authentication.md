---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/authentication"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/authentication"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/authentication

Source: https://surrealdb.com/docs/reference/php/v2/concepts/authentication

SurrealDB supports several levels of authentication, from [system users](https://surrealdb.com/docs/learn/security/authentication/authentication#system-user) to fine-grained [record access](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users). Version 2 of the PHP SDK represents each level as a typed credential class, so the required fields are explicit.
##  API references[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` $db->signin($auth) `](https://surrealdb.com/docs/reference/php/v2/api/core#signin)  | Signs in as a root, namespace, database, or record user  |  
| [` $db->signup($auth) `](https://surrealdb.com/docs/reference/php/v2/api/core#signup)  | Signs up a new record user through an access method  |  
| [` $db->authenticate($token) `](https://surrealdb.com/docs/reference/php/v2/api/core#authenticate)  | Authenticates the session with an existing token  |  
| [` $db->invalidate() `](https://surrealdb.com/docs/reference/php/v2/api/core#invalidate)  | Invalidates the current session, signing the user out  |  
##  Credential types[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#credential-types)
Each authentication level has a credential class in the `SurrealDB\SDK\Auth` namespace.  
| Class  | Level  | Constructor  |  
| --- | --- | --- |  
| `RootAuth`  | Root (system) user  | `new RootAuth($username, $password)`  |  
| `NamespaceAuth`  | Namespace user  | `new NamespaceAuth($namespace, $username, $password)`  |  
| `DatabaseAuth`  | Database user  | `new DatabaseAuth($namespace, $database, $username, $password)`  |  
| `RecordAccessAuth`  | Record access  | `new RecordAccessAuth($namespace, $database, $access, $variables)`  |  
| `BearerAuth`  | Bearer access key  | `new BearerAuth($namespace, $database, $access, $key)`  |  
##  Signing in users[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#signing-in-users)
The `signin()` method authenticates an existing user. Pass the credential class for the level you need. It returns a [`Tokens`](https://surrealdb.com/docs/reference/php/v2/api/core#tokens) object holding the access token and an optional refresh token.
Root userNamespace userDatabase userRecord access

```php
use SurrealDB\SDK\Auth\RootAuth;

$tokens = $db->signin(new RootAuth('root', 'surrealdb'));
```

```php
use SurrealDB\SDK\Auth\NamespaceAuth;

$tokens = $db->signin(new NamespaceAuth('surrealdb', 'tobie', 'surrealdb'));
```

```php
use SurrealDB\SDK\Auth\DatabaseAuth;

$tokens = $db->signin(new DatabaseAuth('surrealdb', 'docs', 'tobie', 'surrealdb'));
```

```php
use SurrealDB\SDK\Auth\RecordAccessAuth;

$tokens = $db->signin(new RecordAccessAuth(
    namespace: 'surrealdb',
    database: 'docs',
    access: 'account',
    variables: [
        'email' => 'info@surrealdb.com',
        'pass' => '123456',
    ],
));

echo $tokens->access;
```

The session is authenticated after a successful sign in.
Note
The credential classes map to the keys SurrealDB expects (`user`, `pass`, `ns`, `db`, `ac`). You can also pass a raw array if you prefer, but the typed classes document the required fields and avoid mistakes.
##  Signing up users[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#signing-up-users)
The `signup()` method creates a new record user through a defined [record access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/record). Use `RecordAccessAuth` with the variables your access definition expects.

```php
use SurrealDB\SDK\Auth\RecordAccessAuth;

$tokens = $db->signup(new RecordAccessAuth(
    namespace: 'surrealdb',
    database: 'docs',
    access: 'account',
    variables: [
        'email' => 'info@surrealdb.com',
        'pass' => '123456',
    ],
));
```

##  Authenticating with a token[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#authenticating-with-a-token)
If you already have an access token, authenticate with it directly instead of signing in again. This restores a session without re-entering credentials.

```php
$db->authenticate($accessToken);
```

##  Bearer access[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#bearer-access)
A bearer access key authenticates against a defined [bearer access method](https://surrealdb.com/docs/reference/query-language/statements/define/access/bearer). Use `BearerAuth` with the access name and the key.

```php
use SurrealDB\SDK\Auth\BearerAuth;

$tokens = $db->signin(new BearerAuth(
    namespace: 'surrealdb',
    database: 'docs',
    access: 'api',
    key: $bearerKey,
));
```

##  Refreshing and revoking tokens[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#refreshing-and-revoking-tokens)
When a record access method issues refresh tokens, `signin()` and `signup()` return a `Tokens` object with both an `access` and a `refresh` token. Use the refresh token to obtain a new pair without re-entering credentials. Both operations are on the [`ConnectionController`](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller).

```php
$tokens = $db->connection()->refresh($tokens);   // new access + refresh pair

$db->connection()->revoke($tokens);              // invalidate the refresh token
```

Important
Refresh tokens require SurrealDB `3.0.0` or later. Check with `isFeatureSupported(Features::refreshTokens())` before relying on them.
By default the SDK renews an expiring token in the background. To sign the session out instead of renewing it, set `invalidateOnExpiry` to `true` on [`connect()`](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#connection-options).

```php
use SurrealDB\SDK\Connection\ConnectOptions;

$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    invalidateOnExpiry: true,
));
```

##  Providing credentials on connect[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#providing-credentials-on-connect)
Rather than calling `signin()` separately, pass credentials to `connect()` through the `authentication` option. This is preferred for system users because it lets the SDK re-authenticate automatically after a reconnect.

```php
use SurrealDB\SDK\Connection\ConnectOptions;
use SurrealDB\SDK\Auth\RootAuth;

$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    namespace: 'surrealdb',
    database: 'docs',
    authentication: new RootAuth('root', 'surrealdb'),
));
```

The `authentication` option also accepts a closure, which is useful when credentials are fetched at runtime.

```php
$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    authentication: fn () => new RootAuth(getUsername(), getPassword()),
));
```

##  Listening to authentication changes[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#listening-to-authentication-changes)
The SDK emits an `auth` event whenever the authentication state changes, including on sign in, sign up, token renewal, and invalidation. The payload is the current `Tokens` object, or `null` when signed out.

```php
$db->subscribe('auth', function (?Tokens $tokens): void {
    echo $tokens === null ? 'Signed out' : 'Authenticated';
});
```

##  Selecting the current user[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#selecting-the-current-user)
The `auth()` builder compiles to `SELECT * FROM ONLY $auth`, which returns the record of the authenticated record user.

```php
$me = $db->auth()->execute();
```

##  Signing out[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#signing-out)
The `invalidate()` method clears the session's authentication. Queries after this run unauthenticated.

```php
$db->invalidate();
```

##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/authentication#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/php/v2/api/core) for the authentication method signatures
  * •
[Authentication in SurrealDB](https://surrealdb.com/docs/learn/security/authentication/authentication) for how authentication works at the database level
  * •
[DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access) for defining access methods
