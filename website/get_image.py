#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import cgi
import cgitb
import io
import math
import os
import shutil
import sys
import tempfile

cgitb.enable()
root = "/data/project/polygons/polygons-generation"
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
rel_id    = [int(i) for i in form.getvalue("id", "-1").split(",")]
params    = str(form.getvalue("params", 0))
name      = str(form.getvalue("name", ""))

show = utils.show

PgConn    = utils.get_dbconn()
PgCursor  = PgConn.cursor()

def draw_polygon(rel_id, params, name, color, zorder=0, label=""):
  if name != "" and rel_id != [-1]:
    sql = """select ST_AsText(ST_Union((SELECT ST_Union(geom) from polygons
                                        where id IN %s AND params = %s),
                                       (SELECT geom from polygons_user
                                        WHERE name = %s)))"""
    sql_p = (tuple(rel_id), params, name)

  elif name == "" and rel_id != [-1]:
    sql = """select ST_AsText(ST_Union(geom))
             from polygons where id IN %s AND params = %s"""
    sql_p = (tuple(rel_id), params)

  elif name != "" and rel_id == [-1]:
    sql = """select ST_AsText(geom)
             from polygons_user where name = %s"""
    sql_p = (name, )

  PgCursor.execute(sql, sql_p)

  results = PgCursor.fetchall()
  wkt_geom = results[0][0]

  geom = shapely.wkt.loads(wkt_geom)
  if hasattr(geom, "exterior"):
    a = numpy.asarray(geom.exterior)
    pyplot.plot(a[:,0], a[:,1], color=color, zorder=zorder, label=label)
  else:
    label_shown = False
    for g in geom:
      a = numpy.asarray(g.exterior)
      if label_shown:
        pyplot.plot(a[:,0], a[:,1], color=color, zorder=zorder)
      else:
        label_shown = True
        pyplot.plot(a[:,0], a[:,1], color=color, zorder=zorder, label=label)

  return geom.bounds

fig = pyplot.figure(1, dpi=100)

if rel_id != [-1] and name != "":
  label = "union"
elif rel_id == [-1]:
  label = "user polygon"
elif params != "0":
  label = "simplified geometry"
else:
  label = "base geometry"

(minx, miny, maxx, maxy) = draw_polygon(rel_id, params, name, "blue", zorder=10, label=label)

diff_x = maxx - minx
diff_y = maxy - miny

# TODO: this should depend on the latitude
diff_x_fixed = diff_x
diff_y_fixed = diff_y / math.cos(math.radians((miny+maxy)/2))

if diff_x_fixed > diff_y_fixed:
  fig_height = 10
  fig_width = int(diff_x_fixed / diff_y_fixed * 10)
else:
  fig_width = 10
  fig_height = int(diff_y_fixed / diff_x_fixed * 10)

if fig_width > 200:
  fig_width = 200
if fig_height > 200:
  fig_height = 200

fig.set_size_inches(fig_width, fig_height)
ax = fig.add_subplot(111)
ax.set_xlim(left=minx - 0.05*diff_x, right=maxx + 0.05*diff_x)
ax.set_ylim(bottom=miny - 0.05*diff_y, top=maxy + 0.05*diff_y)
ax.autoscale_view()

if rel_id != [-1] and (params != "0" or name != ""):
  draw_polygon(rel_id, "0", "", "green", zorder=1, label="base geometry")

if name != "" and rel_id != [-1]:
  draw_polygon([-1], "", name, "orange", zorder=2, label="user polygon")

pyplot.legend(loc='upper center', ncol=5, frameon=True,
              bbox_to_anchor=(0.5, 1), bbox_transform=pyplot.gcf().transFigure)
fig.tight_layout()

imgData = io.BytesIO()
pyplot.savefig(imgData, format='png')

# rewind the data
imgData.seek(0)

print("Content-Type: image/png")
print()
sys.stdout.flush()
sys.stdout.buffer.write(imgData.read())

# Clean temporary directory
shutil.rmtree(os.environ['MPLCONFIGDIR'])
