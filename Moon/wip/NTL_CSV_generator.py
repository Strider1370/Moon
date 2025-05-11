#!/usr/bin/env python3
import math
import ssl
import h5py
import numpy as np
import pandas as pd

# ─── 1) 관심 영역 (포함) ───────────────────────────────────────
LAT_MIN, LAT_MAX = 31.5, 39.5
LON_MIN, LON_MAX = 124.0, 131.0

# ─── 2) KMA 동네예보 격자 투영 파라미터 ───────────────────────
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
RE   = 6371.00877      # 지구 반경 (km)
GRID = 5.0             # 격자 간격 (km)
SLAT1 = 30.0 * DEG2RAD
SLAT2 = 60.0 * DEG2RAD
OLON  = 126.0 * DEG2RAD
OLAT  = 38.0 * DEG2RAD
XO, YO = 43, 136       # 기준격자점 X/Y
NX, NY = 149, 253      # 격자 크기

# 투영 상수 계산
sn = math.log(math.cos(SLAT1)/math.cos(SLAT2)) / \
     math.log(math.tan(math.pi*0.25+SLAT2*0.5) / math.tan(math.pi*0.25+SLAT1*0.5))
sf = (math.tan(math.pi*0.25+SLAT1*0.5)**sn * math.cos(SLAT1)) / sn
ro = (RE/GRID) * sf / (math.tan(math.pi*0.25+OLAT*0.5)**sn)

def grid_to_latlon(x: int, y: int):
    """격자(x, y) → (lat, lon) 변환"""
    dx = x - XO
    dy = ro - (y - YO)
    ra = math.hypot(dx, dy)
    if sn < 0: ra = -ra
    alat = 2.0 * math.atan((RE/GRID * sf / ra)**(1.0/sn)) - math.pi/2.0
    theta = math.atan2(dx, dy) if abs(dx) >= 1e-7 else 0.0
    alon = theta/sn + OLON
    return alat * RAD2DEG, alon * RAD2DEG

def find_nearest_idx(vec: np.ndarray, value: float) -> int:
    """1D 배열에서 value와 가장 가까운 인덱스 반환"""
    return np.abs(vec - value).argmin()

def main():
    # ─── (1) 격자 → 위경도 생성 ────────────────────────────────────
    records = []
    for y in range(1, NY+1):
        for x in range(1, NX+1):
            lat, lon = grid_to_latlon(x, y)
            if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                records.append({'x': x, 'y': y, 'lat': lat, 'lon': lon})
    points = pd.DataFrame(records)

    # ─── (2) HDF5 파일 열기 (SSL 인증 무시) ─────────────────────────
    ssl._create_default_https_context = ssl._create_unverified_context
    h5_path = 'VNP46A2.A2025080.h30v05.002.2025088135600.h5'
    with h5py.File(h5_path, 'r') as f:
        lat_arr = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lat'][:]
        lon_arr = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/lon'][:]
        ntl     = f['HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/Gap_Filled_DNB_BRDF-Corrected_NTL'][:]

    # ─── (3) NTL 클리핑 및 이진 변환 ─────────────────────────────────
    ntl = np.clip(ntl, 0, 100)

    def lookup_flag(row):
        i = find_nearest_idx(lat_arr, row['lat'])
        j = find_nearest_idx(lon_arr, row['lon'])
        return 1 if ntl[i, j] >= 20 else 0

    points['NTL'] = points.apply(lookup_flag, axis=1)

    # ─── (4) 결과 저장 ───────────────────────────────────────────────
    output_csv = 'points_with_ntl.csv'
    points.to_csv(output_csv, index=False, float_format='%.6f')
    print(f"✅ {len(points)}개 지점에 대해 NTL_flag를 추가하여 '{output_csv}'에 저장했습니다.")

if __name__ == "__main__":
    main()
