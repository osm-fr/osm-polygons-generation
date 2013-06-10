#! /usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os, cgi, subprocess, psycopg2, re
import cgitb
root = "/home/jocelyn/polygon-generation"
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
    show(u"<h1>%s</h1>" % ("Show polygon"))
    show(u"<br><br>\n")
    show(u"<form method='GET' action=''>")
    show(u"<label for='id'>%s</label>" % "Id of relation")
    show(u"<input type='text' name='id' id='id'>")
    show(u"<br>")
    show(u"<label for='name'>%s</label>" % "Name of user polygon")
    show(u"<input type='text' name='name' id='name'>")
    show(u"<input type='submit'>")
    show(u"</form>")
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
        show(u"<h2>%s</h2>" % ("List of available polygons for id = %d" % rel_id))
        
        show(u"<table class='sortable'>\n")
        show(u"  <tr>\n")
        show(u"    <th class='sorttable_sorted'>%s<span id='sorttable_sortfwdind'>&nbsp;▾</span></th>\n" % ("params"))
        show(u"    <th>%s</th>\n" % ("timestamp"))
        show(u"    <th>%s</th>\n" % ("NPoints"))
        show(u"    <th>%s</th>\n" % ("Length"))
        show(u"    <th>%s</th>\n" % ("WKT"))
        show(u"    <th>%s</th>\n" % ("GeoJSON"))
        show(u"    <th>%s</th>\n" % ("poly"))
        show(u"    <th>%s</th>\n" % ("Image"))
        show(u"  </tr>\n")
        
        for res in osm_results:
            show(u"  <tr>\n")
            show(u"    <td>" + str(res["params"]) + "</td>\n")
            show(u"    <td>" + str(res["timestamp"]) + "</td>\n")
            show(u"    <td>" + str(res["npoints"]) + "</td>\n")
            show(u"    <td>" + str(res["length"]) + "</td>\n")
            show(u"    <td><a href='get_wkt.py?id=%d&amp;params=%s'>WKT</a></td>\n" % (rel_id, str(res["params"])))
            show(u"    <td><a href='get_geojson.py?id=%d&amp;params=%s'>GeoJSON</a></td>\n" % (rel_id, str(res["params"])))
            show(u"    <td><a href='get_poly.py?id=%d&amp;params=%s'>poly</a></td>\n" % (rel_id, str(res["params"])))
            show(u"    <td><a href='images/%d/%s.png'>image</a></td>\n" % (rel_id, str(res["params"])))
            show(u"  </tr>\n")
        
        show(u"</table>\n")

if name != "":

    sql_list = """SELECT name, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons_user WHERE name LIKE %s
                  ORDER BY name"""
    PgCursor.execute(sql_list, (name, ))
    
    user_results = PgCursor.fetchall()
    
    if user_results:
        show(u"<h2>%s</h2>" % ("List of available user polygons for name = %s" % name))
        
        show(u"<table class='sortable'>\n")
        show(u"  <tr>\n")
        show(u"    <th>%s</th>\n" % ("name"))
        show(u"    <th>%s</th>\n" % ("timestamp"))
        show(u"    <th>%s</th>\n" % ("NPoints"))
        show(u"    <th>%s</th>\n" % ("Length"))
        show(u"    <th>%s</th>\n" % ("WKT"))
        show(u"    <th>%s</th>\n" % ("GeoJSON"))
        show(u"    <th>%s</th>\n" % ("poly"))
        show(u"    <th>%s</th>\n" % ("Image"))
        show(u"  </tr>\n")
        
        for res in user_results:
            n = str(res["name"])
            show(u"  <tr>\n")
            show(u"    <td>" + n + "</td>\n")
            show(u"    <td>" + str(res["timestamp"]) + "</td>\n")
            show(u"    <td>" + str(res["npoints"]) + "</td>\n")
            show(u"    <td>" + str(res["length"]) + "</td>\n")
            show(u"    <td><a href='get_wkt.py?name=%s'>WKT</a></td>\n" % (n))
            show(u"    <td><a href='get_geojson.py?name=%s'>GeoJSON</a></td>\n" % (n))
            show(u"    <td><a href='get_poly.py?name=%s'>poly</a></td>\n" % (n))
            show(u"    <td><a href='get_image.py?name=%s'>image</a></td>\n" % (n))
            show(u"  </tr>\n")
        
        show(u"</table>\n")


if rel_id != -1 and name != "" and osm_results and user_results:

    show(u"<h2>%s</h2>" % ("Union of all osm/user polygons"))

    show(u"<table>\n")
    show(u"  <tr>\n")
    show(u"    <th>params</th>\n")
    for u_res in user_results:
        show(u"    <th>%s</th>\n" % (u_res["name"]))
    show(u"  </tr>\n")
    for o_res in osm_results:
        show(u"  <tr>\n")
        show(u"    <td>" + str(o_res["params"]) + "</td>\n")
        for u_res in user_results:
            show(u"    <td>")
            show(u"<a href='get_poly.py?id=%d&amp;params=%s&amp;name=%s' title='poly'>p</a>\n" % (rel_id, o_res["params"], u_res["name"]))
            show(u"<a href='get_image.py?id=%d&amp;params=%s&amp;name=%s' title='image'>i</a>\n" % (rel_id, o_res["params"], u_res["name"]))
            show(u"    </td>")
        show(u"  </tr>\n")
    show(u"</table>\n")
 

###########################################################################
utils.print_tail()

PgConn.commit()
PgConn.close()
