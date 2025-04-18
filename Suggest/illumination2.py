# illumination.py

import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from calculate import get_illuminance_at

def main():
    # 1) 설정
    year, month, day = 2025, 4, 14
    input_csv  = "fine_with_groups.csv"   # 원본: Latitude,Longitude,Nighttime_Lights,Flag
    output_dir = "assets"
    os.makedirs(output_dir, exist_ok=True)

    # 2) 시간 범위 (UTC 기준)
    start_utc = datetime(year, month, day, 13)
    end_utc   = datetime(year, month, day, 14)

    # 3) 원본 CSV 읽기 (4개 컬럼 모두)
    df = pd.read_csv(input_csv)  # cols: Latitude,Longitude,Nighttime_Lights,Flag

    # 4) 0.1°×0.1° 그룹 태그를 계산해 컬럼 추가
    #    각 격자가 속하는 구간의 하한값을 태그로 사용
    df["lat_group"] = np.floor(df["Latitude"]  * 10) / 10
    df["lon_group"] = np.floor(df["Longitude"] * 10) / 10

    # 5) 고유 그룹(tag) 목록만 추출
    groups = df[["lat_group", "lon_group"]].drop_duplicates().reset_index(drop=True)

    overall_start = time.perf_counter()
    current_utc = start_utc

    # 6) 시간별 루프
    while current_utc <= end_utc:
        t0 = time.perf_counter()

        # 6-A) 그룹별 조도 계산 (한 번씩만)
        coarse = {}
        for _, row in groups.iterrows():
            lg = row["lat_group"]
            ln = row["lon_group"]
            coarse[(lg, ln)] = get_illuminance_at(
                current_utc.year,
                current_utc.month,
                current_utc.day,
                current_utc.hour,
                current_utc.minute,
                lg,  # latitude tag
                ln   # longitude tag
            )

        # 6-B) dict → DataFrame
        df_coarse = pd.DataFrame([
            {"lat_group": k[0], "lon_group": k[1], "lux": v}
            for k, v in coarse.items()
        ])

        # 6-C) 원본에 병합
        df_out = df.merge(df_coarse, on=["lat_group", "lon_group"], how="left")

        # 6-D) 파일명 (KST 기준)
        kst = current_utc + timedelta(hours=9)
        fname = kst.strftime("%Y%m%d%H.csv")

        # 6-E) 결과 저장
        #    원본 4개 + lat_group, lon_group, lux 총 7개 컬럼 순서 유지
        df_out.to_csv(
            os.path.join(output_dir, fname),
            columns=[
                "Latitude","Longitude","Nighttime_Lights","Flag",
                "lat_group","lon_group","lux"
            ],
            index=False
        )

        elapsed = time.perf_counter() - t0
        print(f"[{kst:%Y-%m-%d %H:%M} KST] {fname} saved ({elapsed:.2f}s)")

        current_utc += timedelta(hours=1)

    total = time.perf_counter() - overall_start
    print(f"\n전체 처리 시간: {total:.2f}s")


if __name__ == "__main__":
    main()
