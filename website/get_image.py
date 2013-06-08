#! /usr/bin/env python
#-*- coding: utf-8 -*-

import cgi
import cgitb
import os
import sys
import tempfile

cgitb.enable()
root = "/home/jocelyn/polygon-generation"
sys.path.append(root)
from tools import utils

os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()

import matplotlib
import numpy
import shapely.wkt

# chose a non-GUI backend
matplotlib.use('Agg')
import matplotlib.pyplot as pyplot

form      = cgi.FieldStorage()
rel_id    = int(form.getvalue("id", -1))
params    = str(form.getvalue("params", 0))
name      = str(form.getvalue("name", ""))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

def draw_polygon(rel_id, params, name, color, zorder=0):
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

  PgCursor.execute(sql, sql_p)

  results = PgCursor.fetchall()
  wkt_geom = results[0][0]

  geom = shapely.wkt.loads(wkt_geom)
  if hasattr(geom, "exterior"):
    a = numpy.asarray(geom.exterior)
    pyplot.plot(a[:,0], a[:,1], color=color, zorder=zorder)
  else:
    for g in geom:
      a = numpy.asarray(g.exterior)
      pyplot.plot(a[:,0], a[:,1], color=color, zorder=zorder)

  return geom.bounds

fig = pyplot.figure(1, dpi=100)

(minx, miny, maxx, maxy) = draw_polygon(rel_id, params, name, "blue", zorder=10)

fig_width = 0.5*(maxx-minx)
fig_height = 0.75*(maxy-miny)

if fig_width > fig_height:
  fig_height = int(fig_height / fig_width * 10)
  fig_width = 10
else:
  fig_width = int(fig_width / fig_width * 10)
  fig_height = 10

fig.set_size_inches(fig_width, fig_height)

if rel_id != -1 and (params != 0 or name != ""):
  draw_polygon(rel_id, "0", "", "green", zorder=1)

if name != "":
  draw_polygon(-1, "", name, "orange", zorder=2)


import cStringIO
imgData = cStringIO.StringIO()
pyplot.savefig(imgData, format='png')

# rewind the data
imgData.seek(0)

print "Content-Type: image/png"
print

print imgData.read()
