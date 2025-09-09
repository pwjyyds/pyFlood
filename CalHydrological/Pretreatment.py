# coding:utf-8
"""
数据预处理，包括打断断面线、计算比降等
"""
import os
import CalHydrological.Common as HC
import numpy as np
from osgeo import gdal, ogr, osr

import setting
import SimulateFlood.LongLine as ZL


def getJ(inLine, inSlpp, inRiverDiv):
    """
    计算每个断面线的平均比降
    :param inLine: 断面线
    :param inSlpp: 坡度
    :param inRiverDiv: 打断的河流线
    :return: 带有平均比降的断面线
    """
    # 1. 利用断面线打断河流  --> 直接输入处理好的数据算了，GDAL好难实现
    # 2. 计算每段河流的平均坡度J
    layer = inRiverDiv.GetLayer()
    layer_dmx = inLine.GetLayer()
    # temp_tif = r"E:\College\project\GD\geodata\keshan\temp_vector2raster.tif"
    temp_tif = os.path.join(setting.output_dir,"temp_vector2raster.tif")
    # temp_shp = r'E:\College\project\GD\geodata\keshan\temp_createLine.shp'
    temp_shp =os.path.join(setting.output_dir,"temp_createLine.shp")

    # 新增字段J.....
    addField = setting.dmx_field['J']
    HC.CreateNewField(layer_dmx, addField, ogr.OFTReal)

    for i in range(layer.GetFeatureCount()):
        # for i in range(1):
        fc = layer.GetFeature(i)
        geom = fc.GetGeometryRef()
        HC.createLine(geom, temp_shp, ogr.wkbLineString)  # 导出成一份单独的线
        HC.vector2raster(inputfilePath=temp_shp,
                         outputfile=temp_tif)  # 线转栅格
        # 读取所占行列
        temp_raster = gdal.Open(temp_tif)
        temp_raster_array = temp_raster.ReadAsArray()
        temp_raster_yx = np.where(temp_raster_array == 0)  # 二维数组，[[y1,y2,y3,...],[x1,x2,x3....]]
        temp_raster_xy = []
        for index, x in enumerate(temp_raster_yx[1]):
            temp_xy = [x, temp_raster_yx[0][index]]
            temp_raster_xy.append(temp_xy)
        # 计算平均坡度
        slope_array = inSlpp.ReadAsArray()
        sum = 0
        for n in temp_raster_xy:
            slope_value = slope_array[n[1]][n[0]]
            # print("slope_array[n[1]][n[0]]:",slope_value)
            if slope_value == -3.402823e+38 or slope_value < 0:
                slope_value = 0
            sum += slope_value
        mean = sum / len(temp_raster_xy)
        # print(sum, len(temp_raster_xy), mean)

        # 3. 赋值给断面线
        geom_list = []
        for count in range(geom.GetPointCount()):
            geom_list.append([round(geom.GetPoint(count)[0], 4), round(geom.GetPoint(count)[1], 4)])
        for j in range(layer_dmx.GetFeatureCount()):
            fc_dmx = layer_dmx.GetFeature(j)
            geom_dmx = fc_dmx.GetGeometryRef()

            # 获取断面线数据和河流线数据的交点
            for count in range(geom_dmx.GetPointCount()):
                if [geom_dmx.GetPoint(count)[0], geom_dmx.GetPoint(count)[1]] in geom_list or [
                    round(geom_dmx.GetPoint(count)[0], 4), round(geom_dmx.GetPoint(count)[1], 4)] in geom_list:
                    # print("存在交点", [round(geom_dmx.GetPoint(count)[0], 4), round(geom_dmx.GetPoint(count)[1], 4)])
                    # 赋值
                    HC.UpdateField(layer_dmx, fc_dmx, addField, mean)
                    # print("FID_middle的断面线将赋值", fc_dmx.GetField("FID_middle"), mean)

        del temp_raster
        # 删除中间数据
        os.remove(temp_tif)
        os.remove(temp_shp)

    # 可能会存在不相交的部分（其实是BUG）
    for j in range(layer_dmx.GetFeatureCount()):
        fc_dmx = layer_dmx.GetFeature(j)
        if fc_dmx.GetField(addField) is None or fc_dmx.GetField(addField) <= 0:
            HC.UpdateField(layer_dmx, fc_dmx, addField, layer_dmx.GetFeature(j + 1).GetField(addField))


