import io
import random
import string
from typing import Annotated

import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Form, HTTPException, Path, Request, Query, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from tools import utils
from tools import OsmGeom

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(utils.DATABASE_URL,
                                               min_size=1, max_size=5,
                                               init=utils.init_connection,
                                              )
    yield
    await app.state.pool.close()

app = FastAPI(root_path="/dev", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

async def get_db_connection(request: Request):
    async with request.app.state.pool.acquire() as connection:
        yield connection

def get_state_timestamp(name):
    try:
        with open(name, encoding="utf-8") as f:
            for line in f:
                (key, _, value) = line.partition("=")
                if key.strip() == "timestamp":
                    return value.replace("\\", "")
    except OSError:
        return ""

    return ""

class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request,
               conn: asyncpg.Connection = Depends(get_db_connection)):

    context = {"title": "Polygon creation",
               "last_update": get_state_timestamp("/data/work/osmbin/replication/state.txt"),
              }

    sql_list = """SELECT polygons.id, timestamp, relations.tags
                  FROM polygons
                  LEFT JOIN relations ON relations.id = polygons.id
                  WHERE params = '0'
                  ORDER BY timestamp DESC
                  LIMIT 20"""
    context["last_polygons"] = await conn.fetch(sql_list)

    sql_list = """SELECT name, timestamp
                  FROM polygons_user
                  ORDER BY timestamp DESC
                  LIMIT 20"""
    context["last_user_polygons"] = await conn.fetch(sql_list)

    return templates.TemplateResponse(request=request, name="index.html", context=context)

# ---------------
# Simple relation
# ---------------

async def relation_start(conn: asyncpg.Connection,
                         sql_func: str,
                         relation_id: int,
                         x: float | None = None,
                         y: float | None = None,
                         z: float | None = None,
                        ):

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    try:
        async with conn.transaction():
            await utils.check_polygon(conn, relation_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        raise HTTPException(status_code=500, detail="Polygon couldn't be generated - " + repr(e))

    try:
        sql_list = f"""SELECT {sql_func}(ST_Union(geom))
                       FROM polygons WHERE id = $1 AND params = $2"""
        content = await conn.fetchval(sql_list, relation_id, params)
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail="Database error while generating polygon:" + str(e))

    if content is None:
        raise HTTPException(status_code=404, detail="Relation wasn't generated")

    return content

@app.get("/relation/{relation_id}.geojson", response_class=JSONResponse)
async def relation_json(relation_id: int,
                        x: float | None = None,
                        y: float | None = None,
                        z: float | None = None,
                        conn: asyncpg.Connection = Depends(get_db_connection)
                       ):

    content = await relation_start(conn, "ST_AsGeoJSON", relation_id, x, y, z)
    return JSONResponse(content=content)

@app.get("/relation/{relation_id}.png", response_class=PNGStreamingResponse)
async def relation_png(relation_id: int,
                       x: float | None = None,
                       y: float | None = None,
                       z: float | None = None,
                       conn: asyncpg.Connection = Depends(get_db_connection)
                     ):

    wkt_geom = await relation_start(conn, "ST_AsText", relation_id, x, y, z)
    content = await run_in_threadpool(utils.render_png, wkt_geom)
    return StreamingResponse(content=content, media_type="image/png")

@app.get("/relation/{relation_id}.poly", response_class=PlainTextResponse)
async def relation_poly(relation_id: int,
                        x: float | None = None,
                        y: float | None = None,
                        z: float | None = None,
                        conn: asyncpg.Connection = Depends(get_db_connection)
                       ):

    content = await relation_start(conn, "ST_AsText", relation_id, x, y, z)
    poly_io = io.StringIO()
    OsmGeom.write_multipolygon(poly_io, content)
    content = "polygon\n" + poly_io.getvalue() + "END"
    return PlainTextResponse(content=content)

@app.get("/relation/{relation_id}.wkt", response_class=PlainTextResponse)
async def relation_wkt(relation_id: int,
                       x: float | None = None,
                       y: float | None = None,
                       z: float | None = None,
                       conn: asyncpg.Connection = Depends(get_db_connection)
                      ):

    content = await relation_start(conn, "ST_AsEWKT", relation_id, x, y, z)
    return PlainTextResponse(content=content, media_type="text/wkt")

