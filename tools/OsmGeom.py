#! /usr/bin/env python
#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Jocelyn Jaubert <jocelyn.jaubert@gmail.com> 2011           ##
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

import re

# Read a polygon from file
# NB: holes aren't supported yet
def read_polygon_wkt(f):

    coords = []
    while True:
        line = f.readline()
        if not(line):
            break

        line = line.strip()
        if line == "END":
            break

        if not(line):
            continue

        ords = line.split()
        coords.append("%f %f" % (float(ords[0]), float(ords[1])))

    if len(coords) < 3:
        return None

    polygon = "((" + ", ".join(coords) + "))"

    return polygon

# Read a multipolygon from the file
# First line: name (discarded)
# Polygon: numeric identifier, list of lon, lat, END
# Last line: END
def read_multipolygon_wkt(f):

    dummy = f.readline()

    polygons = []
    while True:
        dummy = f.readline()
        if not(dummy):
            break

        polygon = read_polygon_wkt(f)
        if polygon is not None:
            polygons.append(polygon)

    wkt = "MULTIPOLYGON (" + ",".join(polygons) + ")"

    return wkt


def write_polygon(f, wkt, p):

    match = re.search(r"^\(\((?P<pdata>.*)\)\)$", wkt)
    pdata = match.group("pdata")
    rings = re.split(r"\),\(", pdata)

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
            f.write("  %-11s  %s\n" % (ords[0], ords[1]))

        f.write("END\n")

    return p

def write_multipolygon(f, wkt):

    match = re.search(r"^MULTIPOLYGON\((?P<mpdata>.*)\)$", wkt)

    if match:
        mpdata = match.group("mpdata")
        polygons = re.split(r"(?<=\)\)),(?=\(\()", mpdata)

        p = 0
        for polygon in polygons:
            p = write_polygon(f, polygon, p)

        return

    match = re.search("^POLYGON(?P<pdata>.*)$", wkt)
    if match:
        pdata = match.group("pdata")
        write_polygon(f, pdata, 0)