# def main(inLine, inDEM, inSlpp, inRiver, workSpace):
def main(dmx, slope, river, riverDiv, dem, inFlowDir, inSeed):
    """
    打断断面线，获取每个断点的值
    :param inRiver: 河流线
    :param inSlpp: 坡度
    :param inDEM: 数字高程模型
    :param inLine:断面线
    :return:打断点
    """
    print("-----------------“打断断面线”开始执行-----------------")
    dmxLong = setting.temp_dmxLong
    ZL.main(dmx,dmxLong)
    dmxLongDs = ogr.Open(dmxLong)
    print("计算断面线平均比降...")
    getJ(dmx, slope, riverDiv)
    print("计算糙度...")
    layer = dmx.GetLayer()
    layerLong = dmxLongDs.GetLayer()
    HC.CreateNewField(layer, setting.dmx_field['n0'], ogr.OFTReal)
    # tempDmx = r'E:\College\project\GD\geodata\keshan\temp_dmx.shp'
    tempDmx = os.path.join(setting.output_dir,'temp_dmx.shp')
    # tempDmxRaster = r'E:\College\project\GD\geodata\keshan\temp_dmxRaster.tif'
    tempDmxRaster = os.path.join(setting.output_dir,'temp_dmxRaster.tif')
    print("打断断面线...")
    dem_arr = dem.ReadAsArray()
    # 获取栅格转换信息
    transform = slope.GetGeoTransform()

    # 获取每个格子的大小
    cell_size_x = transform[1]
    # print(cell_size_x)

    # 创建一个新的shapefile文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.CreateDataSource(setting.dmx_points)
    # 坐标系
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(32650)  # WGS_1984_UTM_Zone_50N的EPSG代码是32650
    # 在shapefile文件中创建一个新的图层
    layer_points = ds.CreateLayer('temp_dmx_points', geom_type=ogr.wkbPoint, srs=output_srs)
    # 新建字段名
    HC.CreateNewField(layer_points, setting.dmxPoints_field['ObjectID'], ogr.OFTInteger)
    HC.CreateNewField(layer_points, setting.dmxPoints_field['DmxID'], ogr.OFTInteger)
    HC.CreateNewField(layer_points, setting.dmxPoints_field['J'], ogr.OFTReal)
    HC.CreateNewField(layer_points, setting.dmxPoints_field['n0'], ogr.OFTReal)
    HC.CreateNewField(layer_points, setting.dmxPoints_field['DemValue'], ogr.OFTReal)

    for field in setting.fields_z:
        HC.CreateNewField(layer, field, ogr.OFTReal)
    for field in setting.fields_h:
        HC.CreateNewField(layer, field, ogr.OFTReal)



    for j in range(layerLong.GetFeatureCount()):
        fc_ = layerLong.GetFeature(j)
        geom_ = fc_.GetGeometryRef()
        HC.UpdateField(layerLong, fc_, setting.dmx_field['n0'], 0.025)
        HC.createLine(geom_, tempDmx, ogr.wkbLineString)  # 导出成一份单独的线
        # 转为栅格
        HC.vector2raster(tempDmx, tempDmxRaster)
        dmx_raster = gdal.Open(tempDmxRaster)  # 断面线栅格

        raster_arr = dmx_raster.ReadAsArray()
        raster_yx = np.where(raster_arr == 0)  # 二维数组，[[y1,y2,y3,...],[x1,x2,x3....]]
        for index, x in enumerate(raster_yx[1]):
            px, py = HC.imagexy2geo(dmx_raster, raster_yx[0][index], x)
            if px > 0 and py > 0:
                # 在图层中创建一个新的要素
                feature = ogr.Feature(layer_points.GetLayerDefn())
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint(px + cell_size_x / 2, py - cell_size_x / 2)  # 让点生成在格子中间，不然在格子左上角
                feature.SetGeometry(point)
                layer_points.CreateFeature(feature)
                # print('ObjectID', index, "DmxID", layer.GetFeature(j).GetField(setting.dmx_field['ObjectID']))
                HC.UpdateField(layer_points, feature, setting.dmxPoints_field['ObjectID'], index)
                HC.UpdateField(layer_points, feature, setting.dmxPoints_field['DmxID'],
                               layer.GetFeature(j).GetField(setting.dmx_field['ObjectID']))
                HC.UpdateField(layer_points, feature, setting.dmxPoints_field['J'],
                               layer.GetFeature(j).GetField(setting.dmx_field['J']))
                HC.UpdateField(layer_points, feature, setting.dmxPoints_field['n0'],
                               layer.GetFeature(j).GetField(setting.dmx_field['n0']))
                if float(dem_arr[raster_yx[0][index]][x]) < 0:
                    HC.UpdateField(layer_points, feature, setting.dmxPoints_field['DemValue'],
                                   500)
                else:
                    HC.UpdateField(layer_points, feature, setting.dmxPoints_field['DemValue'],
                                   float(dem_arr[raster_yx[0][index]][x]))
        del dmx_raster  # 删除中间数据源，不然会占用tempDmxRaster
        os.remove(tempDmx)
        os.remove(tempDmxRaster)
    # 保存并关闭文件
    ds = None
    dmxLongDs = None
    dmx = None
    print("生成子流域...")
    HC.CreateBasins(inFlowDir, inSeed, setting.temp_units)
    print("-----------------“打断断面线”运行成功-----------------")
    return setting.dmx_points
