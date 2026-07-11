---
title: "https://surrealdb.com/docs/reference/swift/installation"
url: "https://surrealdb.com/docs/reference/swift/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/swift/installation

Source: https://surrealdb.com/docs/reference/swift/installation

Before you can use this SDK in your Swift applications, you need to add it as a dependency and import it into your project. The SDK is distributed via [Swift Package Manager](https://www.swift.org/package-manager/).
Note
The package is not yet listed on [Swift Package Index](https://swiftpackageindex.com). Until it is, add it using the repository's git URL as shown below. Once published, you will also be able to find it by searching the index.
##  Install the SDK[](https://surrealdb.com/docs/reference/swift/installation#install-the-sdk)
###  Using `Package.swift`[](https://surrealdb.com/docs/reference/swift/installation#using-packageswift)
Add the package to the `dependencies` array of your `Package.swift`, then add the `SurrealDB` product to the dependencies of your target:

```swift
// swift-tools-version:6.1
import PackageDescription

let package = Package(
    name: "YourApp",
    dependencies: [
        .package(url: "https://github.com/surrealdb/surrealdb.swift.git", from: "0.1.0"),
    ],
    targets: [
        .target(
            name: "YourTarget",
            dependencies: [
                .product(name: "SurrealDB", package: "surrealdb.swift")
            ]
        )
    ]
)
```

###  Using Xcode[](https://surrealdb.com/docs/reference/swift/installation#using-xcode)
  1. 1.
Open your project and choose **File → Add Package Dependencies…**
  2. 2.
Enter the repository URL `https://github.com/surrealdb/surrealdb.swift.git` in the search field.
  3. 3.
Select a dependency rule (for example **Up to Next Major Version**) and click **Add Package**.
  4. 4.
Choose the `SurrealDB` library product and add it to your application target.

##  Import the SDK[](https://surrealdb.com/docs/reference/swift/installation#import-the-sdk)
Once the package is resolved, import it wherever you need it:

```swift
import SurrealDB
```

##  Next steps[](https://surrealdb.com/docs/reference/swift/installation#next-steps)
See the [getting started guide](https://surrealdb.com/docs/languages/swift) to connect to a database and run your first query.
