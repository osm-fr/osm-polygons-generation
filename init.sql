CREATE TABLE polygons (
    id integer NOT NULL,
    params character varying(40) NOT NULL,
    "timestamp" timestamp without time zone,
    geom public.geometry
);
ALTER TABLE ONLY polygons ADD CONSTRAINT polygons_pkey PRIMARY KEY (id, params);

CREATE OR REPLACE FUNCTION ends(linestring geometry) RETURNS SETOF geometry AS $$
DECLARE BEGIN
    RETURN NEXT ST_PointN(linestring,1);
    RETURN NEXT ST_PointN(linestring,ST_NPoints(linestring));
    RETURN;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_polygon(rel_id integer) RETURNS integer
AS $BODY$
DECLARE
  line RECORD;
  ok boolean;
BEGIN
  DELETE FROM polygons WHERE id = rel_id;

  -- recup des way des relations
  CREATE TEMP TABLE tmp_way_poly AS
  WITH RECURSIVE deep_relation(id) AS (
        SELECT
            rel_id::bigint AS member_id
    UNION
        SELECT
            relation_members.member_id
        FROM
            deep_relation
            JOIN relation_members ON
                relation_members.relation_id = deep_relation.id AND
                relation_members.member_type = 'R' AND
                relation_members.member_role != 'subarea'
  )
  SELECT
    ways.linestring
  FROM
    deep_relation
    JOIN relation_members ON
        relation_members.relation_id = deep_relation.id AND
        relation_members.member_type = 'W'
    JOIN ways ON
        ways.id = relation_members.member_id
  ;

  SELECT INTO ok 't';

  FOR line in SELECT
             ST_X(geom) AS x, ST_Y(geom) AS y
           FROM
             (SELECT ends(linestring) AS geom FROM tmp_way_poly) AS d
           GROUP BY
             geom
           HAVING
             COUNT(*) != 2
  LOOP
    SELECT INTO ok 'f';
    RAISE NOTICE 'missing connexion at point %f %f', line.x, line.y;
  END LOOP;

  INSERT INTO polygons
  VALUES (rel_id,
          '0',
          NOW(),
          (SELECT st_collect(st_makepolygon(geom))
           FROM (SELECT (st_dump(st_linemerge(st_collect(d.linestring)))).geom
                 FROM (SELECT DISTINCT(linestring) AS linestring
                        FROM tmp_way_poly) as d
                ) as c
         ));

  RETURN st_npoints(geom) FROM polygons WHERE id = rel_id;
END
$BODY$
LANGUAGE 'plpgsql' ;
