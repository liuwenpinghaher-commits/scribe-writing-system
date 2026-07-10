---
title: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation"
url: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation

Source: https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation

In the bottom left of the interface you can find a settings button (⚙) to open the settings dialog. These settings allow you to further customise the behaviour and appearance of Surrealist, such as switching between light and dark mode, increasing or decreasing the editor font sizes, and configure default values for new connections.
##  Behaviour[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation#behaviour)
In this section you can configure the behaviour of the interface, such as connection and editor related settings.
##  Appearance[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation#appearance)
The appearance section allows you to scale the fonts in the editor and also select your default query output view and set the behaviour for your Query and designer views.
##  Templates[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation#templates)
You can configure [connection templates](https://surrealdb.com/docs/explore/surrealist/advanced-topics/connection-templates) to reuse connection details when creating new connections. This is especially useful when you find yourself connecting to similar databases frequently.
##  Database serving[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation#database-serving)
This section allows you to alter the behaviour of the database serving functionality found in Surrealist Desktop, such as altering the port and specifying the path to the database executable.
##  Feature flags[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/settings-and-customisation#feature-flags)
Feature flags allow you to enable or disable stable and experimental features in Surrealist to suit your needs best.
Some of these features may not be stable and may not work as expected or be removed in future versions. To access the feature flags, press `Ctrl + K` or `Cmd + K` on your keyboard to open the command palette, then type in "Manage Feature Flags" and hit enter. You'll be taken to the feature flags settings.
After enabling a feature flag, you can access it by clicking on the settings button in the bottom left of the interface and selecting the feature flags tab. Here, you can enable or disable features. Here is a list of the current feature flags:  
| Options  | Description  |  
| --- | --- |  
| `feature_flags`  | Toggle feature flags.  |  
| `models_view`  | Toggle the view for SurrealML models.  |  
| `apidocs_view`  | Toggle the view for API documentation.  |  
| `themes`  | Toggle between light and dark mode.  |  
| `newsfeed`  | Toggle the newsfeed view.  |  
| `database_version_check`  | Toggle the database version check in the Surrealist CLI  |  
| `highlight_tool`  | Toggle the highlight tool.  |  
| `surreal_compat`  | Toggle SurrealDB version between `1.x` and `2.x`.  |  
| `changelog`  | Toggle the changelog view to see the latest changes, read all or unread all.  |
