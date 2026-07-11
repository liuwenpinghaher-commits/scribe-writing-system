---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries

A `geometry` is a type based on the GeoJSON spec that is optimised for working with data pertaining to locations on Earth.
SurrealDB makes working with GeoJSON easy, with support for `Point`, `LineString`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon`, and `Collection` values. SurrealQL automatically detects GeoJSON objects converting them into a single data type.  
| Type  | Description  |  
| --- | --- |  
| [`Point`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#point)  | A geolocation point with longitude and latitude  |  
| [`LineString`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#LineString)  | A GeoJSON LineString value for storing a geometric path  |  
| [`Polygon`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#polygon)  | A GeoJSON Polygon value for storing a geometric area  |  
| [`MultiPoint`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipoint)  | A value which contains multiple geometry points  |  
| [`MultiLineString`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multilinestring)  | A value which contains multiple geometry lines  |  
| [`MultiPolygon`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipolygon)  | A value which contains multiple geometry polygons  |  
| [`Collection`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#collection)  | A value which contains multiple different geometry types  |  
##  The GeoJSON spec[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#the-geojson-spec)
There are two main points to keep in mind when creating a `geometry` type in SurrealDB. They are:
  * •
Points are defined according to the GeoJSON spec, which specificies longitude before latitude. Many sites - including Google Maps - provide location data in the opposite order, so be sure to confirm that any data being used to create a `Point` is in the order `(longitude, latitude)`, and not the other way around.
  * •
A `geometry` created from an object must contain a `type` field and a `coordinates` field, no more and no less.

This can be shown by calling the [`type::is_geometry()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/type#typeis_geometry) function on some sample objects.

```surql
-- true: has `type` and `coordinates` field with valid data
{ type: "Point", coordinates: [-0.118092, 51.509865] }.is_geometry();

-- false: lacks 'type' field
{ coordinates: [-0.118092, 51.509865] }.is_geometry();

-- false: has an extra field
{ type: "Point", coordinates: [-0.118092, 51.509865], unnecessary: "data" }.is_geometry();
```

##  `Point`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#point)
The simplest form of GeoJSON that SurrealDB supports is a geolocation point. These can be written using two different formats. The first format is that of an object that matches the GeoJSON spec.

```surql
CREATE city:london SET centre = {
    type: "Point",
    coordinates: [-0.118092, 51.509865],
};
```

The other format is a simple 2-element tuple containing the longitude and the latitude of a location. This output for this format is no different from the above, and is simply a convenience due to the frequency of use of the `Point` type.

```surql
CREATE city:london SET centre = (-0.118092, 51.509865);
```

  

##  `LineString`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#linestring)
A GeoJSON LineString value for storing a geometric path.

```surql
CREATE city:london SET distance = {
    type: "LineString",
    coordinates: [[-0.118092, 51.509865],[0.1785278, 51.37692386]],
};
```

  

##  `Polygon`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#polygon)
A GeoJSON Polygon value for storing a geometric area.

```surql
CREATE city:london SET boundary = {
	type: "Polygon",
	coordinates: [[
		[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
		[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
		[-0.38314819, 51.37692386]
	]]
};
```

  

##  `MultiPoint`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipoint)
MultiPoints can be used to store multiple geometry points in a single value.

```surql
CREATE person:tobie SET locations = {
	type: "MultiPoint",
	coordinates: [
		[10.0, 11.2],
		[10.5, 11.9]
	],
};
```

  

##  `MultiLineString`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multilinestring)
A MultiLineString can be used to store multiple geometry lines in a single value.

```surql
CREATE travel:yellowstone SET routes = {
	type: "MultiLineString",
	coordinates: [
		[ [10.0, 11.2], [10.5, 11.9] ],
		[ [11.0, 12.2], [11.5, 12.9], [12.0, 13.0] ]
	]
}
```

  

##  `MultiPolygon`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#multipolygon)
MultiPolygons can be used to store multiple geometry polygons in a single value.

```surql
CREATE university:oxford SET locations = {
	type: "MultiPolygon",
	coordinates: [
		[
			[ [10.0, 11.2], [10.5, 11.9], [10.8, 12.0], [10.0, 11.2] ]
		],
		[
			[ [9.0, 11.2], [10.5, 11.9], [10.3, 13.0], [9.0, 11.2] ]
		]
	]
};
```

  

##  `Collection`[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#collection)
Collections can be used to store multiple different geometry types in a single value.

```surql
CREATE university:oxford SET buildings = {
	type: "GeometryCollection",
	geometries: [
		{
			type: "MultiPoint",
			coordinates: [
				[10.0, 11.2],
				[10.5, 11.9]
			],
		},
		{
			type: "Polygon",
			coordinates: [[
				[-0.38314819, 51.37692386], [0.1785278, 51.37692386],
				[0.1785278, 51.61460570], [-0.38314819, 51.61460570],
				[-0.38314819, 51.37692386]
			]]
		},
		{
			type: "MultiPolygon",
			coordinates: [
				[
					[ [10.0, 11.2], [10.5, 11.9], [10.8, 12.0], [10.0, 11.2] ]
				],
				[
					[ [9.0, 11.2], [10.5, 11.9], [10.3, 13.0], [9.0, 11.2] ]
				]
			]
		}
	]
};
```

  

