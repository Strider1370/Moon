# 지도 파일을 불러오기
import geopandas as gpd
import os

# 현재 파일의 디렉토리 경로를 가져옵니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
shapefile_path = os.path.join(current_dir, "map3.shp")

# .shp 파일을 불러옵니다.
gdf = gpd.read_file(shapefile_path)

# 지도 경계 확인
x_min, y_min, x_max, y_max = gdf.total_bounds
print(f"지도 경계: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")

# 이 경계 값을 extent로 설정
extent = [x_min, x_max, y_min, y_max]