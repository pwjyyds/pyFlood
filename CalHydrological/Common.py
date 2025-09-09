"""
通用的方法
"""
import os
import pygeodesy
import pyproj
from osgeo import ogr, gdal, osr
import richdem as rd
import geopandas as gpd
import numpy as np
import pyflwdir
import rasterio
from pygeodesy.sphericalNvector import LatLon

import setting


# convenience method for vectorizing a raster
def vectorize(data, nodata, transform, name="value"):
    from rasterio import features
    # read example elevation data and derive background hillslope
    fn = os.path.join(os.path.dirname(__file__), setting.dem_dir)
    with rasterio.open(fn, "r") as src:
        elevtn = src.read(1)
        extent = np.array(src.bounds)[[0, 2, 1, 3]]
        crs = src.crs
    feats_gen = features.shapes(
        data,
        mask=data != nodata,
        transform=transform,
        connectivity=8,
    )
    feats = [
        {"geometry": geom, "properties": {name: val}} for geom, val in list(feats_gen)
    ]

    # parse to geopandas for plotting / writing to file
    gdf = gpd.GeoDataFrame.from_features(feats, crs=crs)
    gdf[name] = gdf[name].astype(data.dtype)
    return gdf


def CreateNewField(layer, fieldName, fieldType):
    """
    新增字段
    :param layer: 图层
    :param fieldName: 要添加的字段名
    :return:
    """
    layerDefinition = layer.GetLayerDefn()
    ifExistField = False
    for i in range(layerDefinition.GetFieldCount()):  # 看看有哪些字段
        # print(layerDefinition.GetFieldDefn(i).GetName())
        if layerDefinition.GetFieldDefn(i).GetName() == fieldName:
            ifExistField = True
            # print("存在字段",fieldName)
            break
    if not ifExistField:
        # 添加字段(注意添加完后要保存  数据源= None)
        fieldDefn = ogr.FieldDefn(fieldName, fieldType)
        layer.CreateField(fieldDefn)
        # print("创建字段成功", fieldName)

def UpdateField(layer, feature, fieldName, fieldValue):
    """
    更新字段
    :param layer:图层
    :param feature:要素对象
    :param fieldName:字段名
    :param fieldValue:要更新的值
    :return:
    """
    # 设置字段值
    feature.SetField(fieldName, fieldValue)
    # 更新要素
    layer.SetFeature(feature)


"""
矢量转栅格
"""


def vector2raster(inputfilePath, outputfile, bands=[1], burn_values=[0], field="", all_touch="False"):
    """
    inputfilePath 输入矢量文件
    outputfile 输出栅格文件
    """
    import warnings
    warnings.filterwarnings('ignore')
    # data = gdal.Open(r"E:\College\project\geoData\dsz_dem")  # 栅格模板文件，确定输出栅格的元数据（坐标系等，栅格大小，范围等）
    data = gdal.Open(setting.dem_dir)  # 栅格模板文件，确定输出栅格的元数据（坐标系等，栅格大小，范围等）
    # 确定栅格大小
    x_res = data.RasterXSize
    y_res = data.RasterYSize
    vector = inputfilePath
    if type(inputfilePath) is str:
        # 打开矢量文件
        vector = ogr.Open(inputfilePath)
    # 获取矢量图层
    layer = vector.GetLayer()
    # 查看要素数量
    featureCount = layer.GetFeatureCount()
    # 创建输出的TIFF栅格文件
    targetDataset = gdal.GetDriverByName('GTiff').Create(outputfile, x_res, y_res, 1, gdal.GDT_Byte)
    # 设置栅格坐标系与投影
    targetDataset.SetGeoTransform(data.GetGeoTransform())
    targetDataset.SetProjection(data.GetProjection())
    # 目标band 1
    band = targetDataset.GetRasterBand(1)
    # 白色背景
    NoData_value = 255
    band.SetNoDataValue(NoData_value)
    band.FlushCache()
    if field:
        # 调用栅格化函数。RasterizeLayer函数有四个参数，分别有栅格对象，波段，矢量对象，options
        # options可以有多个属性，其中ATTRIBUTE属性将矢量图层的某字段属性值作为转换后的栅格值
        gdal.RasterizeLayer(targetDataset, bands, layer, burn_values=burn_values,
                            options=["ALL_TOUCHED=" + all_touch, "ATTRIBUTE=" + field])
    else:
        gdal.RasterizeLayer(targetDataset, bands, layer, burn_values=burn_values, options=["ALL_TOUCHED=" + all_touch])

