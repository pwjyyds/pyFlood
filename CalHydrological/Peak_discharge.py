# coding:utf-8
import os.path

import numpy as np
from osgeo import ogr, gdal, osr

import setting
import CalHydrological.Common as HC

"""
计算流域洪峰流量
Qm_0 ：假设值默认900（m3/s）
Qm_1 :计算值初始为0（m3/s）
"""


def hongfeng(F, L, J, n, Sp, u, m):
    """
    计算洪峰流量
    :param F: 流域面积
    :param L: 流域内最长河流长度
    :param J: 沿L的平均坡降
    :param n: 暴雨衰减指数
    :param Sp: 设计暴雨
    :param u: 产流参数
    :param m: 汇流参数
    :return: 洪峰流量Qm
    """

    Qm_0 = setting.Qm_0  # 默认为900
    Qm_1 = 0

    def __getQmWhenYes__():  # 全汇流洪峰计算公式
        # print(pow(t, n) - u)
        out_Qm = 0.278 * (Sp / pow(t, n) - u) * F
        return out_Qm

    def __getQmWhenNo__():  # 部分汇流洪峰计算公式
        out_Qm = 0.278 * (Sp * pow(tc, 1 - n) - u * tc) * F / t
        return out_Qm

    while True:
        # 求t
        t = 0.278 * L / (m * pow(J, 1 / 3.0) * pow(Qm_0, 1 / 4.0))
        # 求tc
        tc = pow((1 - n) * Sp / u, 1 / n)
        # print(Qm_0,Qm_1,abs(Qm_0 - Qm_1) / Qm_0)
        if tc >= t:
            Qm_1 = __getQmWhenYes__()
        else:
            Qm_1 = __getQmWhenNo__()

        if abs(Qm_0 - Qm_1) / Qm_0 <= 0.01:
            break
        else:
            Qm_0 = Qm_1

    # 验算
    m1 = 0.278 * L / (t * pow(J, 1 / 3.0) * pow(Qm_0, 1 / 4.0))
    if abs(m1 - m) <= 0.01:
        qm_result = int(Qm_0)
        return qm_result


def main(inFc, inRiver, inSlope, inSp, inN, inField):
    """
    计算每个子流域的洪峰流量
    :param inSeed: 种子点
    :param inFlowDir: 流向栅格目录
    :param inFc:流域面
    :param inRiver:河流线
    :param inSlope:坡度栅格
    :return:
    """
    print("-----------------“计算设计洪峰”开始执行-----------------")
    # temp_riverInUnit = r'E:\College\project\GD\geodata\Output\temp_riverInUnit.shp'  # 栅格化的河流
    # temp_river = r'E:\College\project\GD\geodata\Output\temp_river.tif'  # 栅格化的河流
    temp_riverInUnit = os.path.join(setting.output_dir,"temp_riverInUnit.shp")  # 栅格化的河流
    temp_river =  os.path.join(setting.output_dir,'temp_river.tif')  # 栅格化的河流
    # temp_units_geom = r'E:\College\project\GD\geodata\Output\temp_units_geom.shp'  # 子流域面
    # temp_units_geomTRaster = r'E:\College\project\GD\geodata\Output\temp_units_geomTRaster.tif'  # 子流域面转栅格
    # temp_same = r'E:\College\project\GD\geodata\Output\temp_same.shp'  # 流域内的河流线
    # temp_same_sample = r'E:\College\project\GD\geodata\Output\temp_same_sample.shp'  # 流域内的河流线（简化后）

    layer_ds = ogr.Open(setting.temp_units, 1)
    layer_unit = layer_ds.GetLayer()
    # 给子流域添加字段
    HC.CreateNewField(layer_unit, setting.unit_fields['Sp'], ogr.OFTReal)
    HC.CreateNewField(layer_unit, setting.unit_fields['n'], ogr.OFTReal)
    print("获取流域信息...")
    listdata = []
    river_lyr = inRiver.GetLayer()
    HC.CreateNewField(layer_unit, "J", ogr.OFTReal)
    HC.CreateNewField(layer_unit, "L", ogr.OFTReal)
    for i in range(layer_unit.GetFeatureCount()):
        fc_unit = layer_unit.GetFeature(i)
        # fc_unit = layer_unit.GetFeature(layer_unit.GetFeatureCount()-1)
        geom_unit = fc_unit.GetGeometryRef()
        riverInUnit = None  # 当前流域内的河流
        for river_i in range(river_lyr.GetFeatureCount()):
            river_fc = river_lyr.GetFeature(river_i)
            river_geom = river_fc.GetGeometryRef()
            riverInUnit = geom_unit.Intersection(river_geom)
            if riverInUnit.GetPointCount() == 0:
                # print("The two do not intersect.")
                pass
            else:
                # print("The two lines intersect.")
                break
        # print("riverInUnit", type(riverInUnit), riverInUnit)
        # 计算平均坡度（河道比降）
        HC.createLine(riverInUnit, temp_riverInUnit, ogr.wkbLineString)
        HC.vector2raster(temp_riverInUnit, temp_river)
        river_arr = gdal.Open(temp_river).ReadAsArray()

        # HC.vector2raster(inputfilePath=inRiver, outputfile=temp_river)  # 线转栅格
        temp_raster_yx = np.where(river_arr == 0)
        temp_raster_xy = []  # 河流所占行列
        for index, x in enumerate(temp_raster_yx[1]):
            temp_xy = [x, temp_raster_yx[0][index]]
            temp_raster_xy.append(temp_xy)

        slope_array = inSlope.ReadAsArray()
        sum = 0
        for n in temp_raster_xy:
            slope_value = slope_array[n[1]][n[0]]
            if slope_value == -3.402823e+38 or slope_value < 0:
                slope_value = 0
            sum += slope_value
        if sum == 0:
            mean = 22.121  # 用所有河流平均来替代
        else:
            mean = sum / len(temp_raster_xy)
        HC.UpdateField(layer_unit, fc_unit, "J", mean)

        # print('mean:', sum, len(temp_raster_xy), mean)
        area = geom_unit.GetArea() / 1000000  # 流域面积 km²

        length = riverInUnit.Length()
        if length <=0:
            length = 100
        HC.UpdateField(layer_unit, fc_unit, "L", length)
        # print("length",length,mean,i)
        # 计算汇流参数m
        if area <= 50:
            m = 1
        elif area <= 100:
            m = 1.5
        else:
            m = 2
        listdata.append([area,  # 流域面积 km²
                         length / 1000,  # 河流长度，修改单位为千米
                         mean / 100,  # 河流比降，例如:90%-->0.9
                         inN,
                         inSp,
                         2.5,  # 产流参数u
                         m])
    # print("listdata", listdata)
    print("计算并保存洪峰流量...")
    HC.CreateNewField(layer_unit, inField, ogr.OFTReal)
    for i in range(layer_unit.GetFeatureCount()):
        fc_unit = layer_unit.GetFeature(i)
        temp = hongfeng(listdata[i][0], listdata[i][1], listdata[i][2], listdata[i][3], listdata[i][4], listdata[i][5],listdata[i][6])
        HC.UpdateField(layer_unit, fc_unit, inField, temp)
        # print('洪峰流量：', temp)
    layer_ds = None
    print("-----------------“计算设计洪峰”运行成功-----------------")
