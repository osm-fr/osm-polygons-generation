#! /usr/bin/env python
#-*- coding: utf-8 -*-

import ast
import psycopg2
import re
import subprocess

################################################################################

pg_user           = "polygons"
pg_pass           = "-polygons-"
pg_base           = "polygons"

def get_dbconn():
    import psycopg2.extras
#    return psycopg2.connect(host="localhost", database = pg_base, user = pg_user, password = pg_pass)
    db_string = "host='localhost' dbname='%s' user='%s' password='%s'" % (pg_base, pg_user, pg_pass)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
    conn = psycopg2.extras.DictConnection(db_string)
    psycopg2.extras.register_hstore(conn)
    return conn

################################################################################

class NonExistingRelation(Exception):
    def __init__(self):
        pass

class InvalidGeometry(Exception):
    def __init__(self):
        pass

class InvalidSimplifiedGeometry(Exception):
    def __init__(self, pg_msg):
        self.pg_msg = pg_msg

def check_polygon(pgcursor, rel_id, x=0, y=0, z=0, create=False):
    if rel_id < 0:
        raise NonExistingRelation

    if (x, y, z) == (0, 0, 0):
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)
    pgcursor.execute("SELECT id FROM polygons WHERE id = %s AND params = %s", (rel_id, params))
    if pgcursor.fetchone():
        return True

    if create:
        if (x, y, z) == (0, 0, 0):
            create_polygon(pgcursor, rel_id)
        else:
            simplify_polygon(pgcursor, rel_id, x, y, z)
        return True

    return False

def create_polygon(pgcursor, rel_id):
    pgcursor.execute("DROP TABLE IF EXISTS tmp_way_poly_%d" % rel_id)
    pgcursor.execute("CREATE TABLE tmp_way_poly_%d (id integer, linestring geometry);" % rel_id)
    cmd = ("../tools/osmbin.py", "--dir", "/data/work/osmbin/data", "--read", "relation_geom", "%d" % rel_id)
    try:
        run = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except:
        raise NonExistingRelation
    pgcursor.copy_from(run.stdout, "tmp_way_poly_%d" % rel_id)
    sql_create = "select create_polygon2(%s);"
    try:
        pgcursor.execute(sql_create, (rel_id, ))
    except psycopg2.InternalError:
        raise InvalidGeometry()

    cmd = ("../tools/osmbin.py", "--dir", "/data/work/osmbin/data", "--read", "relation", "%d" % rel_id)
    run = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    j = ast.literal_eval(run.stdout.read().decode("utf-8"))
    if not j:
        raise NonExistingRelation

    pgcursor.execute("DELETE FROM relations WHERE id = %s", (rel_id, ))
    pgcursor.execute("INSERT INTO relations VALUES (%s, %s)", (rel_id, j["tag"]))

def simplify_polygon(pgcursor, rel_id, x, y, z):
    if not check_polygon(pgcursor, rel_id):
        create_polygon(pgcursor, rel_id)

    params = "%f-%f-%f" % (x, y, z)
    sql_gen1 = "DELETE FROM polygons WHERE id = %s AND params = %s"
    sql_gen2_1 = """INSERT INTO polygons VALUES
  (%s,
   %s,
   NOW(),
   (SELECT """
    sql_gen2_2 = """ST_Buffer(ST_SimplifyPreserveTopology(ST_Buffer(ST_SnapToGrid(st_buffer(geom, %s), %s), 0), %s), 0))
    FROM polygons
    WHERE id = %s AND params = '0')
  );"""
    if x > 0:
      sql_gen2 = sql_gen2_1 + "ST_Union(ST_MakeValid(ST_SimplifyPreserveTopology(geom, 0.00001)), " + sql_gen2_2
    elif x == 0:
      sql_gen2 = sql_gen2_1 + "(" + sql_gen2_2
    else:
      sql_gen2 = sql_gen2_1 + "ST_Intersection(geom, " + sql_gen2_2
    pgcursor.execute(sql_gen1, (rel_id, params))
    try:
        pgcursor.execute(sql_gen2, (rel_id, params,
                                    x, y, z, rel_id))
    except psycopg2.InternalError:
        raise InvalidSimplifiedGeometry(PgConn.notices)

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
