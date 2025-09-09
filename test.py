# coding:utf-8
import os.path

from osgeo import gdal, ogr
import numpy as np

import SimulateFlood.LongLine, SimulateFlood.CreateDivLine
import CalHydrological.Common as HC


def getSeedXY(seed, data, dem_array, field_h):
    """
    获取所有种子所在的经纬度坐标等属性，并将其转为行列号，存放到一个种子字典里
    """
    seed_dict = []
    layer = seed.GetLayer(0)  # 得到图层
    transform = data.GetGeoTransform()  # 获取栅格的仿射矩阵
    xOrigin = transform[0]  # 获取栅格左上角栅格的点位信息
    yOrigin = transform[3]  # 获取栅格左上角栅格的点位信息
    pixelWidth = transform[1]  # 获取栅格的宽度
    pixelHeight = transform[5]  # 获取栅格的高度

    for i in range(layer.GetFeatureCount()):
        feat = layer.GetFeature(i)
        x = feat.GetField('POINT_X')  # 经度
        y = feat.GetField('POINT_Y')  # 纬度
        x_col = int((x - xOrigin) / pixelWidth)  # 获取点所在的列号X
        y_row = int((y - yOrigin) / pixelHeight)  # 获取点所在的行号Y
        high = dem_array[y_row][x_col]

        seed_h = high+field_h

        seed_dict.append({
            "FID": feat.GetField('Id'),
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


def main(data, seed,output_dir, inHField):
    """
    输入数据：DEM、断面线、种子点（有洪峰水位）
    data = gdal.Open(r"E:\College\project\geoData\dsz_dem")  # DEM
    dmx = ogr.Open(r"E:\College\project\geoData\dxm.shp")  # 断面线
    seed = ogr.Open(r"E:\College\project\geoData\seed.shp")  # 种子点
    """
    print("-----------------“计算淹没区”开始执行-----------------")
    # print(inZField)
    # temp_dmxLong = r'E:\College\project\GD\geodata\Output\temp_dmxLong.shp'
    result_path = os.path.join(output_dir, 'result_' + str(inHField) + '.tif')
    dem_array = data.ReadAsArray()

    seed_dict = getSeedXY(seed, data, dem_array, inHField)

    """
    模拟淹没区
    """
    print("计算淹没区...")
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
                            i["done"] = 1  # 八邻域遍历结束后，当前种子标记为已遍历
                            haveDonePoint.append(point)
                            continue
                        break
                print("一共", len(newPoint), "当前")

        # print("=========一次种子循环结束===========", "FID=", i["FID"], "len(seed_dict)", len(seed_dict))
        newPoint = []

    # print("被淹格子数量：", len(floodPart))
    print("保存结果...")
    saveResult(data, floodPart, result_path)
    print("-----------------“计算淹没区”运行成功-----------------")

main(gdal.Open(r"H:\saga_demo\DEM\珠乔镇DEM.tif"),
     ogr.Open(r"H:\saga_demo\data\seeds.shp",1),
     r"H:\saga_demo\data",
     10)