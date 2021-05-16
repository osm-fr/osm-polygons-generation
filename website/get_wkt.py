#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import sys, os, cgi
root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = int(form.getvalue("id", -1))
params    = str(form.getvalue("params", -1))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

sql = """select ST_AsEWKT(geom)
         from polygons where id = %s AND params = %s"""
PgCursor.execute(sql, (rel_id, params))

results = PgCursor.fetchall()

if len(results) == 0:
  show(u"Status: 500")
  show(u"Content-Type: text/plain; charset=utf-8")
  show(u"")
  show(u"Error: Polygons wasn't correctly generated")
  sys.exit(0)

show(u"Content-Type: text/plain; charset=utf-8")
show(u"")

for res in results:
    show(u"%s" % res[0])
