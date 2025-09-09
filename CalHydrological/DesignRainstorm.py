# coding:utf-8
from osgeo import ogr
from scipy.special.cython_special import gdtrix
import numpy

import setting
import CalHydrological.Common as HC

"""
计算流域设计暴雨
"""


def DR(P, H, Cv):
    """
    计算设计暴雨
    :param H:平均雨量
    :param P:频率
    :param Cv:变差系数
    :return:设计暴雨
    """
    Cs = 3.5 * Cv  # 浙江省定为3.5倍
    a = 4.0 / (Cs * Cs)
    b = 2.0 / (H * Cs * Cv)
    a_0 = H - 2 * H * Cv / Cs
    tp = gdtrix(1, a, 1 - P)
    Kp = 1 + Cv * (Cs / 2 * tp - 2 / Cs)
    Hp = Kp * H
    return Hp


def RainPow(H1, H2):
    """
    计算暴雨雨力和暴雨衰减指数
    :param H1:如6小时设计暴雨
    :param H2:如24小时设计暴雨
    :return:Sp和n
    """
    n = 1 + 1.661 * (numpy.log10(H1) - numpy.log10(H2))
    Sp = H2 * pow(24, n - 1)
    return Sp, n


def main(inP, inFc):
    """

    :param inP: 频率
    :param inFc: 流域面
    :return:
    """
    print("================= 当前频率为", inP, " ======================================")
    print("-----------------“计算设计暴雨”开始执行-----------------")
    print("获取6、24小时数据...")
    listdata6 = []  # 6小时数据
    listdata24 = []  # 24小时数据
    layer_unit = inFc.GetLayer()
    for i in range(layer_unit.GetFeatureCount()):
        fc_unit = layer_unit.GetFeature(i)
        listdata6.append([fc_unit.GetField(setting.unit_fields['H_6']), fc_unit.GetField(setting.unit_fields['Cv_6'])])
        listdata24.append([fc_unit.GetField(setting.unit_fields['H_24']), fc_unit.GetField(setting.unit_fields['Cv_24'])])

    print("计算并保存设计暴雨...")
    # 添加字段
    HC.CreateNewField(layer_unit, setting.unit_fields['Sp'], ogr.OFTReal)
    HC.CreateNewField(layer_unit, setting.unit_fields['n'], ogr.OFTReal)

    for i in range(layer_unit.GetFeatureCount()):
        fc_unit = layer_unit.GetFeature(i)
        H6 = DR(inP, listdata6[i][0], listdata6[i][1])
        H24 = DR(inP, listdata24[i][0], listdata24[i][1])
        temp = RainPow(H6, H24)
        HC.UpdateField(layer_unit, fc_unit, setting.unit_fields['Sp'], temp[0])
        HC.UpdateField(layer_unit, fc_unit, setting.unit_fields['n'], temp[1])
        # print("h6 h24",H6,H24)
        # print("sp,n",temp[0],temp[1])
    return temp[0],temp[1]  # Sp,n
    print("-----------------“计算设计暴雨”运行成功-----------------")
