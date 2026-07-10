---
title: "https://surrealdb.com/docs/reference/dotnet/core/dependency-injection"
url: "https://surrealdb.com/docs/reference/dotnet/core/dependency-injection"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/dependency-injection

Source: https://surrealdb.com/docs/reference/dotnet/core/dependency-injection

The .NET SDK also support Dependency Injection to ease the use of `SurrealDbClient` and `SurrealDbSession` in your application.
##  Create a new project[](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection#create-a-new-project)
Let's start by creating a new ASP.NET Core web app.

```sh
dotnet new webapp -o SurrealDbWeatherApi
cd SurrealDbWeatherApi
dotnet add package SurrealDb.Net
```

##  Define a connection string[](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection#define-a-connection-string)
Open `appsettings.Development.json` and replace everything in there with the following code.  
We have added a new Connection String called `SurrealDB` with the default configuration.

```json
{
  "AllowedHosts": "*",
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "ConnectionStrings": {
    "SurrealDB": "Server=http://127.0.0.1:8000;Namespace=test;Database=test;Username=root;Password=root"
  }
}
```

##  Register services[](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection#register-services)
Open `Program.cs` and replace everything in there with the following code.  
This code is using the `AddSurreal()` extension method to inject services automatically.  
Notice that all we have to do is one line of code to configure the SurrealDB client with the previously set Connection String.
Note
By default, this function will register both `ISurrealDbSession` and `SurrealDbSession` using the `Scoped` service lifetime. This mean that a new isolated SurrealDB session is created per scope.

```csharp
var builder = WebApplication.CreateBuilder(args);

var services = builder.Services;
var configuration = builder.Configuration;

services.AddControllers();
services.AddEndpointsApiExplorer();
services.AddSwaggerGen();
services.AddSurreal(configuration.GetConnectionString("SurrealDB"));

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();

app.MapControllers();

app.Run();
```

Note
In this example, we use a [Connection String](https://surrealdb.com/docs/reference/dotnet/core/connection-strings) to configure services.  
This is the most convenient way to initialize the `SurrealDbClient` in your application.  
You can always choose to construct a Connection String manually via a `SurrealDbOptionsBuilder` and pass it to the `AddSurreal()` method.
##  Consume the SurrealDB client/session[](https://surrealdb.com/docs/reference/dotnet/core/dependency-injection#consume-the-surrealdb-clientsession)
Open `WeatherForecastController.cs` and replace everything in there with the following code.  
Finally, we can inject the `SurrealDbSession` inside our Controller.

```csharp
using Microsoft.AspNetCore.Mvc;

namespace SurrealDbWeatherApi.Controllers;

[ApiController]
[Route("[controller]")]
public class WeatherForecastController : ControllerBase
{
    private const string Table = "weatherForecast";

    private readonly SurrealDbSession _db;

    public WeatherForecastController(SurrealDbSession db)
    {
        _db = db;
    }

    [HttpGet]
    [Route("/")]
    public Task<List<WeatherForecast>> GetAll(CancellationToken cancellationToken)
    {
        return _db.Select<WeatherForecast>(Table, cancellationToken);
    }

    [HttpPost]
    [Route("/")]
    public Task<WeatherForecast> Create(CreateWeatherForecast data, CancellationToken cancellationToken)
    {
        var weatherForecast = new WeatherForecast
        {
            Date = data.Date,
            Country = data.Country,
            TemperatureC = data.TemperatureC,
            Summary = data.Summary
        };

        return _db.Create(Table, weatherForecast, cancellationToken);
    }

    // ...
    // Other methods omitted for brevity
}

public class CreateWeatherForecast
{
    public DateTime Date { get; set; }
    public string? Country { get; set; }
    public int TemperatureC { get; set; }
    public string? Summary { get; set; }
}
```

Then make sure your SurrealDB server is running on `127.0.0.1:8000` and run your app from the command line with:

```sh
dotnet run
```
