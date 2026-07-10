---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/string"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/string"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/string

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/string

Note
Since version 3.0.0-beta, the `::is::` functions (e.g. `string::is::domain()`) now use underscores (e.g. `string::is_domain()`) to better match the intent of the function and method syntax.
These functions can be used when working with and manipulating text and string values.  
| Function  | Description  |  
| --- | --- |  
| [`string::capitalize()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringcapitalize)  | Capitalizes each word of a string  |  
| [`string::concat()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringconcat)  | Concatenates strings together  |  
| [`string::contains()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringcontains)  | Checks whether a string contains another string  |  
| [`string::ends_with()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringends_with)  | Checks whether a string ends with another string  |  
| [`string::join()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringjoin)  | Joins strings together with a delimiter  |  
| [`string::len()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringlen)  | Returns the length of a string  |  
| [`string::lowercase()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringlowercase)  | Converts a string to lowercase  |  
| [`string::matches()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringmatches)  | Performs a regex match on a string  |  
| [`string::repeat()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringrepeat)  | Repeats a string a number of times  |  
| [`string::replace()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringreplace)  | Replaces an occurrence of a string with another string  |  
| [`string::reverse()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringreverse)  | Reverses a string  |  
| [`string::slice()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringslice)  | Extracts and returns a section of a string  |  
| [`string::slug()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringslug)  | Converts a string into human and URL-friendly string  |  
| [`string::split()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsplit)  | Divides a string into an ordered list of substrings  |  
| [`string::starts_with()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringstarts_with)  | Checks whether a string starts with another string  |  
| [`string::trim()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringtrim)  | Removes whitespace from the start and end of a string  |  
| [`string::uppercase()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringuppercase)  | Converts a string to uppercase  |  
| [`string::words()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringwords)  | Splits a string into an array of separate words  |  
| [`string::distance::damerau_levenshtein()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancedamerau_levenshtein)  | Returns the Damerau–Levenshtein distance between two strings  |  
| [`string::distance::normalized_damerau_levenshtein()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancenormalizeddamerau_levenshtein)  | Returns the normalized Damerau–Levenshtein distance between two strings  |  
| [`string::distance::hamming()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancehamming)  | Returns the Hamming distance between two strings  |  
| [`string::distance::levenshtein()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancelevenshtein)  | Returns the Levenshtein distance between two strings  |  
| [`string::distance::normalized_levenshtein()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancenormalized_levenshtein)  | Returns the normalized Levenshtein distance between two strings  |  
| [`string::distance::osa()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistanceosa_distance)  | Returns the OSA (Optimal String Alignment) distance between two strings  |  
| [`string::html::encode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringhtmlencode)  | Encodes special characters into HTML entities to prevent HTML injection  |  
| [`string::html::sanitize()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringhtmlsanitize)  | Sanitizes HTML code to prevent the most dangerous subset of HTML injection  |  
| [`string::is_alphanum()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_alphanum)  | Checks whether a value has only alphanumeric characters  |  
| [`string::is_alpha()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_alpha)  | Checks whether a value has only alpha characters  |  
| [`string::is_ascii()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ascii)  | Checks whether a value has only ascii characters  |  
| [`string::is_datetime()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_datetime)  | Checks whether a string representation of a date and time matches a specified format  |  
| [`string::is_domain()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_domain)  | Checks whether a value is a domain  |  
| [`string::is_email()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_email)  | Checks whether a value is an email  |  
| [`string::is_hexadecimal()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_hexadecimal)  | Checks whether a value is hexadecimal  |  
| [`string::is_ip()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ip)  | Checks whether a value is an IP address  |  
| [`string::is_ipv4()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ipv4)  | Checks whether a value is an IP v4 address  |  
| [`string::is_ipv6()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ipv6)  | Checks whether a value is an IP v6 address  |  
| [`string::is_latitude()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_latitude)  | Checks whether a value is a latitude value  |  
| [`string::is_longitude()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_longitude)  | Checks whether a value is a longitude value  |  
| [`string::is_numeric()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_numeric)  | Checks whether a value has only numeric characters  |  
| [`string::is_record()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_record)  | Checks whether a string is a Record ID, optionally of a certain table  |  
| [`string::is_semver()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_semver)  | Checks whether a value matches a semver version  |  
| [`string::is_ulid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ulid)  | Checks whether a string is a ULID  |  
| [`string::is_url()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_url)  | Checks whether a value is a valid URL  |  
| [`string::is_uuid()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_uuid)  | Checks whether a string is a UUID  |  
| [`string::semver::compare()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemvercompare)  | Performs a comparison between two semver strings  |  
| [`string::semver::major()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemvermajor)  | Extract the major version from a semver string  |  
| [`string::semver::minor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverminor)  | Extract the minor version from a semver string  |  
| [`string::semver::patch()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverpatch)  | Extract the patch version from a semver string  |  
| [`string::semver::inc::major()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincmajor)  | Increment the major version of a semver string  |  
| [`string::semver::inc::minor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincminor)  | Increment the minor version of a semver string  |  
| [`string::semver::inc::patch()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincpatch)  | Increment the patch version of a semver string  |  
| [`string::semver::set::major()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetmajor)  | Set the major version of a semver string  |  
| [`string::semver::set::minor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetminor)  | Set the minor version of a semver string  |  
| [`string::semver::set::patch()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetpatch)  | Set the patch version of a semver string  |  
| [`string::similarity::fuzzy()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityfuzzy)  | Return the similarity score of fuzzy matching strings  |  
| [`string::similarity::jaro()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityjaro)  | Returns the Jaro similarity between two strings  |  
| [`string::similarity::jaro_winkler()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityjarowinkler)  | Return the Jaro-Winkler similarity between two strings  |  
##  `string::capitalize`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringcapitalize)
Available since: v3.0.0
The `string::capitalize` function capitalizes the first letter of each word in a string.
API DEFINITION

```surql
string::capitalize(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
string::capitalize("how to cook for forty humans");

-- 'How To Cook For Forty Humans'
```

  

##  `string::concat`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringconcat)
The `string::concat` function concatenates values together into a single string.
API DEFINITION

```surql
string::concat(value, ...) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::concat('this', ' ', 'is', ' ', 'a', ' ', 'test');

-- 'this is a test'
```

Any values received that are not a string will be stringified before concatenation.

```surql
string::concat(true, [], false);
-- ['true[]false']
```

Note that the stringified inputs are based on their actual computed values, and not the input tokens themselves. Even an expression can be 

```surql
string::concat(not, actual, values);
-- ['NONENONENONE']

string::concat(CREATE ONLY person:aeon RETURN VALUE id, ' is ', 'cool!');
-- ['person:aeon is cool!']
```

  

##  `string::contains`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringcontains)
The `string::contains` function checks whether a string contains another string.
API DEFINITION

```surql
string::contains(string, $predicate: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::contains('abcdefg', 'cde');

-- true
```

  

##  `string::ends_with`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringends_with)
Note
This function was known as `string::endsWith` in versions of SurrealDB before 2.0. The behaviour has not changed.
The `string::ends_with` function checks whether a string ends with another string.
API DEFINITION

```surql
string::ends_with(string, $other: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::ends_with('some test', 'test');

-- true
```

  

##  `string::join`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringjoin)
The `string::join` function joins strings or stringified values together with a delimiter.
If you want to join an array of strings use [`array::join`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayjoin).
API DEFINITION

```surql
string::join($delimiter: value, value...) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::join(', ', 'a', 'list', 'of', 'items');

-- "a, list, of, items"
```

  

##  `string::len`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringlen)
The `string::len` function returns the length of a given string in characters.
API DEFINITION

```surql
string::len(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::len('this is a test');

-- 14
```

  

##  `string::lowercase`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringlowercase)
The `string::lowercase` function converts a string to lowercase.
API DEFINITION

```surql
string::lowercase(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::lowercase('THIS IS A TEST');

-- 'this is a test'
```

  

##  `string::matches`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringmatches)
The `string::matches` function performs a regex match on a string.
API DEFINITION

```surql
string::matches(string, $match_with: string|regex) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
[
  string::matches("grey", "gr(a|e)y"), 
  string::matches("gray", "gr(a|e)y")
];

-- [true, true]
```

The second argument can be either a string or a [regex](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex).

```surql
LET $input = "grey";
LET $string = "gr(a|e)y";
LET $regex = <regex>"gr(a|e)y";

[type::of($string), type::of($regex)];
-- ['string', 'regex']

[
  string::matches($input, $string),
  string::matches($input, $regex),
];
-- [true, true]
```

  

##  `string::repeat`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringrepeat)
The `string::repeat` function repeats a string a number of times. The repeat count must be non-negative; negative values return an error.
API DEFINITION

```surql
string::repeat(string, $times: number) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::repeat('test', 3);

-- 'testtesttest'
```

  

##  `string::replace`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringreplace)
The `string::replace` function replaces an occurrence of a string with another string.
Before 2.3After 2.3
API DEFINITION

```surql
string::replace(string, $from: string, $to: string) -> string
```

API DEFINITION

```surql
string::replace(string, $from: string|regex, $to: string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::replace('this is a test', 'a test', 'awesome');

-- 'this is awesome'
```

As [`regexes`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex) are their own data type, the second argument can also be a regex instead of a string.

```surql
RETURN string::replace('Many languages only use consonants in their writing', <regex>'a|e|i|o|u', '');
```

Output

```surql
'Mny lnggs nly s cnsnnts n thr wrtng'
```

  

##  `string::reverse`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringreverse)
The `string::reverse` function reverses a string.
API DEFINITION

```surql
string::reverse(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::reverse('this is a test');

-- 'tset a si siht'
```

  

##  `string::slice`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringslice)
The `string::slice` function extracts and returns a section of a string.
API DEFINITION

```surql
string::slice(string, $from: number, $to: number) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::slice('this is a test', 10, 4);

"test"
```

  

##  `string::slug`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringslug)
The `string::slug` function converts a string into a human and URL-friendly string.
API DEFINITION

```surql
string::slug(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::slug('SurrealDB Cloud has launched!!! #ai_native_database #awesome');

-- 'surrealdb-cloud-has-launched-ai_native_database-awesome'
```

  

##  `string::split`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsplit)
The `string::split` function splits a string by a given delimiter.
API DEFINITION

```surql
string::split(string, $delimiter: string) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::split('this, is, a, list', ', ');

-- ['this', 'is', 'a', 'list']
```

  

##  `string::starts_with`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringstarts_with)
Note
This function was known as `string::startsWith` in versions of SurrealDB before 2.0. The behaviour has not changed.
The `string::starts_with` function checks whether a string starts with another string.
API DEFINITION

```surql
string::starts_with(string, $predicate: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::starts_with('some test', 'some');

-- true
```

  

##  `string::trim`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringtrim)
The `string::trim` function removes whitespace from the start and end of a string.
API DEFINITION

```surql
string::trim(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::trim('    this is a test    ');

-- 'this is a test'
```

  

##  `string::uppercase`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringuppercase)
The `string::uppercase` function converts a string to uppercase.
API DEFINITION

```surql
string::uppercase(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::uppercase('this is a test');

-- 'THIS IS A TEST'
```

##  `string::words`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringwords)
The `string::words` function splits a string into an array of separate words.
API DEFINITION

```surql
string::words(string) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::words('this is a test');

-- ['this', 'is', 'a', 'test']
```

##  `string::distance::damerau_levenshtein`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancedamerau_levenshtein)
The `string::distance::damerau_levenshtein` function returns the Damerau-Levenshtein distance between two strings.
API DEFINITION

```surql
string::distance::damerau_levenshtein(string, string) -> int
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 0
string::distance::damerau_levenshtein($first, $same);
-- Returns 7
string::distance::damerau_levenshtein($first, $close);
-- Returns 34
string::distance::damerau_levenshtein($first, $different);
-- Returns 38
string::distance::damerau_levenshtein($first, $short);
```

##  `string::distance::normalized_damerau_levenshtein`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancenormalized_damerau_levenshtein)
The `string::distance::normalized_damerau_levenshtein` function returns the normalized Damerau-Levenshtein distance between two strings. Normalized means that identical strings will return a score of 1, with less similar strings returning lower numbers as the distance grows.
API DEFINITION

```surql
string::distance::normalized_damerau_levenshtein(string, string) -> float
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 1f
string::distance::normalized_damerau_levenshtein($first, $same);
-- Returns 0.8409090909090909f
string::distance::normalized_damerau_levenshtein($first, $close);
-- Returns 0.2272727272727273f
string::distance::normalized_damerau_levenshtein($first, $different);
-- Returns 0.13636363636363635f
string::distance::normalized_damerau_levenshtein($first, $short);
```

##  `string::distance::hamming`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancehamming)
The `string::distance::hamming` function returns the Hamming distance between two strings of equal length.
API DEFINITION

```surql
string::distance::hamming(string, string) -> int
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 0
string::distance::hamming($first, $same);
-- Returns 7
string::distance::hamming($first, $close);
-- Returns 40
string::distance::hamming($first, $different);
-- Error: strings must be of equal length
string::distance::hamming($first, $short);
```

##  `string::distance::levenshtein`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancelevenshtein)
The `string::distance::levenshtein` function returns the Levenshtein distance between two strings.
API DEFINITION

```surql
string::distance::levenshtein(string, string) -> int
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 0
string::distance::levenshtein($first, $same);
-- Returns 7
string::distance::levenshtein($first, $close);
-- Returns 35
string::distance::levenshtein($first, $different);
-- Returns 38
string::distance::levenshtein($first, $short);
```

##  `string::distance::normalized_levenshtein`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistancenormalized_levenshtein)
The `string::distance::normalized_levenshtein` function returns the normalized Levenshtein distance between two strings. Normalized means that identical strings will return a score of 1, with less similar strings returning lower numbers as the distance grows.
API DEFINITION

```surql
string::distance::normalized_levenshtein(string, string) -> float
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 1
string::distance::normalized_levenshtein($first, $same);
-- Returns 0.8409090909090909f
string::distance::normalized_levenshtein($first, $close);
-- Returns 0.20454545454545459f
string::distance::normalized_levenshtein($first, $different);
-- Returns 0.13636363636363635f
string::distance::normalized_levenshtein($first, $short);
```

##  `string::distance::osa`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringdistanceosa)
Note
This function was known as `string::distance::osa_distance` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::distance::osa_distance` function returns the OSA (Optimal String Alignment) distance between two strings.
API DEFINITION

```surql
string::distance::normalized_levenshtein(string, string) -> int
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 0
string::distance::osa($first, $same);
-- Returns 7
string::distance::osa($first, $close);
-- Returns 34
string::distance::osa($first, $different);
-- Returns 38
string::distance::osa($first, $short);
```

##  `string::html::encode`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringhtmlencode)
The `string::html::encode` function encodes special characters into HTML entities to prevent HTML injection. It is recommended to use this function in most cases when retrieving any untrusted content that may be rendered inside of an HTML document. You can learn more about its behavior from the [original implementation](https://docs.rs/ammonia/latest/ammonia/fn.clean_text.html).
API DEFINITION

```surql
string::html::encode(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::html::encode("<h1>Safe Title</h1><script>alert('XSS')</script><p>Safe paragraph. Not safe <span onload='logout()'>event</span>.</p>");

-- '&lt;h1&gt;Safe&#32;Title&lt;&#47;h1&gt;&lt;script&gt;alert(&apos;XSS&apos;)&lt;&#47;script&gt;&lt;p&gt;Safe&#32;paragraph.&#32;Not&#32;safe&#32;&lt;span&#32;onload&#61;&apos;logout()&apos;&gt;event&lt;&#47;span&gt;.&lt;&#47;p&gt;'
```

  

##  `string::html::sanitize`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringhtmlsanitize)
The `string::html::sanitize` function sanitizes HTML code to prevent the most dangerous subset of HTML injection that can lead to attacks like cross-site scripting, layout breaking or clickjacking. This function will keep any other HTML syntax intact in order to support user-generated content that needs to contain HTML styling. It is only recommended to rely on this function if you want to allow the creators of the content to have some control over its HTML styling. You can learn more about its behavior from the [original implementation](https://docs.rs/ammonia/latest/ammonia/fn.clean.html).
API DEFINITION

```surql
string::html::sanitize(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::html::sanitize("<h1>Safe Title</h1><script>alert('XSS')</script><p>Safe paragraph. Not safe <span onload='logout()'>event</span>.</p>");

-- '<h1>Safe Title</h1><p>Safe paragraph. Not safe <span>event</span>.</p>'
```

  

##  `string::is_alphanum`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_alphanum)
Note
This function was known as `string::is::alphanum` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_alphanum` function checks whether a value has only alphanumeric characters.
API DEFINITION

```surql
string::is_alphanum(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_alphanum("ABC123");

-- true
```

  

##  `string::is_alpha`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_alpha)
Note
This function was known as `string::is::alpha` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_alpha` function checks whether a value has only alpha characters.
API DEFINITION

```surql
string::is_alpha(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_alpha("ABCDEF");

-- true
```

  

##  `string::is_ascii`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ascii)
Note
This function was known as `string::is::ascii` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_ascii` function checks whether a value has only ascii characters.
API DEFINITION

```surql
string::is_ascii(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_ascii("ABC123"); -- true
'𓀀'.is_ascii(); -- false
```

  

##  `string::is_datetime`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_datetime)
Note
This function was known as `string::is::datetime` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_datetime` function checks whether a string representation of a date and time matches either the [datetime](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) format or a user-specified format.
API DEFINITION

```surql
string::is_datetime(string, $format: option<string>) -> bool
```

If no second argument is specified, this function will check if a string is a datetime or a format that can be cast into a datetime.

```surql
'1970-01-01'.is_datetime();  -- true
'1970-Jan-01'.is_datetime(); -- false
```

With a second argument, this function will check if a string matches the user-specified format. The output `false` may be returned in this case even if the input string is a valid datetime.

```surql
RETURN string::is_datetime("2015-09-05 23:56:04", "%Y-%m-%d %H:%M:%S");
-- true

RETURN string::is_datetime("1970-01-01", "%Y-%m-%d %H:%M:%S");
-- false
```

This can be useful when validating datetimes obtained from other sources that do not use the [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) format.

```surql
RETURN string::is_datetime("5sep2024pm012345.6789", "%d%b%Y%p%I%M%S%.f");
```

Response

```surql
true
```

```surql
RETURN string::is_datetime("23:56:00 2015-09-05", "%Y-%m-%d %H:%M");
```

Response

```surql
false
```

[View all format options](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/formatters)
  

##  `string::is_domain`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_domain)
Note
This function was known as `string::is::domain` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_domain` function checks whether a value is a domain.
API DEFINITION

```surql
string::is_domain(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_domain("surrealdb.com");

-- true
```

  

##  `string::is_email`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_email)
Note
This function was known as `string::is::email` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_email` function checks whether a value is an email.
API DEFINITION

```surql
string::is_email(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_email("info@surrealdb.com");

-- true
```

  

##  `string::is_hexadecimal`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_hexadecimal)
Note
This function was known as `string::is::hexadecimal` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_hexadecimal` function checks whether a value is hexadecimal.
API DEFINITION

```surql
string::is_hexadecimal(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_hexadecimal("ff009e");

-- true
```

  

##  `string::is_ip`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ip)
Note
This function was known as `string::is::ip` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_ip` function checks whether a value is an IP address.
API DEFINITION

```surql
string::is_ip(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_ip("192.168.0.1");

-- true
```

  

##  `string::is_ipv4`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ipv4)
Note
This function was known as `string::is::ipv4` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_ipv4` function checks whether a value is an IP v4 address.
API DEFINITION

```surql
string::is_ipv4(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_ipv4("192.168.0.1");

-- true
```

  

##  `string::is_ipv6`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ipv6)
Note
This function was known as `string::is::ipv6` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_ipv6` function checks whether a value is an IP v6 address.
API DEFINITION

```surql
string::is_ipv6(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334");

-- true
```

  

##  `string::is_latitude`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_latitude)
Note
This function was known as `string::is::latitude` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_latitude` function checks whether a value is a latitude value.
API DEFINITION

```surql
string::is_latitude(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_latitude("-0.118092");

-- true
```

  

##  `string::is_longitude`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_longitude)
Note
This function was known as `string::is::longitude` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_longitude` function checks whether a value is a longitude value.
API DEFINITION

```surql
string::is_longitude(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_longitude("51.509865");

-- true
```

  

##  `string::is_numeric`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_numeric)
Note
This function was known as `string::is::numeric` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_numeric` function checks whether a value has only numeric characters.
API DEFINITION

```surql
string::is_numeric(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_numeric("1484091748");

-- true
```

  

##  `string::is_semver`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_semver)
Note
This function was known as `string::is::semver` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_semver` function checks whether a value matches a semver version.
API DEFINITION

```surql
string::is_semver(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_semver("1.0.0");

-- true
```

  

##  `string::is_ulid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_ulid)
Note
This function was known as `string::is::ulid` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_ulid` function checks whether a string is a ULID.
API DEFINITION

```surql
string::is_ulid(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_ulid("01JCJB3TPQ50XTG32WM088NKJD");

-- true
```

  

##  `string::is_url`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_url)
Note
This function was known as `string::is::url` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_url` function checks whether a value is a valid URL.
API DEFINITION

```surql
string::is_url(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_url("https://surrealdb.com");

-- true
```

  

##  `string::is_record`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_record)
Note
This function was known as `string::is::record` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_record` function checks whether a string is a Record ID.
API DEFINITION

```surql
string::is_record(string, $table_name: option<string|table>) -> bool
```

The second argument is optional and can be used to specify the table name that the record ID should belong to. If the table name is provided, the function will check if the record ID belongs to that table only.

```surql
RETURN string::is_record("person:test");           -- true
RETURN string::is_record("person:test", "person"); -- true
RETURN string::is_record("person:test", type::table("personn")); -- false
RETURN string::is_record("person:test", "other");  -- false
RETURN string::is_record("not a record id");       -- false
```

  

##  `string::is_uuid`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringis_uuid)
Note
This function was known as `string::is::uuid` in versions of SurrealDB before 3.0.0. The behaviour has not changed.
The `string::is_uuid` function checks whether a string is a UUID.
API DEFINITION

```surql
string::is_uuid(string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::is_uuid("018a6680-bef9-701b-9025-e1754f296a0f");

-- true
```

  

##  `string::semver::compare`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemvercompare)
The `string::semver::compare` function performs a comparison on two semver strings and returns a number.
A value of `-1` indicates the first version is lower than the second, `0` indicates both versions are equal, and `1` indicates the first version is higher than the second.
API DEFINITION

```surql
string::semver::compare(string, $other: string) -> 1|0|-1
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::compare("1.0.0", "1.3.5");
-- Returns -1
RETURN string::semver::compare("1.0.0", "1.0.0");
-- Returns 0
RETURN string::semver::compare("3.0.0-beta.4", "2.6.0");
-- Returns 1
```

  

##  `string::semver::major`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemvermajor)
The `string::semver::major` function extracts the major number out of a semver string.
API DEFINITION

```surql
string::semver::major(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::major("3.2.6");

-- 3
```

  

##  `string::semver::minor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverminor)
The `string::semver::minor` function extracts the minor number out of a semver string.
API DEFINITION

```surql
string::semver::minor(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::minor("3.2.6");

-- 2
```

  

##  `string::semver::patch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverpatch)
The `string::semver::patch` function extracts the patch number out of a semver string.
API DEFINITION

```surql
string::semver::patch(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::patch("3.2.6");

-- 6
```

  

##  `string::semver::inc::major`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincmajor)
The `string::semver::inc::major` function increments the major number of a semver string. As a result, the minor and patch numbers are reset to zero.
API DEFINITION

```surql
string::semver::inc::major(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::inc::major("1.2.3");

-- '2.0.0'
```

  

##  `string::semver::inc::minor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincminor)
The `string::semver::inc::minor` function increments the minor number of a semver string. As a result, the patch number is reset to zero.
API DEFINITION

```surql
string::semver::inc::minor(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::inc::minor("1.2.3");

-- '1.3.0'
```

  

##  `string::semver::inc::patch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemverincpatch)
The `string::semver::inc::patch` function increments the patch number of a semver string.
API DEFINITION

```surql
string::semver::inc::patch(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::inc::patch("1.2.3");

-- '1.2.4'
```

  

##  `string::semver::set::major`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetmajor)
The `string::semver::set::major` function sets the major number of a semver string without changing the minor and patch numbers. The numeric argument must be non-negative.
API DEFINITION

```surql
string::semver::set::major(string, $major: number) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::set::major("1.2.3", 9);

-- '9.2.3'
```

  

##  `string::semver::set::minor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetminor)
The `string::semver::set::minor` function sets the minor number of a semver string without changing the major and patch numbers. The numeric argument must be non-negative.
API DEFINITION

```surql
string::semver::set::minor(string, $minor: number) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::set::minor("1.2.3", 9);

-- '1.9.3'
```

  

##  `string::semver::set::patch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsemversetpatch)
The `string::semver::set::patch` function sets the patch number of a semver string without changing the major and minor numbers. The numeric argument must be non-negative.
API DEFINITION

```surql
string::semver::set::patch(string, $patch: number) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN string::semver::set::patch("1.2.3", 9);

-- '1.2.9'
```

  

##  `string::similarity::fuzzy`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityfuzzy)
API DEFINITION

```surql
string::similarity::fuzzy(string, string) -> int
```

The `string::similarity::fuzzy` function allows a comparison of similarity to be made. Any value that is greater than 0 is considered a fuzzy match.

```surql
-- returns 51
RETURN string::similarity::fuzzy("DB", "DB");
-- returns 47
RETURN string::similarity::fuzzy("DB", "db");
```

The similarity score is not based on a single score such as 1 to 100, but is built up over the course of the algorithm used to compare one string to another and will be higher for longer strings. As a result, similarity can only be compared from a single string to a number of possible matches, but not multiple strings to a number of possible matches.
While the first two uses of the function in the following example compare identical strings, the longer string returns a much higher fuzzy score.

```surql
-- returns 51
string::similarity::fuzzy("DB", "DB");
-- returns 2935
string::similarity::fuzzy(
  "SurrealDB Cloud is now live! We are excited to announce that we are inviting users from the waitlist to join. Stay tuned for your invitation!", "SurrealDB Cloud is now live! We are excited to announce that we are inviting users from the waitlist to join. Stay tuned for your invitation!"
);
-- returns 151 despite nowhere close to exact match
string::similarity::fuzzy(
  "SurrealDB Cloud is now live! We are excited to announce that we are inviting users from the waitlist to join. Stay tuned for your invitation!", "Surreal"
);
```

A longer example showing a comparison of similarity scores to one another:

```surql
LET $original = "SurrealDB";
LET $strings = ["SurralDB", "surrealdb", "DB", "Surreal", "real", "basebase", "eel", "eal"];

FOR $string IN $strings {
    LET $score = string::similarity::fuzzy($original, $string);
    IF $score > 0 {
        CREATE comparison SET of = $original + '\t' + $string,
        score = $score
    };
};

SELECT of, score FROM comparison ORDER BY score DESC;
```

Response

```surql
[
	{
		of: 'SurrealDB	surrealdb',
		score: 187
	},
	{
		of: 'SurrealDB	SurralDB',
		score: 165
	},
	{
		of: 'SurrealDB	Surreal',
		score: 151
	},
	{
		of: 'SurrealDB	real',
		score: 75
	},
	{
		of: 'SurrealDB	eal',
		score: 55
	},
	{
		of: 'SurrealDB	DB',
		score: 41
	}
]
```

##  `string::similarity::jaro`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityjaro)
The `string::similarity::jaro` function returns the Jaro similarity between two strings. Two strings that are identical have a score of 1, while less similar strings will have lower scores as the distance between them increases.
API DEFINITION

```surql
string::similarity::jaro(string, string) -> float
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 1
string::similarity::jaro($first, $same);
-- Returns 0.8218673218673219f
string::similarity::jaro($first, $close);
-- Returns 0.6266233766233765f
string::similarity::jaro($first, $different);
-- Returns 0.4379509379509379f
string::similarity::jaro($first, $short);
```

##  `string::similarity::jaro_winkler`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringsimilarityjaro_winkler)
The `string::similarity::jaro_winkler` function returns the Jaro-Winkler similarity between two strings. Two strings that are identical have a score of 1, while less similar strings will have lower scores as the distance between them increases.
API DEFINITION

```surql
string::similarity::jaro_winkler(string, string) -> float
```

The following examples shows this function, and its output in comparison with a number of strings.

```surql
LET $first     = "In a hole in the ground there lived a hobbit";
LET $same      = "In a hole in the ground there lived a hobbit";
LET $close     = "In a hole in the GROUND there lived a Hobbit";
LET $different = "A narrow passage holds four hidden treasures";
LET $short     = "Hi I'm Brian";

-- Returns 0
string::similarity::jaro_winkler($first, $same);
-- Returns 0.8931203931203932f
string::similarity::jaro_winkler($first, $close);
-- Returns 0.6266233766233765f
string::similarity::jaro_winkler($first, $different);
-- Returns 0.4379509379509379f
string::similarity::jaro_winkler($first, $short);
```

##  Method chaining[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#method-chaining)
Method chaining allows functions to be called using the `.` dot operator on a value of a certain type instead of the full path of the function followed by the value.

```surql
-- Traditional syntax
string::is_alphanum("MyStrongPassword123");

-- Method chaining syntax
"MyStrongPassword123".is_alphanum();
```

Response

```surql
true
```

This is particularly useful for readability when a function is called multiple times.

```surql
-- Traditional syntax
string::concat(
  string::uppercase(
    string::replace(
      string::replace("I'll send you a check for the catalog", "ck", "que")
    , "og", "ogue")
  )
, "!!!!");

-- Method chaining syntax
"I'll send you a check for the catalog"
  .replace("ck", "que")
  .replace("og", "ogue")
  .uppercase()
  .concat("!!!!");
```

Response

```surql
"I'LL SEND YOU A CHEQUE FOR THE CATALOGUE!!!!"
```
