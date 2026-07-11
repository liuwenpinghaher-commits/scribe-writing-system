---
title: "https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins"
url: "https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins

Source: https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins

You do not have to author Rust yourself to benefit from Surrealism. Many teams consume a **pre-built`.surli` archive** produced by another team or pipeline. Authoring a module means writing Rust, configuring `surrealism.toml`, and running [`surreal module`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/module) yourself. This page focuses on the consumer workflow.
##  Storing the module archive[](https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins#storing-the-module-archive)
SurrealDB needs access to the `.surli` binary. Use [`DEFINE BUCKET`](https://surrealdb.com/docs/reference/query-language/statements/define/bucket) to create or configure bucket storage, then upload the `.surli` file according to your environment’s path and permissions model.
##  Registering the module[](https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins#registering-the-module)
Once the binary is stored, [`DEFINE MODULE`](https://surrealdb.com/docs/reference/query-language/statements/define/module) associates that artefact with a module name and exposes the compiled functions to SurrealQL. The module definition must line up with the exported function names and signatures from the build.
##  Inspecting exports before use[](https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins#inspecting-exports-before-use)
If you receive a module from another team, inspect it locally before upload:

```bash
surreal module info demo.surli
surreal module sig --fnc can_drive demo.surli
```

These commands let you verify function signatures and metadata (such as writeable/comment annotations) before registration.
##  Calling functions from SurrealQL[](https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins#calling-functions-from-surrealql)
After the module is defined, call its exported functions by qualifying the function with the registered module path. Consult your module’s documentation for exact names and parameters.
If you upgrade the module archive, repeat upload and module definition steps (or your deployment automation) so the running instance picks up the new build.
##  Further reading[](https://surrealdb.com/docs/learn/extensions/guides/using-wasm-plugins#further-reading)
  * •
[Surrealism overview](https://surrealdb.com/docs/learn/extensions/plugins/overview) — how compilation, buckets, and modules fit together.
  * •
[`DEFINE BUCKET` reference](https://surrealdb.com/docs/reference/query-language/statements/define/bucket) — file storage for WASM.
  * •
[`DEFINE MODULE` reference](https://surrealdb.com/docs/reference/query-language/statements/define/module) — registering Surrealism functions.
