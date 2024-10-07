#output.py

from .sun import calculate_sun_position
from .moon import calculate_moon_position_and_phase
from datetime import datetime, timedelta, timezone

def calculate_and_collect_data(year, month, day, timezone_offset, latitude, longitude):
    """
    지정된 날짜와 시간대에 대해 태양과 달의 데이터를 계산하고 수집합니다.
    
    Parameters:
        year (int): 연도
        month (int): 월
        day (int): 일
        timezone_offset (int): 시간대 오프셋 (예: KST는 +9)
        latitude (float): 위도
        longitude (float): 경도
    
    Returns:
        list of dict: 각 시간대별 태양과 달의 데이터
    """
    data = []
    # 시작 시간과 종료 시간 설정 (UTC 기준, 09:00부터 23:00 UTC)
    start_time_utc = datetime(year, month, day, 7, 0, 0, tzinfo=timezone.utc)
    end_time_utc = datetime(year, month, day, 23, 0, 0, tzinfo=timezone.utc)
    delta = timedelta(minutes=10)
    current_time = start_time_utc

    while current_time <= end_time_utc:
        # 현지 시간 계산 (timezone_offset을 적용하여 현지 시간으로 변환)
        local_time = current_time + timedelta(hours=timezone_offset)
        
        # 태양 위치 계산 (UTC 시간 기준으로 전달)
        sun_data = calculate_sun_position(
            current_time.year, current_time.month, current_time.day,
            current_time.hour, current_time.minute, current_time.second,
            latitude, longitude
        )

        # 달 위치 및 위상 계산 (UTC 시간 기준으로 전달)
        moon_data = calculate_moon_position_and_phase(
            current_time.year, current_time.month, current_time.day,
            current_time.hour, current_time.minute, current_time.second,
            latitude, longitude
        )

        # E_surface 계산 (lux 단위)
        E_surface = sun_data['R_Twilight_sun'] + moon_data['R_light_moon']

        # 데이터 수집 (달빛 조도(E_MT) 및 태양 외계 조도(E_ST) 추가)
        data.append({
            'Local Time': local_time.strftime('%Y-%m-%d %H:%M'),
            'Sun Lambda (°)': f"{sun_data['lambda_sun']:.2f}",
            'Sun Alt (°)': f"{sun_data['altitude_sun']:.2f}",
            'Sun Az (°)': f"{sun_data['azimuth_sun']:.2f}",
            'Sun Dist (AU)': f"{sun_data['r_sun_earth']:.6f}",
            'Moon Lambda (°)': f"{moon_data['lambda_moon']:.2f}",
            'Moon Beta (°)': f"{moon_data['beta_moon']:.2f}",
            'Moon Alt (°)': f"{moon_data['altitude']:.2f}",
            'Moon Az (°)': f"{moon_data['azimuth']:.2f}",
            'Moon Dist (km)': f"{moon_data['distance_moon']:.2f}",
            'Moon Phase Angle (°)': f"{moon_data['phase_angle_moon']:.2f}",
            'Moon Illumination (%)': f"{moon_data['illumination'] * 100:.2f}",
            'R_light_sun (lux)': f"{sun_data['R_light_sun']:.2f}",    
            'R_light_moon (millilux)': f"{moon_data['R_light_moon'] * 1000:.2f}",  
            'R_Twilight_sun (lux)': f"{sun_data['R_Twilight_sun']:.2f}",
            'E_surface (millilux)': f"{E_surface * 1000:.2f}"      
        })

        # 다음 시간으로 이동
        current_time += delta

    return data
