#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import json
import os
import sys

root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root)
from tools import utils
from tools import OsmGeom

form = cgi.FieldStorage()

try:
    rel_id = [int(i) for i in form.getvalue("id", "-1").split(",")]
    params = str(form.getvalue("params", 0))
    if params == "0":
        (x, y, z) = (0, 0, 0)
    else:
        (x, y, z) = [float(i) for i in params.split("-")]
        params = "%f-%f-%f" % (x, y, z)
    format = str(form.getvalue("format", "geojson"))
    if format not in ("geojson", "wkt", "poly"):
        raise NotImplementedError
except:
    print("Status: 400 Bad Request")
    print("Content-Type: application/json; charset=utf-8")
    print("")
    print(json.dumps({"status": "ERROR", "message": "Parameters not supported"}))
    sys.exit(0)

PgConn   = utils.get_dbconn()
PgCursor = PgConn.cursor()

for id in rel_id:
    try:
        utils.check_polygon(PgCursor, id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        print("Status: 500 Internal Server Error")
        print("Content-Type: application/json; charset=utf-8")
        print("")
        print(json.dumps({"status": "ERROR", "message": "Polygon couldn't be generated"}))
        sys.exit(0)

if format == "geojson":
    sql_func = "ST_AsGeoJSON"
elif format == "wkt":
    sql_func = "ST_AsEWKT"
elif format == "poly":
    sql_func = "ST_AsText"

sql = "select " + sql_func + """(ST_Union(geom))
         from polygons where id IN %s AND params = %s"""
PgCursor.execute(sql, (tuple(rel_id), params))

results = PgCursor.fetchall()

if results == None:
    print("Status: 500 Internal Server Error")
    print("Content-Type: application/json; charset=utf-8")
    print("")
    print(json.dumps({"status": "ERROR", "message": "Polygon is empty"}))

if format == "geojson":
    print("Content-Type: application/geo+json; charset=utf-8")
else:
    print("Content-Type: text/plain; charset=utf-8")
print("")

if format == "poly":
    print("polygon")
    OsmGeom.write_multipolygon(sys.stdout, results[0][0])
else:
    for res in results:
        print(res[0])

PgConn.commit()
