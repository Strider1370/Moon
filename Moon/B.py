# B.py

import csv
import os
from astronomy.sun import calculate_sun_position
from astronomy.moon import calculate_moon_position_and_phase
from datetime import datetime, timedelta

def calculate_illuminance_for_point_at_time(latitude, longitude, time_utc):
    """주어진 위도, 경도, 시간에 대해 E_surface 값을 계산."""
    sun_data = calculate_sun_position(
        time_utc.year, time_utc.month, time_utc.day,
        time_utc.hour, time_utc.minute, time_utc.second,
        latitude, longitude
    )
    moon_data = calculate_moon_position_and_phase(
        time_utc.year, time_utc.month, time_utc.day,
        time_utc.hour, time_utc.minute, time_utc.second,
        latitude, longitude
    )

    R_Twilight_sun = sun_data['R_Twilight_sun']
    R_light_moon = moon_data['R_light_moon']

    # E_surface 계산
    E_surface = R_Twilight_sun + R_light_moon
    return E_surface

def process_csv(input_csv, year, month, day):
    """CSV 파일에서 위도와 경도를 읽어와 각 시간에 대한 E_surface 값을 시간별로 저장."""
    start_time_utc = datetime(year, month, day, 7, 0, 0)  # 07:00 UTC
    end_time_utc = datetime(year, month, day, 12, 0, 0)   # 12:00 UTC
    delta = timedelta(minutes=10)  # 10분 간격

    # assets 폴더가 없으면 생성
    assets_dir = './assets'
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    current_time = start_time_utc

    while current_time <= end_time_utc:
        # 각 시간별로 파일을 assets 폴더에 저장
        output_csv = f'{assets_dir}/E_surface_{current_time.strftime("%Y%m%d%H%M")}.csv'
        
        with open(input_csv, mode='r') as infile, open(output_csv, mode='w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            # CSV 헤더 작성
            writer.writerow(['longitude', 'latitude', 'E_surface'])

            for row in reader:
                longitude = float(row[0])  # 1번째 열에 경도
                latitude = float(row[1])  # 2번째 열에 위도

                # 각 시간에 대해 E_surface 계산
                E_surface = calculate_illuminance_for_point_at_time(latitude, longitude, current_time)
                
                # CSV 파일에 기록
                writer.writerow([longitude, latitude, E_surface])

        # 파일 저장 완료 메시지 출력
        print(f'{output_csv} 파일이 저장되었습니다.')

        current_time += delta

def main():
    """메인 함수."""
    input_csv = './grid_info.csv'  # 입력 CSV 파일 경로 (B.py와 동일한 경로)

    year = 2024
    month = 10
    for day in range(18, 19):  # 1일부터 30일까지 반복
        process_csv(input_csv, year, month, day)

if __name__ == "__main__":
    main()
