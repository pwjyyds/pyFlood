# coding:utf-8
import numpy as np
from osgeo import gdal
from scipy import ndimage
import matplotlib.pyplot as plt


def read_dem(file_path):
    """读取DEM数据并返回numpy数组和地理信息"""
    ds = gdal.Open(file_path)
    band = ds.GetRasterBand(1)
    dem_array = band.ReadAsArray().astype(np.float32)
    geotransform = ds.GetGeoTransform()
    projection = ds.GetProjection()
    nodata = band.GetNoDataValue()
    return dem_array, geotransform, projection, nodata


def write_raster(array, file_path, geotransform, projection, nodata=None):
    """将numpy数组写入栅格文件"""
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = array.shape
    out_ds = driver.Create(file_path, cols, rows, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)
    out_band = out_ds.GetRasterBand(1)
    if nodata is not None:
        out_band.SetNoDataValue(nodata)
    out_band.WriteArray(array)
    out_band.FlushCache()
    out_ds = None


def calculate_slope(dem, cellsize):
    """计算DEM坡度（弧度）"""
    x, y = np.gradient(dem, cellsize, cellsize)
    slope = np.arctan(np.sqrt(x ** 2 + y ** 2))
    return slope


def calculate_relief(dem, window_size=5):
    """计算局部地形起伏度"""
    max_dem = ndimage.maximum_filter(dem, size=window_size)
    min_dem = ndimage.minimum_filter(dem, size=window_size)
    relief = max_dem - min_dem
    return relief


def region_growing(dem, slope, relief, seed_thresholds, grow_thresholds, max_size=100000):
    """
    区域生长算法实现

    参数:
    - dem: DEM数组
    - slope: 坡度数组（弧度）
    - relief: 地形起伏度数组
    - seed_thresholds: 种子点筛选阈值字典 {'slope': , 'relief': }
    - grow_thresholds: 区域生长阈值字典 {'slope': , 'relief': , 'dem_diff': }
    - max_size: 最大区域尺寸（像素数）

    返回:
    - 标记的区域数组
    """
    # 创建种子点掩码
    seed_mask = (slope < np.radians(seed_thresholds['slope'])) & \
                (relief < seed_thresholds['relief'])

    # 初始化标记数组
    rows, cols = dem.shape
    labeled = np.zeros_like(dem, dtype=np.int32)
    current_label = 1

    # 8邻域偏移
    neighbors = [(-1, -1), (-1, 0), (-1, 1),
                 (0, -1), (0, 1),
                 (1, -1), (1, 0), (1, 1)]

    # 遍历所有种子点
    for i in range(rows):
        for j in range(cols):
            if seed_mask[i, j] and labeled[i, j] == 0:
                # 开始新区域生长
                region_size = 0
                queue = [(i, j)]
                labeled[i, j] = current_label
                region_size += 1

                # 区域平均属性
                sum_dem = dem[i, j]
                sum_slope = slope[i, j]
                sum_relief = relief[i, j]

                while queue and region_size < max_size:
                    x, y = queue.pop(0)

                    # 检查所有邻居
                    for dx, dy in neighbors:
                        nx, ny = x + dx, y + dy

                        # 边界检查
                        if nx < 0 or nx >= rows or ny < 0 or ny >= cols:
                            continue

                        # 已标记或不符合生长条件的点跳过
                        if labeled[nx, ny] != 0:
                            continue

                        # 检查生长条件
                        dem_diff = abs(dem[nx, ny] - (sum_dem / region_size))
                        if (slope[nx, ny] < np.radians(grow_thresholds['slope'])) and \
                                (relief[nx, ny] < grow_thresholds['relief']) and \
                                (dem_diff < grow_thresholds['dem_diff']):
                            # 添加到当前区域
                            labeled[nx, ny] = current_label
                            queue.append((nx, ny))
                            region_size += 1

                            # 更新区域统计
                            sum_dem += dem[nx, ny]
                            sum_slope += slope[nx, ny]
                            sum_relief += relief[nx, ny]

                # 如果区域足够大，增加标签
                if region_size > 100:  # 忽略过小的区域
                    current_label += 1
                else:
                    # 移除过小的区域
                    labeled[labeled == current_label] = 0

    return labeled


def post_process(labeled, min_size=500):
    """后处理：移除小区域"""
    unique_labels, counts = np.unique(labeled, return_counts=True)
    for label, count in zip(unique_labels, counts):
        if label != 0 and count < min_size:
            labeled[labeled == label] = 0
    return labeled


def main():
    # 输入输出路径
    dem_path = r"H:\saga_demo\DEM\珠乔镇DEM.tif"
    output_path = r"H:\saga_demo\data"
    # 设置GDAL配置选项，使用官方EPSG参数
    gdal.SetConfigOption('GTIFF_SRS_SOURCE', 'EPSG')
    # 读取DEM
    dem, geotransform, projection, nodata = read_dem(dem_path)

    # 设置NoData值
    if nodata is not None:
        dem[dem == nodata] = np.nan

    # 计算坡度（转换为度）
    cellsize = geotransform[1]  # 假设为正方形像素
    slope_rad = calculate_slope(dem, cellsize)
    slope_deg = np.degrees(slope_rad)

    # 计算地形起伏度
    relief = calculate_relief(dem)

    # 设置阈值
    seed_thresholds = {'slope': 2, 'relief': 10}  # 种子点阈值
    grow_thresholds = {'slope': 5, 'relief': 15, 'dem_diff': 5}  # 生长阈值

    # 执行区域生长
    labeled_regions = region_growing(dem, slope_rad, relief, seed_thresholds, grow_thresholds)

    # 后处理
    processed_regions = post_process(labeled_regions)

    # 创建平地掩码（所有标记区域为平地）
    flat_mask = np.where(processed_regions > 0, 1, 0).astype(np.float32)

    # 保存结果
    write_raster(flat_mask, output_path, geotransform, projection)

    # 可视化结果（可

    print("平地提取完成！")


if __name__ == "__main__":
    main()