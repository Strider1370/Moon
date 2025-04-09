# illumination.py - 1500 UTC 테스트용 코드

import pandas as pd
from calculate import get_illuminance_at

def main():
    """
    테스트:
    - 입력 CSV 파일("test_locations.csv")은 최소 'Latitude'와 'Longitude' 컬럼을 포함해야 합니다.
    - 이 코드에서는 2025년 4월 9일 15:00 UTC (즉, 1500 UTC)에 대해 조도값(R_light_total)을 계산합니다.
    - 계산된 결과는 원본 데이터에 "Illuminance" 컬럼으로 추가되고,
      "result_1500UTC.csv" 파일로 저장됩니다.
    """

    # 입력 CSV 파일 경로 (테스트용)
    input_csv = "viirs_ntl_land_only.csv"
    # 출력 CSV 파일 경로
    output_csv = "result_1500UTC.csv"
    
    # 테스트 날짜/시간 설정 (UTC 기준)
    utc_year = 2025
    utc_month = 4
    utc_day = 9
    utc_hour = 15
    utc_minute = 0
    
    # CSV 파일 읽기 (CSV 파일은 'Latitude'와 'Longitude' 컬럼을 포함해야 합니다)
    df = pd.read_csv(input_csv)
    
    # 각 행마다 calculate.py의 get_illuminance_at 함수를 호출하여 조도값 계산
    df["Illuminance"] = df.apply(
        lambda row: get_illuminance_at(
            utc_year, utc_month, utc_day, utc_hour, utc_minute,
            row["Latitude"],
            row["Longitude"]
        ),
        axis=1
    )
    
    # 결과 CSV 파일 저장
    df.to_csv(output_csv, index=False)
    print(f"파일 저장 완료: {output_csv}")

if __name__ == "__main__":
    main()
