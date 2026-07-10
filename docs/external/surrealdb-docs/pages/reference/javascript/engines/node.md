---
title: "https://surrealdb.com/docs/reference/javascript/engines/node"
url: "https://surrealdb.com/docs/reference/javascript/engines/node"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/engines/node

Source: https://surrealdb.com/docs/reference/javascript/engines/node

The `@surrealdb/node` package is a plugin for the [JavaScript SDK](https://surrealdb.com/docs/reference/javascript/installation) that runs SurrealDB as an embedded database within Node.js, Bun, or Deno. It supports in-memory databases and persistent storage via RocksDB and SurrealKV.
Important
This package works with ES modules (`import`), not CommonJS (`require`).
##  Installation[](https://surrealdb.com/docs/reference/javascript/engines/node#installation)
First, [install the JavaScript SDK](https://surrealdb.com/docs/reference/javascript/installation) if you haven't already. Then add the Node.js engine:
npmyarnpnpm

```bash
npm install --save @surrealdb/node
```

```bash
yarn add @surrealdb/node
```

```bash
pnpm install @surrealdb/node
```

##  Quick start[](https://surrealdb.com/docs/reference/javascript/engines/node#quick-start)

```ts
import { Surreal, createRemoteEngines } from 'surrealdb';
import { createNodeEngines } from '@surrealdb/node';

const db = new Surreal({
    engines: {
        ...createRemoteEngines(),
        ...createNodeEngines(),
    },
});

await db.connect('mem://');

// Always close the connection when done
await db.close();
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/engines/node#learn-more)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for engine registration, embedded protocols, and connection options
  * •
[`@surrealdb/node` on npm](https://npmjs.com/package/@surrealdb/node)
