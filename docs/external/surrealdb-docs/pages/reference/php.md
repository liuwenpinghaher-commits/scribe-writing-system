---
title: "https://surrealdb.com/docs/reference/php"
url: "https://surrealdb.com/docs/reference/php"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php

Source: https://surrealdb.com/docs/reference/php

The SurrealDB SDK for PHP lets you connect to SurrealDB from server-side applications, APIs, and command-line tools. You can run queries, manage data and authentication, call database functions, and subscribe to real-time updates with live queries. When connecting over WebSocket, the SDK reconnects automatically if the connection drops.
The SDK ships in two lines. Version 1.x is the current stable release and uses direct RPC-style methods such as `$db->create($thing, $data)`. Version 2.x is a rewrite with a fluent query builder, typed credentials, and a PSR-based transport layer. It is in alpha and introduces breaking changes.
Note
The latest stable release is `2.0.0-alpha.1`, documented under [v1](https://surrealdb.com/docs/reference/php/v1).  
The `2.0.0-alpha.1` release is documented under [v2](https://surrealdb.com/docs/reference/php/v2). It is an alpha with breaking changes, so pin the exact version when installing it.
##  Choose a version[](https://surrealdb.com/docs/reference/php#choose-a-version)
[ ![v1 \(stable\)](https://surrealdb.com/docs/assets/static/php.BPWEJkpY.png)![v1 \(stable\)](https://surrealdb.com/docs/assets/static/php.ChoaVsbs.png)v1 (stable) available The current stable release. Direct RPC-style methods over HTTP and WebSocket.](https://surrealdb.com/docs/reference/php/v1)[ ![v2 \(alpha\)](https://surrealdb.com/docs/assets/static/php.BPWEJkpY.png)![v2 \(alpha\)](https://surrealdb.com/docs/assets/static/php.ChoaVsbs.png)v2 (alpha) alpha The rewrite with fluent query builders and typed credentials. Alpha, breaking changes.](https://surrealdb.com/docs/reference/php/v2)[Migration guide Move an existing project from v1 to v2, with a method-by-method mapping.](https://surrealdb.com/docs/reference/php/v2/migration)
##  Ecosystem[](https://surrealdb.com/docs/reference/php#ecosystem)
[ Surqlize (ORM) in development An object-relational mapper with attribute-driven models, a typed query builder, and graph relations.](https://surrealdb.com/docs/reference/php/ecosystem/surqlize)
##  Frameworks[](https://surrealdb.com/docs/reference/php#frameworks)
[ ![Laravel](https://surrealdb.com/docs/assets/static/laravel.D_YdZiNL.png)![Laravel](https://surrealdb.com/docs/assets/static/laravel.Cl2KBf6a.png)Laravel alpha A Laravel integration that wires the SDK and Surqlize into config, the service container, and Artisan.](https://surrealdb.com/docs/reference/php/frameworks/laravel)
##  Contributing[](https://surrealdb.com/docs/reference/php#contributing)
To contribute to the SDK code, submit an issue or pull request in the [surrealdb.php](https://github.com/surrealdb/surrealdb.php) repository. To contribute to this documentation, submit an issue or pull request in the [docs.surrealdb.com](https://github.com/surrealdb/docs.surrealdb.com) repository.
##  Sources[](https://surrealdb.com/docs/reference/php#sources)
  * •
[GitHub repository](https://github.com/surrealdb/surrealdb.php)
  * •
[Composer package](https://packagist.org/packages/surrealdb/surrealdb.php)
