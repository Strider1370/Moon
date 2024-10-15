import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import matplotlib.colors as mcolors

# 시간대 리스트 생성 (10분 간격)
hours = [f"{hour:02d}{minute:02d}" for hour in range(7, 12) for minute in range(0, 60, 10)]

# E_surface의 최대, 최소 값을 전역적으로 설정
vmin = None
vmax = None

# 모든 파일을 한번 순회하여 E_surface의 전체 범위를 계산
for hour in hours:
    file_path = f'assets/E_surface_20241018{hour}.csv'
    data = pd.read_csv(file_path)
    E_surface = data['E_surface'].values
    
    if vmin is None or vmax is None:
        vmin = E_surface.min()
        vmax = E_surface.max()
    else:
        vmin = min(vmin, E_surface.min())
        vmax = max(vmax, E_surface.max())

for hour in hours:
    # 파일 경로 생성
    file_path = f'assets/E_surface_20241018{hour}.csv'
    
    # CSV 파일을 불러옴
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
        llcrnrlon=125, llcrnrlat=32.5,  # 왼쪽 아래 모서리 (longitude, latitude)
        urcrnrlon=130, urcrnrlat=38.5,  # 오른쪽 위 모서리 (longitude, latitude)
        resolution='i',  # 'c' (낮은 해상도), 'l' (중간 해상도), 'i' (높은 해상도)
        projection='merc',  # 메르카토르 투영법 사용
        lat_0=36, lon_0=128,  # 중심점
        ax=ax
    )
    
    # 위도, 경도를 Basemap 좌표로 변환
    x, y = m(lon_grid, lat_grid)
    
    # 색상 범위에 따라 데이터를 시각화
    # 0 ~ 0.1: 검은색에서 어두운 회색
    mask_0_01 = (E_surface_grid >= 0) & (E_surface_grid <= 0.1)
    c_0_01 = ax.pcolormesh(x, y, np.where(mask_0_01, E_surface_grid, np.nan), cmap='Greys', shading='auto', vmin=0, vmax=0.1)
    
    # 0.1 ~ 0.25: 어두운 회색에서 밝은 노란색
    mask_01_025 = (E_surface_grid > 0.1) & (E_surface_grid <= 0.25)
    c_01_025 = ax.pcolormesh(x, y, np.where(mask_01_025, E_surface_grid, np.nan), cmap='cividis', shading='auto', vmin=0.1, vmax=0.25)
    
    # 0.25 ~ 10: 노란색에서 붉은색
    mask_025_10 = (E_surface_grid > 0.25) & (E_surface_grid <= 10)
    c_025_10 = ax.pcolormesh(x, y, np.where(mask_025_10, E_surface_grid, np.nan), cmap='autumn_r', shading='auto', vmin=0.25, vmax=10)
    
    # 10 ~ 1000: 밝은 파란색에서 붉은색으로 전환
    mask_10_1000 = (E_surface_grid > 10) & (E_surface_grid <= 1000)
    c_10_1000 = ax.pcolormesh(x, y, np.where(mask_10_1000, E_surface_grid, np.nan), cmap='RdYlBu_r', shading='auto', vmin=10, vmax=1000)
    
    # 1000 이상: 붉은색에서 어두운 파란색으로 전환
    mask_1000_up = E_surface_grid > 1000
    c_1000_up = ax.pcolormesh(x, y, np.where(mask_1000_up, E_surface_grid, np.nan), cmap='coolwarm_r', shading='auto', vmin=1000, vmax=vmax)
    
    # 지도 그리기
    m.drawcoastlines()  # 해안선 그리기
    m.drawcountries()   # 국가 경계 그리기
    m.drawparallels(range(30, 40, 1), labels=[1,0,0,0])  # 위도선 그리기
    m.drawmeridians(range(120, 140, 1), labels=[0,0,0,1])  # 경도선 그리기
    
    # 컬러바 추가
    cbar_0_01 = plt.colorbar(c_0_01, ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
    cbar_0_01.set_label('E_surface (0-0.1 milli lux)')
    cbar_01_025 = plt.colorbar(c_01_025, ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
    cbar_01_025.set_label('E_surface (0.1-0.25 milli lux)')
    cbar_025_10 = plt.colorbar(c_025_10, ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
    cbar_025_10.set_label('E_surface (0.25-10 milli lux)')
    
    # 그래프 제목 설정
    ax.set_title(f'E_surface Visualization at {hour[:2]}:{hour[2:]} on Basemap')
    
    # 그래프를 PNG 파일로 저장
    save_path = f'assets/E_surface_20241018{hour}.png'
    plt.savefig(save_path)
    
    # 로그 출력
    print(f"Saved graph to {save_path}")
    
    # 그래프 닫기
    plt.close()