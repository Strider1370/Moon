import h5py
import numpy as np

file_path = 'VNP46A2.A2025080.h30v05.002.2025088135600.h5'

with h5py.File(file_path, 'r') as f:
    # 위도와 경도 배열 읽기
    lat = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lat'][:]
    lon = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lon'][:]

# 위도, 경도 범위 확인
lat_min, lat_max = np.min(lat), np.max(lat)
lon_min, lon_max = np.min(lon), np.max(lon)

print("Latitude range:", lat_min, "to", lat_max)
print("Longitude range:", lon_min, "to", lon_max)
