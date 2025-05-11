import math
from skyfield.api import load, Topos

# Skyfield preparations
# 전역에서 한 번만 ephemeris와 timescale 준비
ts = load.timescale()
eph = load('de440.bsp')

# --- Constants for moon illuminance calculations ---
A = 0.072            # Moon's albedo
R_M = 1737.4         # Moon's radius (km)
E_sm = 1300          # Solar illuminance at Moon (W/m²)
K_norm = 1.0         # Normalized reflectance

# Atmosphere extinction components (clear sky)
C_aerosol = 0.0218
C_rayleigh = 0.008735
C_ozone = 0.02975
C_atmosphere = C_aerosol + C_rayleigh + C_ozone

# Starlight illuminance (approx)
star_illuminance = 0.00022  # lux

# --- Moon illuminance theory functions (inlined) ---

def calculate_opposition_effect(phase_angle):
    """
    phase_angle: 달의 위상각 (°)
    완전충(≤1°) 시 최대 1.27배, 
    1°<phase<7° 사이 선형 보간, 
    7° 이상 1.0배
    """
    if phase_angle <= 1:
        return 1.27
    elif phase_angle < 7:
        # 1.27 → 1.00 사이를 선형 보간 (차이는 0.27)
        return 1 + 0.27 * (7 - phase_angle) / 6
    else:
        return 1.0


def calculate_moon_illuminance(phase_angle, moon_distance):
    """
    달 자체 조도 E_MT 계산
    phase_angle: 달 위상각 (°)
    moon_distance: 달-지구 거리 (km)
    """
    phi = math.radians(phase_angle)
    Oef = calculate_opposition_effect(phase_angle)

    # Earthshine (E_em)
    earth_phase = math.pi - phi
    E_em = (0.19 * 0.5 *
            (1 - math.sin(earth_phase / 2)
             * math.tan(earth_phase / 2)
             * math.log(1 / math.tan(earth_phase / 4))))
    try:
        E_MT = (683 * (2/3) * Oef * A * (R_M ** 2) / (moon_distance ** 2) *
                (E_em + E_sm * (1
                          - math.sin(phi / 2)
                          * math.tan(phi / 2)
                          * math.log(1 / math.tan(phi / 4)))))
    except ValueError:
        E_MT = 0
    return E_MT


def calculate_E_DN_moon(E_MT, altitude_moon_deg):
    """
    대기를 통과한 달빛 조도 E_DN
    altitude_moon_deg: 대기 보정 전 고도 (°)
    """
    alt_rad = math.radians(altitude_moon_deg)
    m_limit = 500
    # Kasten & Young 공식으로 공기질량 계수 계산
    if altitude_moon_deg > 0:
        z = math.radians(90 - altitude_moon_deg)
        delta = 96.07995 - (90 - altitude_moon_deg)
        m_air = 1 / (math.cos(z) + 0.50572 * (delta ** -1.6364))
        m_air = min(m_air, m_limit)
    else:
        m_air = m_limit
    return E_MT * math.exp(-C_atmosphere * m_air)


def calculate_cos_theta_s_moon(altitude_moon_deg, azimuth_moon_deg):
    """
    입사각과 표면 법선 사이의 코사인 계산
    """
    alt_rad = math.radians(altitude_moon_deg)
    az_rad = math.radians(azimuth_moon_deg)
    # 입사 벡터
    ix = math.cos(alt_rad) * math.cos(az_rad)
    iy = math.cos(alt_rad) * math.sin(az_rad)
    iz = math.sin(alt_rad)
    # 표면 법선 = (0,0,1)
    dot = iz
    norm_incident = math.sqrt(ix**2 + iy**2 + iz**2)
    return dot / norm_incident


def calculate_E_DV_moon(E_DN_moon, altitude_moon_deg, azimuth_moon_deg):
    """
    지표면 입사 조도 E_DV
    """
    if altitude_moon_deg <= 0:
        return 0
    cos_theta = calculate_cos_theta_s_moon(altitude_moon_deg, azimuth_moon_deg)
    return E_DN_moon * cos_theta


def calculate_R_light_moon(E_DV_moon):
    """
    램버트 확산 반사량 R_light_moon
    """
    return E_DV_moon * K_norm * (1 / math.pi)

# 태양 고도에 따른 조도 근사 함수

def sun_illuminance(altitude_sun_deg):
    if altitude_sun_deg >= 0:
        return 400
    if altitude_sun_deg >= -6:
        return 400 * math.exp(0.7951 * altitude_sun_deg)
    if altitude_sun_deg >= -12:
        return 3.4 * math.exp(0.4728 * (altitude_sun_deg + 6))
    if altitude_sun_deg >= -18:
        return 0.25 * math.exp(0.920244 * (altitude_sun_deg + 12))
    return 0


def get_illuminance_at(year, month, day, hour, minute, latitude, longitude):
    """
    UTC 시각과 위치에서 총 조도(R_light_total) 계산
    """
    # Skyfield 시각 및 관측자 정의
    t = ts.utc(year, month, day, hour, minute, 0)
    observer = eph['earth'] + Topos(latitude_degrees=latitude,
                                    longitude_degrees=longitude)
    sun_app = observer.at(t).observe(eph['sun']).apparent()
    moon_app = observer.at(t).observe(eph['moon']).apparent()

    # 달 위상각 / 거리
    sep = moon_app.separation_from(sun_app).degrees
    phase_angle = 180.0 - sep
    dist_km = moon_app.distance().au * 1.496e+8

    # --- 달빛 조도 계산 ---
    E_MT = calculate_moon_illuminance(phase_angle, dist_km)
    alt_moon, az_moon, _ = moon_app.altaz()
    alt_moon_deg = alt_moon.degrees
    az_moon_deg = az_moon.degrees
    E_DN = calculate_E_DN_moon(E_MT, alt_moon_deg)
    E_DV = calculate_E_DV_moon(E_DN, alt_moon_deg, az_moon_deg)
    R_moon = calculate_R_light_moon(E_DV)

    # --- 별빛 반사 ---
    R_stars = calculate_R_light_moon(star_illuminance)

    # --- 태양 조도 ---
    alt_sun, az_sun, _ = sun_app.altaz()
    R_sun = sun_illuminance(alt_sun.degrees)

    R_light_total = R_moon + R_sun + R_stars
    # 총 조도 합산
    return R_light_total

def get_moon_altitude(year, month, day, hour, minute, latitude, longitude):
    t = ts.utc(year, month, day, hour, minute, 0)
    observer = eph['earth'] + Topos(latitude_degrees=latitude,
                                    longitude_degrees=longitude)
    moon_app = observer.at(t).observe(eph['moon']).apparent()
    alt, az, _ = moon_app.altaz()
    return alt.degrees
