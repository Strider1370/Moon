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

# 배열의 차원 확인 및 메시그리드 생성
# 만약 lat, lon이 1차원 배열이면, meshgrid를 사용해 2차원 배열로 변환합니다.
if lat.ndim == 1 and lon.ndim == 1:
    # 일반적으로 ntl의 shape가 (m, n)일 때, lat의 길이는 m, lon의 길이는 n이어야 합니다.
    lon2d, lat2d = np.meshgrid(lon, lat)
else:
    lat2d = lat
    lon2d = lon

# 배열 평탄화: 모든 배열이 1차원 배열로 변환되어 길이가 같아집니다.
lat_flat = lat2d.ravel()
lon_flat = lon2d.ravel()
ntl_flat = ntl.ravel()

# 데이터프레임 생성
df = pd.DataFrame({
    'Latitude': lat_flat,
    'Longitude': lon_flat,
    'Nighttime_Lights': ntl_flat
})

# CSV 파일로 저장
df.to_csv('viirs_ntl_500m.csv', index=False)
print("CSV 파일이 성공적으로 저장되었습니다.")