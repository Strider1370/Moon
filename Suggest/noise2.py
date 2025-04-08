import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# 1. 대한민국 행정구역 shapefile (시도 경계) 읽기
# shapefile의 이름은 ctprvn.shp로 가정합니다.
gdf_ctprvn = gpd.read_file('ctprvn.shp')

# shapefile에 좌표계 정보가 없다면, 수동으로 GRS80 UTM-K / EPSG:5179로 설정합니다.
if gdf_ctprvn.crs is None:
    gdf_ctprvn.set_crs(epsg=5179, inplace=True)

# CSV 데이터는 위경도(WGS84, EPSG:4326)를 사용할 것이므로, shapefile을 WGS84로 변환합니다.
gdf_ctprvn = gdf_ctprvn.to_crs(epsg=4326)

# (선택 사항) 폴리곤 유효성 보정: buffer(0)을 적용하여 잘못된 geometry를 수정합니다.
gdf_ctprvn["geometry"] = gdf_ctprvn.geometry.buffer(0)

# 2. CSV 파일 읽기 (CSV 파일에는 'Latitude', 'Longitude', 'Nighttime_Lights' 컬럼이 존재)
df = pd.read_csv('viirs_ntl_500m_filtered.csv')

# CSV 데이터 범위 (예: 대한민국 영역 내 데이터) 확인
print("CSV 데이터 범위:")
print("Longitude:", df["Longitude"].min(), "-", df["Longitude"].max())
print("Latitude:", df["Latitude"].min(), "-", df["Latitude"].max())

# 3. CSV 데이터의 각 행에 대해 Point 객체 생성 후 GeoDataFrame으로 변환
geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
gdf_ntl = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# 4. 공간 조인: 각 포인트가 행정구역(시도 경계) 폴리곤 내부에 있는지 확인하여, 내부에 있는 데이터만 남김
gdf_ntl_land = gpd.sjoin(gdf_ntl, gdf_ctprvn, how='inner', predicate='intersects')

# 5. Flag 열 추가: Nighttime_Lights가 30 이상이면 1, 30 미만이면 0
gdf_ntl_land["Flag"] = (gdf_ntl_land["Nighttime_Lights"] >= 30).astype(int)

# 6. 최종 결과 저장: 원래 CSV 컬럼들과 Flag 열, 그리고 좌표정보(geometry) 등 필요한 부분만 선택.
columns_to_save = ['Latitude', 'Longitude', 'Nighttime_Lights', 'Flag']
gdf_ntl_land[columns_to_save].to_csv('viirs_ntl_land_only.csv', index=False)

print("행정구역(시도 경계) 내부에 해당하는 데이터에 Flag 열이 추가된 CSV 파일 'viirs_ntl_land_only.csv'가 생성되었습니다.")
