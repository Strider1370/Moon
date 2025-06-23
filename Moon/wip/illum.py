import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from calculate2 import get_illuminance_at
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map
import multiprocessing

def compute_r(args):
    year, month, day, hour, lat, lon = args
    return get_illuminance_at(year, month, day, hour, 0, lat, lon)

def main():
    # 1) 원본 CSV 경로 설정
    in_csv = os.path.join("assets", "clouds", "2025060917", "clouds_all_2025060917.csv")
    df_orig = pd.read_csv(in_csv)

    # 2) 메타 컬럼 및 시간 컬럼 분리
    meta_cols = ["x", "y", "lat", "lon", "NTL"]
    time_cols = [c for c in df_orig.columns if c not in meta_cols]

    # 3) 출력용 DataFrame 초기화
    df_r = df_orig[meta_cols].copy()
    df_w = df_r.copy()

    # 4) 시간별 루프에 tqdm 적용
    for tmef in tqdm(time_cols, desc="Processing time steps"):
        # 원본 구름값
        cloud_vals = df_orig[tmef].astype(int).tolist()

        # KST → UTC 변환
        kst_dt = datetime.strptime(tmef, "%Y%m%d%H")
        utc_dt = kst_dt.replace(tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc)
        year, month, day, hour = utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour

        # 5) 격자점별 조도 계산 병렬 처리
        args_list = [(year, month, day, hour, lat, lon)
                     for lat, lon in zip(df_r.lat, df_r.lon)]
        r_vals = process_map(
            compute_r,
            args_list,
            max_workers=multiprocessing.cpu_count(),
            chunksize=1,  # 한 번에 한 작업씩 분배
            desc=f"  Computing R for {tmef}"
        )
        df_r[tmef] = r_vals

        # 6) 구름 가중치 적용 (1→1.0, 3→0.5, 4→0.2, 기타→1.0)
        weight_map = {1: 1.0, 3: 0.5, 4: 0.2}
        df_w[tmef] = [rv * weight_map.get(cv, 1.0)
                      for rv, cv in zip(r_vals, cloud_vals)]

    # 7) 결과 저장
    out_dir = os.path.dirname(in_csv)
    df_r.to_csv(os.path.join(out_dir, "r_light.csv"), index=False)
    df_w.to_csv(os.path.join(out_dir, "r_light_weighted.csv"), index=False)
    print(f"Saved files:\n - {os.path.join(out_dir, 'r_light.csv')}\n - {os.path.join(out_dir, 'r_light_weighted.csv')}")

if __name__ == "__main__":
    main()
