# illumination.py

import os
import time
import pandas as pd
from datetime import datetime, timedelta

# calculate.py에 정의된 함수 불러오기
from calculate import get_illuminance_at

def main():
    """
    예시:
    2025-04-09 KST 18:00 ~ 2025-04-10 KST 08:00 사이(한 시간 간격)  
    CSV로부터 위도, 경도 데이터를 읽어서, 각 지점의 조도값을 계산 후 
    (Illuminance 컬럼 추가) 각 시간대별 CSV 파일로 저장합니다.
    
    또한 각 파일의 처리 소요 시간을 콘솔에 출력합니다.
    """

    # -------------------------
    # 1) 사용자 입력(예시)
    # -------------------------
    # 계산할 '기준일' (KST)
    year = 2025
    month = 4
    day = 9

    # 읽어들일 CSV 파일 경로 (위치 데이터가 포함된 파일)
    input_csv = "viirs_ntl_land_only.csv"

    # 결과 CSV를 저장할 폴더
    output_folder = "assets"
    os.makedirs(output_folder, exist_ok=True)

    # -------------------------
    # 2) 시간 범위 설정 (KST)
    # -------------------------
    start_kst = datetime(year, month, day, 18, 0, 0)      # 당일 18:00 KST
    end_kst   = datetime(year, month, day + 1, 8, 0, 0)     # 다음날 08:00 KST

    # -------------------------
    # 3) CSV 파일 읽기
    # -------------------------
    # CSV 파일은 최소한 Latitude, Longitude 컬럼이 있어야 합니다.
    df_base = pd.read_csv(input_csv)

    # 전체 처리 시작 시간 측정
    overall_start = time.perf_counter()

    # -------------------------
    # 4) 한 시간 간격으로 루프
    # -------------------------
    current_kst = start_kst
    while current_kst <= end_kst:
        # 각 파일 처리 전 시간 측정
        file_start = time.perf_counter()

        # (A) current_kst(한국 시각)를 UTC로 변환 (KST = UTC +9 → UTC = KST - 9)
        current_utc = current_kst - timedelta(hours=9)

        # (B) 원본 DataFrame 복사 후 조도 계산 (Illuminance 컬럼 추가)
        df = df_base.copy()

        df["Illuminance"] = df.apply(
            lambda row: get_illuminance_at(
                current_utc.year,
                current_utc.month,
                current_utc.day,
                current_utc.hour,
                current_utc.minute,
                row["Latitude"],
                row["Longitude"]
            ),
            axis=1
        )

        # (C) 파일 이름 생성 (예: 2025-04-09_18.csv)
        filename = f"{year:04d}-{month:02d}-{day:02d}_{current_kst.hour:02d}.csv"
        output_path = os.path.join(output_folder, filename)

        # (D) CSV 파일 저장
        df.to_csv(output_path, index=False)

        # 파일 처리 후 시간 측정
        file_end = time.perf_counter()
        elapsed = file_end - file_start

        print(f"[{current_kst.strftime('%Y-%m-%d %H:%M:%S')} KST] 파일 저장 완료 -> {output_path} (소요 시간: {elapsed:.2f}초)")

        # (E) 다음 시간으로 1시간 증가
        current_kst += timedelta(hours=1)

    overall_end = time.perf_counter()
    total_elapsed = overall_end - overall_start
    print(f"\n전체 처리 완료 (총 소요 시간: {total_elapsed:.2f}초)")

if __name__ == "__main__":
    main()
