import math
from .helpers import (
    julian_day,
    get_julian_centuries,
    greenwich_mean_sidereal_time,
    apparent_sidereal_time,
    equatorial_to_horizontal,
    atmospheric_refraction_correction
)
from .sun import calculate_lambda_sun, calculate_sun_earth_distance, solar_mean_anomaly, sun_equation_of_center, eccentricity_earth_orbit

# Constants
AU_TO_KM = 149597870.7  # 1 AU = 149,597,870.7 km
R_M = 1737.4  # Moon's radius in km
E_sm = 1300  # Solar illuminance (W/m²)
C = 0.072  # Moon's albedo
K_norm = 1.0  # Normal lobe contribution (assuming dull white surface)

C_aerosol = 0.0218  # Clear
C_rayleigh = 0.008735
C_ozone = 0.02975
C_atmosphere = C_aerosol + C_rayleigh + C_ozone
#C_atmosphere = 0.21 simple(clear)

def moon_mean_anomaly(T):
    """
    달의 평균 근점을 보다 정확하게 계산합니다.
    T: 줄리안 세기
    반환값: 평균 근점 (도 단위)
    """
    M = (134.96340251 + 477198.8675613 * T + 0.0087423 * T**2 +
         T**3 / 69699 - T**4 / 14712000)
    return M % 360.0

def moon_mean_longitude(T):
    """
    달의 평균 황경을 보다 정확하게 계산합니다.
    T: 줄리안 세기
    반환값: 평균 황경 (도 단위)
    """
    L = (218.3164477 + 481267.88123421 * T - 0.0015786 * T**2 +
         T**3 / 538841 - T**4 / 65194000)
    return L % 360.0

def moon_mean_elongation(T):
    """
    달의 평균 편각을 보다 정확하게 계산합니다.
    T: 줄리안 세기
    반환값: 평균 편각 (도 단위)
    """
    D = (297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 +
         T**3 / 545868 - T**4 / 113065000)
    return D % 360.0

def moon_ecliptic_latitude(T):
    """
    달의 황위(β)를 계산합니다.
    T: 줄리안 세기
    반환값: 황위 (도 단위)
    """
    F_moon = (93.272 + 483202.0175 * T) % 360.0
    beta_moon = 5.128 * math.sin(math.radians(F_moon))
    return beta_moon

def moon_equation_of_center(T, M_moon, D_moon, F_moon):
    """
    달의 중심차를 보다 정확하게 계산합니다.
    T: 줄리안 세기
    M_moon: 평균 근점 (도 단위)
    D_moon: 평균 편각 (도 단위)
    F_moon: 달의 평균 황위 (도 단위)
    반환값: 중심차 (도 단위)
    """
    M_rad = math.radians(M_moon)
    D_rad = math.radians(D_moon)
    F_rad = math.radians(F_moon)
    
    C = (
        6.289 * math.sin(M_rad)
        + 1.274 * math.sin(2 * D_rad - M_rad)
        + 0.658 * math.sin(2 * D_rad)
        + 0.214 * math.sin(2 * M_rad)
        + 0.11 * math.sin(D_rad)
        # 추가적인 항
        + 0.046 * math.sin(M_rad + F_rad)
        + 0.014 * math.sin(2 * D_rad - 2 * M_rad)
        + 0.011 * math.sin(M_rad - F_rad)
    )
    return C

