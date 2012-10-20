#! /usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os, cgi
root = "/home/jocelyn/polygon-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = int(form.getvalue("id", -1))
params    = str(form.getvalue("params", -1))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

show(u"Content-Type: text/plain; charset=utf-8")
print

sql = """select ST_AsEWKT(geom)
         from polygons where id = %s AND params = %s"""
PgCursor.execute(sql, (rel_id, params))

results = PgCursor.fetchall()

for res in results:
    show(u"%s" % res[0])
