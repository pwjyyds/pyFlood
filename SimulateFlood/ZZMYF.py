# coding:utf-8
import os.path

from osgeo import gdal
from osgeo.gdalconst import *  # GDAL中常用的一些常量
import geopandas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from osgeo import ogr
from matplotlib import colors

import SimulateFlood.LongLine, SimulateFlood.CreateDivLine
import CalHydrological.Common as HC
import setting


def getSeedXY(seed, data, dmx, dem_array, field_z, field_h):
    """
    获取所有种子所在的经纬度坐标等属性，并将其转为行列号，存放到一个种子字典里
    """
    seed_dict = []
    layer = seed.GetLayer(0)  # 得到图层
    layer_dmx = dmx.GetLayer(0)  # 得到图层
    transform = data.GetGeoTransform()  # 获取栅格的仿射矩阵
    xOrigin = transform[0]  # 获取栅格左上角栅格的点位信息
    yOrigin = transform[3]  # 获取栅格左上角栅格的点位信息
    pixelWidth = transform[1]  # 获取栅格的宽度
    pixelHeight = transform[5]  # 获取栅格的高度

    for i in range(layer.GetFeatureCount()):
        feat = layer.GetFeature(i)
        feat_dmx = layer_dmx.GetFeature(i)
        x = feat.GetField('POINT_X')  # 经度
        y = feat.GetField('POINT_Y')  # 纬度
        x_col = int((x - xOrigin) / pixelWidth)  # 获取点所在的列号X
        y_row = int((y - yOrigin) / pixelHeight)  # 获取点所在的行号Y
        high = dem_array[y_row][x_col]

        seed_h = feat_dmx.GetField(field_z) + high
        HC.UpdateField(layer_dmx, feat_dmx, field_h, seed_h)  # 水位+高程值

        seed_dict.append({
            "FID": feat.GetField('FID_middle'),
            "X": x_col,
            "Y": y_row,
            "done": 0,
            "z": seed_h
        })

    # print(seed_dict)
    return seed_dict


def saveResult(data, floodPart, savePath):
    """
    生成淹没区,numpy数组转tif
    """
    fleed = np.zeros((data.RasterYSize, data.RasterXSize))
    for i in floodPart:
        # print(i)
        fleed[i[1], i[0]] = 1
    # 设置输出文件名和路径
    # output_file = r"E:\College\project\GD\keshan\result_h100.tif"
    output_file = savePath
    # 获取数组的形状
    rows, cols = fleed.shape
    # 创建输出文件
    driver = gdal.GetDriverByName("GTiff")
    out_data_set = driver.Create(output_file, cols, rows, 1, gdal.GDT_Float32)
    # 将数组写入输出文件
    out_data_set.GetRasterBand(1).WriteArray(fleed)
    # 设置地理参考信息# 设置投影信息
    out_data_set.SetGeoTransform(data.GetGeoTransform())
    out_data_set.SetProjection(data.GetProjection())
    # 关闭输出文件
    out_data_set = None


def main(data, dmx, seed, inZField, inHField):
    """
    输入数据：DEM、断面线、种子点（有洪峰水位）
    data = gdal.Open(r"E:\College\project\geoData\dsz_dem")  # DEM
    dmx = ogr.Open(r"E:\College\project\geoData\dxm.shp")  # 断面线
    seed = ogr.Open(r"E:\College\project\geoData\seed.shp")  # 种子点
    """
    print("-----------------“计算淹没区”开始执行-----------------")
    # print(inZField)
    # temp_dmxLong = r'E:\College\project\GD\geodata\Output\temp_dmxLong.shp'
    temp_dmxLong = os.path.join(setting.output_dir,'temp_dmxLong.shp')
    temp_divLine = os.path.join(setting.output_dir,'temp_divLine.shp')
    temp_divLine_tif =  os.path.join(setting.output_dir,'temp_divLine.tif')
    result_path = os.path.join(setting.output_dir, 'result_' + inZField + '.tif')
    dem_array = data.ReadAsArray()
    print("延长断面线...")
    SimulateFlood.LongLine.main(dmx, temp_dmxLong)
    print("切割河流...")
    SimulateFlood.CreateDivLine.main(seed, temp_divLine)
    HC.vector2raster(inputfilePath=temp_divLine, outputfile=temp_divLine_tif)
    """
    读取所有延长后的断面线所占格子，存放到断面线数组里
    """
    print("读取延长后的断面线...")
    newDmx = gdal.Open(temp_divLine_tif)
    newDmx_raster_array = newDmx.ReadAsArray()
    newDmx_yx = np.where(newDmx_raster_array == 0)  # 二维数组，[[y1,y2,y3,...],[x1,x2,x3....]]
    newDmx_xy = []
    for index, x in enumerate(newDmx_yx[1]):
        temp_xy = [x, newDmx_yx[0][index]]
        newDmx_xy.append(temp_xy)
    # a = pd.DataFrame(dmx_yx)

    # seed_dict = getSeedXY(seed, data)
    seed_dict = getSeedXY(seed, data, dmx, dem_array, inZField, inHField)

    """
    模拟淹没区
    """
    print("计算淹没区...")

    # p = "h100"  # 频率字段
    p = inZField  # 频率字段
    floodPart = []  # 被淹数组
    newPoint = []  # 新原点数组
    haveDonePoint = []  # 已遍历原点数组
    for i in seed_dict:
        seed_x = i["X"]
        seed_y = i["Y"]
        # print("当前种子坐标", seed_x, seed_y)
        # 首先判断种子是否已遍历
        if i["done"] == 0:
            # print('当前水位', i["z"], i['FID'])
            # 未遍历，以种子为原点，进行八邻域遍历
            newPoint.append([seed_x, seed_y])
            for point in newPoint:
                # print('原点坐标', point[0], point[1])
                if point not in haveDonePoint:
                    for x in range(point[0] - 1, point[0] + 2):
                        for y in range(point[1] - 1, point[1] + 2):
                            # print('八邻域中的点为', x, y)
                            # 1. 判断这个格子在不在断面线数组[[y1,y2,y3,...],[x1,x2,x3....]]：如果在，就不做b
                            # 2. 原点高程≤`当前种子洪峰水位`
                            if [x, y] not in newDmx_xy:
                                # print('不在边界')
                                if x in range(data.RasterXSize) and y in range(data.RasterYSize):
                                    thisDem = dem_array[y][x]  # 原点高程
                                else:
                                    # print("触碰到边界了")
                                    continue
                                # print("原点高程", thisDem, "当前种子洪峰水位", i[p])
                                if thisDem != -32768 and 0 < thisDem <= i["z"]:
                                    # 被淹没的格子存放到一个被淹数组和新原点数组里
                                    floodPart.append([x, y])
                                    newPoint.append([x, y])
                                    # print('被淹')
                                else:
                                    # print('未被淹')
                                    pass
                            else:
                                # print('在边界')
                                floodPart.append([x, y])  # 默认在边界上的点都被淹没
                                break

                        else:
                            i["done"] = 1  # 八邻域遍历结束后，当前种子标记为已遍历
                            haveDonePoint.append(point)
                            continue
                        break
                # print("一共", len(newPoint), "当前")

        # print("=========一次种子循环结束===========", "FID=", i["FID"], "len(seed_dict)", len(seed_dict))
        newPoint = []

    # print("被淹格子数量：", len(floodPart))
    print("保存结果...")
    saveResult(data, floodPart, result_path)
    print("-----------------“计算淹没区”运行成功-----------------")
