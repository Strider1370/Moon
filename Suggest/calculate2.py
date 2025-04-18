from skyfield.api import load, Topos
import numpy as np
import math 

# ================================
# 1. 천체 위치 계산 (Skyfield)
# ================================

# 관측자 위치 (서울: 위도 37.57° N, 경도 126.98° E) 및 시간 (2025년 4월 3일 15:00 UTC)
latitude = 37.57
longitude = 126.98
ts = load.timescale()
t = ts.utc(2025, 4, 3, 15, 00, 0)

# 로컬에 저장된 de440.bsp 파일 로드
eph = load('de440.bsp')
earth = eph['earth']
observer = earth + Topos(latitude_degrees=latitude, longitude_degrees=longitude)

# 태양 및 달 객체
sun = eph['sun']
moon = eph['moon']

# 관측자 위치에서 천체 관측 (astrometric → apparent)
sun_apparent = observer.at(t).observe(sun).apparent()
moon_apparent = observer.at(t).observe(moon).apparent()

# 태양 및 달의 적경(RA), 적위(Dec), 거리 계산
ra_sun, dec_sun, distance_sun = sun_apparent.radec()
ra_moon, dec_moon, distance_moon = moon_apparent.radec()

# 지평 좌표: 고도, 방위각 계산
alt_sun, az_sun, _ = sun_apparent.altaz()
alt_moon, az_moon, _ = moon_apparent.altaz()

# 달과 태양의 분리각을 이용해 달의 위상각 계산  
# (여기서는 달의 위상각 φ = 180° - (달과 태양 사이의 분리각), 단위: degree)
phase_angle = 180 - moon_apparent.separation_from(sun_apparent).degrees

# 달의 조명된 면적 비율 (illuminated fraction): (1 + cos(φ))/2  
illuminated_fraction = (1 + np.cos(np.radians(phase_angle))) / 2

# RA (시간 단위)를 도(degree)로 변환 (1시간 = 15°)
ra_sun_deg = ra_sun.hours * 15
ra_moon_deg = ra_moon.hours * 15

# Skyfield로부터 얻은 태양 고도 alt_sun는 Angle 객체이므로, degree 단위로 사용합니다.
sun_alt_deg = alt_sun.degrees  # 예: alt_sun.degrees

# ================================
# 2. 야간 조도 (Illuminance) 모델링
# ================================

# 기본 상수들
E_sm = 1300              # 달에 도달하는 태양 직사 illuminance (W/m²)
Radius_Moon = 1737.4           # 달의 반지름 (km)
star_illuminance = 0.00022  # 모든 별의 illuminance (lux, 지표면 도달값)
C = 0.21                 # 대기 extinction 계수 (맑은 날 가정)
K_norm = 1.0             # 표면 확산 반사 계수 (dull white surface 가정)
A = 0.072  # Moon's albedo

# (B) 달과 지구 사이 거리 변환
distance_moon_km = distance_moon.au * 1.496e+8

# (A) 달의 반대 효과 (Opposition Effect) 함수
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

Oef = opposition_effect(phase_angle)

def calculate_moon_illuminance(phase_angle, distance_moon_km):
    """
    달빛 조도(E_MT)를 계산하는 함수
    phase_angle_moon: 달의 위상각 (도 단위)
    moon_distance: 달과 지구 사이의 거리 (km 단위)
    """
    # 달의 위상각을 라디안으로 변환
    phi = math.radians(phase_angle)

    # E_em: Earthshine 계산
    earth_phase = math.pi - phi
    E_em = 0.19 * 0.5 * (1 - math.sin(earth_phase / 2) * math.tan(earth_phase / 2) * math.log(1 / math.tan(earth_phase / 4)))

    # 달빛 조도(E_MT) 계산
    try:
        E_MT = 683 * (2 / 3) * Oef * A * (Radius_Moon ** 2) / (distance_moon_km ** 2) * (
            E_em + E_sm * (1 - math.sin(phi / 2) * math.tan(phi / 2) * math.log(1 / math.tan(phi / 4)))
        )
    except ValueError as e:
        E_MT = 0  # 오류 발생 시 0으로 설정
    
    return E_MT

