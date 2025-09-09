# coding:utf-8
"""
在两个相邻seed间生成分割线
"""

from osgeo import ogr


def main(inSeed,outPath):
    # s = ogr.Open(r"E:\College\project\geoData\seed.shp")  # 种子点
    s = inSeed  # 种子点
    point_data = s.GetLayer(0)  # 得到图层

    # 设置输出文件名和路径
    # output_file = r"E:\College\project\GD\keshan\divideLine.shp"
    output_file = outPath
    # 创建输出文件
    driver = ogr.GetDriverByName("ESRI Shapefile")
    out_data_set = driver.CreateDataSource(output_file)
    # 在shapefile文件中创建一个新的图层
    out_layer = out_data_set.CreateLayer("line_data", geom_type=ogr.wkbLineString)

    # 获取点数据的数量
    num_points = point_data.GetFeatureCount()

    # 遍历点数据，生成线性数据
    for i in range(num_points - 1):
        # 获取相邻两个点
        point1 = point_data.GetFeature(i)
        point2 = point_data.GetFeature(i + 1)
        point1_x = point1.GetField('POINT_X')  # 经度
        point1_y = point1.GetField('POINT_Y')  # 纬度
        point2_x = point2.GetField('POINT_X')  # 经度
        point2_y = point2.GetField('POINT_Y')  # 纬度
        # 中点坐标
        mid_x = (point1_x + point2_x) / 2
        mid_y = (point1_y + point2_y) / 2
        # print(point1_x, point1_y, point2_x, point2_y, mid_x, mid_y)
        # 拟合断面线 y=k2x+b
        if (point1_x - point2_x) == 0:  # 河道线段与y轴平行,断面直线与x轴平行,y=C
            # print("k=0")
            x1 = mid_x - 300
            x2 = mid_x + 300
            y1 = mid_y
            y2 = mid_y
            k2 = 0
        else:
            k1 = (point2_y - point1_y) / (point2_x - point1_x)  # 垂直斜率乘积=-1
            if k1 == 0:  # 断面线斜率不存在,即断面线与y轴平行
                # print("k不存在")
                x1 = mid_x
                x2 = mid_x
                y1 = mid_y + 300
                y2 = mid_y - 300
                k2 = 0
            else:
                k2 = -1 / k1
                if k2 > 87 or k2 < -87:  # 若斜率大于87°,认定为90°
                    # print("k约为不存在")
                    x1 = mid_x
                    x2 = mid_x
                    y1 = mid_y + 300
                    y2 = mid_y - 300
                    k2 = 9999
                else:
                    # print("k=", k2)
                    b = mid_y - k2 * mid_x  # 带入起点
                    x1 = mid_x - 300  # 左
                    x2 = mid_x + 300  # 右
                    y1 = k2 * x1 + b
                    y2 = k2 * x2 + b
        # print(x1, y1, x2, y2)
        # 创建线性数据
        line_data = ogr.Geometry(ogr.wkbLineString)
        line_data.AddPoint(x1, y1)
        line_data.AddPoint(x2, y2)

        # 在图层中创建一个新的要素
        feature = ogr.Feature(out_layer.GetLayerDefn())
        feature.SetGeometry(line_data)
        out_layer.CreateFeature(feature)
        # 将要素写入输出文件
        out_layer.CreateFeature(feature)

    # 关闭输出文件
    out_data_set = None
