---
title: "https://surrealdb.com/docs/reference/java/installation"
url: "https://surrealdb.com/docs/reference/java/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/installation

Source: https://surrealdb.com/docs/reference/java/installation

The SurrealDB SDK for Java is available on the [Maven Central](https://mvnrepository.com/artifact/com.surrealdb/surrealdb) repository. You can add it to your project using Gradle or Maven.
Note
The SDK requires Java JDK version `8` or later.
###  Install the SDK[](https://surrealdb.com/docs/reference/java/installation#install-the-sdk)
Install the [SurrealDB SDK](https://mvnrepository.com/artifact/com.surrealdb/surrealdb) from Maven Central using [Gradle](https://gradle.org/) or [Maven](https://maven.apache.org/).
Gradle (Groovy)Gradle (Kotlin)Maven

```groovy
ext {
    surrealdbVersion = "2.1.1"
}

dependencies {
    implementation "com.surrealdb:surrealdb:${surrealdbVersion}"
}
```

```kotlin
val surrealdbVersion by extra("2.1.1")

dependencies {
    implementation("com.surrealdb:surrealdb:${surrealdbVersion}")
}
```

```xml
<dependency>
    <groupId>com.surrealdb</groupId>
    <artifactId>surrealdb</artifactId>
    <version>2.1.1</version>
</dependency>
```

###  Import the SDK[](https://surrealdb.com/docs/reference/java/installation#import-the-sdk)
After installing, you can access the SDK by importing from the `com.surrealdb` package.

```java
import com.surrealdb.Surreal;
```

##  Next steps[](https://surrealdb.com/docs/reference/java/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/languages/java) for a complete working example
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/java/concepts/connecting-to-surrealdb) for connection options and protocols
  * •
[Authentication](https://surrealdb.com/docs/reference/java/concepts/authentication) for signing in and managing credentials
