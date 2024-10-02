# api/CLOUDS.py
import os
import numpy as np
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from datetime import datetime, timedelta

# 서비스 키 및 변수 설정
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
vars = "SKY"

# 현재 UTC 시간
now_utc = datetime.utcnow()

# 한국 표준시로 변환
now_kst = now_utc + timedelta(hours=9)

# 발표 시간 리스트 (시간만)
release_hours = [2, 5, 8, 11, 14, 17, 20, 23]

# 현재 날짜와 발표 시간 조합하여 datetime 객체 생성
release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)

# 발표 시간 중 가장 최근의 시간 선택
tmfc_datetime = max([rt for rt in release_times if rt <= now_kst])
tmfc_short_term = tmfc_datetime.strftime('%Y%m%d%H')  # 단기예보용 tmfc
tmfc_very_short_term = tmfc_datetime.strftime('%Y%m%d%H') + "00"  # 초단기예보용 tmfc (뒤에 "00" 추가)

# tmef 리스트 생성 (tmfc보다 1시간 후부터 24시간 후까지)
tmef_datetimes = [tmfc_datetime + timedelta(hours=i) for i in range(1, 25)]
tmef_list = [dt.strftime('%Y%m%d%H') for dt in tmef_datetimes]

# API 요청 URL 설정 함수 (단기 예보)
def get_short_term_api_url(tmfc_short_term, tmef):
    return f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_shrt_grd?tmfc={tmfc_short_term}&tmef={tmef}&vars={vars}&authKey={service_key}"

# API 요청 URL 설정 함수 (초단기 예보)
def get_very_short_term_api_url(tmfc_very_short_term, tmef):
    return f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_vsrt_grd?tmfc={tmfc_very_short_term}&tmef={tmef}&vars={vars}&authKey={service_key}"

# API 요청 보내기 함수
def call_api(api_url):
    response = requests.get(api_url)
    return response

# API 호출 및 응답 확인 함수
def check_response(response):
    if response.status_code == 200:
        data = response.text
        if "SERVICE ERROR" in data or "NO_OPENAPI_SERVICE_ERROR" in data:
            return False, data
        return True, data
    return False, None

# .shp 파일 경로 설정 
shapefile_path = "map3.shp"  

# .shp 파일을 geopandas로 읽어오기
try:
    gdf = gpd.read_file(shapefile_path)
except Exception as e:
    print(f"지도 파일을 읽을 수 없습니다: {e}")
    exit()

# 좌표 설정
#x_min, x_max = gdf.total_bounds[0], gdf.total_bounds[2]
#y_min, y_max = gdf.total_bounds[1], gdf.total_bounds[3]
#extent = [x_min, x_max, y_min, y_max]
extent = [123.3102, 132.7750, 31.6518, 43.3935]

# 데이터 값과 인덱스 매핑
value_to_index = {
    -999.0: 0,
    1.0: 1,
    3.0: 2,
    4.0: 3
}

# 색상 및 컬러맵 설정
colors = ['darkgray', 'white', 'blue', 'darkblue']
cmap = ListedColormap(colors)

# 이미지 저장 경로 설정 (api 폴더 기준, assets 폴더는 프로젝트 루트에 있음)
image_dir = "../assets/cloud_images"
if not os.path.exists(image_dir):
    os.makedirs(image_dir)

# tmef_list를 파일로 저장
tmef_list_path = os.path.join(image_dir, 'tmef_list.txt')
with open(tmef_list_path, 'w') as f:
    for tmef in tmef_list:
        f.write(f"{tmef}\n")

# 각 tmef에 대해 데이터를 요청하고 이미지 저장
for idx, tmef in enumerate(tmef_list):
    # 초단기예보 시간대 
    if 1 <= idx + 1 <= 5:
        api_url = get_very_short_term_api_url(tmfc_very_short_term, tmef)
    # 단기예보 시간대 
    else:
        api_url = get_short_term_api_url(tmfc_short_term, tmef)

    response = call_api(api_url)

    if response.status_code == 200:
        data = response.text
        data = data.replace("\n", "").split(",")
        data = [float(val.strip()) for val in data if val.strip()]
        
        # 초단기예보 데이터에서 -99.00 값을 -999.00으로 통일
        if 1 <= idx + 1 <= 6:
            data = [-999.00 if val == -99.00 else val for val in data]

        # 1차원 배열을 좌측 하단에서부터 우측 상단 순서로 채우기 위해 행을 뒤집는다
        # 이때 먼저 253행, 149열 배열로 만든 후 행을 뒤집는다
        grid_data = np.array(data).reshape(253, 149)[::-1, :]

        # 인덱스 배열 생성
        index_grid_data = np.full_like(grid_data, -1, dtype=int)
        for val, idx_val in value_to_index.items():
            index_grid_data[grid_data == val] = idx_val

        # 그림 생성 및 저장, origin을 upper로 하여 왼쪽 위부터 배열(?)
        fig, ax = plt.subplots(figsize=(10, 8))
        gdf.plot(ax=ax, linewidth=0.5, edgecolor='black')
        im = ax.imshow(index_grid_data, extent=extent, origin='upper', cmap=cmap, interpolation='none', alpha=0.6)
        ax.set_title(f"Time: {tmef}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        # 이미지 파일명 설정 (tmef 시간을 파일명에 반영)
        image_filename = f"cloud_image_{tmef}.png"
        image_path = os.path.join(image_dir, image_filename)

        # 이미지 저장
        plt.savefig(image_path, bbox_inches='tight')
        plt.close(fig)

        print(f"Saved {image_filename}")
    else:
        print(f"{tmef}에 대한 데이터를 가져올 수 없습니다: {response.status_code}")