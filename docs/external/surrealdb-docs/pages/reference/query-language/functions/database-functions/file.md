---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/file"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/file"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/file

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/file

These functions can be used to work with files.  
| Function  | Description  |  
| --- | --- |  
| [`file::bucket()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filebucket)  | Returns the bucket path from a file pointer  |  
| [`file::copy()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filecopy)  | Copies the contents of a file  |  
| [`file::copy_if_not_exists()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filecopy_if_not_exists)  | Copies the contents of a file to a new file if the name is available  |  
| [`file::delete()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filedelete)  | Deletes a file  |  
| [`file::exists()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileexists)  | Checks if a file already exists  |  
| [`file::get()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileget)  | Loads a file  |  
| [`file::head()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filehead)  | Returns the metadata of a file  |  
| [`file::key()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filekey)  | Returns the key (the portion following the bucket) from a file pointer  |  
| [`file::list()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filelist)  | Returns a list of files inside a bucket  |  
| [`file::put()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileput)  | Writes bytes to a file  |  
| [`file::put_if_not_exists()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileput_if_not_exists)  | Attempts to write bytes to a file  |  
| [`file::rename()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filerename)  | Renames a file  |  
| [`file::rename_if_not_exists()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filerename_if_available)  | Renames a file if the new name is not already in use  |  
Available since: v3.0.0
##  `file::bucket`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filebucket)
API DEFINITION

```surql
file::bucket(file) -> string
```

The `file::bucket` function returns the name of the bucket in which a file is located.

```surql
file::bucket(f"my_bucket:/file_name");

DEFINE PARAM $SOME_DATABASE_FILE VALUE f"my_bucket:/file_name";
file::bucket($SOME_DATABASE_FILE);
```

Output

```surql
'my_bucket'
```

The counterpart to this function is `file::key`, which returns the latter part of a file pointer.
##  `file::copy`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filecopy)
The `file::copy` function copies the contents of a file to a new file, overwriting any existing file that has the same name as the new file.
API DEFINITION

```surql
file::copy(string)
```

Example of a file `my_book.txt` being copied to a new location `lion_witch_wardrobe.txt`:

```surql
f"my_bucket:/my_book.txt".copy("lion_witch_wardrobe.txt");
```

  

##  `file::copy_if_not_exists`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filecopy_if_not_exists)
The `file::copy_if_not_exists` function copies the contents of a file to a new file, returning an error if a file already exists that has the same name as that of the intended copy.
API DEFINITION

```surql
file::copy_if_not_exists(string)
```

Example of a file `my_book.txt` attempting to copy to a new location `lion_witch_wardrobe.txt`:

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

f"my_bucket:/lion_witch_wardrobe.txt".put("Once there were four children whose names were Peter, Susan...");
f"my_bucket:/other_book.txt".put("Um meine Geschichte zu erzählen, muß ich weit vorn anfangen.");
f"my_bucket:/other_book.txt".copy_if_not_exists("lion_witch_wardrobe.txt");
```

Output

```surql
'Operation for bucket `my_bucket` failed: Object at location lion_witch_wardrobe.txt already exists:
Object already exists at that location: lion_witch_wardrobe.txt'
```

  

##  `file::delete`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filedelete)
The `file::delete` function deletes a file.
API DEFINITION

```surql
file::delete(string)
```

Example of a file `my_book.txt` being deleted:

```surql
f"my_bucket:/my_book.txt".delete();
```

  

##  `file::exists`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileexists)
The `file::exists` function checks to see if a file exists at the path and file name indicated.
API DEFINITION

```surql
file::exists(string) -> bool
```

Example of an `IF` else `STATEMENT` used to check if a file exists before writing content to the location:

```surql
IF f"my_bucket:/my_book.txt".exists() {
    THROW "Whoops, already there!"
} ELSE {
    f"my_bucket:/my_book.txt".put("Some content")
};
```

  

##  `file::get`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileget)
The `file::get` function retrieves a file for use.
API DEFINITION

```surql
file::get(string) -> bytes
```

A retrieved file will display as bytes. If valid text, these can be cast into a `string`.

```surql
f"my_bucket:/my_book.txt".get();
<string>f"my_bucket:/my_book.txt".get();
```

Output

```surql
-------- Query --------

b"536F6D6520636F6E74656E74"

-------- Query --------

'Once there were four children whose names were Peter, Susan...'
```

  

##  `file::head`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filehead)
The `file::head` function returns the metadata for a file.
API DEFINITION

```surql
file::head() -> object
```

If a file is found, the metadata will be returned as an object with the following fields:
  * •
`e_data` (`option`): the unique identifier for the file.
  * •
`last_modified` (`datetime`)
  * •
`location` (`string`)
  * •
`size` (`int`)
  * •
`version` (`option`)

An example of this function and its output:

```surql
f"my_bucket:/my_book.txt".head();
```

Output

```surql
{
	e_tag: '1',
	key: 'my_book.txt',
	last_modified: d'2025-03-26T06:29:18.988Z',
	size: 78,
	version: NONE
}
```

  

##  `file::key`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filekey)
API DEFINITION

```surql
file::key(file) -> string
```

The `file::key` function returns the key of a file: the part of a file pointer following the bucket name.

```surql
file::key(f"my_bucket:/file_name");

DEFINE PARAM $SOME_DATABASE_FILE VALUE f"my_bucket:/file_name";
file::key($SOME_DATABASE_FILE);
```

Output

```surql
'/file_name'
```

The counterpart to this function is `file::bucket`, which returns the bucket name of a file pointer.
##  `file::list`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filelist)
API DEFINITION

```surql
file::list(string, $list_options: option<object>) -> array<object>
```

The `file::list` returns the metadata for the files inside a certain bucket. The output is an array of objects, each containing the following fields:
  * •
`file`: the pointer to the file.
  * •
`size` (`int`): the file size in bytes.
  * •
`updated` (`datetime`): the last time a change was made to the file.

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

f"my_bucket:/some_book".put("Once upon a time...");
f"my_bucket:/some_book".rename("awesome_book");
f"my_bucket:/some_book".put("In a hole in the ground lived a Hobbit.");
file::list("my_bucket");
```

Output

```surql
[
	{
		file: f"my_bucket:/awesome_book",
		size: 19,
		updated: d'2025-04-08T03:28:20.530511Z'
	},
	{
		file: f"my_bucket:/some_book",
		size: 39,
		updated: d'2025-04-08T03:28:20.530704Z'
	}
]
```

To modify the output, a second argument can be passed in that contains a single object with up to three fields:
  * •
`limit` (`int`): the maximum number of files to display.
  * •
`start` (`string`): displays files ordered after `start`.
  * •
`prefix` (`string`): displays files whose names begin with `prefix`.

Some examples of the function containing the second object and their responses:

```surql
file::list("my_bucket", { limit: 1 });
file::list("my_bucket", { limit: 0 });
```

Output

```surql
-------- Query --------
[
	{
		file: f"my_bucket:/awesome_book",
		size: 19,
		updated: d'2025-04-15T05:35:40.913221Z'
	}
]

-------- Query --------
[]
```

```surql
file::list("my_bucket", { prefix: "some" });
file::list("my_bucket", { prefix: "someBOOOEOEOK" });
```

Output

```surql
-------- Query --------
[
	{
		file: f"my_bucket:/some_book",
		size: 39,
		updated: d'2025-04-15T05:35:40.913554Z'
	}
]

-------- Query --------
[]
```

```surql
file::list("my_bucket", { start: "a" });
file::list("my_bucket", { start: "m" });
```

Output

```surql
-------- Query --------
[
	{
		file: f"my_bucket:/awesome_book",
		size: 19,
		updated: d'2025-04-15T05:55:41.973869Z'
	},
	{
		file: f"my_bucket:/some_book",
		size: 39,
		updated: d'2025-04-15T05:55:41.974370Z'
	}
]

-------- Query --------
[
	{
		file: f"my_bucket:/some_book",
		size: 39,
		updated: d'2025-04-15T05:55:41.974370Z'
	}
]
```

```surql
file::list("my_bucket", { prefix: "some", start: "a", limit: 1 });
```

Output

```surql
[
	{
		file: f"my_bucket:/some_book",
		size: 39,
		updated: d'2025-04-15T05:35:40.913554Z'
	}
]
```

##  `file::put`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileput)
The `file::put` function adds data into a file, overwriting any existing data.
API DEFINITION

```surql
file::put()
```

An example of this function followed by `file::get()` to display the contents:

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

f"my_bucket:/my_book.txt".put("Once there were four children whose names were Peter, Susan...");
f"my_bucket:/my_book.txt".put("Or were there? I don't quite remember.");
<string>f"my_bucket:/my_book.txt".get();
```

Output

```surql
"Or were there? I don't quite remember."
```

  

##  `file::put_if_not_exists`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#fileput_if_not_exists)
The `file::put` function adds data into a file, unless a file of the same name already exists.
API DEFINITION

```surql
file::put_if_not_exists()
```

An example of this function followed by `file::get()` to display the contents:

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

-- Creates file and adds data
f"my_bucket:/my_book.txt".put_if_not_exists("Once there were four children whose names were Peter, Susan...");
-- Does nothing
f"my_bucket:/my_book.txt".put_if_not_exists("Or were there? I don't quite remember.");
<string>f"my_bucket:/my_book.txt".get();
```

Output

```surql
'Once there were four children whose names were Peter, Susan...'
```

  

##  `file::rename`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filerename)
The `file::rename` function renames a file, overwriting any existing file that has the same name as the target name.
API DEFINITION

```surql
file::rename()
```

An example of a file being renamed over an existing file:

```surql
DEFINE BUCKET my_bucket BACKEND "memory";

f"my_bucket:/my_book.txt".put("Once there were four children whose names were Peter, Susan...");
f"my_bucket:/other_book.txt".put("Or were there? I don't quite remember.");
-- Rename to my_book.txt, overwriting existing file of the same name
f"my_bucket:/other_book.txt".rename("my_book.txt");
<string>f"my_bucket:/my_book.txt".get();
```

Output

```surql
"Or were there? I don't quite remember."
```

  

##  `file::rename_if_not_exists`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file#filerename_if_not_exists)
The `file::rename_if_not_exists` function renames a file, returning an error if a file already exists that has the same name as the target name.
API DEFINITION

```surql
file::rename_if_not_exists()
```

Output

```surql
-------- Query --------

'Operation for bucket `my_bucket` failed: Object at location my_book.txt already exists:
Object already exists at that location: my_book.txt'

-------- Query --------

'Once there were four children whose names were Peter, Susan...
```
