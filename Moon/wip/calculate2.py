import math
import numpy as np
from skyfield.api import load, Topos
from datetime import datetime, timedelta

#--------------------------------------
# SPICE Ephemeris 불러오기
# de440.bsp: JPL DE440 궤도 데이터 (태양, 달, 행성 위치 정보 포함)
eph = load('de440.bsp')
ts = load.timescale()

# 전역 대기압 (Pa)
pressure_pa = 101325

def sun_illuminance(altitude_sun_deg):
    """
    태양 고도에 따른 조도(lux) 계산 함수.
    - 고도 >= 0°: 낮 (400 lux로 가정)
    - -6° ≤ 고도 < 0°: 시민 황혼 (지수함수 감소)
    - -12° ≤ 고도 < -6°: 항해 황혼 (지수함수 감소)
    - -18° ≤ 고도 < -12°: 항해 황혼 후반 (지수함수 감소)
    - 고도 < -18°: 완전 어둠 (0 lux)
    """
    if altitude_sun_deg >= 0:
        # 맑은 낮 햇빛 대략 400 lux
        return 400
    elif altitude_sun_deg >= -6:
        # 시민 황혼 초기: 조도가 지수함수적으로 감소
        return 400 * math.exp(0.7951 * altitude_sun_deg)
    elif altitude_sun_deg >= -12:
        # 시민 황혼 후반 ~ 항해 황혼 초기
        return 3.4 * math.exp(0.4728 * (altitude_sun_deg + 6))
    elif altitude_sun_deg >= -18:
        # 항해 황혼 구간
        return 0.25 * math.exp(0.920244 * (altitude_sun_deg + 12))
    else:
        # 태양이 더 깊이 지평선 아래에 있으면 0
        return 0

def get_illuminance_at(year, month, day, hour, minute, latitude, longitude):
    """
    지정한 UTC 시각(year, month, day, hour, minute)과
    관측 지점(latitude, longitude)에서의 
    달빛+햇빛 합산 조도(lux)를 반환.
    """
    # 1) Skyfield 시간 생성
    t = ts.utc(year, month, day, hour, minute)
    # 하루 전 시각 (위상 변화 비교용)
    t_prev = ts.utc(t.utc_datetime() - timedelta(days=1))

    # 2) 천체 객체 가져오기
    moon  = eph['moon']
    sun   = eph['sun']
    earth = eph['earth']
    # 관측자 위치 정의
    observer = earth + Topos(latitude_degrees=latitude,
                             longitude_degrees=longitude)

    # 3) 관측자 기준 천체의 겉보기 위치 계산
    moon_apparent = observer.at(t).observe(moon).apparent()
    sun_apparent  = observer.at(t).observe(sun).apparent()

    # 4) 달의 고도, 방위각, 거리 추출
    alt_moon, az_moon, dist_moon = moon_apparent.altaz()
    altitude_deg     = alt_moon.degrees      # 달 고도(°)
    distance_moon_km = dist_moon.km           # 지구-달 거리(km)
    z_deg            = 90 - altitude_deg      # 천정각(zenith angle)

    # 5) 달이 지평선 아래(고도 ≤ 0)면 조도 0
    if altitude_deg <= 0:
        Ev_G = 0.0
    else:
        # 6) 달 위상각, 등급 계산
        separation  = moon_apparent.separation_from(sun_apparent).degrees
        phase_angle = 180 - separation  # 달의 위상각(°)
        # 등급(magnitude) 모델식
        m = -12.73 + 0.026 * abs(phase_angle) + 4e-9 * phase_angle**4

        # 7) 대기 감쇠 계수(X) 계산 (Michaelis–Menten 형태)
        X = (-0.140194 * z_deg / (-91.674385 + z_deg)) - 0.03

        # 8) 초기 달빛 조도 Ev_A (천문 등급 → lux)
        Ev_A = 10**(-0.4 * (m + X + 16.57)) * 10.7637

        # 9) 입사각 보정: 음수 sin 제거
        Ev_B = Ev_A * max(0.0, math.sin(math.radians(altitude_deg)))

        # 10) Opposition surge 보정 (위상각 < 6°)
        if abs(phase_angle) < 6:
            Ev_C = Ev_B * (1 + 0.4 * (6 - abs(phase_angle)) / 6)
        else:
            Ev_C = Ev_B

        # 11) 하현(waning) 단계 체크
        frac_today     = observer.at(t).observe(moon).apparent().fraction_illuminated(sun)
        frac_yesterday = observer.at(t_prev).observe(moon).apparent().fraction_illuminated(sun)
        is_waning      = frac_today < frac_yesterday

        # 12) Lunar maria 효과 보정
        if is_waning:
            Ev_D = Ev_C * (1 - 0.00026 * abs(phase_angle))
        else:
            Ev_D = Ev_C

        # 13) 달–지구 거리 보정 (괘도 거리 차 보정)
        Ev_E = Ev_D * (384400 / distance_moon_km)**2

        # 14) 해발고도(기압) 보정
        Ev_F = Ev_E * ((18.964 * math.exp(-0.229 * (pressure_pa / 101325))) / 15.083)

        # 15) 산란·오차 최종 보정
        Ev_G = (Ev_F + 0.0008) * 0.863

    # 16) 태양 조도 계산
    alt_sun, az_sun, _ = sun_apparent.altaz()
    alt_sun_deg        = alt_sun.degrees
    R_light_sun        = sun_illuminance(alt_sun_deg)

    # 17) 최종 달빛+햇빛 조도 합산
    R_light_total = Ev_G + R_light_sun
    return R_light_total

def get_moon_altitude(year, month, day, hour, minute, latitude, longitude):
    """
    지정한 UTC 시각과 위치에서 달의 고도(°)만 반환하는 보조 함수.
    """
    # 1) Skyfield용 시간 생성 (초 단위 포함)
    t = ts.utc(year, month, day, hour, minute, 0)

    # 2) 관측자 위치 설정
    observer = eph['earth'] + Topos(latitude_degrees=latitude,
                                    longitude_degrees=longitude)

    # 3) 달의 겉보기 위치 계산
    moon_apparent = observer.at(t).observe(eph['moon']).apparent()

    # 4) 달의 고도·방위각 추출
    alt, az, _ = moon_apparent.altaz()

    # 5) 높이(고도)만 반환
    return alt.degrees