def createLine(inGeom, savePath, type):
    # 根据geom创建一个新的shapefile文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.CreateDataSource(savePath)
    # 坐标系
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(32650)  # WGS_1984_UTM_Zone_50N的EPSG代码是32650
    # 在shapefile文件中创建一个新的图层
    layer = ds.CreateLayer('temp_createLine', geom_type=type, srs=output_srs)
    # 在图层中创建一个新的要素
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(inGeom)
    layer.CreateFeature(feature)

    # 保存并关闭shp文件
    ds = None


def imagexy2geo(dataset, row, col):
    """
    根据GDAL的六参数模型将影像图上坐标（行列号）转为投影坐标或地理坐标（根据具体数据的坐标系统转换）
    :param dataset: GDAL地理数据
    :param row: 像素的行号
    :param col: 像素的列号
    :return: 行列号(row, col)对应的投影坐标或地理坐标(x, y)
    """
    trans = dataset.GetGeoTransform()
    px = trans[0] + col * trans[1] + row * trans[2]
    py = trans[3] + col * trans[4] + row * trans[5]
    return px, py


def RasterToPoint(inputRaster, savePath):
    """
    栅格转矢量点
    :return:
    """
    # 打开栅格文件
    # inputRaster = gdal.Open(r"E:\College\project\geoData\dmx_raster1")
    # 获取栅格转换信息
    transform = inputRaster.GetGeoTransform()

    # 获取每个格子的大小
    cell_size_x = transform[1]
    # print(cell_size_x)

    # 创建一个新的shapefile文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.CreateDataSource(savePath)
    # 坐标系
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(32650)  # WGS_1984_UTM_Zone_50N的EPSG代码是32650
    # 在shapefile文件中创建一个新的图层
    layer = ds.CreateLayer('temp_createLine', geom_type=ogr.wkbPoint, srs=output_srs)

    raster_arr = inputRaster.ReadAsArray()
    raster_yx = np.where(raster_arr == 1)  # 二维数组，[[y1,y2,y3,...],[x1,x2,x3....]]
    for index, x in enumerate(raster_yx[1]):
        px, py = imagexy2geo(inputRaster, raster_yx[0][index], x)
        if px > 0 and py > 0:
            # 在图层中创建一个新的要素
            feature = ogr.Feature(layer.GetLayerDefn())
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(px + cell_size_x / 2, py - cell_size_x / 2)  # 让点生成在格子中间，不然在格子左上角
            feature.SetGeometry(point)
            layer.CreateFeature(feature)

    # 保存并关闭文件
    ds = None


def flow(dem_dir):
    """
    流量
    :param dem_dir:DEM路径
    :return:
    """
    dem = rd.LoadGDAL(dem_dir)
    accum_d8 = rd.FlowAccumulation(dem, method='D8')
    # print(accum_d8, type(accum_d8))
    rd.SaveGDAL("/geodata/keshan\hydrink\liuxiangFromRd.tif", accum_d8)
    # d8_fig = rd.rdShow(accum_d8, figsize=(12, 8), axes=False, cmap='jet')


# flow(r"E:\College\project\GD\geodata\Input\dem.tif")

def FlowDir(dem_dir):
    """
    流向
    https://deltares.github.io/pyflwdir/latest/_examples/from_dem.html#Derive-flow-direction
    :param dem_dir:
    :return:
    """
    # read elevation data of the rhine basin using rasterio
    with rasterio.open(dem_dir, "r") as src:
        elevtn = src.read(1)
        nodata = src.nodata
        transform = src.transform
        crs = src.crs
        extent = np.array(src.bounds)[[0, 2, 1, 3]]
        latlon = src.crs.is_geographic
        prof = src.profile
    flw = pyflwdir.from_dem(
        data=elevtn,
        nodata=src.nodata,
        transform=transform,
        latlon=latlon,
        outlets="min",
    )
    d8_data = flw.to_array(ftype="d8")
    prof.update(dtype=d8_data.dtype, nodata=247)
    with rasterio.open(r"/geodata/keshan\hydrink\liuxiangFromFlw.tif", "w", **prof) as src:
        src.write(d8_data, 1)
    # print("FlowDir ok!")


# FlowDir(r"E:\College\project\GD\geodata\Input\dem.tif")


