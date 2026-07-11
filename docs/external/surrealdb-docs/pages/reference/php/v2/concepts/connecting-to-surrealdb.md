---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb

Source: https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb

Before you can run queries, you open a connection to a SurrealDB instance. You create a `Surreal` instance and call `connect()` with a connection string and a set of options. The options carry the namespace, database, authentication, and reconnection settings.
##  API references[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` $db->connect($url, $options) `](https://surrealdb.com/docs/reference/php/v2/api/core#connect)  | Connects to a local or remote database endpoint  |  
| [` $db->close() `](https://surrealdb.com/docs/reference/php/v2/api/core#close)  | Closes the connection to the database  |  
| [` $db->use($namespace, $database) `](https://surrealdb.com/docs/reference/php/v2/api/core#use)  | Switches to a specific namespace and database  |  
| [` $db->status() `](https://surrealdb.com/docs/reference/php/v2/api/core#status)  | Returns the current connection status  |  
##  Opening a connection[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#opening-a-connection)
Create a `Surreal` instance, then call `connect()` with a connection string and a [`ConnectOptions`](https://surrealdb.com/docs/reference/php/v2/api/core#connectoptions) object.

```php
use SurrealDB\SDK\Surreal;
use SurrealDB\SDK\Connection\ConnectOptions;
use SurrealDB\SDK\Auth\RootAuth;

$db = new Surreal();

$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    namespace: 'surrealdb',
    database: 'docs',
    authentication: new RootAuth('root', 'root'),
));
```

###  Connection string[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#connection-string)
The connection string is a URI pointing to a SurrealDB instance. Version 2 supports two transports:
  * •
**WebSocket** (`ws://`, `wss://`) for long-lived connections that support live queries and server-side transactions.
  * •
**HTTP** (`http://`, `https://`) for stateless, short-lived requests.

```php
// WebSocket, local
$db->connect('ws://127.0.0.1:8000/rpc');

// HTTP, local
$db->connect('http://127.0.0.1:8000/rpc');

// WebSocket, remote
$db->connect('wss://cloud.surrealdb.com');
```

The SDK appends `/rpc` to the path if you leave it out, so `ws://127.0.0.1:8000` and `ws://127.0.0.1:8000/rpc` are equivalent.
Note
Version 2 does not include the embedded engines available in some other SDKs. Connect to a running SurrealDB instance over WebSocket or HTTP.
###  Connection options[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#connection-options)
`ConnectOptions` configures the connection. Every argument is optional.  
| Option  | Type  | Description  |  
| --- | --- | --- |  
| `namespace`  | `?string`  | Namespace to select on connect  |  
| `database`  | `?string`  | Database to select on connect  |  
| `authentication`  | `Credentials \| Token \| string \| Closure \| null`  | Credentials or a token used to authenticate, and to re-authenticate after a reconnect  |  
| `versionCheck`  | `bool`  | Check the server version on connect (default `true`)  |  
| `invalidateOnExpiry`  | `bool`  | Invalidate the session when its token expires instead of renewing it (default `false`)  |  
| `reconnect`  | `bool \| ReconnectStrategyInterface`  | Reconnection behaviour for WebSocket connections (default `true`)  |  
###  Authentication details[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#authentication-details)
Passing credentials to `connect()` is the preferred way to authenticate, because it lets the SDK re-authenticate automatically when a WebSocket connection drops and reconnects. You can also pass a token, or a closure that returns credentials. See [Authentication](https://surrealdb.com/docs/reference/php/v2/concepts/authentication) for the credential types.
###  Reconnection behaviour[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#reconnection-behaviour)
For WebSocket connections, the SDK reconnects automatically if the connection is lost. Set `reconnect` to `false` to disable this, leave it as `true` for the defaults, or pass a `ReconnectStrategyInterface` such as `ExponentialBackoffReconnect` to control the backoff.

```php
use SurrealDB\SDK\Reconnect\ExponentialBackoffReconnect;

$db->connect('ws://127.0.0.1:8000/rpc', new ConnectOptions(
    reconnect: new ExponentialBackoffReconnect(),
));
```

##  Selecting a namespace and database[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#selecting-a-namespace-and-database)
You can select the namespace and database on connect, or switch later with `use()`. Pass a namespace and an optional database.

```php
$db->use('surrealdb', 'docs');
```

The SDK emits a `using` event whenever the namespace or database changes, including on the initial connection.
##  Connection status[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#connection-status)
The `status()` method returns a [`ConnectionStatus`](https://surrealdb.com/docs/reference/php/v2/api/core#connectionstatus) enum with one of four values:
  * •
`Disconnected` when there is no connection
  * •
`Connecting` when a connection is being opened
  * •
`Connected` when the SDK is ready to run queries
  * •
`Reconnecting` when the connection dropped and the SDK is reconnecting

```php
use SurrealDB\SDK\Connection\ConnectionStatus;

if ($db->status() === ConnectionStatus::Connected) {
    // ready to query
}

// Shorthand for the check above
if ($db->isConnected()) {
    // ready to query
}
```

You can also subscribe to lifecycle events to react to status changes.

```php
$db->subscribe('connected', function (string $version): void {
    echo "Connected to SurrealDB {$version}";
});
```

The available events are `connecting`, `connected`, `reconnecting`, `disconnected`, `error`, `auth`, and `using`. The `subscribe()` method returns a closure that removes the listener when called.
##  Closing a connection[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#closing-a-connection)
Call `close()` when you are done. This releases the connection and its resources.

```php
$db->close();
```

##  Checking the server[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#checking-the-server)
The `health()` method throws if the instance is unreachable, and `version()` returns the server version string.

```php
$db->health();

echo $db->version(); // "surrealdb-2.1.0"
```

##  Testing for features[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#testing-for-features)
Some features depend on the transport or the server version. Use `isFeatureSupported()` to check before relying on one.

```php
use SurrealDB\SDK\Protocol\Features;

if ($db->isFeatureSupported(Features::liveQueries())) {
    // safe to run a live query
}
```

##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/php/v2/api/core) for the full connection interface
  * •
[Authentication](https://surrealdb.com/docs/reference/php/v2/concepts/authentication) for signing in and managing credentials
  * •
[Error handling](https://surrealdb.com/docs/reference/php/v2/concepts/error-handling) for connection and version errors
