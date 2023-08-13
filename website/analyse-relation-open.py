#!/usr/bin/env python3
#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## This program is free software: you can redistribute it and/or modify  ##
## it under the terms of the GNU General Public License as published by  ##
## the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                   ##
##                                                                       ##
## This program is distributed in the hope that it will be useful,       ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of        ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         ##
## GNU General Public License for more details.                          ##
##                                                                       ##
## You should have received a copy of the GNU General Public License     ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>. ##
##                                                                       ##
###########################################################################

import cgi
import cgitb
import sys
sys.path.append("/data/project/osmbin/osm/osc_modif/")
from modules import OsmBin

root = "/data/project/polygons/polygons-generation"
sys.path.append(root)
from tools import utils

show = utils.show
cgitb.enable()

###########################################################################

def get_ts():
    url = "/data/work/osmbin/replication/diffs/planet/minute/state.txt"
    f = open(url, "r")
    res = f.read().split("\n")
    res = [x.replace("\\","") for x in res if x.startswith("timestamp")][0]
    f.close()
    return res

###########################################################################

def get_ways(relid):
    data = bin.RelationFullRecur(relid, WayNodes = False, RemoveSubarea = True)
    ways = []
    for x in data:
        if x["type"] == "way":
            ways.append(x["data"])
    return ways

def ways_bounds(ways):
    nodes = []
    for w in ways:
        nodes.append(w["nd"][0])
        nodes.append(w["nd"][-1])
    err = []
    for n in set(nodes):
        if (nodes.count(n) % 2) == 1:
            err.append((n, nodes.count(n)))
    return err

###########################################################################

if __name__=="__main__":

    form = cgi.FieldStorage()
    rel_id = int(form.getvalue("id", -1))

    if rel_id == -1:
        utils.print_header("Open relation analyser")
        show("<h1>%s</h1>" % ("Open relation analyser"))
        show("<p>This will analyse a relation, and show the location of nodes where an odd number of ways are connected. These nodes are locations where relation might be broken</p>")
        show("<form method='GET' action=''>")
        show("<label for='id'>%s</label>" % "Id of relation")
        show("<input type='text' name='id' id='id'>")
        show("<input type='submit'>")
        show("</form>")
        show("<br>\n")
        utils.print_tail()
        sys.exit(0)

    utils.print_header("Open relation analyser for id=%d" % rel_id)
    show("<h1>Open relation analyser for id=%d</h1>" % rel_id)
    bin = OsmBin.OsmBin("/data/work/osmbin/data/")
    wys = get_ways(rel_id)

    error_found = 0
    for nid, cpt in ways_bounds(wys):
        dta = bin.NodeGet(nid)
        if not error_found:
            show("<p>Here are the location of nodes where an odd number of ways are connected. These nodes are locations where relation might be broken</p>")
            show("<table class='sortable'>")
            show("  <tr>")
            show("    <th>%s</th>" % ("node id"))
            show("    <th>%s</th>" % ("count"))
            show("    <th>%s</th>" % ("lat"))
            show("    <th>%s</th>" % ("lon"))
            show("  </tr>")
        error_found = 1
        if dta:
            show("  <tr>")
            show("    <td><a href='http://www.openstreetmap.org/api/0.6/node/%s'>%s</a></td>" % (nid, nid))
            show("    <td>%s</td>" % cpt)
            show("    <td>%s</td>" % dta["lat"])
            show("    <td>%s</td>" % dta["lon"])
            show("  </tr>")

        else:
            show(dta)

    if error_found:
        show("</table>")
    else:
        show("<p>No problem found. All nodes are connected to an even number of ways.</p>")

    utils.print_tail()
