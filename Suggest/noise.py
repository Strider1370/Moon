import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# 1. 대한민국 행정구역 shapefile (시도 경계) 읽기
# shapefile의 파일명이 "ctprvn.shp"라고 가정합니다.
gdf_ctprvn = gpd.read_file('ctprvn.shp')

# shapefile에 CRS 정보가 없으면 수동으로 GRS80 UTM-K / EPSG:5179를 설정합니다.
if gdf_ctprvn.crs is None:
    gdf_ctprvn.set_crs(epsg=5179, inplace=True)

# CSV 데이터는 일반적으로 위경도(WGS84, EPSG:4326)로 되어 있으므로, shapefile을 WGS84로 변환합니다.
gdf_ctprvn = gdf_ctprvn.to_crs(epsg=4326)

# (필요시) 폴리곤의 유효성 보정을 위해 버퍼(0)를 적용합니다.
gdf_ctprvn["geometry"] = gdf_ctprvn.geometry.buffer(0)

# 2. CSV 파일 읽기 및 GeoDataFrame 생성
df = pd.read_csv('viirs_ntl_500m_filtered.csv')
# CSV 파일은 최소한 'Latitude', 'Longitude', 'Nighttime_Lights' 컬럼이 포함되어 있어야 합니다.
geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
gdf_ntl = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# 3. left 방식 공간 조인: 모든 CSV 포인트는 유지하면서 행정구역 폴리곤과 교차하는지 확인합니다.
# predicate='intersects'를 사용하여, 포인트가 폴리곤과 교차하는 경우 join 결과에 해당 폴리곤 정보가 담깁니다.
gdf_joined = gpd.sjoin(gdf_ntl, gdf_ctprvn, how='left', predicate='intersects')

# 4. 행정구역 외에 해당하는(즉, join 결과가 없는) 포인트의 Nighttime_Lights 값을 0으로 변경
# 일반적으로 공간 조인 결과, 행정구역에 포함되면 'index_right' 값이 부여되며, 그렇지 않으면 NaN입니다.
gdf_joined.loc[gdf_joined['index_right'].isna(), 'Nighttime_Lights'] = 0

# (옵션) join 과정에서 추가된 컬럼(index_right, 그리고 shapefile의 속성들)이 필요하지 않으면 제거할 수 있습니다.
columns_to_keep = ['Latitude', 'Longitude', 'Nighttime_Lights']
result = gdf_joined[columns_to_keep]

# 5. 결과 CSV 파일로 저장
result.to_csv('viirs_ntl_masked.csv', index=False)
print("행정구역 외부 포인트의 야간 조명 값이 0으로 설정된 CSV 파일 'viirs_ntl_masked.csv'가 생성되었습니다.")
