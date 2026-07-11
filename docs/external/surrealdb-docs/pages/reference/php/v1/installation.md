---
title: "https://surrealdb.com/docs/reference/php/v1/installation"
url: "https://surrealdb.com/docs/reference/php/v1/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/installation

Source: https://surrealdb.com/docs/reference/php/v1/installation

Version 1 of the PHP SDK is installed with the [Composer](https://getcomposer.org/download/) package manager. It requires PHP `8.2` or later and the `curl` extension.
##  Install the SDK[](https://surrealdb.com/docs/reference/php/v1/installation#install-the-sdk)
Run the following command in your project to install the latest stable release.

```bash
composer require surrealdb/surrealdb.php:^1.0
```

##  Import the SDK[](https://surrealdb.com/docs/reference/php/v1/installation#import-the-sdk)
Include the [Composer autoloader](https://getcomposer.org/doc/01-basic-usage.md#autoloading), then import the `Surreal` class.

```php
require __DIR__ . '/vendor/autoload.php';

use Surreal\Surreal;
```

You can now create a `Surreal` instance and connect to your database.
##  Next steps[](https://surrealdb.com/docs/reference/php/v1/installation#next-steps)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/php/v1/concepts/connecting) to open a connection
  * •
[Getting started](https://surrealdb.com/docs/languages/php) to run your first queries
