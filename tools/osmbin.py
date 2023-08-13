#! /usr/bin/env python3
#-*- coding: utf-8 -*-

from modules.OsmBin import OsmBin

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Handle osmbin database.')

    parser.add_argument("--dir", action="store",
                        help="Directory for osmbin database")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--init", action="store_true",
                        help="Init database")
    group.add_argument("--import", metavar="FILE", action="store", dest="import_",
                        help="Import file to database")
    group.add_argument("--update", metavar="FILE", action="store",
                        help="Update file to database")
    group.add_argument("--read", nargs=2, metavar=("ELEM", "ID"), action="store",
                        help="Read node/way/relation id from database")
    args = parser.parse_args()

    if args.init:
        from modules import OsmBin
        OsmBin.InitFolder(args.dir)

    elif args.import_:
        o = OsmBin(args.dir, "w")
        o.Import(args.import_)

    elif args.update:
        o = OsmBin(args.dir, "w")
        o.Update(args.update)

    elif args.read:
        i = OsmBin(args.dir)
        if args.read[0] == "node":
            print(i.NodeGet(int(args.read[1])))
        elif args.read[0] == "way":
            print(i.WayGet(int(args.read[1])))
        elif args.read[0] == "relation":
            print(i.RelationGet(int(args.read[1])))
        elif args.read[0] == "relation_full":
            import pprint
            pprint.pprint(i.RelationFullRecur(int(args.read[1])))
        elif args.read[0] == "relation_geom":
            res = i.RelationGetWayGeom(int(args.read[1]), ["subarea", "land_area", "water_area", "collection", "admin_centre", "disputed_exclave"])
            for (way_id, d) in res.items():
                s = "LINESTRING(" + (",".join(["%s %s" % (n[0], n[1]) for n in d])) + ")"
                print("%d	%s" % (way_id, s))
        else:
            raise ValueError("--read option %s not recognized" % args.read[0])
