#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import sys

root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = [int(i) for i in form.getvalue("id", "-1").split(",")]
params    = str(form.getvalue("params", 0))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

sql = """select ST_AsEWKT(ST_Union(geom))
         from polygons where id IN %s AND params = %s"""
PgCursor.execute(sql, (tuple(rel_id), params))

results = PgCursor.fetchall()

if len(results) == 0:
  show("Status: 500")
  show("Content-Type: text/plain; charset=utf-8")
  show("")
  show("Error: Polygons wasn't correctly generated")
  sys.exit(0)

show("Content-Type: text/plain; charset=utf-8")
show("")

for res in results:
    show("%s" % res[0])
