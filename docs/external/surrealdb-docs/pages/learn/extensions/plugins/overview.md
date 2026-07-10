---
title: "https://surrealdb.com/docs/learn/extensions/plugins/overview"
url: "https://surrealdb.com/docs/learn/extensions/plugins/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/extensions/plugins/overview

Source: https://surrealdb.com/docs/learn/extensions/plugins/overview

Surrealism extensions are written in Rust, compiled into `.surli` modules, and loaded into a running SurrealDB instance. This gives you access to the Rust ecosystem while keeping extensions sandboxed within the database.
Surrealism was built in order to allow users to extend SurrealDB in ways that benefit them, without needing to make any changes to the code of SurrealDB itself. Some potential use cases are:
  * •
Adding functions to create fake / mock data for testing.
  * •
Accessing functionality in Rust crates that are too specific to merge into SurrealDB itself, such as [language-specific functionality](https://crates.io/crates/hangeul), [custom case conversions](https://docs.rs/convert_case/latest/convert_case/enum.Case.html), or [quantitative finance](https://docs.rs/crate/RustQuant/latest).
  * •
Anything else you have built in your own code that you would like to access inside SurrealDB.

##  How Surrealism works[](https://surrealdb.com/docs/learn/extensions/plugins/overview#how-surrealism-works)
Surrealism works by using the following steps:
  * •
Use the [`surreal module init`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/module) command to begin a new project. This command works in a similar manner to `cargo new` in scaffolding a new project with its own `toml` file (`surrealism.toml`).
  * •
Annotate functions to export with `#[surrealism]`.
  * •
Use the `surreal module build` command to build the module.
  * •
In SurrealDB, [allow access to module files](https://surrealdb.com/docs/reference/query-language/statements/define/bucket) and [define a module](https://surrealdb.com/docs/reference/query-language/statements/define/module) to access the functions.

![A flowchart showing the steps involved to turn regular Rust code into a compiled WASM binary that can be accessed from a running SurrealDB instance.](https://surrealdb.com/docs/learn/extensions/plugins/~/assets/img/surrealdb/extension/surrealism_flow.png)
##  What is available in Surrealism[](https://surrealdb.com/docs/learn/extensions/plugins/overview#what-is-available-in-surrealism)
Current Surrealism releases include:
  * •
function-level metadata such as `writeable` and `comment` via `#[surrealism(...)]`;
  * •
one-time module initialisation with `#[surrealism(init)]`;
  * •
namespaced exports with `#[surrealism] mod ...`;
  * •
optional read-only attached filesystem data packaged into the module archive;
  * •
server-side resource controls for execution time, memory, and module KV limits.

The next pages walk through the workflow and APIs:
  * •
[Quick tutorial](https://surrealdb.com/docs/learn/extensions/plugins/quick-tutorial)
  * •
[Creating custom modules](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules)
  * •
[Surrealism attribute reference](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference)
