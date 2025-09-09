# coding:utf-8
import math
import copy

from osgeo import ogr

import setting
import CalHydrological.Common as HC

"""
利用曼宁公式计算洪峰水位
遍历断面点：
    计算断面面积和湿周长
    带入公式计算Q
    如果Q和流域的Qm相差太大，就把水位+0.1
"""


def Mnll(n, S, L, I):
    """
    计算曼宁公式的流量
    :param n: 糙度
    :param S: 过水断面积
    :param L: 湿周长
    :param I: 比降
    :return: 流量
    """

    Q = pow(n, -1) * pow(S, 5 / 3.0) * pow(L, -2 / 3.0) * pow(I, 1 / 2.0)
    return Q


def zhouchang(points, inH, length):
    """
    计算湿周周长
    :param points:坐标数据
    :return: 湿周周长L
    """
    sum = 0

    for i in range(len(points) - 1):
        if inH - points[i][2] >= 0:  # 水位线以下
            Xc = setting.raster_pixel_width / length
            Yc = abs(points[i][2] - points[i + 1][2])
            sum += math.sqrt(Xc * Xc + Yc * Yc)
    if sum <= 0:
        return setting.raster_pixel_width / length
    else:
        return abs(sum)


def square(points, inH, length):
    """
    计算不规则面积
    :param length: 单位长度
    :param inH: 当前水位
    :param points: 坐标数据
    :return: 面积
    """
    sum0 = 0.0
    # for i in range(len(p) - 1):
    #     sum0 += (p[i][0] * p[i + 1][1] - p[i + 1][0] * p[i][1])
    # sum = (abs(sum0 + (p[len(p) - 1][0] * p[0][1]) - (p[0][0] * p[len(p) - 1][1]))) / 2
    for point in points:
        # print(setting.raster_pixel_width,inH-i[1])
        if inH - point[2] >= 0:
            sum0 += (setting.raster_pixel_width / length) * (inH - point[2])

    return sum0


