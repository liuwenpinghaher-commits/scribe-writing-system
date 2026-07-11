---
title: "https://surrealdb.com/docs/reference/rust/methods/signup"
url: "https://surrealdb.com/docs/reference/rust/methods/signup"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/rust/methods/signup

Source: https://surrealdb.com/docs/reference/rust/methods/signup

3.x2.x
Signs up as a record user (formerly known as a scope user) to a specific access method.
Method Syntax

```rust
db.signup(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/signup#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signup query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/signup#example-usage)

```rust
// Use the following statement to set up the access
// 
//  DEFINE ACCESS account ON DATABASE TYPE RECORD
// 	SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
// 	SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) )
// 	DURATION FOR TOKEN 15m, FOR SESSION 12h
// ;

use surrealdb::Surreal;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Record;
use surrealdb::types::SurrealValue;

#[derive(SurrealValue)]
struct Credentials {
    email: String,
    pass: String,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;
    let jwt = db
        .signup(Record {
            namespace: "main".to_string(),
            database: "main".to_string(),
            access: "account".to_string(),
            params: Credentials {
                email: "info@surrealdb.com".to_string(),
                pass: "123456".to_string(),
            },
        })
        .await?;

    // ⚠️: It is important to note that the token should be handled securely and protected from unauthorized access.
    let token = jwt.access.as_insecure_token();
    dbg!(token);
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/signup#see-also)
  * •
[.signup() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.signup)

Signs up as a record user (formerly known as a scope user) to a specific access method.
Method Syntax

```rust
db.signup(credentials)
```

###  Arguments[](https://surrealdb.com/docs/reference/rust/methods/signup#arguments-1)  
| Argument  | Description  |  
| --- | --- |  
| `credentials`  | Variables used in a signup query.  |  
###  Example usage[](https://surrealdb.com/docs/reference/rust/methods/signup#example-usage-1)

```rust
// Use the following statement to set up the access
// 
//  DEFINE ACCESS account ON DATABASE TYPE RECORD
// 	SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
// 	SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) )
// 	DURATION FOR TOKEN 15m, FOR SESSION 12h
// ;

use serde::Serialize;
use surrealdb::engine::remote::ws::Ws;
use surrealdb::opt::auth::Record;
use surrealdb::Surreal;

#[derive(Serialize)]
struct Credentials<'a> {
    email: &'a str,
    pass: &'a str,
}

#[tokio::main]
async fn main() -> surrealdb::Result<()> {
    let db = Surreal::new::<Ws>("127.0.0.1:8000").await?;
    let jwt = db
        .signup(Record {
            namespace: "main",
            database: "main",
            access: "account",
            params: Credentials {
                email: "info@surrealdb.com",
                pass: "123456",
            },
        })
        .await?;

    // ⚠️: It is important to note that the token should be handled securely and protected from unauthorized access.
    let token = jwt.as_insecure_token();
    dbg!(token);
    Ok(())
}
```

###  See also[](https://surrealdb.com/docs/reference/rust/methods/signup#see-also-1)
  * •
[.signup() method on Docs.rs](https://docs.rs/surrealdb/latest/surrealdb/struct.Surreal.html#method.signup)
