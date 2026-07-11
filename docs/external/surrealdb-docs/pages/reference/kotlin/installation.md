---
title: "https://surrealdb.com/docs/reference/kotlin/installation"
url: "https://surrealdb.com/docs/reference/kotlin/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/installation

Source: https://surrealdb.com/docs/reference/kotlin/installation

The SurrealDB SDK for Kotlin is distributed through [Maven Central](https://central.sonatype.com/) under the `com.surrealdb` group. You can add it to your project using [Gradle](https://gradle.org/) or [Maven](https://maven.apache.org/).
Note
The Kotlin SDK is in early development. The current version is `0.1.0-SNAPSHOT` and is **not yet published** to Maven Central. Until the first release is cut, the coordinates below are provisional, and you may need to build the SDK locally with `./gradlew publishToMavenLocal`.
##  Requirements[](https://surrealdb.com/docs/reference/kotlin/installation#requirements)
The SDK is a [Kotlin Multiplatform](https://kotlinlang.org/docs/multiplatform.html) library built with Kotlin `2.1.x`. It supports the following targets:  
| Target  | Requirement  |  
| --- | --- |  
| JVM  | Java 11 or later  |  
| Android  |  `minSdk` 26 or later, Java 11  |  
| iOS  |  `iosX64`, `iosArm64`, `iosSimulatorArm64`  |  
It depends on Kotlin Coroutines, [`kotlinx.serialization`](https://github.com/Kotlin/kotlinx.serialization), [`kotlinx.datetime`](https://github.com/Kotlin/kotlinx-datetime), and [Ktor](https://ktor.io/) for transport. Embedded (in-process) databases are intentionally not included in this release; connect to a running SurrealDB instance over WebSocket or HTTP instead.
##  Install the SDK[](https://surrealdb.com/docs/reference/kotlin/installation#install-the-sdk)
For a Kotlin Multiplatform project, add the metadata artifact `com.surrealdb:kotlin` to your `commonMain` source set. For a single-platform project, you may instead depend on the platform-specific variant (`kotlin-jvm`, `kotlin-android`, `kotlin-iosarm64`, `kotlin-iossimulatorarm64`, or `kotlin-iosx64`).
Gradle (Kotlin)Gradle (Groovy)Maven

```kotlin
val surrealdbVersion = "0.1.0-SNAPSHOT"

dependencies {
    implementation("com.surrealdb:kotlin:$surrealdbVersion")
}
```

```groovy
ext {
    surrealdbVersion = "0.1.0-SNAPSHOT"
}

dependencies {
    implementation "com.surrealdb:kotlin:${surrealdbVersion}"
}
```

```xml
<dependency>
    <groupId>com.surrealdb</groupId>
    <artifactId>kotlin-jvm</artifactId>
    <version>0.1.0-SNAPSHOT</version>
</dependency>
```

Note
Maven projects cannot resolve the Kotlin Multiplatform metadata artifact, so use a platform-specific variant such as `kotlin-jvm`.
##  Import the SDK[](https://surrealdb.com/docs/reference/kotlin/installation#import-the-sdk)
After installing, import the client from the `com.surrealdb.kotlin` package.

```kotlin
import com.surrealdb.kotlin.SurrealClient
import com.surrealdb.kotlin.SurrealClientConfig
```

##  Next steps[](https://surrealdb.com/docs/reference/kotlin/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/languages/kotlin) for a complete working example
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/kotlin/concepts/connecting-to-surrealdb) for connection options and protocols
  * •
[Authentication](https://surrealdb.com/docs/reference/kotlin/concepts/authentication) for signing in and managing credentials
