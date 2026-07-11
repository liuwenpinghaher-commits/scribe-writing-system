---
title: "https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules"
url: "https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules

Source: https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules

This page walks you through the options available when building a [Surrealism](https://surrealdb.com/docs/learn/extensions/plugins/overview) module from scratch.
##  Prerequisites[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#prerequisites)
You need a recent [Rust toolchain](https://www.rust-lang.org/tools/install), the `wasm32-wasip2` target, and the SurrealDB CLI (`surreal`) on your `PATH`.

```sh
rustup target add wasm32-wasip2
```

Install SurrealDB from the [installation guide](https://surrealdb.com/docs/running/installation) if you have not already.
##  Scaffold a module project[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#scaffold-a-module-project)
The fastest way to start is `surreal module init`:

```sh
surreal module init
```

This creates the project scaffold (`Cargo.toml`, `surrealism.toml`, `.cargo/Config.toml` with flags needed for the WASI build, and `src/lib.rs`) ready for Surrealism builds.
.cargo/Config.toml flags

```toml
[build]
rustflags = ["--cfg", "tokio_unstable"]
```

To automatically set the name and organisation for a project, you can use the following flags:

```sh
surreal module init --headless --org surrealdb --name my_surreal_module ./my_surreal_module
```

##  Create a Rust project manually[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#create-a-rust-project-manually)
Create a new library crate for your module:

```sh
cargo new --lib my_surreal_module
cd my_surreal_module
```

Configure the library as a dynamic WASM library and add the Surrealism SDK plus any other crates you need to `Cargo.toml`, following versions recommended for your SurrealDB release:

```toml
[lib]
crate-type = ["cdylib"]
```

For a full annotated example, follow the [quick tutorial](https://surrealdb.com/docs/learn/extensions/plugins/quick-tutorial).
##  Configure `surrealism.toml`[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#configure-surrealismtoml)
Add a `surrealism.toml` file at the crate root next to `Cargo.toml`.
A minimal example:

```toml
[package]
organisation = "surrealdb"
name = "demo"
version = "1.0.0"

[capabilities]
allow_scripting = true
allow_arbitrary_queries = true
allow_functions = ["fn::test"]
allow_net = ["127.0.0.1:8080"]
```

Optional attached filesystem:

```toml
[attach]
fs = "fs"
```

When `[attach] fs = "fs"` is present, the `fs/` folder in your project is packed into the module archive as a read-only filesystem available to the module at runtime.
##  Annotate exported functions[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#annotate-exported-functions)
Expose functions to SurrealQL by annotating them with `#[surrealism]`. Only functions you mark this way are included in the module and callable from the database.

```rust
use surrealism::surrealism;

#[surrealism]
fn can_drive(age: i64) -> bool {
    age >= 18
}

#[surrealism(writeable, comment = "Creates a value in module KV")]
fn kv_set_value(key: String, value: String) -> bool {
    // implementation omitted
    true
}
```

For the full attribute reference (`writeable`, `comment`, `init`, and namespaced modules), see [Surrealism attribute reference](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference).
##  Compile with `surreal module`[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#compile-with-surreal-module)
From your project directory, compile to a `.surli` artefact with the Surreal CLI:

```sh
surreal module build --out demo.surli .
```

For faster local iteration, use debug builds. This works in the same way as `cargo build --debug` in skipping optimisation passes to speed up compiling time in exchange for lower performance.

```sh
surreal module build --debug --out demo.surli .
```

See the [module command reference](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/module) for all flags.
##  Load into SurrealDB[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#load-into-surrealdb)
Upload the `.surli` file with [`DEFINE BUCKET`](https://surrealdb.com/docs/reference/query-language/statements/define/bucket) so SurrealDB can store it, then register exported functions with [`DEFINE MODULE`](https://surrealdb.com/docs/reference/query-language/statements/define/module). The exact names and paths must match your bucket and module identifiers.
##  Test your functions[](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules#test-your-functions)
Connect with the CLI, [Surrealist](https://surrealdb.com/docs/surrealist/overview), or an SDK and invoke your functions from SurrealQL. Confirm return values and error handling match what you expect.
If something fails:
  * •
verify that experimental capabilities include `surrealism` (and `files` if using buckets/files);
  * •
verify the module was rebuilt after source changes;
  * •
verify your SurrealDB build supports the Surrealism version your module targets.

For a high-level picture of how these steps fit together, see the [Surrealism overview](https://surrealdb.com/docs/learn/extensions/plugins/overview).
