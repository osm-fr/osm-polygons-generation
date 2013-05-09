#! /usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os, cgi, re
import random
import string
root = "/home/jocelyn/polygon-generation"
sys.path.append(root)
from tools import utils
from tools import OsmGeom

show = utils.show

form = cgi.FieldStorage()

if "name" not in form and "poly" not in form:
    utils.print_header("Importer of .poly files")
    show(u"<h1>%s</h1>" % ("Import of .poly files"))
    show(u"<br><br>\n")
    show(u"<form method='POST' action=''>")
    show(u"<label for='name'>%s</label>" % "Name")
    show(u"<input type='text' name='name' id='name'>")
    show(u"<label for='poly'>%s</label>" % ".poly file")
    show(u"<input type='file' name='poly' id='poly'>")
    show(u"<input type='submit'>")
    show(u"</form>")
    sys.exit(0)


name = int(form.getvalue("name", -1))
poly = str(form.getvalue("poly", -1))

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

show(u"Content-Type: text/plain; charset=utf-8")
print

char_set = string.ascii_lowercase + string.digits
name += ''.join(random.sample(char_set*6,6))

show(u"importing as %s" % name)
wkt = OsmGeom.read_multipolygon_wkt(sys.stdout, wkt)

sql = """INSERT INTO polygons_user
         VALUES (%s, %s, NOW())"""
PgCursor.execute(sql, (name, poly))

results = PgCursor.fetchall()


