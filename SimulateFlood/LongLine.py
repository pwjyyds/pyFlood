"""
延长断面线
"""
from osgeo import ogr, osr
import sympy as sp
from scipy.optimize import curve_fit


# 定义线性方程
def linear_eq(x, k, b):
    return k * x + b


def main(oldLine, newLine):
    """
    延长断面线
    :param oldLine:断面线
    :param newLine:延长后断面线
    :return:
    """
    # 延长断面线
    # dataSource = ogr.Open(r"E:\College\project\geoData\dxm.shp")  # 断面线
    dataSource = oldLine  # 断面线
    if type(dataSource) is str:
        # 打开矢量文件
        dataSource = ogr.Open(dataSource)

    sourceLayer = dataSource.GetLayer()

    # 创建一个新的shapefile文件
    driver = ogr.GetDriverByName('ESRI Shapefile')
    # ds = driver.CreateDataSource(r'E:\College\project\GD\keshan\newLine.shp')
    ds = driver.CreateDataSource(newLine)
    # 坐标系
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(32650)  # WGS_1984_UTM_Zone_50N的EPSG代码是32650
    # 在shapefile文件中创建一个新的图层
    layer = ds.CreateLayer('newLine', geom_type=ogr.wkbLineString, srs=output_srs)
    # 向图层中添加一个字段
    # field_defn = ogr.FieldDefn('field_name', ogr.OFTString)
    # layer.CreateField(field_defn)

    for feature in sourceLayer:
        geom = feature.GetGeometryRef()
        # 获取起始点坐标
        # print(geom)
        # print(geom.GetX(0),geom.GetY(0),geom.GetX(1),geom.GetY(1),geom.GetX(2),geom.GetY(2))

        # 将数据拟合到线性方程
        popt, pcov = curve_fit(linear_eq, [geom.GetX(0), geom.GetX(2)], [geom.GetY(0), geom.GetY(2)])  # 打印k和b的值
        k = popt[0]
        b = popt[1]
        # print("y =", k, "* x+", b)

        # 求解延长后的左右点坐标，即新线段的起始点坐标
        x3 = sp.symbols('x3')  # 定义符号变量
        eq = sp.Eq(600, sp.sqrt((x3 - geom.GetX(2)) ** 2 + (k * x3 + b - geom.GetY(2)) ** 2))  # 定义方程
        sol = sp.solve(eq, x3)  # 解方程
        # print("x3_起点= ", sol[0], "y3=", k * sol[0] + b)  # 打印解
        # print("x3_终点= ", sol[1], "y3=", k * sol[1] + b)
        # 在图层中创建一个新的要素
        feature = ogr.Feature(layer.GetLayerDefn())
        newline = ogr.Geometry(ogr.wkbLineString)
        newline.AddPoint(float(sol[0]), float(k * sol[0] + b))
        newline.AddPoint(float(sol[1]), float(k * sol[1] + b))
        feature.SetGeometry(newline)
        # feature.SetField('field_name', 'field_value')
        layer.CreateFeature(feature)

    # 保存并关闭shapefile文件
    ds = None
