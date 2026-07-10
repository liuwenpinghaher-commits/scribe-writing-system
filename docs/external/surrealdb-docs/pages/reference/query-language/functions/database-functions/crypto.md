---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto

These functions can be used when hashing data, encrypting data, and for securely authenticating users into the database.  
| Function  | Description  |  
| --- | --- |  
| [`crypto::blake3()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoblake3)  | Returns the blake3 hash of a value  |  
| [`crypto::joaat()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptojoaat)  | Returns the joaat hash of a value  |  
| [`crypto::md5()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptomd5)  | Returns the md5 hash of a value  |  
| [`crypto::sha1()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha1)  | Returns the sha1 hash of a value  |  
| [`crypto::sha256()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha256)  | Returns the sha256 hash of a value  |  
| [`crypto::sha512()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha512)  | Returns the sha512 hash of a value  |  
| [`crypto::argon2::compare()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoargon2compare)  | Compares an argon2 hash to a password  |  
| [`crypto::argon2::generate()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoargon2generate)  | Generates a new argon2 hashed password  |  
| [`crypto::bcrypt::compare()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptobcryptcompare)  | Compares an bcrypt hash to a password  |  
| [`crypto::bcrypt::generate()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptobcryptgenerate)  | Generates a new bcrypt hashed password  |  
| [`crypto::pbkdf2::compare()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptopbkdf2compare)  | Compares an pbkdf2 hash to a password  |  
| [`crypto::pbkdf2::generate()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptopbkdf2generate)  | Generates a new pbkdf2 hashed password  |  
| [`crypto::scrypt::compare()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoscryptcompare)  | Compares an scrypt hash to a password  |  
| [`crypto::scrypt::generate()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoscryptgenerate)  | Generates a new scrypt hashed password  |  
##  `crypto::blake3`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoblake3)
The `crypto::blake3` function returns the blake3 hash of the input value.
API DEFINITION

```surql
crypto::blake3(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::blake3("tobie");

-- '85052e9aab1b67b6622d94a08441b09fd5b7aca61ee360416d70de5da67d86ca'
```

  

##  `crypto::joaat`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptojoaat)
Available since: v3.0.0
The `crypto::joaat` function returns the joaat hash of the input value.
API DEFINITION

```surql
crypto::joaat(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::joaat("tobie");

-- 2129482046
```

  

##  `crypto::md5`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptomd5)
The `crypto::md5` function returns the md5 hash of the input value.
API DEFINITION

```surql
crypto::md5(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::md5("tobie");

-- "4768b3fc7ac751e03a614e2349abf3bf"
```

  

##  `crypto::sha1`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha1)
The `crypto::sha1` function returns the sha1 hash of the input value.
API DEFINITION

```surql
crypto::sha1(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::sha1("tobie");

-- "c6be709a1b6429472e0c5745b411f1693c4717be"
```

  

##  `crypto::sha256`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha256)
The `crypto::sha256` function returns the sha256 hash of the input value.
API DEFINITION

```surql
crypto::sha256(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::sha256("tobie");

-- "33fe1859daba927ea5674813adc1cf34b9e2795f2b7e91602fae19c0d0c493af"
```

  

##  `crypto::sha512`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptosha512)
The `crypto::sha512` function returns the sha512 hash of the input value.
API DEFINITION

```surql
crypto::sha512(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::sha512("tobie");

"39f0160c946c4c53702112d6ef3eea7957ea8e1c78787a482a89f8b0a8860a20ecd543432e4a187d9fdcd1c415cf61008e51a7e8bf2f22ac77e458789c9cdccc"
```

  

##  `crypto::argon2::compare`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoargon2compare)
The `crypto::argon2::compare` function compares a hashed-and-salted argon2 password value with an unhashed password value.
API DEFINITION

```surql
crypto::argon2::compare(string, $against: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $hash = "$argon2id$v=19$m=4096,t=3,p=1$pbZ6yJ2rPJKk4pyEMVwslQ$jHzpsiB+3S/H+kwFXEcr10vmOiDkBkydVCSMfRxV7CA";
LET $pass = "this is a strong password";
RETURN crypto::argon2::compare($hash, $pass);

-- true
```

  

