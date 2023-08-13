#!/usr/bin/env python

try:
    from osgeo import gdal
    from osgeo import osr
    from osgeo import ogr
except:
    import gdal
    import osr
    import ogr

import math
import sys

# To be adjusted to your needs
shp = sys.argv[1]
tiff = sys.argv[2]
# Alternative A: Set raster dataset dimensions
tiff_width = 2000
tiff_height = 2000
# Alternative B: Set pixel resolution
x_res = 0.5
y_res = 0.75

# add some pixel margin
margin = 50

# Import vector shapefile
vector = ogr.GetDriverByName('ESRI Shapefile')
src_ds = vector.Open(shp)
src_lyr = src_ds.GetLayer(0)
src_extent = src_lyr.GetExtent()

# Alternative A: Calculate pixel resolution from desired dataset dimensions
x_res = (src_extent[1] - src_extent[0]) / tiff_width
y_res = (src_extent[3] - src_extent[2]) / tiff_height
y_res = x_res / 1.5
# Alternative B: Calculate raster dataset dimensions from desired pixel resolution
tiff_width = int(math.ceil(abs(src_extent[1] - src_extent[0]) / x_res)) + 2 * margin
tiff_height = int(math.ceil(abs(src_extent[3] - src_extent[2]) / y_res)) + 2 * margin

margin_x_in_src = margin * x_res
margin_y_in_src = margin * y_res

# Create new raster layer with 4 bands
raster = gdal.GetDriverByName('GTiff')
dst_ds = raster.Create(tiff, tiff_width, tiff_height, 4, gdal.GDT_Byte)

# Create raster GeoTransform based on upper left corner and pixel dimensions
raster_transform = [src_extent[0] - margin_x_in_src, x_res, 0.0, src_extent[3] + margin_y_in_src, 0.0, -y_res]
dst_ds.SetGeoTransform(raster_transform)

# Get projection of shapefile and assigned to raster
srs = osr.SpatialReference()
srs.ImportFromWkt(src_lyr.GetSpatialRef().__str__())
dst_ds.SetProjection(srs.ExportToWkt())

# Create blank raster with fully opaque alpha band
dst_ds.GetRasterBand(1).Fill(0)
dst_ds.GetRasterBand(2).Fill(0)
dst_ds.GetRasterBand(3).Fill(0)
dst_ds.GetRasterBand(4).Fill(255)