def moon_distance(T, D_moon, M_moon, F_moon):
    """
    달과 지구 사이의 거리를 보다 정확하게 계산합니다.
    T: 줄리안 세기
    D_moon: 평균 편각 (도 단위)
    M_moon: 평균 근점 (도 단위)
    F_moon: 달의 평균 황위 (도 단위)
    반환값: 달-지구 거리 (킬로미터)
    """
    distance = (
        385000.56
        - 20905.355 * math.cos(math.radians(M_moon))
        - 3699.111 * math.cos(math.radians(2 * D_moon))
        - 2955.968 * math.cos(math.radians(2 * M_moon))
        - 570.0 * math.cos(math.radians(2 * D_moon - M_moon))
        + 246.0 * math.cos(math.radians(2 * D_moon + M_moon))
        - 205.0 * math.cos(math.radians(M_moon + F_moon))
        + 171.0 * math.cos(math.radians(D_moon - F_moon))
        - 152.0 * math.cos(math.radians(D_moon + F_moon))
        + 129.0 * math.cos(math.radians(D_moon - 2 * F_moon))
        + 63.0 * math.cos(math.radians(2 * D_moon + F_moon))
        + 63.0 * math.cos(math.radians(M_moon + 2 * F_moon))
        - 59.0 * math.cos(math.radians(2 * D_moon - 2 * F_moon))
        - 58.0 * math.cos(math.radians(M_moon - F_moon))
        + 51.0 * math.cos(math.radians(D_moon + 2 * F_moon))
        - 48.0 * math.cos(math.radians(D_moon - M_moon))
        - 46.0 * math.cos(math.radians(2 * D_moon + 2 * F_moon))
        + 46.0 * math.cos(math.radians(3 * D_moon))
        + 29.0 * math.cos(math.radians(2 * M_moon + F_moon))
        + 29.0 * math.cos(math.radians(D_moon + M_moon))
        + 26.0 * math.cos(math.radians(2 * D_moon - M_moon + F_moon))
        - 22.0 * math.cos(math.radians(M_moon + 2 * F_moon))
        + 21.0 * math.cos(math.radians(D_moon - 2 * F_moon))
        + 17.0 * math.cos(math.radians(2 * D_moon + M_moon))
        - 16.0 * math.cos(math.radians(D_moon - M_moon - F_moon))
        - 16.0 * math.cos(math.radians(2 * D_moon + M_moon - F_moon))
        - 15.0 * math.cos(math.radians(2 * D_moon - M_moon - F_moon))
    )
    return distance  # km 단위

def nutation(T):
    """
    지구의 세차와 진동을 계산하여 세차(Δψ)와 진동(Δε)을 반환합니다.
    단위: 도
    """
    D = math.radians((297.85036 + 445267.111480 * T - 0.0019142 * T**2 + T**3 / 189474) % 360)
    M = math.radians((357.52772 + 35999.050340 * T - 0.0001603 * T**2 - T**3 / 300000) % 360)
    M_prime = math.radians((134.96298 + 477198.867398 * T + 0.0086972 * T**2 + T**3 / 56250) % 360)
    F = math.radians((93.27191 + 483202.017538 * T - 0.0036825 * T**2 + T**3 / 327270) % 360)
    Omega = math.radians((125.04452 - 1934.136261 * T + 0.0020708 * T**2 + T**3 / 450000) % 360)
    
    # 세차 Δψ (arcseconds)
    delta_psi = (-17.20 * math.sin(Omega)
                - 1.32 * math.sin(2 * D + 2 * F)
                - 0.23 * math.sin(2 * M)
                + 0.21 * math.sin(2 * Omega))
    
    # 진동 Δε (arcseconds)
    delta_epsilon = (9.20 * math.cos(Omega)
                     + 0.57 * math.cos(2 * D + 2 * F)
                     + 0.10 * math.cos(2 * M)
                     - 0.09 * math.cos(2 * Omega))
    
    # arcseconds to degrees
    delta_psi_deg = delta_psi / 3600.0
    delta_epsilon_deg = delta_epsilon / 3600.0
    
    return delta_psi_deg, delta_epsilon_deg

def mean_obliquity_of_ecliptic(T):
    """
    세차와 진동을 고려한 평균 황경을 계산합니다.
    단위: 도
    """
    # 평균 황경 계산 (초 단위)
    epsilon0 = 23 + (26 + (21.448 - 46.815 * T - 0.00059 * T**2 + 0.001813 * T**3) / 60) / 60
    delta_psi, delta_epsilon = nutation(T)
    epsilon = epsilon0 + delta_epsilon
    return epsilon