@app.get("/relation/{relation_id}", response_class=HTMLResponse)
@app.post("/relation/{relation_id}", response_class=HTMLResponse)
async def relation_root(request: Request,
                        relation_id: int,
                        x: Annotated[float, Form()] = None,
                        y: Annotated[float, Form()] = None,
                        z: Annotated[float, Form()] = None,
                        refresh: Annotated[bool, Form()] = False,
                        conn: asyncpg.Connection = Depends(get_db_connection)
                       ):
    context = {"id": relation_id}

    sql_list = """SELECT id, params, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons WHERE id = $1
                  ORDER BY params"""
    context["polygons"] = await conn.fetch(sql_list, relation_id)
    if refresh or context["polygons"] == []:
        collected_notices = []
        collector = utils.create_pgnotice_collector(collected_notices)
        conn.add_log_listener(collector)
        try:
            async with conn.transaction():
                if x is None or y is None or z is None:
                    await utils.create_polygon(conn, relation_id)
                else:
                    await utils.simplify_polygon(conn, relation_id, x, y, z)
        except utils.InvalidSimplifiedGeometry:
            context["notices"] = utils.parse_pg_notices(collected_notices)
            return templates.TemplateResponse(request=request,
                                              name="relation_invalid.html",
                                              context=context,
                                              status_code=500)
        except utils.InvalidGeometry:
            context["notices"] = utils.parse_pg_notices(collected_notices)
            return templates.TemplateResponse(request=request,
                                              name="relation_invalid.html",
                                              context=context,
                                              status_code=500)
        except utils.NonExistingRelation:
            return templates.TemplateResponse(request=request,
                                              name="relation_non_present.html",
                                              context=context,
                                              status_code=500)
        finally:
            conn.remove_log_listener(collector)

        context["polygons"] = await conn.fetch(sql_list, relation_id)

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

# ------------
# User polygon
# ------------

