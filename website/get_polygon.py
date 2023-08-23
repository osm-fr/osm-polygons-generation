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

format = os.path.basename(__file__).removeprefix("get_").removesuffix(".py")

form = cgi.FieldStorage()

try:
    rel_id = [int(i) for i in form.getvalue("id", "-1").split(",")]
    params = str(form.getvalue("params", 0))
    if params == "0":
        (x, y, z) = (0, 0, 0)
    else:
        (x, y, z) = [float(i) for i in params.split("-")]
        params = "%f-%f-%f" % (x, y, z)
    name = str(form.getvalue("name", ""))
    if form.getvalue("format", None):
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

if rel_id != [-1]:
    for id in rel_id:
        try:
            if id < 0:
                raise utils.NonExistingRelation
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

if rel_id != [-1]:
  sql1 = """SELECT ST_Union(geom)
            FROM polygons WHERE id IN %s AND params = %s"""
  param1 = (tuple(rel_id), params)
else:
  sql1 = "SELECT 'SRID=4326;POINT EMPTY'::geometry"
  param1 = ()

if name != "":
  sql2 = """SELECT geom
           FROM polygons_user WHERE name = %s"""
  param2 = (name, )
else:
  sql2 = "SELECT 'SRID=4326;POINT EMPTY'::geometry"
  param2 = ()

sql = "select " + sql_func + "(ST_Union((" + sql1 + "), (" + sql2 + ")))"
PgCursor.execute(sql, param1 + param2)

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