# RasterToPoint()
def CreateBasins(fldir, outlet, outPath):
    """
    生成流域面
    :param outPath: 结果保存路径
    :param fldir: 流向栅格
    :param outlet:  出水口点数据
    :return:
    """

    # read and parse data
    with rasterio.open(fldir, "r") as src:
        flwdir = src.read(1)
        crs = src.crs
        flw = pyflwdir.from_array(
            flwdir,
            ftype="d8",
            transform=src.transform,
            latlon=crs.is_geographic,
            cache=True,
        )

    # define output locations
    layer = outlet.GetLayer(0)  # 得到图层
    lyr_count = layer.GetFeatureCount()
    x_list = []
    y_list = []
    for i in range(lyr_count):
        # for i in range(1):
        feat = layer.GetFeature(i)
        x_list.append(feat.GetField('POINT_X'))  # 经度
        y_list.append(feat.GetField('POINT_Y'))  # 纬度
    x = np.array(x_list)
    y = np.array(y_list)

    gdf_out = gpd.GeoSeries(gpd.points_from_xy(x, y, crs=4326))
    # delineate subbasins
    subbasins = flw.basins(xy=(x, y), streams=flw.stream_order() >= 4)
    # vectorize subbasins using the vectorize convenience method from utils_keshan.py
    gdf_bas = vectorize(subbasins.astype(np.int32), 0, flw.transform, name="basin")
    gdf_bas.crs = pyproj.CRS.from_user_input('EPSG:32650')  # 给输出的shp增加投影
    # gdf.rename(columns={'name':'ave_price'},inplace=True) #对原来的字段名进行更改
    # gdf.rename(columns={'addrees':'area_ave_price'},inplace=True)
    gdf_bas.to_file(outPath, driver='ESRI Shapefile', encoding='utf-8')
    # print("OK")


# CreateBasins(r"E:\College\project\GD\keshan\hydrink\liuxiang.tif", ogr.Open(r"E:\College\project\geoData\seed.shp"))

def CreateShapefile(inXY_arr, outPath,epsg):
    """
    根据经纬度创建矢量
    :param inXY_arr:
    :param outPath:
    :return:
    """
    # 创建一个新的shapefile文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.CreateDataSource(outPath)
    # 坐标系
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(epsg)  # WGS_1984_UTM_Zone_50N的EPSG代码是32650
    # 在shapefile文件中创建一个新的图层
    layer = ds.CreateLayer('newLine', geom_type=ogr.wkbLineString, srs=output_srs)
    # 向图层中添加一个字段
    # field_defn = ogr.FieldDefn('field_name', ogr.OFTString)
    # layer.CreateField(field_defn)
    # 在图层中创建一个新的要素
    feature = ogr.Feature(layer.GetLayerDefn())
    newline = ogr.Geometry(ogr.wkbLineString)
    for pointXY in inXY_arr:
        newline.AddPoint(pointXY[0], pointXY[1])
    feature.SetGeometry(newline)

    # feature.SetField('field_name', 'field_value')
    layer.CreateFeature(feature)
    # 保存并关闭shapefile文件
    ds = None


def SimplifyLine(XYlist):
    """
    简化线
    :param XYlist:
    :return:
    """
    points = []
    src_srs = osr.SpatialReference()  # 定义源坐标系
    src_srs.ImportFromEPSG(32650)  # EPSG代码3857代表Web墨卡托投影
    tgt_srs = osr.SpatialReference()  # 定义目标坐标系
    tgt_srs.ImportFromEPSG(4326)  # EPSG代码4326代表WGS84经纬度坐标系
    transform = osr.CoordinateTransformation(src_srs, tgt_srs)
    for p in XYlist:
        x, y = p[0], p[1]  # 假设源坐标为(1000000, 500000)
        lon, lat, z = transform.TransformPoint(x, y)
        p1 = LatLon(lon, lat)
        points.append(p1)
    simplified_points = pygeodesy.simplifyRW(points, radius=1000)
    # print(simplified_points)

    # 结果图形的绘制，抽稀之前绘制
    # fig = plt.figure()
    #
    # a = fig.add_subplot(121)
    # dx = []
    # dy = []
    # for i in XYlist:
    #     dx.append(i[0])
    #     dy.append(i[1])
    # a.plot(dx, dy, color='g', linestyle='-', marker='+')
    # 结果图形的绘制，抽稀之后绘制
    # a2 = fig.add_subplot(122)
    # dx1 = []
    # dy1 = []
    # for i in simplified_points:
    #     dx1.append(i.lon)
    #     dy1.append(i.lat)
    # a2.plot(dx1, dy1, color='g', linestyle='-', marker='+')
    # plt.show()
    # print("simplify ok")

    return simplified_points
