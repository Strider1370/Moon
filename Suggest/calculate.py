# calculate.py

import math
import numpy as np
from skyfield.api import load, Topos

# 전역에서 한 번만 ephemeris와 timescale 준비
ts = load.timescale()
eph = load('de440.bsp')

# 대기 감쇠 상수 등 필요한 상수들
C = 0.21  # 대기 extinction 계수 (맑은 날 가정)
K_norm = 1.0
A = 0.072  # Moon's albedo
E_sm = 1300              # 달에 도달하는 태양 직사 illuminance (W/m²)
Radius_Moon = 1737.4     # 달의 반지름 (km)
star_illuminance = 0.00022  # 별빛 illuminance (lux)

def opposition_effect(phase_angle):
    """
    phase_angle: 달의 위상각 (°).
    위상각이 1° 이하이면 최대 효과 (1.27), 7° 이상이면 효과가 1.0,
    그 사이에서는 선형 보간.
    """
    if phase_angle <= 1:
        return 1.27
    elif phase_angle >= 7:
        return 1.0
    else:
        return 1.27 - (1.27 - 1.0) * ((phase_angle - 1) / (7 - 1))

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
    """
    (year, month, day, hour, minute) UTC 기준 시각과
    (latitude, longitude) 위치를 받아서
    최종 조도(R_light_total)를 계산하여 반환.
    """

    # Skyfield용 시각 생성
    t = ts.utc(year, month, day, hour, minute, 0)

    # 관측자 위치 설정
    earth = eph['earth']
    observer = earth + Topos(latitude_degrees=latitude, longitude_degrees=longitude)

    # 태양 및 달 객체
    sun = eph['sun']
    moon = eph['moon']

    # 천체 위치 (apparent)
    sun_apparent = observer.at(t).observe(sun).apparent()
    moon_apparent = observer.at(t).observe(moon).apparent()

    # 분리각을 이용한 달 위상각
    separation = moon_apparent.separation_from(sun_apparent).degrees
    phase_angle = 180 - separation  # 달의 위상각

    # 달과 지구 사이 거리 (km)
    distance_moon_au = moon_apparent.distance().au
    distance_moon_km = distance_moon_au * 1.496e+8

    # 반사효과(Opposition Effect)
    Oef = opposition_effect(phase_angle)

    # 달 조도(E_MT) 계산
    phi = math.radians(phase_angle)
    # Earthshine 대략 E_em 계산 (여기서는 예시적 사용)
    earth_phase = math.pi - phi
    E_em = 0.19 * 0.5 * (1 - math.sin(earth_phase / 2) *
                         math.tan(earth_phase / 2) *
                         math.log(1 / math.tan(earth_phase / 4)))
    # 달빛 직사 조도
    try:
        E_MT = (683 * (2 / 3) * Oef * A * (Radius_Moon ** 2) / (distance_moon_km ** 2) *
               (E_em + E_sm * (1 - math.sin(phi / 2) *
                               math.tan(phi / 2) *
                               math.log(1 / math.tan(phi / 4)))))
    except ValueError:
        E_MT = 0

    # 달 고도, 방위각
    alt_moon, az_moon, _ = moon_apparent.altaz()
    alt_moon_deg = alt_moon.degrees

    # 천정각 z = 90 - alt
    z_deg = 90 - alt_moon_deg
    if z_deg < 0:
        # 달이 천정 위에 있으면 z=0으로 처리(계산 안정화)
        z_deg = 0
    z_rad = math.radians(z_deg)

    # Kasten & Young (1989) 대기질량
    m_air = 1.0 / (math.cos(z_rad) + 0.50572 * ((96.07995 - z_deg) ** -1.6364))
    # m_air가 너무 크면 제한
    if m_air > 500:
        m_air = 500

    # 대기 감쇠
    EDN_moon = E_MT * math.exp(-m_air * C)

    # 표면 수평 가정하에 입사각 θ = 90° - alt(달)
    theta = math.radians(90 - alt_moon_deg)
    EDV_moon = EDN_moon * math.cos(theta)

    # 램버트 확산 반사
    R_light_moon = (K_norm / math.pi) * EDV_moon

    # 별빛 반사
    R_light_stars = (K_norm / math.pi) * star_illuminance

    # 태양 고도에 따른 지표면 illuminance
    alt_sun, az_sun, _ = sun_apparent.altaz()
    alt_sun_deg = alt_sun.degrees
    R_light_sun = sun_illuminance(alt_sun_deg)

    # 총 조도
    R_light_total = R_light_moon + R_light_sun + R_light_stars

    return R_light_total
