---
title: "https://surrealdb.com/docs/reference/javascript/engines/wasm"
url: "https://surrealdb.com/docs/reference/javascript/engines/wasm"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/engines/wasm

Source: https://surrealdb.com/docs/reference/javascript/engines/wasm

The `@surrealdb/wasm` package is a plugin for the [JavaScript SDK](https://surrealdb.com/docs/reference/javascript/installation) that runs SurrealDB as an embedded database within a browser environment. It supports in-memory databases and persistent storage via IndexedDB, and can optionally run inside a Web Worker.
Important
This package works with ES modules (`import`), not CommonJS (`require`).
##  Installation[](https://surrealdb.com/docs/reference/javascript/engines/wasm#installation)
First, [install the JavaScript SDK](https://surrealdb.com/docs/reference/javascript/installation) if you haven't already. Then add the WASM engine:
npmyarnpnpm

```bash
npm install --save @surrealdb/wasm
```

```bash
yarn add @surrealdb/wasm
```

```bash
pnpm install @surrealdb/wasm
```

##  Quick start[](https://surrealdb.com/docs/reference/javascript/engines/wasm#quick-start)

```ts
import { Surreal, createRemoteEngines } from 'surrealdb';
import { createWasmEngines } from '@surrealdb/wasm';

const db = new Surreal({
    engines: {
        ...createRemoteEngines(),
        ...createWasmEngines(),
    },
});

await db.connect('mem://');
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/engines/wasm#learn-more)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for engine registration, embedded protocols, and connection options
  * •
[`@surrealdb/wasm` on npm](https://npmjs.com/package/@surrealdb/wasm)
