import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# 0) 설정
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
vars = "SKY"

# 세션 설정
session = requests.Session()

# 클라우드 API 실행 함수
def run_cloud_api(tmfc, tmfc_datetime, tmfc_hour):
    # 1) 예보기간 종료 시각 계산
    if tmfc_hour in [2, 5, 8, 11, 14]:
        end_dt = (tmfc_datetime + timedelta(days=4)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        end_dt = (tmfc_datetime + timedelta(days=5)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # 2) tmef 리스트 생성 (tmfc+1h부터 end_dt까지 1시간 단위)
    tmef_list = []
    current = tmfc_datetime + timedelta(hours=1)
    while current <= end_dt:
        tmef_list.append(current.strftime("%Y%m%d%H"))
        current += timedelta(hours=1)

    # 3) 원하는 시간대만 필터링: 저녁(18~23시)과 밤~아침(00~08시)
    tmef_list = [t for t in tmef_list if (int(t[-2:]) >= 18 or int(t[-2:]) <= 8)]

    # 4) 포인트 불러오기
    points_df = pd.read_csv("points_with_ntl.csv")[["x","y","lat","lon","NTL"]]
    df_all = points_df.copy()

    # 5) API 요청 및 결과 병합 준비
    new_cols = {}
    for tmef in tmef_list:
        time.sleep(0.5)
        url = (
            f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/"
            f"nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}"
            f"&vars={vars}&authKey={service_key}"
        )
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"API 요청 실패: {tmef} → {e}")
            continue

        data = [float(s) for s in resp.text.replace("\n", ",").split(",") if s.strip()]
        two_d = [data[i:i+149] for i in range(0, len(data), 149)]
        values = [two_d[int(row.y)-1][int(row.x)-1] for _, row in df_all.iterrows()]
        new_cols[tmef] = values
        print(f"Processed tmef={tmef}")

    # 6) 결과 병합
    if new_cols:
        df_new = pd.DataFrame(new_cols, index=df_all.index)
        df_all = pd.concat([df_all, df_new], axis=1)

    # 7) 저장
    out_dir = f"assets/clouds/{tmfc}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"clouds_all_{tmfc}.csv")
    df_all.to_csv(out_path, index=False)
    print(f"Saved combined CSV: {out_path}")

# 메인 실행부
def main():
    tmfc = input("Enter TMFC (YYYYMMDDHH): ")
    tmfc_datetime = datetime.strptime(tmfc, "%Y%m%d%H")
    tmfc_hour = tmfc_datetime.hour
    run_cloud_api(tmfc, tmfc_datetime, tmfc_hour)

if __name__ == "__main__":
    main()
