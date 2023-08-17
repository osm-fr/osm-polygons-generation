#! /usr/bin/env python
#-*- coding: utf-8 -*-

import ast
import os
import psycopg2
import re
import subprocess

################################################################################

root_folder       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

def show(s):
    print(s)

def multiple_replace(dict, text):

  """ Replace in 'text' all occurences of any key in the given
  dictionary by its corresponding value.  Returns the new tring."""

  # Create a regular expression  from the dictionary keys
  regex = re.compile("(%s)" % "|".join(map(re.escape, dict.keys())))

  # For each match, look-up corresponding value in dictionary
  return regex.sub(lambda mo: dict[mo.string[mo.start():mo.end()]], text)


def print_template(filename, rules = None):
    page = open(os.path.join(root_folder, "templates", filename)).read()
    if rules:
        r = {}
        for (k, v) in rules.items():
            r["#%s#" % k] = v
        page = multiple_replace(r, page)
    print(page)

def print_header(title = ""):
    rules = {"title": title}
    print_template("head.tpl", rules)

def print_tail():
    print_template("tail.tpl")

################################################################################

class NonExistingRelation(Exception):
    def __init__(self):
        pass

class InvalidGeometry(Exception):
    def __init__(self, pg_msg):
        self.pg_msg = pg_msg

class InvalidSimplifiedGeometry(Exception):
    def __init__(self, pg_msg):
        self.pg_msg = pg_msg

def check_polygon(pgcursor, rel_id, x=0, y=0, z=0):
    if (x, y, z) == (0, 0, 0):
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)
    pgcursor.execute("SELECT id FROM polygons WHERE id = %s AND params = %s", (rel_id, params))
    if pgcursor.fetchone():
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
        raise InvalidGeometry(PgConn.notices)

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
