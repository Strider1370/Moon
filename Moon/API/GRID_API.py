import requests
import datetime

service_key = "boxdzlyoTGWMXc5cqDxlQQ"
lat = 37.5665
lon = 126.9780
api_url = f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_xy_lonlat?lon={lon}&lat={lat}&authKey={service_key}&help=0"

# API 요청
response = requests.get(api_url)

# 요청이 성공했는지 확인
if response.status_code == 200:
    # 응답 데이터 텍스트
    data = response.text
    print("API 응답 데이터:", data)
    
    # 응답 데이터 파싱
    lines = data.splitlines()  # 줄 단위로 분리
    if len(lines) > 2:  # 두 번째 줄에 필요한 값이 있음
        # 두 번째 줄에서 공백을 기준으로 분리 후 쉼표로 나누기
        values = lines[2].split(",")
        
        # X와 Y 추출
        lon = values[0].strip()  # 경도
        lat = values[1].strip()  # 위도
        x = values[2].strip()    # 격자 X
        y = values[3].strip()    # 격자 Y
        
        # 출력
        print(f"격자 좌표 X: {x}, Y: {y}")
    else:
        print("데이터 형식이 예상과 다릅니다.")
else:
    print(f"API 요청 실패: {response.status_code}")