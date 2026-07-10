---
title: "https://surrealdb.com/docs/reference/javascript/installation"
url: "https://surrealdb.com/docs/reference/javascript/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/installation

Source: https://surrealdb.com/docs/reference/javascript/installation

In this section, you will learn how to install the JavaScript SDK in your project.
###  Install the SDK[](https://surrealdb.com/docs/reference/javascript/installation#install-the-sdk)
First, install the [SurrealDB SDK](https://npmjs.com/package/surrealdb) using your favorite package manager:
bunnpmyarnpnpm

```bash
bun install surrealdb
```

```bash
npm install --save surrealdb
```

```bash
yarn add surrealdb
```

```bash
pnpm install surrealdb
```

Note
The SurrealDB SDK for JavaScript is also available in the JSR registry as [`@surrealdb/surrealdb`](https://jsr.io/@surrealdb/surrealdb).
###  Import the SDK into your project[](https://surrealdb.com/docs/reference/javascript/installation#import-the-sdk-into-your-project)
After installing the SDK as a dependency, you can import the SDK into your project. Depending on your setup and environment, we supported multiple options.
ESMCommonJSDenoCDN

```ts
import { Surreal } from 'surrealdb';
```

```ts
const { Surreal } = require('surrealdb');
```

```ts
//Importing from Deno
import { Surreal } from "https://deno.land/x/surrealdb/mod.ts";

// Import with version 
import { Surreal } from "https://deno.land/x/surrealdb/mod.ts";
```

```ts
import { Surreal } from "https://unpkg.com/surrealdb";
// or
import { Surreal } from "https://cdn.jsdelivr.net/npm/surrealdb";
```

##  Next steps[](https://surrealdb.com/docs/reference/javascript/installation#next-steps)
After installing the SDK, check out the quick start guide to build your a simple application with the SDK. You can also learn more about carrying out common tasks with the SDK in the following sections:
  * •
[Getting started](https://surrealdb.com/docs/languages/javascript)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb)
  * •
[Authentication](https://surrealdb.com/docs/reference/javascript/concepts/authentication)
