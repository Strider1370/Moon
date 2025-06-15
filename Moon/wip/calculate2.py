import math
import numpy as np
from skyfield.api import load, Topos
from datetime import datetime, timedelta

#--------------------------------------
#Ephemeris
eph = load('de440.bsp')
ts = load.timescale()
pressure_pa=101325

def sun_illuminance(altitude_sun_deg):
    """
    태양 고도에 따른 조도값을 대략적으로 계산해 주는 함수.
    낮(>=0°)은 400 lux로 가정.
    황혼 구간(-6°, -12°, -18°)에 따라 지수함수적으로 감소.
    -18° 미만이면 0으로 간주.
    """
    if altitude_sun_deg >= 0:
        # 낮
        return 400
    elif altitude_sun_deg >= -6:
        # 시민 황혼 초기 (0° ~ -6°)
        return 400 * math.exp(0.7951 * altitude_sun_deg)
    elif altitude_sun_deg >= -12:
        # 시민 황혼 후반 ~ 항해 황혼 초기 (-6° ~ -12°)
        return 3.4 * math.exp(0.4728 * (altitude_sun_deg + 6))
    elif altitude_sun_deg >= -18:
        # 항해 황혼 구간 (-12° ~ -18°)
        return 0.25 * math.exp(0.920244 * (altitude_sun_deg + 12))
    else:
        # -18° 미만
        return 0

def get_illuminance_at(year, month, day, hour, minute, latitude, longitude):
    t = ts.utc(year, month, day, hour, minute)
    t_prev = ts.utc(t.utc_datetime() - timedelta(days=1))

    moon    = eph['moon']
    sun     = eph['sun']
    earth   = eph['earth']
    observer = earth + Topos(latitude_degrees=latitude,
                             longitude_degrees=longitude)

    moon_apparent = observer.at(t).observe(moon).apparent()
    sun_apparent  = observer.at(t).observe(sun).apparent()

    # 달 고도·거리 계산
    alt_moon, az_moon, dist_moon = moon_apparent.altaz()
    altitude_deg      = alt_moon.degrees
    distance_moon_km  = dist_moon.km
    z_deg             = 90 - altitude_deg

    # **달이 지평선 아래에 있으면 조도 0**
    if altitude_deg <= 0:
        Ev_G = 0.0
    else:
        # (기존) 위상각, 등급(m), 대기감쇄(X) 계산
        separation   = moon_apparent.separation_from(sun_apparent).degrees
        phase_angle  = 180 - separation
        m = -12.73 + 0.026 * abs(phase_angle) + 4e-9 * phase_angle**4
        X = (-0.140194 * z_deg / (-91.674385 + z_deg)) - 0.03

        Ev_A = 10**(-0.4*(m + X + 16.57)) * 10.7637
        # 음수 sin을 막기 위해 max() 사용해도 좋습니다.
        Ev_B = Ev_A * max(0.0, math.sin(math.radians(altitude_deg)))
        Ev_C = Ev_B * (1 + 0.4*(6 - abs(phase_angle))/6) if abs(phase_angle) < 6 else Ev_B

        frac_today     = earth.at(t).observe(moon).apparent().fraction_illuminated(sun)
        frac_yesterday = earth.at(t_prev).observe(moon).apparent().fraction_illuminated(sun)
        is_waning      = frac_today < frac_yesterday

        Ev_D = Ev_C * (1 - 0.00026 * abs(phase_angle)) if is_waning else Ev_C
        Ev_E = Ev_D * (384400 / distance_moon_km)**2
        Ev_F = Ev_E * ((18.964 * math.exp(-0.229 * (pressure_pa/101325))) / 15.083)
        Ev_G = (Ev_F + 0.0008) * 0.863

    # ☀ 태양 조도 계산
    alt_sun, az_sun, _ = sun_apparent.altaz()
    alt_sun_deg = alt_sun.degrees
    R_light_sun = sun_illuminance(alt_sun_deg)

    # 최종 조도
    R_light_total = Ev_G + R_light_sun
    return R_light_total

def get_moon_altitude(year, month, day, hour, minute, latitude, longitude):
    """
    주어진 UTC 시각과 위치에서 달의 고도(°)를 반환합니다.
    """
    # 1) Skyfield용 시각 생성
    t = ts.utc(year, month, day, hour, minute, 0)

    # 2) 관측자 위치 설정
    observer = eph['earth'] + Topos(latitude_degrees=latitude,
                                    longitude_degrees=longitude)

    # 3) 달의 겉보기 위치 계산
    moon_apparent = observer.at(t).observe(eph['moon']).apparent()

    # 4) 달의 고도, 방위각 추출
    alt, az, _ = moon_apparent.altaz()

    # 5) 고도만 ° 단위로 반환
    return alt.degrees

