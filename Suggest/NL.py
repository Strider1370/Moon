import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import h5py
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# 파일 경로 지정
file_path = 'VNP46A2.A2025080.h30v05.002.2025088135600.h5'

# HDF5 파일 열기 및 데이터 읽기
with h5py.File(file_path, 'r') as f:
    # 야간 조도 데이터 읽기
    ntl = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/Gap_Filled_DNB_BRDF-Corrected_NTL'][:]
    # 위도, 경도 데이터 읽기
    lat = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lat'][:]
    lon = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lon'][:]

# (옵션) 데이터 클리핑: 0~100 범위로 값 제한
ntl = np.clip(ntl, 0, 100)

# 지도 시각화를 위한 Cartopy 설정
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# 타일의 전체 범위로 지도 설정 (좌표 배열을 사용하여 범위 지정)
ax.set_extent([125, 130, 32.5, 38.5], crs=ccrs.PlateCarree())

# 지도 배경 추가
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.add_feature(cfeature.OCEAN, facecolor='azure')
ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS, linestyle=':')

# 위성 데이터를 지도 위에 pcolormesh로 오버레이 (vmin, vmax로 0~100 범위 지정)
c = ax.pcolormesh(lon, lat, ntl, cmap='inferno', transform=ccrs.PlateCarree(), vmin=0, vmax=100)

# 색상 바 추가 및 레이블 지정
plt.colorbar(c, ax=ax, orientation='vertical', label='Nighttime Lights Intensity')
plt.title('VIIRS/NPP Gap-Filled Lunar BRDF-Adjusted Nighttime Lights')
plt.show()