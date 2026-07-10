---
title: "https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations"
url: "https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations

Source: https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations

The first question when modeling connections is whether **graph edges** are the right tool: SurrealDB can also connect records with **record links**.
##  Record links[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#record-links)
A record link is a pointer from one record to another: any field that holds a record id. Record ids are efficient direct pointers and avoid table scans.
Example: one `user` with two `comment` rows linked from the user:

```surql
LET $new_user = CREATE ONLY user SET name = "User McUserson";
-- Create a new comment, use the output to update the user
UPDATE $new_user SET comments += (CREATE ONLY comment SET 
    text = "I learned something new!", 
    created_at = time::now())
    .id;
UPDATE $new_user SET comments += (CREATE ONLY comment SET
    text = "I don't get it, can you explain?",
    created_at = time::now())
    .id;
```

Querying is like reading any other field:

```surql
SELECT 
    name, 
    comments.{ created_at, text }
FROM user;
```

Output

```surql
[
	{
		comments: [
			{
				created_at: d'2024-12-12T02:39:07.644Z',
				text: 'I learned something new!'
			},
			{
				created_at: d'2024-12-12T02:39:07.645Z',
				text: "I don't get it, can you explain?"
			}
		],
		name: 'User McUserson'
	}
]
```

###  Reverse direction without edges[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#reverse-direction-without-edges)
Historically, record links were unidirectional; the other direction often needed a subquery; while graph edges made reverse walks easy:

```surql
SELECT 
    *,
    -- Check the `user` table's `comments` field
    -- for the id of the current comment
    (SELECT id, name FROM user WHERE $parent.id IN comments) AS author
FROM comment;

-- Equivalent graph query is much easier
-- to read and write
SELECT 
	*,
	<-wrote<-author
FROM comment;
```

```surql
[
	{
		author: [
			{
				id: user:f3t90z8uvns76sr3nxrd,
				name: 'User McUserson'
			}
		],
		created_at: d'2024-12-12T02:39:07.645Z',
		id: comment:gj1vtsd9d19z9afrc14j,
		text: "I don't get it, can you explain?"
	},
	{
		author: [
			{
				id: user:f3t90z8uvns76sr3nxrd,
				name: 'User McUserson'
			}
		],
		created_at: d'2024-12-12T02:39:07.644Z',
		id: comment:zhnbfopxspekknsi6vx6,
		text: 'I learned something new!'
	}
]
```

###  Bidirectional record links (3.0+)[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#bidirectional-record-links-30)
Since version `3.0.0`, a record link can be bidirectional by defining a field with the [`REFERENCE`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/references) clause and using a computed back-reference:

```surql
DEFINE FIELD comments ON user TYPE option<array<record<comment>>> REFERENCE;
DEFINE FIELD author ON comment COMPUTED <~user;

LET $new_user = CREATE ONLY user SET name = "User McUserson";
-- Create a new comment, use the output to update the user
UPDATE $new_user SET comments += (CREATE ONLY comment:one SET 
    text = "I learned something new!", 
    created_at = time::now())
    .id;
UPDATE $new_user SET comments += (CREATE ONLY comment:two SET
    text = "I don't get it, can you explain?",
    created_at = time::now())
    .id;

-- 'author' field is populated with the 'user' who wrote the comment
SELECT * FROM ONLY comment:one;

-- Regular queries on incoming references work too
SELECT text, <~user.id[0] AS commenter FROM comment;
```

Output

```surql
-------- Query --------

{
	author: [
		user:igi77zrlewsqemgjz4zi
	],
	created_at: d'2025-09-02T02:56:03.408Z',
	id: comment:one,
	text: 'I learned something new!'
}

-------- Query --------

[
	{
		commenter: user:igi77zrlewsqemgjz4zi,
		text: 'I learned something new!'
	},
	{
		commenter: user:igi77zrlewsqemgjz4zi,
		text: "I don't get it, can you explain?"
	}
]
```

##  When to prefer record links[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#when-to-prefer-record-links)
**Record links are preferred if:**
  * •
Performance is the top priority.
  * •
You do not need very complex multi-hop graph queries.
  * •
You want the schema to declare what happens when a linked row is deleted (cascade, refuse, ignore, etc.) via [`ON DELETE`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/references) and related options.

##  When to prefer graph relations[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#when-to-prefer-graph-relations)
**Graph relations are preferred if:**
  * •
You want to create links quickly **without** pre-defining every field, or you link across many record types in one go (for example `RELATE person:one->wrote->[blog:one, book:one, comment:one]` versus several `DEFINE FIELD` steps.
  * •
You need expressive arrow syntax for multi-hop patterns such as `->wrote->commentwrote->comment` starting from `person`.
  * •
You want Surrealist’s Designer to visualise edges clearly.

Graph edges are **almost required** when the relationship itself carries metadata that belongs neither to the source nor target record alone (for example the moment a user posted a comment:

```surql
{
    ip_addr_location: "Arizona",
    os: "Windows 11",
    current_mood: "Happy"
}
```

That data is about the **link event** , not the whole user or the comment body, so it belongs on an edge table.
The same applies to durable facts about the relationship:

```surql
{
	friends_since: d'2024-12-31T06:43:21.981Z',
	friendship_strength: 0.4
}
```

##  Weighting and counting on graph tables[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#weighting-and-counting-on-graph-tables)
Graph tables are a natural place to store **weights** on the edge row, or to **derive** interaction strength by **counting** how many edges exist between the same endpoints. If you need that kind of scoring or event metadata on the relationship itself, graph relations are usually the right abstraction.
Worked examples (random NPC interactions, `knows` vs `greeted`, aggregations) live in [Social network patterns](https://surrealdb.com/docs/learn/data-models/graph/social-network-patterns).
##  When links are deleted[](https://surrealdb.com/docs/learn/data-models/graph/record-links-vs-graph-relations#when-links-are-deleted)
Record links can encode rich behaviour on delete (for example, removing an id from an array while appending to a history field), via [`REFERENCE` `ON DELETE`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/references).
Graph edges are simpler: if **either** endpoint record is deleted, the edge row is removed.

```surql
-- likes record created without problems
RELATE person:one->likes->person:two;
CREATE person:one, person:two;
DELETE person:one;
-- 'likes' record is now gone
SELECT * FROM likes;
```

Example of record-link cleanup:

```surql
DEFINE FIELD comments ON person TYPE option<array<record<comment>>> REFERENCE ON DELETE THEN {
    UPDATE $this SET
        deleted_comments += $reference,
        comments -= $reference;
};
```

For more on `ON DELETE` and references, see [Record references](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/references).
