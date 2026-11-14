#! /usr/bin/env python
#-*- coding: utf-8 -*-

import io
import re

import asyncpg
from tools.modules import OsmBin

################################################################################

DATABASE_URL = "postgresql://polygons:-polygons-@localhost/polygons"

async def init_connection(conn):
    await conn.set_builtin_type_codec('hstore', codec_name='pg_contrib.hstore')

def create_pgnotice_collector(notices_list: list):
    async def notice_collector(connection, message):
        notices_list.append(message.message)
    return notice_collector

################################################################################

class NonExistingRelation(Exception):
    def __init__(self):
        pass

class InvalidGeometry(Exception):
    def __init__(self):
        pass

class InvalidSimplifiedGeometry(Exception):
    def __init__(self):
        pass

async def check_polygon(conn, rel_id, x=0, y=0, z=0, create=False):
    if rel_id < 0:
        raise NonExistingRelation

    if (x, y, z) == (0, 0, 0):
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    exists = await conn.fetchval("SELECT 1 FROM polygons WHERE id = $1 AND params = $2", rel_id, params)
    if exists:
        return True

    if create:
        if (x, y, z) == (0, 0, 0):
            await create_polygon(conn, rel_id)
        else:
            await simplify_polygon(conn, rel_id, x, y, z)
        return True

    return False

async def create_polygon(conn, rel_id):
    tmp_table_name = f"tmp_way_poly_{int(rel_id)}"
    await conn.execute(f"DROP TABLE IF EXISTS {tmp_table_name}")
    await conn.execute(f"CREATE TABLE {tmp_table_name} (id integer, linestring geometry);")

    osmbin = OsmBin.OsmBin("/data/work/osmbin/data")
    rel_osmbin = osmbin.RelationGetWayGeom(rel_id, ["subarea", "land_area", "water_area", "collection", "admin_centre", "disputed_exclave"])
    if rel_osmbin is None:
        raise NonExistingRelation

    rel_geom = io.BytesIO()
    for (way_id, d) in rel_osmbin.items():
        s = "LINESTRING(" + (",".join(["%s %s" % (n[0], n[1]) for n in d])) + ")"
        line = "%d	%s\n" % (way_id, s)
        rel_geom.write(line.encode("ascii"))

    rel_geom.seek(0)
    await conn.copy_to_table(tmp_table_name, source=rel_geom)
    sql_create = "SELECT create_polygon2($1);"
    try:
        await conn.execute(sql_create, rel_id)
    except asyncpg.PostgresError:
        raise InvalidGeometry()

    rel_osm = osmbin.RelationGet(rel_id)

    if not rel_osm:
        raise NonExistingRelation

    await conn.execute("DELETE FROM relations WHERE id = $1", rel_id)
    await conn.execute("INSERT INTO relations VALUES ($1, $2)", rel_id, rel_osm["tag"])

async def simplify_polygon(conn, rel_id, x, y, z):
    if not await check_polygon(conn, rel_id):
        await create_polygon(conn, rel_id)

    params = "%f-%f-%f" % (x, y, z)
    sql_gen1 = "DELETE FROM polygons WHERE id = $1 AND params = $2"
    sql_gen2_1 = """INSERT INTO polygons VALUES
  ($1,
   $2,
   NOW(),
   (SELECT """
    sql_gen2_2 = """ST_Buffer(ST_SimplifyPreserveTopology(ST_Buffer(ST_SnapToGrid(st_buffer(geom, $3), $4), 0), $5), 0))
    FROM polygons
    WHERE id = $1 AND params = '0')
  );"""
    if x > 0:
        sql_gen2 = sql_gen2_1 + "ST_Union(ST_MakeValid(ST_SimplifyPreserveTopology(geom, 0.00001)), " + sql_gen2_2
    elif x == 0:
        sql_gen2 = sql_gen2_1 + "(" + sql_gen2_2
    else:
        sql_gen2 = sql_gen2_1 + "ST_Intersection(geom, " + sql_gen2_2
    await conn.execute(sql_gen1, rel_id, params)
    try:
        await conn.execute(sql_gen2, rel_id, params, x, y, z)
    except asyncpg.PostgresError:
        raise InvalidSimplifiedGeometry()

def parse_pg_notices(notices):
    re_lat_lon = re.compile("(.*point) ([-0-9.]*)f ([-0-9.]*)f - ways: (.*)$")
    out = []
    for line in notices:
        m = re_lat_lon.match(line)
        if m:
            lon = float(m.group(2))
            lat = float(m.group(3))
            ways = m.group(4).split(" ")
            out.append({"lon": lon, "lat": lat,
                        "ways": [int(i) for i in ways],
                        "start_line": m.group(1),
                       })
        elif line.endswith("does not exist, skipping\n"):
            pass
        else:
            out.append({"line": line})
    return out
