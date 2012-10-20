#! /bin/bash

set -e

id=$1
params=$2

. /home/jocelyn/polygon-generation/tools/draw-functions.sh

mkdir -p $WORKDIR
cd $WORKDIR

pgsql2shp -f "bbox-$id.shp" -P "$PASSWORD" -u "$USER" -h localhost "$DATABASE" "
SELECT id, ST_Boundary(geom)
FROM polygons
WHERE id = '$id' AND params = '0'"

pgsql2shp -f "bbox-$id-$params.shp" -P "$PASSWORD" -u "$USER" -h localhost "$DATABASE" "
SELECT id, ST_Boundary(geom)
FROM polygons
WHERE id = '$id' AND params = '$params'"

mkdir -p "images/$id/thumbs"
TIFF="images/$id/$params.tif"
PNG="images/$id/$params.png"
PNG_THUMB="images/$id/thumbs/$params.png"

create_tif.py bbox-$id.shp $TIFF
draw_shp $TIFF bbox-$id.shp 200 200 255
draw_shp $TIFF bbox-$id-$params.shp 200 200 0

convert -quiet $TIFF $PNG
convert -quiet $TIFF -morphology Dilate Disk:2.0 -adaptive-resize 500x500 $PNG_THUMB

cd "images/$id/"
ln -sf ../../index.php .
