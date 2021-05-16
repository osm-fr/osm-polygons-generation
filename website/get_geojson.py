#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import sys, os, cgi
root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = [int(i) for i in form.getvalue("id", -1).split(",")]
params    = str(form.getvalue("params", 0))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

show(u"Content-Type: text/plain; charset=utf-8")
show(u"")

sql = """select ST_AsGeoJSON(ST_Collect(geom))
         from polygons where id IN %s AND params = %s"""
PgCursor.execute(sql, (tuple(rel_id), params))

results = PgCursor.fetchall()

for res in results:
    show(res[0])
