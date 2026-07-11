---
title: "https://surrealdb.com/docs/reference/query-language/clauses/fetch"
url: "https://surrealdb.com/docs/reference/query-language/clauses/fetch"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/clauses/fetch

Source: https://surrealdb.com/docs/reference/query-language/clauses/fetch

The `FETCH` clause is used to retrieve related records or data from other tables in a single query. This is particularly useful when you want to gather data that is linked through relationships ([record links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links) or [graph edges](https://surrealdb.com/docs/reference/query-language/statements/relate)) without having to perform multiple separate queries.
The `FETCH` clause predates and is functionally identical to the [`ALL`](https://surrealdb.com/docs/reference/query-language/language-primitives/idioms#all-elements) idiom which is used by appending a `.*` to a related record.
##  Example usage[](https://surrealdb.com/docs/reference/query-language/clauses/fetch#example-usage)
Suppose you have a person table and a post table, where each post is related to a person. You can use the FETCH clause to retrieve a person along with their posts in a single query:

```surql
-- Using FETCH syntax
SELECT * FROM person FETCH posts;

-- Using .*
SELECT *, posts.* FROM person;
```

In this example, `posts` would be a related field in the `person` table that links to the `post` table. The `FETCH` clause allows you to retrieve all posts associated with each person in the result set.
Overall, the `FETCH` clause in SurrealQL is a powerful tool for optimizing data retrieval and simplifying query logic when working with related data.
The following example shows querying using `FETCH` or `.*` compared to selecting individual fields of a related record.
CREATE category SET name = 'Technology', created_at = time::now();  
CREATE person:john SET  
first_name = 'John',  
last_name = 'Adams',  
age = 29,  
admin = true,  
signup_at = time::now();  
CREATE article SET  
created_at = time::now(),  
author = person:john,  
title = 'Lorem ipsum dolor',  
text = 'Donec eleifend, nunc vitae commodo accumsan, mauris est fringilla.',  
category = (SELECT VALUE id FROM ONLY category WHERE name = 'Technology' LIMIT 1);  
"  
query="  
-- Fetch all fields from author and category  
SELECT   
title,   
category,   
author  
FROM article  
FETCH author, category;
-- Use .* syntax to do the same  
SELECT   
title,   
category._,  
author._  
FROM article;"  
/>
##  Without the `FETCH` clause[](https://surrealdb.com/docs/reference/query-language/clauses/fetch#without-the-fetch-clause)
CREATE category SET name = 'Technology', created_at = time::now();  
CREATE person:john SET  
first_name = 'John',  
last_name = 'Adams',  
age = 29,  
admin = true,  
signup_at = time::now();  
CREATE article SET  
created_at = time::now(),  
author = person:john,  
title = 'Lorem ipsum dolor',  
text = 'Donec eleifend, nunc vitae commodo accumsan, mauris est fringilla.',  
category = (SELECT VALUE id FROM ONLY category WHERE name = 'Technology' LIMIT 1);  
"  
query="  
-- Access single field from author link  
SELECT   
title,   
category,   
author.full_name AS author_name  
FROM article;  
"  
/>