def calculate_phase_angle_geo(lambda_sun, lambda_moon, beta_moon, distance_moon, T):
    """
    지리적 경도와 위도를 이용하여 달의 위상각을 계산합니다.
    lambda_sun: 태양의 경도 (도)
    lambda_moon: 달의 경도 (도)
    beta_moon: 달의 지리적 위도 (도)
    distance_moon: 달-지구 거리 (km 단위)
    T: 줄리안 세기 (천문 시간 계산)
    """
    # 경도와 위도를 사용한 psi 계산
    cos_psi = math.cos(math.radians(beta_moon)) * math.cos(math.radians(lambda_moon - lambda_sun))
    psi = math.acos(cos_psi)

    # 태양의 평균 근점, 이심률 및 진이각 계산
    M_sun = solar_mean_anomaly(T)
    e = eccentricity_earth_orbit(T)
    C_sun = sun_equation_of_center(T, M_sun)
    v = (M_sun + C_sun) % 360.0  # 진이각 (True Anomaly)
    
    # 지구-태양 거리(AU 단위로 계산)
    r_sun_earth_au = calculate_sun_earth_distance(v, e)
    
    # 지구-태양 거리(AU -> km 변환)
    r_sun_earth_km = r_sun_earth_au * AU_TO_KM

    # 위상각 i 계산 (48.3 식)
    sin_psi = math.sin(psi)
    cos_psi = math.cos(psi)

    # r_sun_earth_km을 사용하여 위상각 i 계산
    tan_i = (r_sun_earth_km * sin_psi) / (distance_moon - r_sun_earth_km * cos_psi)
    phase_angle_moon = math.degrees(math.atan(tan_i))

    # 음수값이 나올 경우 180도에서 해당 값을 빼줌
    if phase_angle_moon < 0:
        phase_angle_moon = 180 - abs(phase_angle_moon)
    
    # 조도 계산 (illuminated fraction)
    illumination = (1 + math.cos(math.radians(phase_angle_moon))) / 2

    return phase_angle_moon, illumination

def calculate_opposition_effect(phase_angle_moon):
    """
    Opposition effect (Oef) 계산 함수
    phase_angle_moon: 달의 위상각 (도 단위)
    반환값: opposition effect
    """
    if phase_angle_moon <= 7:
        Oef = 1 + 1.27 * ((7 - phase_angle_moon) / 6)
    else:
        Oef = 1
    return Oef

def calculate_moon_illuminance(phase_angle_moon, moon_distance):
    """
    달빛 조도(E_MT)를 계산하는 함수
    phase_angle_moon: 달의 위상각 (도 단위)
    moon_distance: 달과 지구 사이의 거리 (km 단위)
    """
    # 달의 위상각을 라디안으로 변환
    phi = math.radians(phase_angle_moon)

    # Opposition effect 계산
    Oef = calculate_opposition_effect(phase_angle_moon)

    # E_em: Earthshine 계산
    earth_phase = math.pi - phi
    E_em = 0.19 * 0.5 * (1 - math.sin(earth_phase / 2) * math.tan(earth_phase / 2) * math.log(1 / math.tan(earth_phase / 4)))

    # 달빛 조도(E_MT) 계산
    try:
        E_MT = 683 * (2 / 3) * Oef * C * (R_M ** 2) / (moon_distance ** 2) * (
            E_em + E_sm * (1 - math.sin(phi / 2) * math.tan(phi / 2) * math.log(1 / math.tan(phi / 4)))
        )
    except ValueError as e:
        E_MT = 0  # 오류 발생 시 0으로 설정
    
    return E_MT

def calculate_surface_illuminance_moon(E_MT, altitude_moon):
    """
    지표면에서 받는 달빛 조도 E_surface_moon을 계산하는 함수.
    
    Parameters:
        E_MT: 달빛 조도 (millilux)
        altitude_moon: 달의 고도 (degrees)
        
    Returns:
        E_surface_moon: 지표면에서의 달빛 조도 (millilux)
    """
    if altitude_moon > 0:  # 달이 지평선 위에 있을 때만 조도 계산
        # Air Mass 계산
        AM = 1 / math.sin(math.radians(altitude_moon))
        
        # 대기 투과율 계산
        T_atm = 0.7 ** (AM ** 0.678)
        
        # 지표면에서 받는 달빛 조도 계산
        E_surface_moon = E_MT * T_atm * math.sin(math.radians(altitude_moon))
    else:
        # 달이 지평선 아래에 있으면 조도는 0
        E_surface_moon = 0
    
    return E_surface_moon

