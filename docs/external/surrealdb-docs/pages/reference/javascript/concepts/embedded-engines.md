---
title: "https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines"
url: "https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines

Source: https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines

The JavaScript SDK supports running SurrealDB as an embedded database through two engine plugins. Choose the one that matches your environment:  
| Engine  | Package  | Environment  | Storage options  |  
| --- | --- | --- | --- |  
| WebAssembly  | `@surrealdb/wasm`  | Browsers  |  `mem://`, `indxdb://`  |  
| Node.js  | `@surrealdb/node`  | Node.js, Bun, Deno  |  `mem://`, `rocksdb://`, `surrealkv://`  |  
Both plugins work with ES modules (`import`), not CommonJS (`require`).
##  WebAssembly engine (browser)[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#webassembly-engine-browser)
The `@surrealdb/wasm` package runs SurrealDB inside a browser environment. It supports in-memory databases and persistent storage via IndexedDB, and can optionally run inside a Web Worker to keep the main thread responsive.
###  Installation[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#installation)

```bash
npm install --save @surrealdb/wasm
```

###  Registering the engine[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#registering-the-engine)

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
// or persist with IndexedDB:
await db.connect('indxdb://myapp');
```

###  Running in a web worker[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#running-in-a-web-worker)
Offload database operations from the main thread to keep your interface responsive:

```ts
import { Surreal, createRemoteEngines } from 'surrealdb';
import { createWasmWorkerEngines } from '@surrealdb/wasm';
import WorkerAgent from '@surrealdb/wasm/worker?worker';

const db = new Surreal({
    engines: {
        ...createRemoteEngines(),
        ...createWasmWorkerEngines({
            createWorker: () => new WorkerAgent(),
        }),
    },
});

await db.connect('mem://');
```

###  Bundler configuration[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#bundler-configuration)
If you are using a bundler like Vite, you may need to exclude the WASM package from dependency optimisation and enable top-level await:
vite.config.js

```js
export default {
    optimizeDeps: {
        exclude: ['@surrealdb/wasm'],
        esbuildOptions: {
            target: 'esnext',
        },
    },
    esbuild: {
        supported: {
            'top-level-await': true,
        },
    },
};
```

##  Node.js engine (server)[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#nodejs-engine-server)
The `@surrealdb/node` package runs SurrealDB within Node.js, Bun, or Deno. It supports in-memory databases and persistent storage via RocksDB and SurrealKV.
###  Installation[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#installation-1)

```bash
npm install --save @surrealdb/node
```

###  Registering the engine[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#registering-the-engine-1)

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
// or persist with SurrealKV:
await db.connect('surrealkv://./data');
```

To enable [versioned storage](https://surrealdb.com/docs/reference/query-language/statements/select#version) for temporal queries, append `?versioned=true` to the connection string:

```ts
await db.connect('surrealkv://./data?versioned=true');
```

###  Closing the connection[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#closing-the-connection)
When using the Node.js engine, you must close the connection with `.close()` when you are done to ensure the database is properly shut down:

```ts
await db.close();
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/embedded-engines#learn-more)
  * •
[WebAssembly engine reference](https://surrealdb.com/docs/reference/javascript/engines/wasm)
  * •
[Node.js engine reference](https://surrealdb.com/docs/reference/javascript/engines/node)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for connection options and reconnection behaviour
  * •
[`@surrealdb/wasm` on npm](https://npmjs.com/package/@surrealdb/wasm)
  * •
[`@surrealdb/node` on npm](https://npmjs.com/package/@surrealdb/node)
