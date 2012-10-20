#! /usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os, cgi, subprocess, psycopg2
import cgitb
root = "/home/jocelyn/polygon-generation"
sys.path.append(root)
from tools import utils

form      = cgi.FieldStorage()
rel_id    = int(form.getvalue("id", -1))
x         = float(form.getvalue("x", -1))
y         = float(form.getvalue("y", -1))
z         = float(form.getvalue("z", -1))
refresh   = form.getvalue("refresh") != None

show = utils.show
cgitb.enable()

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

if rel_id == -1:
    utils.print_header("Polygon creation")
    show(u"<h1>%s</h1>" % ("Polygon creation"))
    show(u"<br><br>\n")
    show(u"<form method='GET' action=''>")
    show(u"<label for='id'>%s</label>" % "Id of relation")
    show(u"<input type='text' name='id' id='id'>")
    show(u"<input type='submit'>")
    show(u"</form>")

    sql_list = """select polygons.id, timestamp, relations.tags
         from polygons
         JOIN relations ON relations.id = polygons.id
         WHERE params = '0'
         ORDER BY id"""
    PgCursor.execute(sql_list)

    results = PgCursor.fetchall()

    show(u"<h1>%s</h1>" % ("List of generated polygons"))

    show(u"<table>\n")
    show(u"  <tr>\n")
    show(u"    <th>%s</th>\n" % ("id"))
    show(u"    <th>%s</th>\n" % ("timestamp"))
    show(u"    <th>%s</th>\n" % ("name"))
    show(u"    <th>%s</th>\n" % ("admin"))
    show(u"  </tr>\n")

    for res in results:
        show(u"  <tr>\n")
        show(u"    <td><a href='?id=%d'>%d</a></td>\n" % (res["id"], res["id"]))
        show(u"    <td>" + str(res["timestamp"]) + "</td>\n")
        if "name" in res["tags"]:
            show(u"    <td>" + res["tags"]["name"] + "</td>\n")
        else:
            show(u"    <td></td>\n")
        if "admin_level" in res["tags"]:
            show(u"    <td>" + res["tags"]["admin_level"] + "</td>\n")
        else:
            show(u"    <td></td>\n")
        show(u"  </tr>\n")

    show(u"</table>\n")

    sys.exit(0)


utils.print_header("Polygon creation for id %d" % rel_id)

if x > 0 and y > 0 and z > 0:
    params = "%f-%f-%f" % (x, y, z)
    sql_gen1 = "DELETE FROM polygons WHERE id = %s AND params = %s"
    sql_gen2 = """INSERT INTO polygons VALUES
  (%s,
   %s,
   NOW(),
   (SELECT ST_Union(geom, ST_Buffer(ST_SimplifyPreserveTopology(ST_Buffer(ST_SnapToGrid(st_buffer(geom, %s), %s), 0), %s), 0))
    FROM polygons
    WHERE id = %s AND params = '0')
  );"""
    PgCursor.execute(sql_gen1, (rel_id, params))
    try:
        PgCursor.execute(sql_gen2, (rel_id, params,
                                    x, y, z, rel_id ))
    except psycopg2.InternalError:
        show(u"Error while generating polygon.")
        show(u"Message from postgresql server:<br>")
        show(u"%s" % PgConn.notices)
        raise

    cmd = [os.path.join(root, "tools", "gen_image.sh"), "%d" % rel_id, "%s" % params]
    proc = subprocess.Popen(cmd)


sql_list = """select id, params, timestamp, ST_NPoints(geom) AS npoints,
              ST_MaxDistance(geom, geom) AS length
         from polygons where id = %s
         ORDER BY params"""
PgCursor.execute(sql_list, (rel_id, ))

results = PgCursor.fetchall()

if len(results) == 0 or refresh:
    sql_create = "select create_polygon(%s);"
    try:
        PgCursor.execute(sql_create, (rel_id, ))
    except psycopg2.InternalError:
        show(u"Error while generating polygon.")
        show(u"You could check the geometry through <a href='http://osm8.openstreetmap.fr//~osmbin/analyse-relation-open.py??%d'>a relation analyser</a>.<br>" % rel_id)
        show(u"Message from postgresql server:<br>")
        show(u"%s" % PgConn.notices)
        sys.exit(0)

    PgCursor.execute(sql_list, (rel_id, ))
        
    results = PgCursor.fetchall()

    cmd = [os.path.join(root, "tools", "gen_image.sh"), "%d" % rel_id, "0"]
    proc = subprocess.Popen(cmd)

show(u"<h1>%s</h1>" % ("List of available polygons for id = %d" % rel_id))

show(u"<table>\n")
show(u"  <tr>\n")
show(u"    <th>%s</th>\n" % ("params"))
show(u"    <th>%s</th>\n" % ("timestamp"))
show(u"    <th>%s</th>\n" % ("NPoints"))
show(u"    <th>%s</th>\n" % ("Length"))
show(u"    <th>%s</th>\n" % ("WKT"))
show(u"    <th>%s</th>\n" % ("poly"))
show(u"    <th>%s</th>\n" % ("Image"))
show(u"  </tr>\n")

for res in results:
    if res["params"] == "0":
        geom_length = res["length"]
    show(u"  <tr>\n")
    show(u"    <td>" + str(res["params"]) + "</td>\n")
    show(u"    <td>" + str(res["timestamp"]) + "</td>\n")
    show(u"    <td>" + str(res["npoints"]) + "</td>\n")
    show(u"    <td>" + str(res["length"]) + "</td>\n")
    show(u"    <td><a href='get_wkt.py?id=%d&amp;params=%s'>WKT</a></td>\n" % (rel_id, str(res["params"])))
    show(u"    <td><a href='get_poly.py?id=%d&amp;params=%s'>poly</a></td>\n" % (rel_id, str(res["params"])))
    show(u"    <td><a href='images/%d/%s.png'>image</a></td>\n" % (rel_id, str(res["params"])))
    show(u"  </tr>\n")

show(u"</table>\n")

show(u"<br>\n")
show(u"<form method='POST' action=''>")
show(u"<input type='submit' value='Refresh original geometry' name='refresh'>")
show(u"</form>")

show(u"<h1>%s</h1>" % ("Generate a simplified polygon"))

show(u"ST_Simplify(ST_SnapToGrid(ST_Buffer(geom, X), Y), Z))")

if geom_length >= 10:
    rec_x = 0.04
    rec_y = 0.01
    rec_z = 0.01
elif geom_length > 1:
    rec_x = 0.02
    rec_y = 0.005
    rec_z = 0.005
else:
    rec_x = 0.004
    rec_y = 0.001
    rec_z = 0.001

show(u"<form method='POST' action=''>")
show(u"<label for='x'>%s</label>" % "X")
show(u"<input type='text' name='x' id='x' value='%f'><br>" % rec_x)
show(u"<label for='y'>%s</label>" % "Y")
show(u"<input type='text' name='y' id='y' value='%f'><br>" % rec_y)
show(u"<label for='z'>%s</label>" % "Z")
show(u"<input type='text' name='z' id='z' value='%f'><br>" % rec_z)
show(u"<input type='submit' name='generate'>")
show(u"</form>")


###########################################################################
utils.print_tail()

PgConn.commit()
PgConn.close()
