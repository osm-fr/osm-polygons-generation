#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import json
import os
import sys

root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root)
from tools import utils

form = cgi.FieldStorage()

try:
    rel_id = [int(i) for i in form.getvalue("id", "-1").split(",")]
    params = str(form.getvalue("params", 0))
    if params == "0":
        (x, y, z) = (0, 0, 0)
    else:
        (x, y, z) = [float(i) for i in params.split("-")]
        params = "%f-%f-%f" % (x, y, z)
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

sql = """select ST_AsGeoJSON(ST_Union(geom))
         from polygons where id IN %s AND params = %s"""
PgCursor.execute(sql, (tuple(rel_id), params))

results = PgCursor.fetchall()

if results == None:
    print("Status: 500 Internal Server Error")
    print("Content-Type: application/json; charset=utf-8")
    print("")
    print(json.dumps({"status": "ERROR", "message": "Polygon is empty"}))

print("Content-Type: application/geo+json; charset=utf-8")
print("")

for res in results:
    print(res[0])

PgConn.commit()
