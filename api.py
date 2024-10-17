import requests
from datetime import datetime, timedelta, timezone
import os

service_key = "boxdzlyoTGWMXc5cqDxlQQ"
lat = 37.5665
lon = 126.9780
vars = "SKY"

# TMFC, TMEF 설정
now_utc = datetime.now(timezone.utc)  # 변경된 부분
now_kst = now_utc + timedelta(hours=9)

release_hours = [2, 5, 8, 11, 14, 17, 20, 23]

release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)

tmfc_datetime = max([rt for rt in release_times if rt <= now_kst])
tmfc = tmfc_datetime.strftime('%Y%m%d%H')

# tmfc 시간 추출
tmfc_hour = tmfc_datetime.hour

# tmef 설정
if tmfc_hour in [2, 5, 8, 11, 14]:
    # 모레 자정까지의 시간 계산
    start_datetime = tmfc_datetime + timedelta(hours=1)  # tmfc 이후 1시간부터 시작
    end_datetime = tmfc_datetime.replace(hour=23, minute=0, second=0, microsecond=0) + timedelta(days=2)  # 모레 자정까지
    tmef_datetimes = [start_datetime + timedelta(hours=i) for i in range((end_datetime - start_datetime).seconds // 3600 + 1 + (end_datetime - start_datetime).days * 24)]
else:  # tmfc_hour가 17, 20, 23시인 경우
    # 글피 자정까지의 시간 계산
    start_datetime = tmfc_datetime + timedelta(hours=1)  # tmfc 이후 1시간부터 시작
    end_datetime = tmfc_datetime.replace(hour=23, minute=0, second=0, microsecond=0) + timedelta(days=3)  # 글피 자정까지
    tmef_datetimes = [start_datetime + timedelta(hours=i) for i in range((end_datetime - start_datetime).seconds // 3600 + 1 + (end_datetime - start_datetime).days * 24)]

tmef_list = [dt.strftime('%Y%m%d%H') for dt in tmef_datetimes]

# Grid API
def Grid_api(lat, lon):
    Grid_api_url = f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_xy_lonlat?lon={lon}&lat={lat}&authKey={service_key}&help=0"

    # API 요청
    response = requests.get(Grid_api_url, verify=False)

    if response.status_code == 200:
        data = response.text

        lines = data.splitlines()
        if len(lines) > 2:
            values = lines[2].split(",")
            if len(values) >= 4:
                lon = values[0].strip()  # 경도
                lat = values[1].strip()  # 위도
                x = values[2].strip()    # x 좌표
                y = values[3].strip()    # y 좌표
                return x, y
            else:
                print("데이터 형식이 예상과 다릅니다. 필드 수가 부족합니다.")
        else:
            print("데이터 형식이 예상과 다릅니다. 줄 수가 부족합니다.")
    else:
        print(f"API 요청 실패: {response.status_code}")

Grid_api(lat, lon)

# Clouds API
def Clouds_api(tmfc, tmef_list):
    # TMFC에 해당하는 폴더 생성
    tmfc_folder_path = f'assets/clouds/{tmfc}'
    if not os.path.exists(tmfc_folder_path):
        os.makedirs(tmfc_folder_path)

    # 저장된 txt 파일들의 목록을 저장할 리스트
    txt_file_list = []

    for tmef in tmef_list:
        Clouds_api_url = f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}&vars={vars}&authKey={service_key}"

        # API 요청
        clouds_url_get = requests.get(Clouds_api_url, verify=False)
        clouds_url_str = clouds_url_get.text

        # 데이터 파싱 및 two_d_list 생성
        data_list = [item.strip() for item in clouds_url_str.replace('\n', ',').split(',') if item.strip()]
        data_list = [float(item) for item in data_list]
        chunk_size = 149
        two_d_list = [data_list[i:i + chunk_size] for i in range(0, len(data_list), chunk_size)]

        # two_d_list를 txt 파일로 저장
        txt_file_path = f'{tmfc_folder_path}/{tmef}.txt'
        with open(txt_file_path, 'w') as f:
            for row in two_d_list:
                row_str = ', '.join(map(str, row))
                f.write(row_str + '\n')

        # 파일 경로를 리스트에 추가
        txt_file_list.append(txt_file_path)

    # txt 파일 리스트를 별도의 txt 파일로 저장
    with open(f'{tmfc_folder_path}/txt_file_list.txt', 'w') as f:
        for file_path in txt_file_list:
            f.write(file_path + '\n')

    return

Clouds_api(tmfc, tmef_list)
