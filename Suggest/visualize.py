import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

# CSV 파일 읽기
df = pd.read_csv('viirs_ntl_land_only.csv')

# pivot_table을 사용해 위도와 경도 그리드 구성 (같은 좌표에 대한 중복 값은 평균 집계)
grid = df.pivot_table(index='Latitude', columns='Longitude', values='Nighttime_Lights', aggfunc='mean')

# 0 값을 마스킹 처리 (0인 셀은 시각화에서 투명하게 처리됨)
grid_masked = np.ma.masked_where(grid.values == 0, grid.values)

# 피벗된 데이터에서 위도, 경도 값 추출 (오름차순 정렬되어 있어야 함)
lat_vals = grid.index.values
lon_vals = grid.columns.values

# 위도, 경도 2차원 격자 생성
lon2d, lat2d = np.meshgrid(lon_vals, lat_vals)

# 지도 생성: Cartopy의 PlateCarree 투영 사용
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# 지도 범위 설정 (경도: 125 ~ 130, 위도: 32.5 ~ 38.5)
ax.set_extent([125, 130, 32.5, 38.5], crs=ccrs.PlateCarree())

# 지도 배경 추가
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.add_feature(cfeature.OCEAN, facecolor='azure')

# pcolormesh를 이용해 마스킹된 데이터를 지도 위에 오버레이
c = ax.pcolormesh(lon2d, lat2d, grid_masked, cmap='inferno',
                  transform=ccrs.PlateCarree(), vmin=0, vmax=100, shading='auto')

# 색상 바 추가 및 레이블 지정
plt.colorbar(c, ax=ax, orientation='vertical', label='Nighttime Lights Intensity')

# ★ 시군구 경계 shapefile 추가 (좌표계: EPSG:5179) ★
shp_path = 'ctprvn.shp'
reader = shpreader.Reader(shp_path)
geoms = list(reader.geometries())
ax.add_geometries(
    geoms, 
    crs=ccrs.PlateCarree(),         # 최종적으로 지도에 표시할 좌표계
    transform=ccrs.epsg(5179),        # shapefile의 원본 좌표계
    edgecolor='white', 
    facecolor='none', 
    linewidth=0.2, 
    zorder=10
)

plt.title('VIIRS Nighttime Lights with Administrative Boundaries')
plt.show()
