#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import sys, cgi
import random
import string
root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils
from tools import OsmGeom

show = utils.show

form = cgi.FieldStorage()

if "name" not in form and "poly" not in form:
    utils.print_header("Importer of .poly files")
    show("<h1>%s</h1>" % ("Import of .poly files"))
    show("<br><br>\n")
    show("<form method='POST' action=''  enctype='multipart/form-data'>")
    show("<label for='name'>%s</label>" % "Name")
    show("<input type='text' name='name' id='name'>")
    show("<label for='poly'>%s</label>" % ".poly file")
    show("<input type='file' name='poly' id='poly'>")
    show("<input type='submit'>")
    show("</form>")
    utils.print_tail()
    sys.exit(0)

import cgitb
cgitb.enable()

name = str(form.getvalue("name", -1))
poly_file = form["poly"].file

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

utils.print_header("Importer of .poly files")

char_set = string.ascii_lowercase + string.digits
name += "_" + (''.join(random.sample(char_set*6,6)))

show("importing as <span id='name'>%s</span>" % name)
wkt = OsmGeom.read_multipolygon_wkt(poly_file)

sql = """INSERT INTO polygons_user
         VALUES (%s, NOW(), ST_GeomFromText(%s, 4326))"""
PgCursor.execute(sql, (name, wkt))

show("<br>")
show("Polygon can be seen on <a href='show_polygon.py?name=%s'>this page</a>." % name)

###########################################################################
utils.print_tail()

PgConn.commit()
PgConn.close()
