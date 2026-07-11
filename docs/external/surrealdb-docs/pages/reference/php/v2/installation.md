---
title: "https://surrealdb.com/docs/reference/php/v2/installation"
url: "https://surrealdb.com/docs/reference/php/v2/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/installation

Source: https://surrealdb.com/docs/reference/php/v2/installation

Version 2 of the PHP SDK is installed with [Composer](https://getcomposer.org/download/). It requires PHP `8.4` or later.
##  Install the SDK[](https://surrealdb.com/docs/reference/php/v2/installation#install-the-sdk)
Version 2 is an alpha release, so you need to request the exact version. Composer will not select it under the default `stable` minimum stability.

```bash
composer require surrealdb/surrealdb.php:2.0.0-alpha.1
```

If you want Composer to keep tracking alpha releases, set the stability flag instead:

```bash
composer require "surrealdb/surrealdb.php:^2.0@alpha"
```

##  Add an HTTP client[](https://surrealdb.com/docs/reference/php/v2/installation#add-an-http-client)
The HTTP engine uses [PSR-18](https://www.php-fig.org/psr/psr-18/) and [PSR-17](https://www.php-fig.org/psr/psr-17/) interfaces rather than a built-in client. Install a compatible client and factory implementation, plus discovery so the SDK can find them automatically.

```bash
composer require guzzlehttp/guzzle php-http/discovery
```

Note
The WebSocket engine uses PHP's native stream functions and needs no extra packages. You only need a PSR-18 client when connecting over `http://` or `https://`, or when using import and export.
##  Import the SDK[](https://surrealdb.com/docs/reference/php/v2/installation#import-the-sdk)
Include the Composer autoloader, then import the classes you need from the `SurrealDB\SDK` namespace.

```php
require __DIR__ . '/vendor/autoload.php';

use SurrealDB\SDK\Surreal;
use SurrealDB\SDK\Connection\ConnectOptions;
use SurrealDB\SDK\Auth\RootAuth;
use SurrealDB\SDK\Types\RecordId;
use SurrealDB\SDK\Types\Table;
```

##  Next steps[](https://surrealdb.com/docs/reference/php/v2/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/reference/php/versions/v2-alpha) to connect and run your first queries
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v2/concepts/connecting-to-surrealdb) for connection options and reconnection
  * •
[Migration guide](https://surrealdb.com/docs/reference/php/v2/migration) if you are coming from v1