@app.get("/user_polygon/{name}.geojson", response_class=JSONResponse)
async def user_polygon_json(name: str,
                            conn: asyncpg.Connection = Depends(get_db_connection)
                           ):

    sql_list = """SELECT ST_AsGeoJSON(geom)
                  FROM polygons_user WHERE name = $1"""
    try:
        content = await conn.fetchval(sql_list, name)
    except asyncpg.PostgresError as e:
        content = {"status": "ERROR", "message": "Got error from database: " + str(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    if content is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        status_code = 200

    return JSONResponse(content=content, status_code=status_code)

@app.get("/user_polygon/{name}.png", response_class=PNGStreamingResponse)
async def user_polygon_png(name: str,
                           conn: asyncpg.Connection = Depends(get_db_connection)
                          ):

    sql_list = """SELECT ST_AsText(ST_Union(geom))
                  FROM polygons_user WHERE name = $1"""
    try:
        wkt_geom = await conn.fetchval(sql_list, name)
    except asyncpg.PostgresError as e:
        content = {"status": "ERROR", "message": "Got error from database: " + str(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    if wkt_geom is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        content = await run_in_threadpool(utils.render_png, wkt_geom)
        status_code = 200

    return StreamingResponse(content=content, media_type="image/png", status_code=status_code)

@app.get("/user_polygon/{name}.poly", response_class=PlainTextResponse)
async def user_polygon_poly(name: str,
                            conn: asyncpg.Connection = Depends(get_db_connection)
                           ):

    sql_list = """SELECT ST_AsText(geom)
                  FROM polygons_user WHERE name = $1"""
    try:
        content = await conn.fetchval(sql_list, name)
    except asyncpg.PostgresError as e:
        content = {"status": "ERROR", "message": "Got error from database: " + str(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    if content is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        poly_io = io.StringIO()
        OsmGeom.write_multipolygon(poly_io, content)
        content = "polygon\n" + poly_io.getvalue() + "END"
        status_code = 200

    return PlainTextResponse(content=content, status_code=status_code)

@app.get("/user_polygon/{name}.wkt", response_class=PlainTextResponse)
async def user_polygon_wkt(name: str,
                           conn: asyncpg.Connection = Depends(get_db_connection)
                          ):

    sql_list = """SELECT ST_AsEWKT(geom)
                  FROM polygons_user WHERE name = $1"""
    try:
        content = await conn.fetchval(sql_list, name)
    except asyncpg.PostgresError as e:
        content = {"status": "ERROR", "message": "Got error from database: " + str(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    if content is None:
        content = {"status": "ERROR", "message": "Relation wasn't generated"}
        status_code = 404
        return JSONResponse(content=content, status_code=status_code)
    else:
        status_code = 200

    return PlainTextResponse(content=content, media_type="text/wkt", status_code=status_code)

@app.post("/user_polygon", response_class=HTMLResponse)
async def user_polygon_create(request: Request,
                              name: Annotated[str, Form()],
                              poly: UploadFile,
                              conn: asyncpg.Connection = Depends(get_db_connection)
                             ):
    char_set = string.ascii_lowercase + string.digits
    name += "_" + (''.join(random.sample(char_set*6,6)))

    wkt = OsmGeom.read_multipolygon_wkt(poly.file)

    sql_list = """INSERT INTO polygons_user
                  VALUES ($1, NOW(), ST_GeomFromText($2, 4326))"""
    try:
        await conn.execute(sql_list, name, wkt)
    except asyncpg.PostgresError as e:
        content = {"status": "ERROR", "message": "Got error from database: " + str(e)}
        status_code = 500
        return JSONResponse(content=content, status_code=status_code)

    return RedirectResponse(url='user_polygon/' + str(name), status_code=status.HTTP_303_SEE_OTHER)

@app.get("/user_polygon/{name}", response_class=HTMLResponse)
async def user_polygon(request: Request,
                       name: str,
                       relation_id: int | None = None,
                       conn: asyncpg.Connection = Depends(get_db_connection)
                      ):
    context = {"name": name}

    sql_list = """SELECT name, timestamp, ST_NPoints(geom) AS npoints,
                         ST_MaxDistance(geom, geom) AS length
                  FROM polygons_user WHERE name LIKE $1
                  ORDER BY name"""
    context["user_polygons"] = await conn.fetch(sql_list, name)

    if relation_id is not None:
        sql_list = """SELECT params
                      FROM polygons WHERE id = $1
                      ORDER BY params"""
        context["rel_polygons"] = await conn.fetch(sql_list, relation_id)
        context["relation_id"] = relation_id

    return templates.TemplateResponse(request=request, name="user_polygon.html", context=context)

# ------------------
# Union of relations
# ------------------

async def union_start(conn: asyncpg.Connection,
                      sql_func: str,
                      relations_id: str,
                      x: float | None = None,
                      y: float | None = None,
                      z: float | None = None,
                      name: str | None = None
                     ):
    MAX_REL_IDS = 300

    if len(relations_id) > MAX_REL_IDS * 11: # allow 10 digits per id
        raise HTTPException(status_code=422, detail="Too many relation ids")

    relations_id = [int(_) for _ in relations_id.split(",")]

    if len(relations_id) > MAX_REL_IDS:
        raise HTTPException(status_code=422, detail="Too many relation ids")

    if x is None or y is None or z is None:
        (x, y, z) = (0, 0, 0)
        params = "0"
    else:
        params = "%f-%f-%f" % (x, y, z)

    try:
        async with conn.transaction():
            for rel_id in relations_id:
                await utils.check_polygon(conn, rel_id, x, y, z, create=True)
    except (utils.NonExistingRelation,
            utils.InvalidGeometry,
            utils.InvalidSimplifiedGeometry) as e:
        raise HTTPException(status_code=500, detail="Polygon couldn't be generated - " + repr(e))

    try:
        if name is None:
            sql_list = f"""SELECT {sql_func}(ST_Union(geom))
                           FROM polygons WHERE id = ANY($1) AND params = $2"""
            content = await conn.fetchval(sql_list, relations_id, params)
        else:
            sql_list = f"""SELECT {sql_func}(ST_Union(
                              (SELECT ST_Union(geom)
                               FROM polygons WHERE id = ANY($1) AND params = $2),
                              (SELECT ST_Union(geom)
                               FROM polygons_user WHERE name = $3)))"""
            content = await conn.fetchval(sql_list, relations_id, params, name)
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail="Database error while generating polygon:" + str(e))

    if content is None:
        raise HTTPException(status_code=404, detail="Relation wasn't generated")

    return content

@app.get("/union/{relations_id}.geojson", response_class=JSONResponse)
async def union_json(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                     x: float | None = None,
                     y: float | None = None,
                     z: float | None = None,
                     name: str | None = None,
                     conn: asyncpg.Connection = Depends(get_db_connection)
                    ):

    content = await union_start(conn, "ST_AsGeoJSON", relations_id, x, y, z, name)
    return JSONResponse(content=content)

@app.get("/union/{relations_id}.png", response_class=PNGStreamingResponse)
async def union_png(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                    x: float | None = None,
                    y: float | None = None,
                    z: float | None = None,
                    name: str | None = None,
                    conn: asyncpg.Connection = Depends(get_db_connection)
                   ):

    wkt_geom = await union_start(conn, "ST_AsText", relations_id, x, y, z, name)
    content = await run_in_threadpool(utils.render_png, wkt_geom)
    return StreamingResponse(content=content, media_type="image/png")

@app.get("/union/{relations_id}.poly", response_class=PlainTextResponse)
async def union_poly(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                     x: float | None = None,
                     y: float | None = None,
                     z: float | None = None,
                     name: str | None = None,
                     conn: asyncpg.Connection = Depends(get_db_connection)
                    ):

    wkt_geom = await union_start(conn, "ST_AsText", relations_id, x, y, z, name)
    poly_io = io.StringIO()
    OsmGeom.write_multipolygon(poly_io, wkt_geom)
    content = "polygon\n" + poly_io.getvalue() + "END"
    return PlainTextResponse(content=content)

@app.get("/union/{relations_id}.wkt", response_class=PlainTextResponse)
async def union_wkt(relations_id: Annotated[str, Path(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$")],
                    x: float | None = None,
                    y: float | None = None,
                    z: float | None = None,
                    name: str | None = None,
                    conn: asyncpg.Connection = Depends(get_db_connection)
                   ):

    content = await union_start(conn, "ST_AsEWKT", relations_id, x, y, z, name)
    return PlainTextResponse(content=content)

# --------------
# Deprecated API
# --------------

@app.get("/get_geojson.py", response_class=JSONResponse, deprecated=True)
async def get_json(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                   x: float | None = None,
                   y: float | None = None,
                   z: float | None = None,
                   name: str | None = None,
                   conn: asyncpg.Connection = Depends(get_db_connection)
                  ):
    if "," in relations_id or name is not None:
        return await union_json(relations_id, x, y, z, name, conn)
    else:
        return await relation_json(int(relations_id), x, y, z, conn)

@app.get("/get_image.py", response_class=PNGStreamingResponse, deprecated=True)
async def get_image(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                    x: float | None = None,
                    y: float | None = None,
                    z: float | None = None,
                    name: str | None = None,
                    conn: asyncpg.Connection = Depends(get_db_connection)
                   ):
    if "," in relations_id or name is not None:
        return await union_png(relations_id, x, y, z, name, conn)
    else:
        return await relation_png(int(relations_id), x, y, z, conn)

@app.get("/get_poly.py", response_class=PlainTextResponse, deprecated=True)
async def get_polygon(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                      x: float | None = None,
                      y: float | None = None,
                      z: float | None = None,
                      name: str | None = None,
                      conn: asyncpg.Connection = Depends(get_db_connection)
                     ):
    if "," in relations_id or name is not None:
        return await union_poly(relations_id, x, y, z, name, conn)
    else:
        return await relation_poly(int(relations_id), x, y, z, conn)

@app.get("/get_wkt.py", response_class=PlainTextResponse, deprecated=True)
async def get_wkt(relations_id: Annotated[str, Query(description="List of relation ids, separated by ','", pattern="^[0-9]+(,[0-9]+)*$", alias="id")],
                  x: float | None = None,
                  y: float | None = None,
                  z: float | None = None,
                  name: str | None = None,
                  conn: asyncpg.Connection = Depends(get_db_connection)
                 ):
    if "," in relations_id or name is not None:
        return await union_wkt(relations_id, x, y, z, name, conn)
    else:
        return await relation_wkt(int(relations_id), x, y, z, conn)

@app.get("/index.py", response_class=HTMLResponse, deprecated=True)
async def index(relation_id: Annotated[int | None, Query(alias="id")] = None,
                x: Annotated[float, Form()] = None,
                y: Annotated[float, Form()] = None,
                z: Annotated[float, Form()] = None,
                refresh: Annotated[bool, Form()] = False
               ):
    if relation_id is None:
        return RedirectResponse(url='./')
    else:
        return RedirectResponse(url='relation/' + str(relation_id))

@app.post("/index.py", response_class=HTMLResponse, deprecated=True)
async def index_post(relation_id: Annotated[int, Query(alias="id")],
                     x: Annotated[float, Form()] = None,
                     y: Annotated[float, Form()] = None,
                     z: Annotated[float, Form()] = None,
                     refresh: Annotated[bool, Form()] = False
                    ):
    return RedirectResponse(url='relation/' + str(relation_id))
