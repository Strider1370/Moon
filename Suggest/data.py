import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import h5py
import numpy as np
import pandas as pd

# 파일 경로 지정
file_path = 'VNP46A2.A2025080.h30v05.002.2025088135600.h5'

# HDF5 파일 열기 및 데이터 읽기
with h5py.File(file_path, 'r') as f:
    ntl = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/Gap_Filled_DNB_BRDF-Corrected_NTL'][:]
    lat = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lat'][:]
    lon = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lon'][:]

# 야간 조도 데이터 클리핑 (0~100)
ntl = np.clip(ntl, 0, 100)

# 배열의 차원 확인 및 meshgrid 생성
if lat.ndim == 1 and lon.ndim == 1:
    lon2d, lat2d = np.meshgrid(lon, lat)
else:
    lat2d = lat
    lon2d = lon

# 배열 평탄화: 모든 배열이 1차원 배열로 변환
lat_flat = lat2d.ravel()
lon_flat = lon2d.ravel()
ntl_flat = ntl.ravel()

# 데이터프레임 생성
df = pd.DataFrame({
    'Latitude': lat_flat,
    'Longitude': lon_flat,
    'Nighttime_Lights': ntl_flat
})

# 지정한 위도, 경도 범위로 필터링 (경도: 125 ~ 130, 위도: 32.5 ~ 38.5)
condition = (
    (df['Longitude'] >= 125) & (df['Longitude'] <= 130) &
    (df['Latitude']  >= 32.5) & (df['Latitude']  <= 38.5)
)
df_filtered = df[condition].copy()

# CSV 파일로 저장
df_filtered.to_csv('viirs_ntl_500m_filtered.csv', index=False)
print("지정한 범위 내의 데이터가 'viirs_ntl_500m_filtered.csv' 파일로 저장되었습니다.")
