#!/bin/bash

WORKDIR=/data/work/jocelyn/polygons

DATABASE=osm
USER=jocelyn
PASSWORD=aueuea

SCRIPT=$(readlink -f $0)
SCRIPTPATH=`dirname $SCRIPT`

export PATH=$PATH:$SCRIPTPATH

function get_line_shp {
  # $1 is the target file
  # $2 is the SQL argument to the WHERE function
  # $3 is an optional SQL argument to check another tag
  sql="SELECT id, linestring AS geom
FROM ways"

  sql="$sql
WHERE ST_IsValid(linestring) AND ST_NPoints(linestring) > 1 AND $2"
  if [ "x$3" != "x" ]; then
    sql="$sql AND $3 "
  fi
  if [ "x$4" != "x" ]; then
    sql="$sql AND $4 "
  fi

  echo "$sql"

  pgsql2shp -f "$1" "$DATABASE" "$sql"
}  

function get_polygon_shp {
  # $1 is the target file
  # $2 is the SQL argument to the WHERE function
  pgsql2shp -f "$1" "$DATABASE" "
SELECT id, ST_MakePolygon(linestring) AS geom
FROM ways
WHERE $2 AND
      ST_IsClosed(linestring) AND
      ST_NumPoints(linestring) >= 4
"
}  

function draw_shp {
  # $1 is the target .tif file
  # $2 is the source .shp file
  # $3 $4 $5 are the RGB colours to write

  layer=`echo "$2" | sed "s/.shp$//"`
  gdal_rasterize -b 1 -b 2 -b 3 -burn "$3" -burn "$4" -burn "$5" \
                 -l "$layer" "$2" "$1"
}
