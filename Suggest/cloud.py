import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

service_key = "boxdzlyoTGWMXc5cqDxlQQ"
vars = "SKY"

# 1) 기준 시각(tmfc) & 유효 시각 목록(tmef_list) 계산 (기존 코드 그대로)
now_utc = datetime.now(timezone.utc)
now_kst = now_utc + timedelta(hours=9)
release_hours = [2,5,8,11,14,17,20,23]
release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)
tmfc_datetime = max(rt for rt in release_times if rt <= now_kst)
tmfc = tmfc_datetime.strftime('%Y%m%d%H')
tmfc_hour = tmfc_datetime.hour

if tmfc_hour in [2,5,8,11,14]:
    days_ahead = 2
else:
    days_ahead = 3
start_dt = tmfc_datetime + timedelta(hours=1)
end_dt = tmfc_datetime.replace(hour=23, minute=0) + timedelta(days=days_ahead)
hours = int((end_dt - start_dt).total_seconds() // 3600) + 1
tmef_list = [(start_dt + timedelta(hours=i)).strftime('%Y%m%d%H') for i in range(hours)]

# 2) 필터된 격자 파일 읽기
grid_df = pd.read_csv('grid_latlon_filtered.csv')  # 컬럼: X, Y, latitude, longitude

def Clouds_api_hourly(tmfc, tmef_list, grid_df):
    out_folder = f'assets/clouds/{tmfc}'
    os.makedirs(out_folder, exist_ok=True)

    for tmef in tmef_list:
        # 1시간 단위 API 호출
        url = (
            f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"
            f"nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}"
            f"&vars={vars}&authKey={service_key}"
        )
        resp = requests.get(url, verify=False)
        data = [float(s) for s in resp.text.replace('\n',',').split(',') if s.strip()]

        # 149열씩 2D 리스트로 재구성
        two_d = [data[i:i+149] for i in range(0, len(data), 149)]

        # 필터된 격자점별로 cloud 값만 뽑아서 DataFrame에 추가
        df = grid_df.copy()
        df['cloud'] = df.apply(lambda r: two_d[int(r.Y)-1][int(r.X)-1], axis=1)

        # tmef별 파일로 저장
        out_path = f'{out_folder}/{tmef}_grid_filtered_clouds.csv'
        df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")

# 3) 실행
Clouds_api_hourly(tmfc, tmef_list, grid_df)
