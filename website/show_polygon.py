#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import sys, cgi
import cgitb
root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils

form   = cgi.FieldStorage()
rel_id = int(form.getvalue("id", -1))
name   = str(form.getvalue("name", ""))

show = utils.show
cgitb.enable()

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

if rel_id == -1 and name == "":
    utils.print_header("Show polygon")
    show("<h1>%s</h1>" % ("Show polygon"))
    show("<form method='GET' action=''>")
    show("<label for='id'>%s</label>" % "Id of relation")
    show("<input type='text' name='id' id='id'>")
    show("<br>")
    show("<label for='name'>%s</label>" % "Name of user polygon")
    show("<input type='text' name='name' id='name'>")
    show("<input type='submit'>")
    show("</form>")
    sys.exit(0)

utils.print_header("Show polygon")

if rel_id != -1:

    sql_list = """SELECT id, params, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons WHERE id = %s
                  ORDER BY params"""
    PgCursor.execute(sql_list, (rel_id, ))

    osm_results = PgCursor.fetchall()

    if osm_results:
        show("<h2>%s</h2>" % ("List of available polygons for id = %d" % rel_id))

        show("<table class='sortable'>\n")
        show("  <tr>\n")
        show("    <th class='sorttable_sorted'>%s<span id='sorttable_sortfwdind'>&nbsp;▾</span></th>\n" % ("params"))
        show("    <th>%s</th>\n" % ("timestamp"))
        show("    <th>%s</th>\n" % ("NPoints"))
        show("    <th>%s</th>\n" % ("Length"))
        show("    <th>%s</th>\n" % ("WKT"))
        show("    <th>%s</th>\n" % ("GeoJSON"))
        show("    <th>%s</th>\n" % ("poly"))
        show("    <th>%s</th>\n" % ("Image"))
        show("  </tr>\n")

        for res in osm_results:
            show("  <tr>\n")
            show("    <td>" + str(res["params"]) + "</td>\n")
            show("    <td>" + str(res["timestamp"]) + "</td>\n")
            show("    <td>" + str(res["npoints"]) + "</td>\n")
            show("    <td>" + str(res["length"]) + "</td>\n")
            show("    <td><a href='get_wkt.py?id=%d&amp;params=%s'>WKT</a></td>\n" % (rel_id, str(res["params"])))
            show("    <td><a href='get_geojson.py?id=%d&amp;params=%s'>GeoJSON</a></td>\n" % (rel_id, str(res["params"])))
            show("    <td><a href='get_poly.py?id=%d&amp;params=%s'>poly</a></td>\n" % (rel_id, str(res["params"])))
            show("    <td><a href='get_image.py?id=%d&amp;params=%s'>image</a></td>\n" % (rel_id, str(res["params"])))
            show("  </tr>\n")

        show("</table>\n")

if name != "":

    sql_list = """SELECT name, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons_user WHERE name LIKE %s
                  ORDER BY name"""
    PgCursor.execute(sql_list, (name, ))

    user_results = PgCursor.fetchall()

    if user_results:
        show("<h2>%s</h2>" % ("List of available user polygons for name = %s" % name))

        show("<table class='sortable'>\n")
        show("  <tr>\n")
        show("    <th>%s</th>\n" % ("name"))
        show("    <th>%s</th>\n" % ("timestamp"))
        show("    <th>%s</th>\n" % ("NPoints"))
        show("    <th>%s</th>\n" % ("Length"))
#        show("    <th>%s</th>\n" % ("WKT"))
#        show("    <th>%s</th>\n" % ("GeoJSON"))
        show("    <th>%s</th>\n" % ("poly"))
        show("    <th>%s</th>\n" % ("Image"))
        show("  </tr>\n")

        for res in user_results:
            n = str(res["name"])
            show("  <tr>\n")
            show("    <td>" + n + "</td>\n")
            show("    <td>" + str(res["timestamp"]) + "</td>\n")
            show("    <td>" + str(res["npoints"]) + "</td>\n")
            show("    <td>" + str(res["length"]) + "</td>\n")
#            show("    <td><a href='get_wkt.py?name=%s'>WKT</a></td>\n" % (n))
#            show("    <td><a href='get_geojson.py?name=%s'>GeoJSON</a></td>\n" % (n))
            show("    <td><a href='get_poly.py?name=%s'>poly</a></td>\n" % (n))
            show("    <td><a href='get_image.py?name=%s'>image</a></td>\n" % (n))
            show("  </tr>\n")

        show("</table>\n")


if rel_id != -1 and name != "" and osm_results and user_results:

    show("<h2>%s</h2>" % ("Union of all osm/user polygons"))

    show("<table>\n")
    show("  <tr>\n")
    show("    <th>params</th>\n")
    for u_res in user_results:
        show("    <th>%s</th>\n" % (u_res["name"]))
    show("  </tr>\n")
    for o_res in osm_results:
        show("  <tr>\n")
        show("    <td>" + str(o_res["params"]) + "</td>\n")
        for u_res in user_results:
            show("    <td>")
            show("<a href='get_poly.py?id=%d&amp;params=%s&amp;name=%s' title='poly'>poly</a>\n" % (rel_id, o_res["params"], u_res["name"]))
            show("<a href='get_image.py?id=%d&amp;params=%s&amp;name=%s' title='image'>image</a>\n" % (rel_id, o_res["params"], u_res["name"]))
            show("    </td>")
        show("  </tr>\n")
    show("</table>\n")

if rel_id == -1 or name == "":
    show("<br><br>\n")
    show("<h1>%s</h1>" % ("Show polygon"))
    show("<form method='GET' action=''>")
    show("<label for='id'>%s</label>" % "Id of relation")
    if rel_id == -1:
        show("<input type='text' name='id' id='id'>")
    else:
        show("<input type='text' name='id' id='id' value='%d'>", rel_id)
    show("<br>")
    show("<label for='name'>%s</label>" % "Name of user polygon")
    show("<input type='text' name='name' id='name' value='%s'>" % name)
    show("<input type='submit'>")
    show("</form>")

###########################################################################
utils.print_tail()

PgConn.commit()
PgConn.close()
