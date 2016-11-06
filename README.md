osm-polygons-generation
=======================

Website to generate polygons for recursive relations in OpenStreetMap

Using this tool, you can get latest polygons from OSM, optionally simplified using PostGIS.

## Features
* Update geometry based on the latest OSM data
* Preserve multiple geometries between sesssion
* Simplify each shape using PostGIS ``ST_Buffer(ST_SimplifyPreserveTopology(ST_Buffer(ST_SnapToGrid(st_buffer(geom, %s), %s), 0), %s), 0))``
* For every version of the relation:
 * Display shape of polygon using image
 * Basic stats (number of nodes, lenght) 
 * Export to WKT, poly and GeoJSON
* More

## Live instances 

* http://polygons.openstreetmap.fr/