##  `crypto::argon2::generate`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoargon2generate)
The `crypto::argon2::generate` function hashes and salts a password using the argon2 hashing algorithm.
Important
At this time, there is no way to customize the parameters for this function. This applies to: memory, iterations and parallelism.
API DEFINITION

```surql
crypto::argon2::generate(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::argon2::generate("this is a strong password");

"$argon2id$v=19$m=4096,t=3,p=1$pbZ6yJ2rPJKk4pyEMVwslQ$jHzpsiB+3S/H+kwFXEcr10vmOiDkBkydVCSMfRxV7CA"
```

  

##  `crypto::bcrypt::compare`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptobcryptcompare)
The `crypto::bcrypt::compare` function compares a hashed-and-salted bcrypt password value with an unhashed password value.
API DEFINITION

```surql
crypto::bcrypt::compare(string, $against: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $hash = "$2b$12$OD7hrr1Hycyk8NUwOekYY.cogCICpUnwNvDZ9NiC1qCPHzpVAQ9BO";
LET $pass = "this is a strong password";
RETURN crypto::bcrypt::compare($hash, $pass);

true
```

  

##  `crypto::bcrypt::generate`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptobcryptgenerate)
The `crypto::bcrypt::generate` function hashes and salts a password using the bcrypt hashing algorithm.
Important
At this time, there is no way to customize the work factor for bcrypt.
API DEFINITION

```surql
crypto::bcrypt::generate(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::bcrypt::generate("this is a strong password");

"$2b$12$OD7hrr1Hycyk8NUwOekYY.cogCICpUnwNvDZ9NiC1qCPHzpVAQ9BO"
```

  

##  `crypto::pbkdf2::compare`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptopbkdf2compare)
The `crypto::pbkdf2::compare` function compares a hashed-and-salted pbkdf2 password value with an unhashed password value.
API DEFINITION

```surql
crypto::pbkdf2::compare(string, $against: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $hash = "$pbkdf2-sha256$i=10000,l=32$DBURRPJODKEt0IId1Lqe+w$Ve8Z00mibHDSKLbyKTceEBBcDpGoK0AEUl7QzDTIec4";
LET $pass = "this is a strong password";
RETURN crypto::pbkdf2::compare($hash, $pass);

true
```

  

##  `crypto::pbkdf2::generate`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptopbkdf2generate)
The `crypto::pbkdf2::generate` function hashes and salts a password using the pbkdf2 hashing algorithm.
Important
At this time, there is no way to customize the number of iterations for pbkdf2.
API DEFINITION

```surql
crypto::pbkdf2::generate(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::pbkdf2::generate("this is a strong password");

"$pbkdf2-sha256$i=10000,l=32$DBURRPJODKEt0IId1Lqe+w$Ve8Z00mibHDSKLbyKTceEB"
```

  

##  `crypto::scrypt::compare`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoscryptcompare)
The `crypto::scrypt::compare` function compares a hashed-and-salted scrypt password value with an unhashed password value.
API DEFINITION

```surql
crypto::scrypt::compare(string, $against: string) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $hash = "$scrypt$ln=15,r=8,p=1$8gl7bipl0FELTy46YJOBrw$eRcS1qR22GI8VHo58WOXn9JyfDivGo5yTJFvpDyivuw";
LET $pass = "this is a strong password";
RETURN crypto::scrypt::compare($hash, $pass);

true
```

  

##  `crypto::scrypt::generate`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto#cryptoscryptgenerate)
The `crypto::scrypt::generate` function hashes and salts a password using the scrypt hashing algorithm.
Important
At this time, there is no way to customize the parameters for this function. This applies to: cost parameter, block size and parallelism.
API DEFINITION

```surql
crypto::scrypt::generate(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN crypto::scrypt::generate("this is a strong password");

"$scrypt$ln=15,r=8,p=1$8gl7bipl0FELTy46YJOBrw$eRcS1qR22GI8VHo58WOXn9JyfDivGo5yTJFvpDyivuw"
```
