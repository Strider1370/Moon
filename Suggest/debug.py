import time
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# 1. CSV 파일 읽기
df = pd.read_csv('viirs_ntl_500m_filtered.csv')

# 서울 지역의 대략적인 경계 값 (필요에 따라 조정하세요)
min_lon, max_lon = 126.8, 127.2
min_lat, max_lat = 37.4, 37.7

# CSV 데이터 중 서울 지역에 해당하는 데이터만 필터링
df_seoul = df[(df['Longitude'] >= min_lon) & (df['Longitude'] <= max_lon) &
              (df['Latitude'] >= min_lat) & (df['Latitude'] <= max_lat)]
print("서울 지역 데이터 건수:", len(df_seoul))

# 2. 필터링된 CSV 데이터 샘플로 GeoDataFrame 생성
# 모든 행을 사용해도 되고, 일부만 사용하고 싶으면 df_seoul.head(100) 등을 사용할 수 있습니다.
geometry_seoul = [Point(xy) for xy in zip(df_seoul['Longitude'], df_seoul['Latitude'])]
gdf_ntl_seoul = gpd.GeoDataFrame(df_seoul, geometry=geometry_seoul, crs="EPSG:4326")

print("=== 서울 GeoDataFrame ===")
print(gdf_ntl_seoul.head())
print("서울 샘플 포인트 유효성 (True 비율):", gdf_ntl_seoul.geometry.is_valid.mean())

# 3. 대한민국 시도경계 shapefile 읽기 및 CRS 변환
gdf_kor = gpd.read_file('ctprvn.shp')
if gdf_kor.crs is None:
    print("Shapefile CRS 없음. EPSG:5179로 수동 설정합니다.")
    gdf_kor.set_crs(epsg=5179, inplace=True)
gdf_kor = gdf_kor.to_crs(epsg=4326)
print("=== Shapefile 데이터 (GeoDataFrame) ===")
print(gdf_kor.head())

# 폴리곤 유효성 검사 및 보정 (필요하면)
gdf_kor["is_valid"] = gdf_kor.geometry.is_valid
print("보정 전 유효하지 않은 폴리곤 수:", (~gdf_kor["is_valid"]).sum())
gdf_kor["geometry"] = gdf_kor.geometry.buffer(0)
gdf_kor["is_valid"] = gdf_kor.geometry.is_valid
print("보정 후 유효하지 않은 폴리곤 수:", (~gdf_kor["is_valid"]).sum())

# 4. 서울 지역 포인트와 시도 폴리곤 간의 공간 조인 디버깅
start_time = time.time()
try:
    # 서울 지역 포인트가 어느 시도(혹은 시군구) 폴리곤과 교차하는지 확인합니다.
    gdf_ntl_land_seoul = gpd.sjoin(gdf_ntl_seoul, gdf_kor, how='inner', predicate='intersects')
    print("서울 지역 공간 조인 후 남은 포인트 수:", len(gdf_ntl_land_seoul))
    print(gdf_ntl_land_seoul.head())
except Exception as e:
    print("공간 조인 실패:", e)
end_time = time.time()
print("서울 지역 공간 조인 처리 시간 (초):", end_time - start_time)
