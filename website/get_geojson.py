#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import os
import sys

root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = [int(i) for i in form.getvalue("id", "-1").split(",")]
params    = str(form.getvalue("params", 0))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

show("Content-Type: application/geo+json; charset=utf-8")
show("")

if params == "0":
    (x, y, z) = (0, 0, 0)
else:
    (x, y, z) = [float(i) for i in params.split("-")]

for id in rel_id:
    utils.check_polygon(PgCursor, id, x, y, z, create=True)

sql = """select ST_AsGeoJSON(ST_Union(geom))
         from polygons where id IN %s AND params = %s"""
PgCursor.execute(sql, (tuple(rel_id), params))

results = PgCursor.fetchall()

for res in results:
    show(res[0])

PgConn.commit()