E_MT = calculate_moon_illuminance(phase_angle, distance_moon_km)

# (D) 대기 감쇠 적용 using Kasten & Young 공식:
# 천정각 z (degree) = 90 - alt_moon.degrees
z_deg = 90 - alt_moon.degrees
z_rad = np.radians(z_deg)

# Kasten & Young (1989) 공식:
# m_air = 1 / (cos(z) + 0.50572 * (96.07995 - z)^(-1.6364))
m_air = 1 / (np.cos(z_rad) + 0.50572 * ((96.07995 - z_deg) ** (-1.6364)))

# 만약 m_air가 너무 큰 경우 (예: 천체가 지평선 근처) 제한값 적용
m_limit = 500
if m_air > m_limit:
    m_air = m_limit

# 대기 감쇠 적용 (논문 Equation (15): E_DN = EMT * exp(-C * m_air))
EDN_moon = E_MT * np.exp(-m_air * C)

# (E) 표면에서 실제 입사 illuminance (EDV) 계산  
# 표면이 수평이라고 가정하면, 입사각 θ = 90° - (달의 고도)
theta = np.radians(90 - alt_moon.degrees)
EDV_moon = EDN_moon * np.cos(theta)

# (F) Lambert 확산 반사 모델을 적용하여 관측자에게 반사되는 조도 R_light (논문 Equation (21))
R_light_moon = (K_norm / np.pi) * EDV_moon

# (G) 별빛의 반사 조도 계산
# 별빛 illuminance는 지표면 도달값으로 주어지며, Lambert 반사를 적용하면
R_light_stars = (K_norm / np.pi) * star_illuminance

def sun_illuminance(altitude_sun_deg):
    if altitude_sun_deg >= 0:
        # 낮: 반사된 조도와 직접 illuminance 400 lux를 합산.
        return 400
    elif altitude_sun_deg >= -6:
        # 시민 황혼 초기 구간 (0° ~ -6°)
        return 400 * math.exp(0.7951 * altitude_sun_deg)
    elif altitude_sun_deg >= -12:
        # 시민 황혼 후반 또는 항해 황혼 초기 구간 (-6° ~ -12°)
        return 3.4 * math.exp(0.4728 * (altitude_sun_deg + 6))
    elif altitude_sun_deg >= -18:
        # 항해 황혼 구간 (-12° ~ -18°)
        return 0.25 * math.exp(0.920244 * (altitude_sun_deg + 12))
    else:
        # -18° 미만: 조도를 0으로 가정
        return 0

R_light_sun = sun_illuminance(sun_alt_deg)

# (H) 최종적으로 야간 조도: 달과 별의 반사 조도 합산
R_light_total = R_light_moon + R_light_sun + R_light_stars

print("== 태양 정보 ==")
print("적경 (RA): {:.2f}°".format(ra_sun_deg))
print("적위 (Dec): {:.2f}°".format(dec_sun.degrees))
print("거리 (AU): {:.6f}".format(distance_sun.au))
print("고도: {:.2f}°".format(alt_sun.degrees))
print("방위각: {:.2f}°".format(az_sun.degrees))
print()

print("== 달 정보 ==")
print("적경 (RA): {:.2f}°".format(ra_moon_deg))
print("적위 (Dec): {:.2f}°".format(dec_moon.degrees))
print("거리: {}".format(distance_moon))
print("고도: {:.2f}°".format(alt_moon.degrees))
print("방위각: {:.2f}°".format(az_moon.degrees))
print()

print("== 달의 위상 ==")
print("위상각: {:.2f}°".format(phase_angle))
print("Illuminated fraction: {:.2f}".format(illuminated_fraction))
print("태양 고도 (°):", sun_alt_deg)
print("달조도:", R_light_moon, "lux")
print("별조도:", R_light_stars, "lux")
print("태양양조도:", R_light_sun, "lux")
print("조도:", R_light_total, "lux")