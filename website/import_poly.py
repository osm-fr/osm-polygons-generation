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
    show(u"<form method='POST' action=''  enctype='multipart/form-data'>")
    show(u"<label for='name'>%s</label>" % "Name")
    show(u"<input type='text' name='name' id='name'>")
    show(u"<label for='poly'>%s</label>" % ".poly file")
    show(u"<input type='file' name='poly' id='poly'>")
    show(u"<input type='submit'>")
    show(u"</form>")
    utils.print_tail()
    sys.exit(0)

import cgitb
cgitb.enable()

name = str(form.getvalue("name", -1))
poly_file = form["poly"].file

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

utils.print_header("Importer of .poly files")

#show(u"Content-Type: text/plain; charset=utf-8")
#print

char_set = string.ascii_lowercase + string.digits
name += "_" + (''.join(random.sample(char_set*6,6)))

show(u"importing as <span id='name'>%s</span>" % name)
wkt = OsmGeom.read_multipolygon_wkt(poly_file)

sql = """INSERT INTO polygons_user
         VALUES (%s, NOW(), ST_GeomFromText(%s, 4326))"""
PgCursor.execute(sql, (name, wkt))

show(u"<br>")
show(u"Polygon can be seen on <a href='show_polygon.py?name=%s'>this page</a>." % name)

###########################################################################
utils.print_tail()

PgConn.commit()
PgConn.close()