##  Example[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#example)
The following example includes five records from [an open database](https://public.opendatasoft.com/explore/dataset/geonames-all-cities-with-a-population-1000/export/?disjunctive.cou_name_en&sort=name) with cities worldwide that have of a population of at least 1000. The queries below create a `city` record from each entry that includes their name, location, and name. Next, it uses the [`geo::distance`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo#geodistance) function to find their two closest neighbours, relating them via the `close_to` relation table. The final query can be viewed in traditional form to see each city's neighbours, or on Surrealist's [graph view](https://surrealdb.com/blog/visualising-your-data-with-surrealists-graph-view) to see a visual representation of the network of closely linked cities.

```surql
DEFINE TABLE city SCHEMAFULL;
DEFINE FIELD name ON city TYPE string;
DEFINE FIELD location ON city TYPE point;

FOR $city IN [{"geoname_id": "5881639", "name": "100 Mile House", "ascii_name": "100 Mile House", "feature_class": "P", "feature_code": "PPL", "country_code": "CA", "cou_name_en": "Canada", "country_code_2": null, "admin1_code": "02", "admin2_code": "5941", "admin3_code": "5941005", "admin4_code": null, "population": 1980, "elevation": null, "dem": 928, "timezone": "America/Vancouver", "modification_date": "2019-11-26", "label_en": "Canada", "coordinates": {"lon": -121.28594, "lat": 51.64982}},{"geoname_id": "5896969", "name": "Beaverlodge", "ascii_name": "Beaverlodge", "feature_class": "P", "feature_code": "PPL", "country_code": "CA", "cou_name_en": "Canada", "country_code_2": null, "admin1_code": "01", "admin2_code": "4819009", "admin3_code": null, "admin4_code": null, "population": 2219, "elevation": null, "dem": 723, "timezone": "America/Edmonton", "modification_date": "2024-02-28", "label_en": "Canada", "coordinates": {"lon": -119.43605, "lat": 55.21664}},{"geoname_id": "5911606", "name": "Burnaby", "ascii_name": "Burnaby", "feature_class": "P", "feature_code": "PPLA3", "country_code": "CA", "cou_name_en": "Canada", "country_code_2": null, "admin1_code": "02", "admin2_code": "5915", "admin3_code": "5915025", "admin4_code": null, "population": 202799, "elevation": null, "dem": 87, "timezone": "America/Vancouver", "modification_date": "2019-02-26", "label_en": "Canada", "coordinates": {"lon": -122.95263, "lat": 49.26636}},{"geoname_id": "5920996", "name": "Chertsey", "ascii_name": "Chertsey", "feature_class": "P", "feature_code": "PPL", "country_code": "CA", "cou_name_en": "Canada", "country_code_2": null, "admin1_code": "10", "admin2_code": "14", "admin3_code": "62047", "admin4_code": null, "population": 4836, "elevation": null, "dem": 251, "timezone": "America/Toronto", "modification_date": "2016-06-22", "label_en": "Canada", "coordinates": {"lon": -73.89095, "lat": 46.07109}},{"geoname_id": "5941905", "name": "Dorset Park", "ascii_name": "Dorset Park", "alternate_names": null, "feature_class": "P", "feature_code": "PPLX", "country_code": "CA", "cou_name_en": "Canada", "country_code_2": null, "admin1_code": "08", "admin2_code": "3520", "admin3_code": null, "admin4_code": null, "population": 25003, "elevation": null, "dem": 164, "timezone": "America/Toronto", "modification_date": "2020-05-02", "label_en": "Canada", "coordinates": {"lon": -79.28215, "lat": 43.75386}}]

{
    CREATE type::record("city", <int>$city.geoname_id) SET
		location = <point>[$city.coordinates.lon, $city.coordinates.lat],
		name = $city.name;        
};

FOR $city IN SELECT * FROM city {
    LET $this_location = $city.location;
    LET $closest = 
		(SELECT id, location, geo::distance($this_location, location) AS distance
		  FROM city
	ORDER BY distance ASC
	LIMIT 3
		).filter(|$c| $c.distance != 0);
    FOR $closest IN $closest {
      RELATE $city->close_to->$closest SET
	  	distance = geo::distance($city.location, $closest.location);
    };
};

SELECT name, id, ->close_to->city AS neighbours FROM city;
```

##  See also[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries#see-also)
  * •
[SurrealQL operators](https://surrealdb.com/docs/reference/query-language/language-primitives/operators)
  * •
[geo functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo)