def main(inPoint, inLine, field_z, field_h, fields_Qm,fields_L,fields_S):
    """
    :param fields_Qm:
    :param inPoint: 断面线断点
    :param inLine:  断面线
    :param field_z:  不同频率的字段名称
    :param field_h:
    :return:
    """
    print("-----------------“计算洪峰水位”开始执行-----------------")

    print("获取关键属性...")
    layer_dmx = inLine.GetLayer()
    HC.CreateNewField(layer_dmx, field_z, ogr.OFTReal)
    HC.CreateNewField(layer_dmx, field_h, ogr.OFTReal)
    HC.CreateNewField(layer_dmx, fields_L, ogr.OFTReal)
    HC.CreateNewField(layer_dmx,fields_S, ogr.OFTReal)
    dmxPointDs = ogr.Open(inPoint, 1)
    layer_point = dmxPointDs.GetLayer()
    tempUnitDs = ogr.Open(setting.temp_units, 1)
    layer_tempUnit = tempUnitDs.GetLayer()
    count_lyrPoints = layer_point.GetFeatureCount()
    thisDmxPoint_dmxID = layer_point.GetFeature(0).GetField(setting.dmxPoints_field['DmxID'])  # 当前断面点属于的断面线ID
    sameDmxPoints = []  # 同一个断面的点
    h_result = 0

    for i in range(count_lyrPoints):  # 遍历断面点
        fc_point = layer_point.GetFeature(i)
        dmxID = fc_point.GetField(setting.dmxPoints_field['DmxID'])

        if thisDmxPoint_dmxID == dmxID:
            # 同一个断面线的点
            tempList = []
            tempList.append(fc_point.GetField(setting.dmxPoints_field['ObjectID']))

            tempList.append(dmxID)
            pointDemValue = fc_point.GetField(setting.dmxPoints_field['DemValue'])
            if pointDemValue is None or pointDemValue <= 0:
                tempList.append(500)
            else:
                tempList.append(pointDemValue)
            tempList.append(fc_point.GetField(setting.dmxPoints_field['n0']))
            tempList.append(fc_point.GetField(setting.dmxPoints_field['J']))

            filter = "basin=" + str(dmxID + 1)
            layer_tempUnit.SetAttributeFilter(filter)  # 设置属性过滤器
            unitQm = None
            for fc_ in layer_tempUnit:
                unitQm = fc_.GetField(fields_Qm)
                break
            if unitQm is None:
                tempList.append(100)
            else:
                tempList.append(unitQm)
            sameDmxPoints.append(tempList)
        else:
            # 计算上一个断面的点
            if dmxID ==0:
                aaaaaaaa=1
            p_h = []
            for p in sameDmxPoints:
                p_h.append(p[2])
            h_0 = (sum(p_h) - max(p_h) - min(p_h)) / len(p_h)

            # mid_0 = int(len(sameDmxPoints) / 2)  # 中间
            # if len(sameDmxPoints) % 2 == 0:
            #     mid_0 -= 1
            # h_0 = sameDmxPoints[mid_0][2]  # 初始洪峰水位

            # h_0 = sameDmxPoints[0][2]
            # for p in sameDmxPoints:  # 令初始洪峰水位为中间断面点
            #     if h_0 > p[2]:
            #         h_0 = p[2]
            sameDmxPoints_more = []  # 精分sameDmxPoints
            for sdp in sameDmxPoints:
                sameDmxPoints_more.append(sdp)
            n = 0
            num_insert = 30  # 插入的个数
            for i_sdp in range(len(sameDmxPoints_more) - 1):
                for j_ni in range(num_insert):
                    eveValue = sameDmxPoints_more[n + j_ni + 1][2] + (
                            sameDmxPoints_more[n + j_ni + 1][2] - sameDmxPoints_more[n + j_ni][2]) / num_insert
                    insertValue = [sameDmxPoints[i_sdp][0],
                                   sameDmxPoints[i_sdp][1],
                                   eveValue,
                                   sameDmxPoints[i_sdp][3],
                                   sameDmxPoints[i_sdp][4],
                                   sameDmxPoints[i_sdp][5],
                                   ]  # 要插入的值
                    sameDmxPoints_more.insert(n + j_ni + 1, insertValue)
                n += num_insert + 1
            count_step = 1
            step = 0.35
            index = 1
            max_count = 85
            # 获取到每个断面点的洪峰水位
            beCalPoints = []  # 即将用于计算的点
            mid = int(len(sameDmxPoints_more) / 2)  # 中间
            if len(sameDmxPoints_more) % 2 == 0:
                mid -= 1
                beCalPoints = [sameDmxPoints_more[mid], sameDmxPoints_more[mid + 1]]
                # print('初始', beCalPoints)
            else:
                beCalPoints = [sameDmxPoints_more[mid]]
                # print('初始', beCalPoints)
            # print("计算洪峰水位...")
            biggerTime = 0  # 大于流域流量次数
            # print("=====开始迭代=========")
            temp_history = []  # 历史迭代数据
            S_result = 0
            L_result = 0

            while True:  # 从中间向两边扩展
                S = square(beCalPoints, h_0, len(sameDmxPoints_more))  # 计算断面过水面积
                L = zhouchang(beCalPoints, h_0, len(sameDmxPoints_more))  # 计算湿周长
                Q = Mnll(n=beCalPoints[0][3],
                         S=S, L=L,
                         I=beCalPoints[0][4])  # 计算曼宁洪峰流量
                Qm = beCalPoints[0][5]
                abs_error = abs(Q - Qm) / Qm
                if abs_error <= 0.01:
                    # print("误差范围内", abs_error)
                    S_result = S
                    L_result = L
                    break
                # elif Q > Qm or abs_error > 100:
                # elif abs_error > 100:
                #     if biggerTime == setting.fields_z.index(field_z):
                #         print("大于了", abs_error)
                #         break
                #     else:
                #         print("还能再大",abs_error)
                #         biggerTime += 1
                else:
                    # print("进行下一次", abs_error)
                    h_0 += step
                    count_step += 1
                    if len(sameDmxPoints_more) % 2 == 0:
                        beCalPoints = sameDmxPoints_more[mid - index:mid + index + 2]
                    else:
                        beCalPoints = sameDmxPoints_more[mid - index:mid + index + 1]
                    index += 1
                    temp_history.append(abs_error)

                if index >= mid + 1 or count_step >= max_count:
                    # print("断面到顶/水位太高了", abs_error)
                    S_result = S
                    L_result = L
                    break
            # print("当前断面点洪峰水位",h_0)
            h_result = h_0
            # 赋值给断面线
            fc_line = layer_dmx.GetFeature(thisDmxPoint_dmxID)
            h_z = step * count_step
            if count_step == max_count:

                h_z = step * (temp_history.index(min(temp_history)) + 1)
            HC.UpdateField(layer_dmx, fc_line, field_z, h_z)  # 水位
            HC.UpdateField(layer_dmx, fc_line, fields_S, S_result)  # 水位
            HC.UpdateField(layer_dmx, fc_line, fields_L, L_result)  # 水位
            # HC.UpdateField(layer_dmx, fc_line, field_h, h_result)  # 水位+高程值
            # print("第几个点属于的断面线的ID:", dmxID)
            # print("最终计算的当前断面水位：", h_z)
            # 到下一个断面线的点了
            thisDmxPoint_dmxID = fc_point.GetField(setting.dmxPoints_field['DmxID'])
            sameDmxPoints = []

    inLine = None
    dmxPointDs = None
    print("-----------------“计算洪峰水位”运行成功-----------------")