def calculate_E_DN_moon(E_MT, altitude_moon_deg):
    """
    대기를 통과한 달빛 조도 E_DN_moon을 계산하는 함수.
    
    Parameters:
        E_MT: 달빛 조도 (millilux)
        altitude_moon_deg: 달의 고도 (degrees)
        
    Returns:
        E_DN_moon: 대기를 통과한 달빛 조도 (millilux)
    """
    # 고도를 라디안으로 변환
    altitude_moon_rad = math.radians(altitude_moon_deg)
    
    if altitude_moon_rad > -1:
        # 광학적 공기 질량 m 계산
        m = 1 / (math.cos(math.pi / 2 - altitude_moon_rad) + 0.15 * (3.885 + altitude_moon_rad)**-1.253)
        
    else:
        # 고도가 -1 라디안 이하인 경우, m = 500
        m = 500
    

    E_DN_moon = E_MT * math.exp(-C_atmosphere * m)
    
    return E_DN_moon

def calculate_cos_theta_s_moon(altitude_moon, azimuth_moon):
    """
    달의 고도와 방위각을 바탕으로 입사각과 표면 법선 사이의 각도 cos(theta_s_moon)를 계산하는 함수.
    
    Parameters:
        altitude_moon: 달의 고도 (degrees)
        azimuth_moon: 달의 방위각 (degrees)
    
    Returns:
        cos_theta_s_moon: 입사각과 표면 법선 사이의 각도 cos(theta_s_moon)
    """
    # 표면이 평평한 경우 표면 법선 벡터 (0, 0, 1)
    surface_normal = (0, 0, 1)
    
    # 달의 고도와 방위각을 바탕으로 빛의 입사 벡터를 계산
    altitude_moon_rad = math.radians(altitude_moon)
    azimuth_moon_rad = math.radians(azimuth_moon)
    
    # 입사 벡터 (빛이 들어오는 방향 벡터) 계산
    incident_vector = (
        math.cos(altitude_moon_rad) * math.cos(azimuth_moon_rad),  # x
        math.cos(altitude_moon_rad) * math.sin(azimuth_moon_rad),  # y
        math.sin(altitude_moon_rad)  # z
    )
    
    # 벡터 내적 계산 (표면 법선 벡터와 입사 벡터의 내적)
    dot_product = (surface_normal[0] * incident_vector[0] +
                   surface_normal[1] * incident_vector[1] +
                   surface_normal[2] * incident_vector[2])
    
    # 표면 법선 벡터와 입사 벡터의 크기
    norm_surface = math.sqrt(surface_normal[0]**2 + surface_normal[1]**2 + surface_normal[2]**2)
    norm_incident = math.sqrt(incident_vector[0]**2 + incident_vector[1]**2 + incident_vector[2]**2)
    
    # cos(theta_s_moon) 계산
    cos_theta_s_moon = dot_product / (norm_surface * norm_incident)
    
    return cos_theta_s_moon

def calculate_E_DV_moon(E_DN_moon, altitude_moon, azimuth_moon):
    """
    표면에서의 달빛 조도 E_DV_moon를 계산하는 함수.
    
    Parameters:
        E_DN_moon: 대기를 통과한 달빛 조도 (millilux)
        altitude_moon: 달의 고도 (degrees)
        azimuth_moon: 달의 방위각 (degrees)
        
    Returns:
        E_DV_moon: 표면에서의 달빛 조도 (millilux)
    """
    # 벡터 내적을 통해 cos(theta_s_moon) 계산
    if altitude_moon > 0:

        cos_theta_s_moon = calculate_cos_theta_s_moon(altitude_moon, azimuth_moon)
    
        # E_DV_moon 계산
        E_DV_moon = E_DN_moon * cos_theta_s_moon
    
    else:
        E_DV_moon = 0
    
    return E_DV_moon
 

def calculate_R_light_moon(E_DV_moon):
    """
    반사된 빛의 양 \(R_{light}\)을 계산하는 함수.
    
    Parameters:
        E_DV_moon: 표면에서의 달빛 조도 (millilux)
        
    Returns:
        R_light_moon: 반사된 빛의 양 (millilux)
    """
    # 반사된 빛의 양 계산
    R_light_moon = E_DV_moon * K_norm * (1 / math.pi)
    return R_light_moon


