import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import argparse

# 0) 설정
service_key   = "boxdzlyoTGWMXc5cqDxlQQ"
vars          = "SKY"
release_hours = [2, 5, 8, 11, 14, 17, 20, 23]

# 1) 기준 시각(tmfc) 계산
now_utc = datetime.now(timezone.utc)
now_kst = now_utc + timedelta(hours=9)

# 기상청 릴리즈 시각 후보 생성
release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)

# 가장 최근 릴리즈 시각
tmfc_datetime = max(rt for rt in release_times if rt <= now_kst)
tmfc          = tmfc_datetime.strftime("%Y%m%d%H")
tmfc_hour     = tmfc_datetime.hour

def run_cloud_api(tmfc, tmfc_datetime, tmfc_hour):
    # 2) 예보 기간 계산
    if tmfc_hour in [2,5,8,11,14]:
        days_ahead = 2
    else:
        days_ahead = 3

    start_dt = tmfc_datetime + timedelta(hours=1)
    end_dt   = tmfc_datetime.replace(hour=23, minute=0) + timedelta(days=days_ahead)
    hours    = int((end_dt - start_dt).total_seconds() // 3600) + 1

    tmef_list = [
        (start_dt + timedelta(hours=i)).strftime("%Y%m%d%H")
        for i in range(hours)
    ]

    # 3) 포인트(x,y) 불러오기
    points_df = pd.read_csv("points_with_ntl.csv")[["x","y","lat","lon","NTL"]]

    # 4) DataFrame 초기화 (x,y 고정)
    df_all = points_df.copy()

    # 5) 각 tmef별 clouds 값을 새 컬럼으로 추가
    for tmef in tmef_list:
        hour = int(tmef[-2:])
        # 3시간 단위 예보만
        if hour not in release_hours:
            continue

        url = (
            f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"
            f"nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}"
            f"&vars={vars}&authKey={service_key}"
        )
        try:
            resp = requests.get(url, verify=False, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"API 요청 실패: {url}\n{e}")
            continue
        data = [float(s) for s in resp.text.replace("\n", ",").split(",") if s.strip()]
        two_d = [data[i:i+149] for i in range(0, len(data), 149)]

        # point별로 cloud 값 추출
        df_all[tmef] = df_all.apply(lambda r: two_d[int(r.y)-1][int(r.x)-1], axis=1)
        print(f"Processed tmef={tmef}")
        print(f"API 요청: tmfc={tmfc}, tmef={tmef}")

    # 6) 결과 저장
    out_dir = f"assets/clouds/{tmfc}"
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"clouds_all_{tmfc}.csv")
    df_all.to_csv(out_path, index=False)
    print(f"Saved combined CSV: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--tmfc', type=str, default=None, help='TMFC(YYYYMMDDHH) 직접 지정')
    args = parser.parse_args()

    if args.tmfc:
        tmfc = args.tmfc
        tmfc_datetime = datetime.strptime(tmfc, "%Y%m%d%H")
        tmfc_hour = tmfc_datetime.hour
    else:
        now_utc = datetime.now(timezone.utc)
        now_kst = now_utc + timedelta(hours=9)
        release_times = []
        for h in release_hours:
            rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
            if rt > now_kst:
                rt -= timedelta(days=1)
            release_times.append(rt)
        tmfc_datetime = max(rt for rt in release_times if rt <= now_kst)
        tmfc = tmfc_datetime.strftime("%Y%m%d%H")
        tmfc_hour = tmfc_datetime.hour

    run_cloud_api(tmfc, tmfc_datetime, tmfc_hour)
