#! /usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os, cgi, re
root = "/home/jocelyn/polygon-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = int(form.getvalue("id", -1))
params    = str(form.getvalue("params", -1))
name      = str(form.getvalue("name", ""))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()


if name != "" and rel_id != -1:
  sql = """select ST_AsText(ST_Union((SELECT geom from polygons
                                      where id = %s AND params = %s),
                                     (SELECT geom from polygons_user
                                      WHERE name = %s)))"""
  sql_p = (rel_id, params, name)

elif name == "" and rel_id != -1:
  sql = """select ST_AsText(geom)
           from polygons where id = %s AND params = %s"""
  sql_p = (rel_id, params)

elif name != "" and rel_id == -1:
  sql = """select ST_AsText(geom)
           from polygons_user where name = %s"""
  sql_p = (name, )

else:
  show(u"Status: 500")
  show(u"Content-Type: text/plain; charset=utf-8")
  print
  show(u"Error: id or name should be given")
  sys.exit(0)

PgCursor.execute(sql, sql_p)

results = PgCursor.fetchall()
if not results:
  show(u"Status: 500")
  show(u"Content-Type: text/plain; charset=utf-8")
  print
  show(u"Error when getting polygon from database")
  sys.exit(0)

else:
  show(u"Content-Type: text/plain; charset=utf-8")
  print

wkt = results[0][0]

def write_polygon(f, wkt, p):

        match = re.search("^\(\((?P<pdata>.*)\)\)$", wkt)
        pdata = match.group("pdata")
        rings = re.split("\),\(", pdata)

        first_ring = True
        for ring in rings:
                coords = re.split(",", ring)

                p = p + 1
                if first_ring:
                        f.write(str(p) + "\n")
                        first_ring = False
                else:
                        f.write("!" + str(p) + "\n")

                for coord in coords:
                        ords = coord.split()
                        f.write("\t%s\t%s\n" % (ords[0], ords[1]))

                f.write("END\n")

        return p

def write_multipolygon(f, wkt):

        match = re.search("^MULTIPOLYGON\((?P<mpdata>.*)\)$", wkt)

        if match:
                mpdata = match.group("mpdata")
                polygons = re.split("(?<=\)\)),(?=\(\()", mpdata)

                p = 0
                for polygon in polygons:
                        p = write_polygon(f, polygon, p)

                return

        match = re.search("^POLYGON(?P<pdata>.*)$", wkt)
        if match:
                pdata = match.group("pdata")
                write_polygon(f, pdata, 0)



show(u"polygon")
write_multipolygon(sys.stdout, wkt)
show(u"END")
