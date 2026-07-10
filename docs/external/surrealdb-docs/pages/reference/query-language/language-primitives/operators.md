---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/operators"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/operators"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/operators

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/operators

A variety of operators in SurrealQL allow for complex manipulation of data, and advanced logic.  
| Operator  | Description  |  
| --- | --- |  
|   | Checks whether both of two values are truthy  |  
|   | Checks whether either of two values is truthy  |  
| [`!`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#not)  | Reverses the truthiness of a value  |  
| [`!!`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#not_not)  | Determines the truthiness of a value  |  
| [`??`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#nco)  | Check whether either of two values are truthy and not NULL  |  
| [`?:`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#tco)  | Check whether either of two values are truthy  |  
|   | Check whether two values are equal  |  
|   | Check whether two values are not equal  |  
| [`==`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#exact)  | Check whether two values are exactly equal  |  
| [`?=`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#anyequal)  | Check whether any value in a set is equal to a value  |  
| [`*=`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#allequal)  | Check whether all values in a set are equal to a value  |  
| [`~`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#match)  | Compare two values for equality using fuzzy matching  |  
| [`!~`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#match)  | Compare two values for inequality using fuzzy matching  |  
| [`?~`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#match)  | Check whether any value in a set is equal to a value using  
fuzzy matching  |  
| [`*~`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#match)  | Check whether all values in a set are equal to a value using  
fuzzy matching  |  
| [`<`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#lessthan)  | Check whether a value is less than another value  |  
| [`<=`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#lessthanorequal)  | Check whether a value is less than or equal to another value  |  
| [`>`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#greaterthan)  | Check whether a value is greater than another value  |  
| [`>=`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#greaterthanorequal)  | Check whether a value is greater than or equal to another  
value  |  
| [`+`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#add)  | Add two values together  |  
| [`-`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#sub)  | Subtract a value from another value  |  
|   | Multiply two values together  |  
|   | Divide a value by another value  |  
| [`**`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#pow)  | Raises a base value by another value  |  
|   | Checks whether a value contains another value  |  
|   | Checks whether a value does not contain another value  |  
|   | Checks whether a value contains all other values  |  
|   | Checks whether a value contains any other value  |  
|   | Checks whether a value contains none of the following values  |  
|   | Checks whether a value is contained within another value  |  
|   | Checks whether a value is not contained within another value  |  
|   | Checks whether all values are contained within other values  |  
|   | Checks whether any value is contained within other values  |  
|   | Checks whether no value is contained within other values  |  
| [`OUTSIDE`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#outside)  | Checks whether a geometry type is outside of another  
geometry type  |  
| [`INTERSECTS`](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#intersects)  | Checks whether a geometry type intersects another geometry  
type  |  
|   | Checks whether the terms are found in a full-text indexed  
field  |  
|   | Performs a K-Nearest Neighbors (KNN) search to find a  
specified number of records closest to a given data point,  
optionally using a defined distance metric. Supports  
customizing the number of results and choice of distance  
calculation method.  |  
##  `&&` or `AND` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or-and-a-idanda)
The `and` operator checks whether both of two values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).

```surql
SELECT * FROM 10 AND 20 AND 30;

-- 30
```

  

##  `||` or `OR` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or-or-a-idora)
The `or` operator checks whether either of two values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).

```surql
SELECT * FROM 0 OR false OR 10;

-- 10
```

  

##  `!` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idnota)
The `not` operator reverses the truthiness of a value.

```surql
SELECT * FROM !(TRUE OR FALSE);
-- false

SELECT * FROM !"Has a value";
-- false
```

  

##  `!!` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idnot_nota)
The `not not` operator is simply an application of the `!` operator twice. It can be used to determines the truthiness of a value.

```surql
SELECT * FROM !!"Has a value";
-- true
```

##  `??` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idncoa)
The `null coalescing operator` checks whether either of two values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness) and not `NONE` or `NULL`.

```surql
SELECT * FROM NULL ?? 0 ?? false ?? 10;

-- 0
```

  

##  `?:` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idtcoa)
The `truthy coalescing operator` checks whether either of two values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).

```surql
SELECT * FROM NULL ?: 0 ?: false ?: 10;

-- 10
```

  

##  `=` or `IS` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or-is-a-idequala)
The `equal` operator checks whether two values are equal.

```surql
SELECT * FROM true = "true";
-- false
```

```surql
SELECT * FROM 10 = "10";
-- false
```

```surql
SELECT * FROM 10 = 10.00;
-- true
```

```surql
SELECT * FROM 10 = "10.3";
-- false
```

```surql
SELECT * FROM [1, 2, 3] = [1, 2, 3];
-- true
```

```surql
SELECT * FROM [1, 2, 3] = [1, 2, 3, 4];
-- false
```

```surql
SELECT * FROM { this: "object" } = { this: "object" };
-- true
```

```surql
SELECT * FROM { this: "object" } = { another: "object" };
-- false
```

  

##  `!=` or `IS NOT` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or-is-not-a-idnotequala)
The `not equal` operator checks whether two values are not equal.

```surql
SELECT * FROM 10 != "15";
-- true
```

```surql
SELECT * FROM 10 != "test";
-- true
```

```surql
SELECT * FROM [1, 2, 3] != [3, 4, 5];
-- true
```

  

##  `==` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idexacta)
The `exact` operator checks whether two values are exact. This operator also checks that each value has the same type.

```surql
SELECT * FROM 10 == 10;
-- true
```

```surql
SELECT * FROM 10 == "10";
-- false
```

```surql
SELECT * FROM true == "true";
-- false
```

  

##  `?=` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idanyequala)
The `any equal` operator checks whether any value in an array equals another value.

```surql
SELECT * FROM [10, 15, 20] ?= 10;
-- true
```

  

##  `*=` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idallequala)
The `all equal` operator checks whether all values in an array equals another value.

```surql
SELECT * FROM [10, 10, 10] *= 10;
-- true
```

  

##  `~` `?~` `!~` `*~` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#----a-idmatcha)
These operators used to compare two values for equality using fuzzy matching. They have been removed since 3.0 to avoid implicitly preferring one algorithm over another, as the type of fuzzy matching to use will depend on each individual case.
Please use the `string::similarity::*` functions instead:

```surql
let $threshold = 10;

string::similarity::smithwaterman("test text", "Test") > $threshold;
-- true
```

  

##  `<` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idlessthana)
The `less than` operator checks whether a value is less than another value.

```surql
SELECT * FROM 10 < 15;
-- true
```

  

##  `<=` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idlessthanorequala)
The `less than or equal` operator checks whether a value is less than or equal to another value.

```surql
SELECT * FROM 10 <= 15;
-- true
```

  

##  `>` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idgreaterthana)
The `greater than` operator checks whether a value is less than another value.

```surql
SELECT * FROM 15 > 10;
-- true
```

  

##  `>=` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idgreaterthanorequala)
The `greater than or equal` operator checks whether a value is less than or equal to another value.

```surql
SELECT * FROM 15 >= 10;
-- true
```

  

##  `+` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idadda)
The `add` operator adds two values together.

```surql
SELECT * FROM 10 + 10;
-- 20
```

```surql
SELECT * FROM "test" + " " + "this";
-- "test this"
```

```surql
SELECT * FROM 13h + 30m;
-- "13h30m"
```

  

##  `-` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#--a-idsuba)
The `subtract` operator subtracts a value from another value.

```surql
SELECT * FROM 20 - 10;
-- 10
```

```surql
SELECT * FROM 2m - 1m;
-- 1m
```

  

##  `*` or `×` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or--a-idmula)
The `multiply` operator multiplies a value by another value.

```surql
SELECT * FROM 20 * 2;
-- 40
```

  

##  `/` or `÷` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-or--a-iddiva)
The `divide` operator divides a value by another value.

```surql
SELECT * FROM 20 / 2;
-- 10
```

  

##  `**` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#-a-idpowa)
The `power` operator raises a base value by another value.

```surql
SELECT * FROM 20 ** 3;
-- 8000
```

  

##  `CONTAINS` or `∋` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#contains-or--a-idcontainsa)
The `contains` operator checks whether a value contains another value.

```surql
SELECT * FROM [10, 20, 30] CONTAINS 10;
-- true
```

```surql
SELECT * FROM "this is some text" CONTAINS "text";
-- true
```

```surql
SELECT * FROM {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
} CONTAINS (-0.118092, 51.509865);

-- true
```

  

##  `CONTAINSNOT` or `∌` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#containsnot-or--a-idcontainsnota)
The `not contains` operator checks whether a value does not contain another value.

```surql
SELECT * FROM [10, 20, 30] CONTAINSNOT 15;
-- true
```

```surql
SELECT * FROM "this is some text" CONTAINSNOT "other";
-- true
```

```surql
SELECT * FROM {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
} CONTAINSNOT (-0.518092, 53.509865);

-- true
```

  

##  `CONTAINSALL` or `⊇` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#containsall-or--a-idcontainsalla)
The `contains all` operator checks whether a value contains all of multiple values.

```surql
SELECT * FROM [10, 20, 30] CONTAINSALL [10, 20, 10];
-- true
```

  

##  `CONTAINSANY` or `⊃` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#containsany-or--a-idcontainsanya)
The `contains any` operator checks whether a value contains any of multiple values.

```surql
SELECT * FROM [10, 20, 30] CONTAINSANY [10, 15, 25];
-- true
```

  

##  `INSIDE` or `∈` or `IN` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#inside-or--or-in-a-idinsidea)
The `inside` operator checks whether a value is contained within another value.

```surql
SELECT * FROM 10 INSIDE [10, 20, 30];
-- true
```

```surql
SELECT * FROM "text" INSIDE "this is some text";
-- true
```

```surql
SELECT * FROM (-0.118092, 51.509865) INSIDE {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
};

true
```

This operator can also be used to check for the existence of a key inside an [object](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects). To do so, precede `IN` with the field name as a string.

```surql
"name" IN {
    name: "Riga",
    country: "Latvia"
};

-- true
```

`IN` can also be used with a record ID as long as the ID is expanded to include the fields. Both of the following queries will return `true`.

```surql
CREATE city:riga SET name = "Riga", country = "Latvia", population = 605273;

"name" IN city:riga.*;
"name" IN city:riga.{ name, country };
```

  

##  `NOTINSIDE` or `∉` or `NOT IN` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#notinside-or--or-not-in-a-idnotinsidea)
The `not inside` operator checks whether a value is not contained within another value.

```surql
SELECT * FROM 15 NOTINSIDE [10, 20, 30];
-- true
```

```surql
SELECT * FROM "other" NOTINSIDE "this is some text";
-- true
```

```surql
SELECT * FROM (-0.518092, 53.509865) NOTINSIDE {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
};

-- true
```

  

##  `ALLINSIDE` or `⊆` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#allinside-or--a-idallinsidea)
The `all inside` operator checks whether all of multiple values are contained within another value.

```surql
SELECT * FROM [10, 20, 10] ALLINSIDE [10, 20, 30];
-- true
```

  

##  `ANYINSIDE` or `⊂` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#anyinside-or--a-idanyinsidea)
The `any inside` operator checks whether any of multiple values are contained within another value.

```surql
SELECT * FROM [10, 15, 25] ANYINSIDE [10, 20, 30];
-- true
```

  

##  `NONEINSIDE` or `⊄` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#noneinside-or--a-idnoneinsidea)
The `none inside` operator checks whether none of multiple values are contained within another value.

```surql
SELECT * FROM [15, 25, 35] NONEINSIDE [10, 20, 30];
-- true
```

  

##  `OUTSIDE` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#outside-a-idoutsidea)
The `outside` operator checks whether a geometry value is outside another geometry value.

```surql
SELECT * FROM (-0.518092, 53.509865) OUTSIDE {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
};

-- true
```

  

##  `INTERSECTS` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#intersects-a-idintersectsa)
The `intersects` operator checks whether a geometry value intersects another geometry value.

```surql
SELECT * FROM {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
} INTERSECTS {
	type: "Polygon",
	coordinates: [[
		[-0.11123657, 51.53160074], [-0.16925811, 51.51921169],
		[-0.11466979, 51.48223813], [-0.07381439, 51.51322956],
		[-0.11123657, 51.53160074]
	]]
};

-- true
```

  

##  `MATCHES` [](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#)[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#matches-a-idmatchesa)
The `matches` operator checks whether the terms are found in a full-text indexed field.

```surql
SELECT * FROM book WHERE title @@ 'rust web';

[
	{
		id: book:1,
		title: 'Rust Web Programming'
	}
]
```

Using the matches operator with a reference checks whether the terms are found, highlights the searched terms, and computes the full-text score.

```surql
SELECT id,
		search::highlight('<b>', '</b>', 1) AS title,
		search::score(1) AS score
FROM book
WHERE title @1@ 'rust web'
ORDER BY score DESC;

[
	{
		id: book:1,
		score: 0.9227996468544006f,
		title: '<b>Rust</b> <b>Web</b> Programming'
	}
]
```

Available since: v3.0.0
###  `AND`, `OR`, and numeric operators inside `@@`[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#and-or-and-numeric-operators-inside-)
In addition to the `AND` keyword, the `OR` matches operator can also be used. This allows a single string to be compared against instead of needing to specify individual parts of the string.

```surql
CREATE document:1 SET text = "It is rare that I find myself penning a personal note in my chronicles.";
DEFINE ANALYZER simple TOKENIZERS blank,class FILTERS lowercase;
DEFINE INDEX some_index ON document FIELDS text FULLTEXT ANALYZER simple;

-- @AND@ and @OR@: can use the entire string
SELECT * FROM document WHERE text @AND@ "personal rare";
SELECT * FROM document WHERE text @OR@ "personal nice weather today";

-- Separate AND and OR outside of matches operator:
-- Must specify parts of string to check for match
SELECT * FROM document WHERE text @@ "personal" AND text @@ "rare";
SELECT * FROM document WHERE text @@ "personal note";
SELECT * FROM document WHERE text @@ "personal"
  OR text @@ "nice weather today";
```

##  `KNN`[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#knn)
K-Nearest Neighbors (KNN) is a fundamental algorithm used for classifying or regressing based on the closest data points in the feature space, with its performance and scalability critical in applications involving large datasets.
In practice, the efficiency and scalability of the KNN algorithm are crucial, especially when dealing with large datasets. Different implementations of KNN are tailored to optimize these aspects without compromising the accuracy of the results.
SurrealDB supports different K-Nearest Neighbors methods to perform KNN searches, each with unique requirements for syntax.  
Below are the details for each method, including how to format your query with examples:
###  Brute force method[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#brute-force-method)
Best for smaller datasets or when the highest accuracy is required.
SurrealQL Syntax

```syntax
<|K,DISTANCE_METRIC|>
```

  * •
K: The number of nearest neighbors to retrieve.
  * •
DISTANCE_METRIC: The metric used to calculate distances, such as EUCLIDEAN or MANHATTAN.

```surql
CREATE pts:3 SET point = [8,9,10,11];
SELECT id FROM pts WHERE point <|2,EUCLIDEAN|> [2,3,4,5];
```

###  Approximate graph indexes[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#approximate-graph-indexes)
HNSWDISKANN
####  HNSW[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#hnsw)
Recommended for very large datasets where speed is essential and some loss of accuracy is acceptable, **while the graph fits in memory**.
SurrealQL Syntax

```syntax
<|K,EF|>
```

  * •
K: The number of nearest neighbors.
  * •
EF: The size of the dynamic candidate list during the search, affecting the search's accuracy and speed.

```surql
CREATE pts:3 SET point = [8,9,10,11];
DEFINE INDEX mt_pts
  ON pts FIELDS point HNSW DIMENSION 4 DIST EUCLIDEAN EFC 150 M 12;
SELECT id FROM pts WHERE point <|10,40|> [2,3,4,5];
```

####  DISKANN[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#diskann)
Available since: v3.1.0
Recommended when embeddings are too large to keep an HNSW graph resident in RAM as the graph lives on disk with caching. Note that WASM targets do not support DISKANN, so use HNSW or brute force there.
The query syntax matches HNSW: use the approximate form `` where the second value bounds the search candidate list (see [`DEFINE INDEX … DISKANN`](/docs/reference/query-language/statements/define/indexes#diskann-disk-based-approximate-nearest-neighbours) for defaults and supported `TYPE` / `DIST` combinations).
SurrealQL Syntax

```syntax
<|K,L|>
```

```surql
CREATE pts:3 SET point = [8,9,10,11];
DEFINE INDEX diskann_pts ON pts FIELDS point DISKANN DIMENSION 4 DIST EUCLIDEAN TYPE F32 DEGREE 8 L_BUILD 20;
SELECT id FROM pts WHERE point <|10,40|> [2,3,4,5];
```

###  Combining a KNN search with a filter[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#combining-a-knn-search-with-a-filter)
A KNN search over an indexed field can be combined with additional `WHERE` conditions. When the vector field is indexed (HNSW or DISKANN), such a condition is pushed into the index search and evaluated _during_ the graph traversal, so non-matching candidates are rejected before they occupy one of the `K` slots — rather than being filtered out after the neighbours have been retrieved.
You can confirm this by using the [`EXPLAIN`](https://surrealdb.com/docs/reference/query-language/statements/explain) clause after a query to see its plan. Here, the condition appears as a `predicate` attribute on the `KnnScan` operator in the output. See [Filtering through vector search](https://surrealdb.com/docs/learn/data-models/vector-search/similarity-search#how-the-filter-is-applied) for a worked example.
  
  

##  Using the `ANY`/`ALL` operators for string indexes[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#using-the-anyall-operators-for-string-indexes)
Available since: v2.4.0
An index defined on a string value can be used via the operators `CONTAINSANY`, `ALLINSIDE`, or `ANYINSIDE`. The operator `CONTAINS`, however, will not use a defined index as `CONTAINS` is used for substring matches between strings themselves as opposed to an index lookup.

```surql
DEFINE FIELD name ON account TYPE string;
DEFINE INDEX name_index ON account FIELDS name;

CREATE account:billy SET name = "Billy McConnell";

-- Both return the user Billy McConnell
SELECT * FROM account WHERE name CONTAINS "Billy McConnell";
SELECT * FROM account WHERE name CONTAINSANY ["Billy McConnell"];

-- However, CONTAINS does not use the index
SELECT * FROM account WHERE name CONTAINS "Billy McConnell" EXPLAIN FULL;
-- CONTAINSANY + putting the value inside an array will use the index
SELECT * FROM account
  WHERE name CONTAINSANY ["Billy McConnell"] EXPLAIN FULL;
```

##  Types of operators, order of operations and binding power[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#types-of-operators-order-of-operations-and-binding-power)
To determine which operator is executed first, a concept called "binding power" is used. Operators with greater binding power will operate directly on their neighbours before those with lower binding power. The following is a list of all operator types from greatest to lowest binding power.  
| Operator name  | Description  |  
| --- | --- |  
| `Unary`  | The `Unary` operators are `!`, `+`, and `-`.  |  
| `Nullish`  | The `Nullish` operators are `?:` and `??`.  |  
| `Range`  | The `Range` operator is `..`.  |  
| `Cast`  |  The `Cast` operator is ` `, with `type_name` a stand in for the type to cast into. For example, ` ` or ` `.  |  
| `Power`  | The only `Power` operator is `**`.  |  
| `MulDiv`  | The `MulDiv` (multiplication and division) operators are `*`, `/`, `÷`, and `%`.  |  
| `AddSub`  | The `AddSub` (addition and subtraction) operators are `+` and `-`.  |  
| `Relation`  | The `Relation` operators are `=`, `∋`, `CONTAINS`, `∌`, `CONTAINSNOT`, `∈`, `INSIDE`, `∉`, `NOTINSIDE`, `⊇`, `CONTAINSALL`, `⊃`, `CONTAINSANY`, `⊅`, `CONTAINSNONE`, `⊆`, `ALLINSIDE`, `⊂`, `ANYINSIDE`, `⊄`, `NONEINSIDE`, `OUTSIDE`, `INTERSECTS`, `NOT`, and `IN`.  |  
| `Equality`  | The `Equality` operators are `=`, `IS`, `==`, `!=`, `*=`, `?=`, and `@`.  |  
| `And`  | The `And` operators are `&&` and `AND`.  |  
| `Or`  | The `Or` operators are `||` and `OR`.  |  
##  Examples of binding power[](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#examples-of-binding-power)
The following samples show examples of basic operations of varying binding power. The original example is followed by the same example with the parts with higher binding power in parentheses, then the final expression after the first bound portion is calculated, and finally the output.
MulDiv first, then AddSub

```surql
1 + 3 * 4;
1 + (3 * 4);
-- Final expression
1 + 12;
-- Output
13
```

Power first, then MulDiv

```surql
2**3 * 3;
(2**3) * 3;
-- Final expression
8*3;
-- Output
24
```

Unary first, then cast

```surql
<string>-4;
<string>(-4);
-- Output
"-4"
```

Cast first, then Power

```surql
<number>"9"**9;
(<number>"9")**9;
-- Final expression
9**9;
-- Output
387420489
```

AddSub first, then Relation

```surql
"c" + "at" IN "cats";
("c" + "at") IN "cats";
-- Final expression
"cat" IN "cats";
-- Output
true
```

And first, then Or

```surql
true AND false OR true;
(true AND false) OR true;
-- Final expression
false OR true;
-- Output
true
```

Unary, then Cast, then Power, then AddSub

```surql
<decimal>-4**2+4;
((<decimal>(-4))**2)+4;
-- Output
20dec
```
