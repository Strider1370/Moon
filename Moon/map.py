import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

# CSV 파일을 불러옴
file_path = 'E_surface_2024101814.csv'  # CSV 파일 경로
data = pd.read_csv(file_path)

# 위도, 경도 데이터 준비
lon = data['longitude'].values
lat = data['latitude'].values
E_surface = data['E_surface'].values

# 위도 경도를 그리드로 변환 (pcolormesh는 그리드 형태가 필요)
lon_grid, lat_grid = np.meshgrid(np.unique(lon), np.unique(lat))
E_surface_grid = E_surface.reshape(len(np.unique(lat)), len(np.unique(lon)))

# Basemap 설정 (한국 영역에 맞춘 지도)
fig, ax = plt.subplots(figsize=(10, 10))

m = Basemap(
    llcrnrlon=123, llcrnrlat=32,  # 왼쪽 아래 모서리 (longitude, latitude)
    urcrnrlon=132, urcrnrlat=39,  # 오른쪽 위 모서리 (longitude, latitude)
    resolution='i',  # 'c' (낮은 해상도), 'l' (중간 해상도), 'i' (높은 해상도)
    projection='merc',  # 메르카토르 투영법 사용
    lat_0=36, lon_0=128,  # 중심점
    ax=ax
)

# 위도, 경도를 Basemap 좌표로 변환
x, y = m(lon_grid, lat_grid)

# E_surface 값을 연속된 면으로 시각화 (pcolormesh 사용)
c = ax.pcolormesh(x, y, E_surface_grid, cmap='viridis', shading='auto')

# 지도 그리기
m.drawcoastlines()  # 해안선 그리기
m.drawcountries()   # 국가 경계 그리기
m.drawparallels(range(30, 40, 1), labels=[1,0,0,0])  # 위도선 그리기
m.drawmeridians(range(120, 140, 1), labels=[0,0,0,1])  # 경도선 그리기

# 컬러바 추가
cbar = plt.colorbar(c, ax=ax, orientation='vertical')
cbar.set_label('E_surface (milli lux)')

# 그래프 제목 설정
ax.set_title('E_surface Visualization with Continuous Surface on Basemap')

# 그래프 표시
plt.show()