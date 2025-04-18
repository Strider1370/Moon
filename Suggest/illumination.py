# illumination.py

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from calculate import get_illuminance_at

def main():
    # 1) 기본 설정
    year, month, day = 2025, 4, 14
    input_csv  = "grid_info.csv"   # CSV: lon, lat, (그 외 컬럼은 무시)
    output_dir = "assets"
    os.makedirs(output_dir, exist_ok=True)

    # 2) 시간 범위 (UTC 기준)
    start_utc = datetime(year, month, day, 13)
    end_utc   = datetime(year, month, day, 20)

    # 3) CSV 읽기: lon / lat 만 사용
    df_base = pd.read_csv(
        input_csv,
        header=None,
        usecols=[0, 1],
        names=["lon", "lat"]
    )

    overall_t0 = time.perf_counter()
    current_utc = start_utc

    # 4) 한 시간 간격 루프
    while current_utc <= end_utc:
        tic = time.perf_counter()

        # (A) UTC 기준으로 조도 계산
        df = df_base.copy()
        df["lux"] = df.apply(
            lambda r: get_illuminance_at(
                current_utc.year,
                current_utc.month,
                current_utc.day,
                current_utc.hour,
                current_utc.minute,
                r["lon"],   # latitude
                r["lat"]    # longitude
            ),
            axis=1
        )

        # (B) KST 변환 및 파일명 생성
        kst_time = current_utc + timedelta(hours=9)
        fname = kst_time.strftime("%Y%m%d%H.csv")

        # (C) CSV 저장 (열 순서: lon, lat, lux)
        df.to_csv(
            os.path.join(output_dir, fname),
            columns=["lon", "lat", "lux"],
            index=False
        )

        # (D) 콘솔 출력도 KST 기준으로
        elapsed = time.perf_counter() - tic
        print(f"[{kst_time:%Y-%m-%d %H:%M} KST] → {fname}  ({elapsed:.2f}s)")

        current_utc += timedelta(hours=1)

    total_elapsed = time.perf_counter() - overall_t0
    print(f"\n전체 처리 시간: {total_elapsed:.2f}s")

if __name__ == "__main__":
    main()
