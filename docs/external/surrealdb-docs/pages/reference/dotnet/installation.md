---
title: "https://surrealdb.com/docs/reference/dotnet/installation"
url: "https://surrealdb.com/docs/reference/dotnet/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/installation

Source: https://surrealdb.com/docs/reference/dotnet/installation

import { packageName, fetchNugetVersion } from './utils';
export const value = await fetchNugetVersion();  
export const packageReferenceXml = ``;
#  Installation[](https://surrealdb.com/docs/reference/dotnet/installation#installation)
Before you can use this SDK in your .NET applications regardless of your environment, you need to install and import it into your project.  
This guide will walk you through the process of installing and importing the SDK into your project.
##  Install the SDK[](https://surrealdb.com/docs/reference/dotnet/installation#install-the-sdk)
  * •
Create a new project using your favorite IDE (Visual Studio, JetBrains Rider, etc...) 
  * •
or use an existing template from the `dotnet new` command.

Once ready, add the SurrealDB SDK to your dependencies:
.NET CLIPackageReference

```bash
dotnet add package SurrealDb.Net
```

  

Alternatively, you can install the SDK via the NuGet user interface provided in your IDE.  
Here is an example within Visual Studio:
![Visual Studio NuGet Package Manager](https://surrealdb.com/docs/reference/dotnet/~/assets/img/dotnet-nuget-search.png)
##  Initialize the SDK[](https://surrealdb.com/docs/reference/dotnet/installation#initialize-the-sdk)
The SDK's initialization may vary depending on the context of your project.
The de facto initialization method is to create and [consume a SurrealDbClient created manually](https://surrealdb.com/docs/reference/dotnet/core/create-a-new-connection).  
Most .NET projects provide a way to configure services using [Dependency Injection](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection), which is the recommended way to use the SDK in your application.
