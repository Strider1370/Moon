# grouping.py

import pandas as pd
import numpy as np

def main():
    # 1) 파일 경로 설정
    input_csv  = "viirs_ntl_land_only.csv"             # 원본: Latitude,Longitude,Nighttime_Lights,Flag
    output_csv = "fine_with_groups.csv"  # 결과물

    # 2) 원본 읽기
    df = pd.read_csv(input_csv)  # cols: Latitude,Longitude,Nighttime_Lights,Flag

    # 3) 원본에 그룹 태그 붙이기 (0.1° 구간 하한값)
    df["lat_group"] = np.floor(df["Latitude"]  * 10) / 10
    df["lon_group"] = np.floor(df["Longitude"] * 10) / 10

    # 4) 코어스 그리드(0.1°×0.1° 전체 격자) 생성
    lons = np.round(np.arange(125.0, 130.0 + 1e-6, 0.1), 1)
    lats = np.round(np.arange(32.5,  38.5 + 1e-6, 0.1), 1)
    # 모든 조합 DataFrame
    full = pd.DataFrame(
        [(lat, lon) for lon in lons for lat in lats],
        columns=["lat_group", "lon_group"]
    )

    # 5) 원본에 이미 있는 태그 조합
    existing = df[["lat_group","lon_group"]].drop_duplicates()

    # 6) 빠진(새로 추가할) 태그 조합
    missing = full.merge(
        existing,
        on=["lat_group","lon_group"],
        how="left",
        indicator=True
    )
    missing = missing[missing["_merge"] == "left_only"][["lat_group","lon_group"]]

    # 7) missing 조합을 실제 행으로 확장
    new_rows = missing.copy()
    new_rows["Latitude"]          = new_rows["lat_group"]
    new_rows["Longitude"]         = new_rows["lon_group"]
    new_rows["Nighttime_Lights"]  = 0
    new_rows["Flag"]              = 0

    # 8) 컬럼 순서 맞춰서 정리
    #    원본 df의 컬럼 순서를 그대로 따르기 위해
    cols = ["Latitude","Longitude","Nighttime_Lights","Flag","lat_group","lon_group"]
    df_out = pd.concat([
        df[cols],
        new_rows[cols]
    ], ignore_index=True)

    # 9) 결과 저장
    df_out.to_csv(output_csv, index=False)
    print(f"✅ '{output_csv}' 생성 완료: 원본 {len(df)}행 + 추가 {len(new_rows)}행 → 총 {len(df_out)}행")

if __name__ == "__main__":
    main()
