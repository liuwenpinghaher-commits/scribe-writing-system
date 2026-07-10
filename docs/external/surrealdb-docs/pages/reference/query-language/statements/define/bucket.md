---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/bucket"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/bucket"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/bucket

Source: https://surrealdb.com/docs/reference/query-language/statements/define/bucket

Available since: v3.0.0
Note
The `DEFINE BUCKET` statement is currently experimental and subject to change. To use this feature, please ensure you are on the latest supported alpha version of SurrealDB. To enable it, either pass `--allow-experimental files` when [starting the database](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) or set the `SURREAL_CAPS_ALLOW_EXPERIMENTAL` environment variable to `files`.
The `DEFINE BUCKET` statement lets you create a bucket that can hold files.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE BUCKET [ OVERWRITE | IF NOT EXISTS ] @name
  [ BACKEND @string ]
  [ READONLY ]
  [ PERMISSIONS @expression ]
  [ COMMENT @string ]
```

DEFINEBUCKETOVERWRITEIFNOTEXISTS@name@backendPERMISSIONS@expressionCOMMENT@string
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#example-usage)
A bucket backend can be set as "memory" for non-persistent in-memory storage, or as "file:/", followed by the path, for storage on disk.
###  Memory backend[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#memory-backend)
The simplest way to experiment with a bucket for files is by using the memory backend:

```surql
DEFINE BUCKET my_bucket BACKEND "memory";
```

Once this is defined, `my_bucket` can be accessed by using a file pointer: a path prefixed by an `f`.

```surql
-- Create a file by adding some content
f"my_bucket:/my_book.txt".put("Once there were four children whose names were Peter, Susan, Edmund, and Lucy.");
-- Copy it to a new file name
f"my_bucket:/my_book.txt".copy("lion_witch_wardrobe.txt");
-- Read the file as bytes
f"my_bucket:/lion_witch_wardrobe.txt".get();
-- Cast the bytes to a string
<string>f"my_bucket:/lion_witch_wardrobe.txt".get();
```

Output

```surql
-------- Query --------

b"4F6E6365207468657265207765726520666F7572206368696C6472656E2077686F7365206E616D657320776572652050657465722C20537573616E2C2045646D756E642C20616E64204C7563792E"

-------- Query --------

'Once there were four children whose names were Peter, Susan, Edmund, and Lucy.'
```

###  File backend[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#file-backend)
A file backend can be chosen for a bucket by typing `"file:"` and then the rest of the path, if necessary.

```surql
DEFINE BUCKET my_bucket BACKEND "file:/some_directory";
DEFINE BUCKET my_bucket BACKEND "file:/some_directory";
```

A check will then be made to see if the `SURREAL_BUCKET_FOLDER_ALLOWLIST` environment variable contains the path, without which the following error will be generated.

```surql
'File access denied: /some_directory'
```

The following command can be used to start running an instance in which a bucket with a file backend can be defined.

```bash
# Unix
SURREAL_BUCKET_FOLDER_ALLOWLIST="/" surreal start --user root --pass secret --allow-experimental files

# Windows (PowerShell)
$env:SURREAL_BUCKET_FOLDER_ALLOWLIST = "/" 
surreal start --user root --pass secret --allow-experimental files
```

###  Global backend[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#global-backend)
A global backend can also be selected, allowing all namespaces and databases access to the same file storage.
If no backend is selected, the database will search for the environment variable `SURREAL_GLOBAL_BUCKET` and assign this as the global bucket. In this case, files will have a `namespace/database` prefix added (e.g. `my_global_bucket:/test_ns/test_db/somefile.txt`). A second `SURREAL_GLOBAL_BUCKET_ENFORCED` environment variable can also be used, which when set to `true` will enforce usage of the global bucket.
If a global backend is set, then a `DEFINE BUCKET` statement can be as short as `DEFINE BUCKET` plus its local name, as the rest of the logic is done via environment variables.

```surql
DEFINE BUCKET my_bucket;

-- Writes to e.g. `my_global_bucket:/test_ns/test_db/my_bucket/my_book.txt`
f"my_bucket:/my_book.txt".put("Once there were four children whose names were Peter, Susan, Edmund, and Lucy.");
```

##  Setting permissions on buckets[](https://surrealdb.com/docs/reference/query-language/statements/define/bucket#setting-permissions-on-buckets)
By default, the permissions on a bucket will be set to FULL unless otherwise specified.

```surql
DEFINE BUCKET my_bucket BACKEND "memory";
INFO FOR DB;
```

Response

```surql
{
  accesses: {},
  analyzers: {},
  apis: {},
  buckets: {
    my_bucket: "DEFINE BUCKET my_bucket BACKEND 'memory' PERMISSIONS FULL"
  },
  configs: {},
  functions: {},
  models: {},
  modules: {},
  params: {},
  sequences: {},
  tables: {},
  users: {}
}
```

You can set permissions on buckets to control who can perform operations on the files stored in them using the `PERMISSIONS` clause. In the clause three additional variables are available:
  * •
`$action`: The action to be executed (`put`, `get`, `head`, `delete`, `copy`, `rename`, `exists`, `list`)
  * •
`$file`: The [file pointer](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) of the file to be accessed
  * •
`$target`: The target [file pointer](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) in copy/rename operations

```surql
-- Set permissions for the bucket
DEFINE BUCKET admin_bucket BACKEND "memory"
  PERMISSIONS WHERE $auth.admin = true
```