def calculate_moon_position_and_phase(year, month, day, hour, minute, second, latitude, longitude):
    """
    달의 위치(고도, 방위각)와 추가 데이터(황경, 황위, 거리, 위상각)를 계산합니다.
    모든 시간은 UTC 시간 기준으로 합니다.
    """
    # 줄리안 날짜 및 세기 계산
    JD = julian_day(year, month, day, hour, minute, second)
    T = get_julian_centuries(JD)
    
    # 달의 평균 근점, 황경, 편각, F_moon 계산
    M_moon = moon_mean_anomaly(T)
    L_moon = moon_mean_longitude(T)
    D_moon = moon_mean_elongation(T)
    F_moon = (93.272 + 483202.0175 * T) % 360.0  # 달의 평균 황위
    
    # 달의 중심차 계산 (고차항 포함)
    C_moon = moon_equation_of_center(T, M_moon, D_moon, F_moon)
    lambda_moon = L_moon + C_moon
    beta_moon = moon_ecliptic_latitude(T)
    
    # 세차와 진동 보정
    delta_psi, delta_epsilon = nutation(T)
    
    # 적경(RA)과 적위(Dec) 계산 (세차와 진동을 반영한 황경 사용)
    epsilon = mean_obliquity_of_ecliptic(T)
    lambda_moon_corrected = lambda_moon + delta_psi  # 진황경 보정
    alpha_moon = math.degrees(math.atan2(
        math.cos(math.radians(epsilon)) * math.sin(math.radians(lambda_moon_corrected)),
        math.cos(math.radians(lambda_moon_corrected))
    ))
    delta_moon = math.degrees(math.asin(
        math.sin(math.radians(epsilon)) * math.sin(math.radians(lambda_moon_corrected))
    ))
    alpha_moon = alpha_moon % 360.0
    
    # 항성시 계산
    GMST = greenwich_mean_sidereal_time(JD, T)
    GAST = apparent_sidereal_time(GMST, T)
    
    # 지역 항성시(LST) 계산
    LST = (GAST + longitude) % 360.0
    
    # 시간각(Hour Angle) 계산 ( -180도에서 +180도 )
    HA_moon = (LST - alpha_moon + 180) % 360 - 180
    
    # 고도와 방위각 계산
    altitude_moon, azimuth_moon = equatorial_to_horizontal(delta_moon, HA_moon, latitude)
    
    # 대기 굴절 보정 적용
    altitude_moon_corrected = altitude_moon + atmospheric_refraction_correction(altitude_moon)
    
    # 달의 거리 계산 (고차항 포함)
    distance_moon = moon_distance(T, D_moon, M_moon, F_moon)
    
    # 태양의 진황경 계산 (위상각 계산에 필요)
    lambda_sun = calculate_lambda_sun(T)
    
    # 달의 위상각과 조도 계산
    phase_angle_moon, illumination = calculate_phase_angle_geo(lambda_sun, lambda_moon, beta_moon, distance_moon, T)

    # 달의 조도(E_MT) 계산
    E_MT = calculate_moon_illuminance(phase_angle_moon, distance_moon)
    
    # 달빛 표면 조도(E_surface_moon) 계산
    E_surface_moon = calculate_surface_illuminance_moon(E_MT, altitude_moon_corrected)
    
    # 대기를 통과한 달빛 조도(E_DN_moon) 계산
    E_DN_moon = calculate_E_DN_moon(E_MT, altitude_moon_corrected)
    
     # 표면에서의 달빛 조도(E_DV_moon) 계산
    cos_theta_s_moon = calculate_cos_theta_s_moon(altitude_moon_corrected, azimuth_moon)  
    E_DV_moon = calculate_E_DV_moon(E_DN_moon, altitude_moon_corrected, azimuth_moon)
    
    # 반사된 빛의 양(R_light_moon) 계산
    R_light_moon = calculate_R_light_moon(E_DV_moon)
    
    return {
        'altitude': altitude_moon_corrected,
        'azimuth': azimuth_moon,
        'lambda_moon': lambda_moon,
        'beta_moon': beta_moon,
        'distance_moon': distance_moon,
        'phase_angle_moon': phase_angle_moon,
        'illumination': illumination,  
        'E_MT': E_MT,  
        'E_surface_moon': E_surface_moon,  
        'E_DN_moon': E_DN_moon,  
        'E_DV_moon': E_DV_moon,  
        'cos_theta_s_moon': cos_theta_s_moon, 
        'R_light_moon': R_light_moon  
    }
