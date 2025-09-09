# coding:utf-8
"""
主入口
"""
from osgeo import gdal, ogr

from CalHydrological import Pretreatment, DesignRainstorm, Peak_discharge, FloodPeakWaterLevel
import setting
from setting import p_all, fields_h, fields_z, Qm_0, fields_Qm, fields_L, fields_S
from SimulateFlood import ZZMYF as ZZ


def main():
    """选择方法"""
    print("各文件目录为:\n    河流线:", setting.river_dir,
          "\n    断面线:", setting.dmx_dir, "\n    研究区范围面:", setting.unit_dir, "\n    数字高程模型:",
          setting.dem_dir, "\n    坡度:", setting.slope_dir)
    print("请确保配置文件修改完成，当前配置下:\n    需计算的频率为:", p_all, "\n    初始洪峰水位为:", Qm_0)

    dmx_points = Pretreatment.main(dmx, slope, river, riverDiv, data, setting.flowDir_dir, seed)
    for index, p in enumerate(p_all):
        Sp, n = DesignRainstorm.main(p, unit)  # 计算流域的设计暴雨
        Peak_discharge.main(unit, river, slope, Sp, n, fields_Qm[index])  # 计算流域的设计洪峰
        FloodPeakWaterLevel.main(dmx_points, dmx,
                                 fields_z[index], fields_h[index], fields_Qm[index], fields_L[index],
                                 fields_S[index])  # 计算断面线的设计水位
        ZZ.main(data, dmx, seed, fields_z[index], fields_h[index])


if __name__ == '__main__':
    """
    输入数据：DEM、断面线、种子点（有洪峰水位）
    """
    data = gdal.Open(setting.dem_dir)  # DEM
    dmx = ogr.Open(setting.dmx_dir, 1)  # 断面线
    river = ogr.Open(setting.river_dir, 1)  # 河流线
    riverDiv = ogr.Open(setting.riverDiv_dir, 1)  # 打断的河流线
    slope = gdal.Open(setting.slope_dir)  # 坡度
    unit = ogr.Open(setting.unit_dir, 1)  # 研究区范围面
    seed = ogr.Open(setting.seed_dir, 1)  # 种子点

    geotransform = data.GetGeoTransform()
    setting.raster_pixel_width = geotransform[1]

    main()
