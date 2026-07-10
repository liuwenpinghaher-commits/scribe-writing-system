---
title: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist"
url: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist

Source: https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist

Surrealist can be added to any website or application using Embeds. This lets you run your queries and results on any website or application. Another use case for embeds is making it easy to share your queries and results with others and debug in the same environments.
![Surrealist Embed](https://surrealdb.com/docs/explore/surrealist/advanced-topics/~/assets/img/image/surrealist/embed.png)
##  Creating a new embed[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#creating-a-new-embed)
To create an embed, head over to the Surrealist overview page and click on the embed surrealist option. Then, in the `Editor query` section, you can write the query you want to be embedded. If the query uses variables, you can enter the values for the variables in the `Editor variables` section, and they will appear in the Embed preview section on the right.
###  Setup query[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#setup-query)
In the `Setup query` section you can enter the queries that you want to run before the main query. This can be used to set up the environment for the main query.
For example, if you want to create a user table with some fields to populate before running the main query to add a record, you can enter the create table query in the `Setup query` section.

```surql
-- Create a schemafull user table.
DEFINE TABLE user SCHEMAFULL;
-- Define some fields.
DEFINE FIELD firstName ON TABLE user TYPE string;
DEFINE FIELD lastName ON TABLE user TYPE string;
DEFINE FIELD email ON TABLE user TYPE string;
  ASSERT string::is_email($value);
```

Then, you can write the main query in the `Editor query` section.

```surql
-- 1: Add a user with all required fields.
CREATE user CONTENT {
    firstName: 'John',
    lastName: 'Doe',
    email: 'JohnDoe@someemail.com',
};
```

Once you have entered your query, the results will appear in the `Embed preview` section on the right. You can copy the URL or embed the generated iframe in the `Embed snippet` section.
Note
If your query uses variables, you can also enter the values for the variables in the `EditorVariables` section, and they will show up in the Embed preview section on the right.
###  Loading dataset in embeds[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#loading-dataset-in-embeds)
Surrealist comes with a few datasets that you can load in the embeds. To select a dataset, click the `Dataset` dropdown and select the dataset you want to load.
For example, to load the [surreal deal dataset](https://surrealdb.com/docs/start) in the embeds by selecting the dropdown in the `Dataset` section and selecting the `surreal deal` dataset. This allows you to query the tables within a dataset and embed the results in your website or application.
###  Orientation in embeds[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#orientation-in-embeds)
You can also select the orientation of the embeds by selecting the `Orientation` dropdown. You can choose between `Vertical` and `Horizontal` orientation. This allows you to embed the query in the orientation that fits your website or application.
##  Restore query in embeds[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#restore-query-in-embeds)
If you have an embed link, you can restore the query by clicking the `Restore from URL` button at the bottom and entering the embed link. This will restore the query and variables if any and you can then run the query. You can also share this link with others to share the query and results.
##  Embed messaging protocol[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#embed-messaging-protocol)
Surrealist embeds can be controlled externally using the iframe messaging protocol. This allows you to manipulate an embed located within your website or application.  
Here is an example which sets the query displayed in the embed:

```js
const embed = document.getElementById("#embed");

embed.postMessage({
	action: "set_query",
	options: {
		query: "SELECT * FROM example;"
	}
}, "https://app.surrealdb.com");
```

###  Messages[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#messages)
  

  
  
| Action  | Description  | Options  |  
| --- | --- | --- |  
| `set_editor`  | Overwrite the query in the editor.  | 
  * •**query** (optional): The query string to set in the editor.  
- **variables** (optional): The variables structure to set in the editor.

 |  
| `clear_response`  | Removes any responses currently present in the embed.  |   |  
| `set_editor_mode`  | Change which panel is currently displayed in the editor.  | 
  * •**mode** : Can either be "query" or "variables".

 |  
| `set_result_mode`  | Change which visualisation is used for rendering results.  | 
  * •**mode** : Can be "combined", "single", "table", or "live".

 |  
| `run_query`  | Executes the query currently present within the embed  |   |  
| `execute_query`  | Executes the specified query in the background without displaying the results.  | 
  * •**query** : The query to execute

 |  
##  Video guide[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/embedding-surrealist#video-guide)
If you prefer a video guide, you can watch the following video which covers similar content to this documentation.
