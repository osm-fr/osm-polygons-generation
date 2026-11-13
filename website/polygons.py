from fastapi import FastAPI, Form, Path, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import io
import matplotlib.pyplot as plt
import os
import psycopg2
import seaborn as sns
import shapely.wkt
import sys
from typing import Annotated

root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root)
from tools import utils
from tools import OsmGeom

app = FastAPI(root_path="/dev")
templates = Jinja2Templates(directory="../templates")

def get_state_timestamp(name):
    f = open(name)
    for line in f:
        (key, sep, value) = line.partition("=")
        if key.strip() == "timestamp":
            return value.replace("\\", "")

    return ""

class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    context = { "title": "Polygon creation",
                "last_update": get_state_timestamp("/data/work/osmbin/replication/state.txt"),
              }

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    sql_list = """SELECT polygons.id, timestamp, relations.tags
                  FROM polygons
                  LEFT JOIN relations ON relations.id = polygons.id
                  WHERE params = '0'
                  ORDER BY timestamp DESC
                  LIMIT 20"""
    PgCursor.execute(sql_list)
    context["last_polygons"] = PgCursor.fetchall()

    PgConn.close()

    return templates.TemplateResponse(request=request, name="index.html", context=context)

# ---------------
# Simple relation
# ---------------

@app.get("/relation/{relation_id}.geojson", response_class=JSONResponse)
async def relation_json(relation_id: int,
                        x: float | None = None,
                        y: float | None = None,
                        z: float | None = None,
                       ):

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        utils.check_polygon(PgCursor, relation_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = {"status": "ERROR", "message": "Polygon couldn't be generated - " + repr(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsGeoJSON(geom)
                  FROM polygons WHERE id = %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (relation_id, params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = {"status": "ERROR", "message": "Got error from database: " + e.pgerror}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        content = content[0][0]
        status_code = 200

    return JSONResponse(content=content, status_code=status_code)

@app.get("/relation/{relation_id}.png", response_class=PNGStreamingResponse)
async def relation_png(relation_id: int,
                       x: float | None = None,
                       y: float | None = None,
                       z: float | None = None,
                     ):

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    sql_list = """SELECT ST_AsText(ST_Union(geom))
                  FROM polygons WHERE id = %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (relation_id, params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = {"status": "ERROR", "message": "Got error from database: " + e.pgerror}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        wkt_geom = content[0][0]
        geom = shapely.wkt.loads(wkt_geom)
        sns.set_theme()
        if hasattr(geom, "exterior"):
            a = shapely.get_coordinates(geom.exterior)
            scatter_plot = sns.lineplot(x=a[:,0], y=a[:,1], sort=False, estimator=None)
        else:
            for g in geom.geoms:
                a = shapely.get_coordinates(g.exterior)
                scatter_plot = sns.lineplot(x=a[:,0], y=a[:,1], sort=False, estimator=None)

        scatter_fig = scatter_plot.get_figure()
        scatter_fig.set_size_inches(10, 10)
        content = io.BytesIO()
        scatter_fig.savefig(content, format="png")
        plt.close(scatter_fig)
        content.seek(0)
        status_code = 200

    return StreamingResponse(content=content, media_type="image/png", status_code=status_code)

@app.get("/relation/{relation_id}.poly", response_class=PlainTextResponse)
async def relation_poly(relation_id: int,
                        x: float | None = None,
                        y: float | None = None,
                        z: float | None = None,
                       ):

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        utils.check_polygon(PgCursor, relation_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = "Polygon couldn't be generated - " + repr(e)
        status_code = 500
        return PlainTextResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsText(geom)
                  FROM polygons WHERE id = %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (relation_id, params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = "Got error from database:\n" + e.pgerror
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        poly_io = io.StringIO()
        OsmGeom.write_multipolygon(poly_io, content[0][0])
        content = "polygon\n" + poly_io.getvalue() + "END"
        status_code = 200

    return PlainTextResponse(content=content, status_code=status_code)

@app.get("/relation/{relation_id}.wkt", response_class=PlainTextResponse)
async def relation_wkt(relation_id: int,
                       x: float | None = None,
                       y: float | None = None,
                       z: float | None = None,
                      ):

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        utils.check_polygon(PgCursor, relation_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = "Polygon couldn't be generated - " + repr(e)
        status_code = 500
        return PlainTextResponse(content=content, media_type="text/wkt", status_code=status_code)

    sql_list = """SELECT ST_AsEWKT(geom)
                  FROM polygons WHERE id = %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (relation_id, params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = "Got error from database:\n" + e.pgerror
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        content = content[0][0]
        status_code = 200

    return PlainTextResponse(content=content, media_type="text/wkt", status_code=status_code)


@app.get("/relation/{relation_id}", response_class=HTMLResponse)
@app.post("/relation/{relation_id}", response_class=HTMLResponse)
async def relation_root(request: Request,
                        relation_id: int,
                        x: Annotated[float, Form()] = None,
                        y: Annotated[float, Form()] = None,
                        z: Annotated[float, Form()] = None,
                        refresh: Annotated[bool, Form()] = False
                       ):
    context = { "id": relation_id }

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    sql_list = """SELECT id, params, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons WHERE id = %s
                  ORDER BY params"""
    PgCursor.execute(sql_list, (relation_id, ))
    context["polygons"] = PgCursor.fetchall()
    if refresh or context["polygons"] == []:
        try:
            if x is None or y is None or z is None:
                utils.create_polygon(PgCursor, relation_id)
            else:
                utils.simplify_polygon(PgCursor, relation_id, x, y, z)
        except utils.InvalidSimplifiedGeometry as e:
            context["notices"] = utils.parse_pg_notices(PgConn.notices)
            return templates.TemplateResponse(request=request,
                                              name="relation_invalid.html",
                                              context=context,
                                              status_code=500)
        except utils.InvalidGeometry as e:
            context["notices"] = utils.parse_pg_notices(PgConn.notices)
            return templates.TemplateResponse(request=request,
                                              name="relation_invalid.html",
                                              context=context,
                                              status_code=500)
        except utils.NonExistingRelation as e:
            return templates.TemplateResponse(request=request,
                                              name="relation_non_present.html",
                                              context=context,
                                              status_code=500)

        PgCursor.execute(sql_list, (relation_id, ))
        context["polygons"] = PgCursor.fetchall()

    PgConn.commit()
    PgConn.close()

    geom_length = None
    for p in context["polygons"]:
        if p["params"] == "0":
            geom_length = p["length"]

    if geom_length is None:
        context["rec_x"] = 0.04
        context["rec_y"] = 0.01
        context["rec_z"] = 0.01
    elif geom_length >= 10:
        context["rec_x"] = 0.04
        context["rec_y"] = 0.01
        context["rec_z"] = 0.01
    elif geom_length > 1:
        context["rec_x"] = 0.02
        context["rec_y"] = 0.005
        context["rec_z"] = 0.005
    else:
        context["rec_x"] = 0.004
        context["rec_y"] = 0.001
        context["rec_z"] = 0.001

    return templates.TemplateResponse(request=request, name="relation.html", context=context)

# ------------------
# Union of relations
# ------------------

@app.get("/union/{relations_id}.geojson", response_class=JSONResponse)
async def union_json(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                     x: float | None = None,
                     y: float | None = None,
                     z: float | None = None,
                    ):

    relations_id = [int(_) for _ in relations_id.split(",")]

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        for rel_id in relations_id:
            utils.check_polygon(PgCursor, rel_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = {"status": "ERROR", "message": "Polygon couldn't be generated - " + repr(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsGeoJSON(ST_Union(geom))
                  FROM polygons WHERE id IN %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (tuple(relations_id), params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = {"status": "ERROR", "message": "Got error from database: " + e.pgerror}
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        content = content[0][0]
        status_code = 200

    return JSONResponse(content=content, status_code=status_code)

@app.get("/union/{relations_id}.png", response_class=PNGStreamingResponse)
async def union_png(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                    x: float | None = None,
                    y: float | None = None,
                    z: float | None = None,
                   ):

    relations_id = [int(_) for _ in relations_id.split(",")]

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        for rel_id in relations_id:
            utils.check_polygon(PgCursor, rel_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = {"status": "ERROR", "message": "Polygon couldn't be generated - " + repr(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsText(ST_Union(geom))
                  FROM polygons WHERE id IN %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (tuple(relations_id), params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = {"status": "ERROR", "message": "Got error from database: " + e.pgerror}
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        wkt_geom = content[0][0]
        geom = shapely.wkt.loads(wkt_geom)
        sns.set_theme()
        if hasattr(geom, "exterior"):
            a = shapely.get_coordinates(geom.exterior)
            scatter_plot = sns.lineplot(x=a[:,0], y=a[:,1], sort=False, estimator=None)
        else:
            for g in geom.geoms:
              a = shapely.get_coordinates(g.exterior)
              scatter_plot = sns.lineplot(x=a[:,0], y=a[:,1], sort=False, estimator=None)

        scatter_fig = scatter_plot.get_figure()
        scatter_fig.set_size_inches(10, 10)
        content = io.BytesIO()
        scatter_fig.savefig(content, format="png")
        plt.close(scatter_fig)
        content.seek(0)
        status_code = 200

    return StreamingResponse(content=content, media_type="image/png", status_code=status_code)

@app.get("/union/{relations_id}.poly", response_class=PlainTextResponse)
async def union_poly(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                     x: float | None = None,
                     y: float | None = None,
                     z: float | None = None,
                    ):

    relations_id = [int(_) for _ in relations_id.split(",")]

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        for rel_id in relations_id:
            utils.check_polygon(PgCursor, rel_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = {"status": "ERROR", "message": "Polygon couldn't be generated - " + repr(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsText(geom)
                  FROM polygons WHERE id IN %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (tuple(relation_id), params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = "Got error from database:\n" + e.pgerror
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        poly_io = io.StringIO()
        OsmGeom.write_multipolygon(poly_io, content[0][0])
        content = "polygon\n" + poly_io.getvalue() + "END"
        status_code = 200

    return PlainTextResponse(content=content, status_code=status_code)

@app.get("/union/{relations_id}.wkt", response_class=PlainTextResponse)
async def union_wkt(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                    x: float | None = None,
                    y: float | None = None,
                    z: float | None = None,
                   ):

    relations_id = [int(_) for _ in relations_id.split(",")]

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    PgConn    = utils.get_dbconn()
    PgCursor  = PgConn.cursor()

    try:
        for rel_id in relations_id:
            utils.check_polygon(PgCursor, rel_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        content = {"status": "ERROR", "message": "Polygon couldn't be generated - " + repr(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    sql_list = """SELECT ST_AsEWKT(ST_Union(geom))
                  FROM polygons WHERE id IN %s AND params = %s"""
    try:
        PgCursor.execute(sql_list, (tuple(relations_id), params))
        content = PgCursor.fetchall()
    except psycopg2.errors.InternalError_ as e:
        content = "Got error from database:\n" + e.pgerror
        status_code = 500

    PgConn.close()

    if len(content) == 0 or content[0][0] is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        content = content[0][0]
        status_code = 200

    return PlainTextResponse(content=content, status_code=status_code)


# --------------
# Deprecated API
# --------------

@app.get("/get_geojson.py", response_class=JSONResponse, deprecated=True)
async def get_json(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                   x: float | None = None,
                   y: float | None = None,
                   z: float | None = None,
                  ):
    if "," in relations_id:
        return await union_json(relations_id, x, y, z)
    else:
        return await relation_json(int(relations_id), x, y, z)

@app.get("/get_image.py", response_class=PNGStreamingResponse, deprecated=True)
async def get_image(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                   x: float | None = None,
                   y: float | None = None,
                   z: float | None = None,
                  ):
    if "," in relations_id:
        return await union_png(relations_id, x, y, z)
    else:
        return await relation_png(int(relations_id), x, y, z)

@app.get("/get_poly.py", response_class=PlainTextResponse, deprecated=True)
async def get_polygon(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                   x: float | None = None,
                   y: float | None = None,
                   z: float | None = None,
                  ):
    if "," in relations_id:
        return await union_poly(relations_id, x, y, z)
    else:
        return await relation_poly(int(relations_id), x, y, z)

@app.get("/get_wkt.py", response_class=PlainTextResponse, deprecated=True)
async def get_wkt(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                   x: float | None = None,
                   y: float | None = None,
                   z: float | None = None,
                  ):
    if "," in relations_id:
        return await union_wkt(relations_id, x, y, z)
    else:
        return await relation_wkt(int(relations_id), x, y, z)

@app.get("/index.py", response_class=HTMLResponse, deprecated=True)
async def index(request: Request,
                relation_id: Annotated[int | None, Query(alias="id")] = None,
                x: Annotated[float, Form()] = None,
                y: Annotated[float, Form()] = None,
                z: Annotated[float, Form()] = None,
                refresh: Annotated[bool, Form()] = False
               ):
    if relation_id == None:
        return RedirectResponse(url='./')
    else:
        return RedirectResponse(url='relation/' + str(relation_id))

@app.post("/index.py", response_class=HTMLResponse, deprecated=True)
async def index(request: Request,
                relation_id: Annotated[int, Query(alias="id")],
                x: Annotated[float, Form()] = None,
                y: Annotated[float, Form()] = None,
                z: Annotated[float, Form()] = None,
                refresh: Annotated[bool, Form()] = False
               ):
    return RedirectResponse(url='relation/' + str(relation_id))
