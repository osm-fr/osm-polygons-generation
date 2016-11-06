#! /usr/bin/env python
#-*- coding: utf-8 -*-

import os, atexit
import re
import Cookie
from xml.sax import make_parser, handler

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
    psycopg2.extras.register_hstore(conn, unicode=True)
    return conn

def show(s):
    print s.encode("utf8")

def multiple_replace(dict, text):

  """ Replace in 'text' all occurences of any key in the given
  dictionary by its corresponding value.  Returns the new tring."""

  # Create a regular expression  from the dictionary keys
  regex = re.compile("(%s)" % "|".join(map(re.escape, dict.keys())))

  # For each match, look-up corresponding value in dictionary
  return regex.sub(lambda mo: dict[mo.string[mo.start():mo.end()]], text)


def print_template(filename, rules = None):
    page = open(os.path.join(root_folder, "templates", filename)).read().decode("utf8")
    if rules:
        r = {}
        for (k, v) in rules.iteritems():
            r["#%s#" % k] = v
        page = multiple_replace(r, page)
    print page.encode("utf8")

def print_header(title = ""):
    rules = { "title" : title }
    print_template("head.tpl", rules)

def print_tail():
    print_template("tail.tpl")

