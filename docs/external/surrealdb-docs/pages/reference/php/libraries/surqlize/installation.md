---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/installation"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/installation

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/installation

Surqlize is installed with [Composer](https://getcomposer.org/download/). It requires PHP `8.4` or later and depends on the alpha [v2 SurrealDB PHP SDK](https://surrealdb.com/docs/reference/php/v2).
##  Install the package[](https://surrealdb.com/docs/reference/php/libraries/surqlize/installation#install-the-package)

```bash
composer require surrealdb/surqlize
```

Surqlize depends on the alpha SDK, so your project must allow alpha releases. If Composer cannot resolve the SDK under the default `stable` minimum stability, lower the stability for the SDK or set it project-wide.

```bash
composer config minimum-stability alpha
composer config prefer-stable true
```

##  Add an HTTP client[](https://surrealdb.com/docs/reference/php/libraries/surqlize/installation#add-an-http-client)
Surqlize runs queries through the SDK, which uses [PSR-18](https://www.php-fig.org/psr/psr-18/) and [PSR-17](https://www.php-fig.org/psr/psr-17/) interfaces for the HTTP transport. Install a client and factory implementation, plus discovery, when you connect over `http://` or `https://`.

```bash
composer require guzzlehttp/guzzle php-http/discovery
```

The WebSocket transport uses PHP's native stream functions and needs no extra packages. See the [SDK installation guide](https://surrealdb.com/docs/reference/php/v2/installation) for details.
##  Requirements[](https://surrealdb.com/docs/reference/php/libraries/surqlize/installation#requirements)  
| Requirement  | Version  |  
| --- | --- |  
| PHP  | `>= 8.4`  |  
| SurrealDB PHP SDK  |  `surrealdb/surrealdb.php` (v2 alpha)  |  
| SurrealDB server  |  `1.x` up to (but not including) `4.0.0`  |  
##  Next steps[](https://surrealdb.com/docs/reference/php/libraries/surqlize/installation#next-steps)
[Models Describe your first table as a model.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/models)[Connections Register the SDK executor Surqlize runs queries through.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections)
