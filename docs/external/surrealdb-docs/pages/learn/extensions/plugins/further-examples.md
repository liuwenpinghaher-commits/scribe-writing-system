---
title: "https://surrealdb.com/docs/learn/extensions/plugins/further-examples"
url: "https://surrealdb.com/docs/learn/extensions/plugins/further-examples"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/extensions/plugins/further-examples

Source: https://surrealdb.com/docs/learn/extensions/plugins/further-examples

More examples of Surrealism in practice can be seen inside the [surrealism repo](https://github.com/surrealdb/surrealdb/tree/main/surrealism).
##  Surrealism Rust code demo[](https://surrealdb.com/docs/learn/extensions/plugins/further-examples#surrealism-rust-code-demo)
[This demo](https://github.com/surrealdb/surrealdb/tree/main/surrealism/demo) contains examples of the `#[surrealism]` attribute in real code.
###  Renaming an export[](https://surrealdb.com/docs/learn/extensions/plugins/further-examples#renaming-an-export)
You can rename a function on the SurrealDB side:

```rust
#[surrealism(name = "other")]
fn can_drive_bla(age: i64) -> bool {
    age >= 18
}
```

###  Setting a default export[](https://surrealdb.com/docs/learn/extensions/plugins/further-examples#setting-a-default-export)
You can make a function the default, allowing calls via the module path alone:

```rust
#[surrealism(default)]
fn def(age: i64) -> bool {
    age >= 18
}
```

###  Attaching export comments[](https://surrealdb.com/docs/learn/extensions/plugins/further-examples#attaching-export-comments)

```rust
#[surrealism(comment = "Parses a string into a number")]
fn parse_number(input: String) -> Result<i64, String> {
    input.parse::<i64>().map_err(|e| e.to_string())
}
```

##  CLI examples[](https://surrealdb.com/docs/learn/extensions/plugins/further-examples#cli-examples)
[This file](https://github.com/surrealdb/surrealdb/blob/main/surrealism/test/test.sh) shows ways to work with module archives directly from the CLI.

```bash
# Scaffold a new module project
surreal module init

# Build quickly while iterating
surreal module build --debug --out demo.surli .

# See function signature
surreal module sig --fnc can_drive demo.surli

# Run function with argument 
surreal module run --fnc can_drive --arg 17 demo.surli
```
