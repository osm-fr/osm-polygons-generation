#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import os
import re
import sys

root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root)
from tools import utils
from tools import OsmGeom

form      = cgi.FieldStorage()
rel_id    = [int(i) for i in form.getvalue("id", "-1").split(",")]
params    = str(form.getvalue("params", 0))
name      = str(form.getvalue("name", ""))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()


if name != "" and rel_id != [-1]:
  sql = """select ST_AsText(ST_Union((SELECT ST_Union(geom) from polygons
                                      where id IN %s AND params = %s),
                                     (SELECT geom from polygons_user
                                      WHERE name = %s)))"""
  sql_p = (tuple(rel_id), params, name)

elif name == "" and rel_id != [-1]:
  sql = """select ST_AsText(ST_Union(geom))
           from polygons where id IN %s AND params = %s"""
  sql_p = (tuple(rel_id), params)

elif name != "" and rel_id == [-1]:
  sql = """select ST_AsText(geom)
           from polygons_user where name = %s"""
  sql_p = (name, )

else:
  show("Status: 500")
  show("Content-Type: text/plain; charset=utf-8")
  show("")
  show("Error: id or name should be given")
  sys.exit(0)

PgCursor.execute(sql, sql_p)

results = PgCursor.fetchall()
if not results:
  show("Status: 500")
  show("Content-Type: text/plain; charset=utf-8")
  show("")
  show("Error when getting polygon from database")
  sys.exit(0)

else:
  show("Content-Type: text/plain; charset=utf-8")
  show("")

wkt = results[0][0]

show("polygon")
OsmGeom.write_multipolygon(sys.stdout, wkt)
show("END")
