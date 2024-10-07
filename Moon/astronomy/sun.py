# astronomy/sun.py

import math
from .helpers import julian_day, get_julian_centuries, greenwich_mean_sidereal_time, \
    apparent_sidereal_time, mean_obliquity_of_ecliptic, equatorial_to_horizontal, atmospheric_refraction_correction

K_norm = 1.0  # Normal lobe contribution (assuming dull white surface)
C_aerosol = 0.0218  # Clear
C_rayleigh = 0.008735
C_ozone = 0.02975
C_atmosphere = C_aerosol + C_rayleigh + C_ozone
#C_atmosphere = 0.21 simple(clear)

def solar_mean_longitude(T):
    """태양의 평균 황경을 계산합니다."""
    return (280.46646 + 36000.76983 * T + 0.0003032 * T**2) % 360.0

def solar_mean_anomaly(T):
    """태양의 평균 근점을 계산합니다."""
    return (357.52911 + 35999.05029 * T - 0.0001537 * T**2) % 360.0

def eccentricity_earth_orbit(T):
    """지구 궤도의 이심률을 계산합니다."""
    return 0.016708634 - 0.000042037 * T - 0.0000001267 * T**2

def sun_equation_of_center(T, M_sun):
    """태양의 중심차를 계산합니다."""
    M_rad = math.radians(M_sun)
    C_sun = (1.914602 - 0.004817 * T - 0.000014 * T**2) * math.sin(M_rad) \
            + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) \
            + 0.000289 * math.sin(3 * M_rad)
    return C_sun

def calculate_lambda_sun(T):
    """태양의 진황경(λ)을 계산합니다."""
    L0_sun = solar_mean_longitude(T)
    M_sun = solar_mean_anomaly(T)
    C_sun = sun_equation_of_center(T, M_sun)
    true_long_sun = L0_sun + C_sun
    omega = 125.04 - 1934.136 * T
    lambda_sun = true_long_sun - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return lambda_sun % 360.0

def calculate_sun_earth_distance(v, e):
    """
    태양과 지구 사이의 거리(AU)를 계산합니다.
    
    Parameters:
        v (float): 진이각 (True Anomaly) in degrees.
        e (float): 지구 궤도의 이심률.
        
    Returns:
        float: 지구-태양 거리 (AU)
    """
    v_rad = math.radians(v)
    r_sun_earth = (1.000001018 * (1 - e**2)) / (1 + e * math.cos(v_rad))  # AU 단위
    return r_sun_earth

def calculate_extraterrestrial_solar_illuminance(JD, T):
    """
    태양의 외계 조도(E_ST)를 계산하는 함수.
    
    Parameters:
        JD: 줄리안 날짜
        T: 줄리안 세기 (JD 기반)
        
    Returns:
        E_ST: 외계 조도 (lux)
    """
    E_SC = 127500  # 태양 상수 (lux)
    epsilon = eccentricity_earth_orbit(T)  # 지구 궤도의 이심률을 동적으로 계산
    
    # E_ST 계산
    term1 = (1 + epsilon * math.cos(2 * math.pi * (JD - 2) / 365.2)) ** 2
    term2 = 1 - epsilon ** 2
    E_ST = E_SC * (term1 / term2)
    
    return E_ST


def calculate_E_DN_sun(E_ST, altitude_sun_deg):
    """
    대기를 통과한 태양 조도 E_DN_sun을 계산하는 함수.
    
    Parameters:
        E_ST: 태양 외계 조도 (lux)
        altitude_sun_deg: 태양의 고도 (degrees)
        
    Returns:
        E_DN_sun: 대기를 통과한 태양 조도 (lux)
    """
    # 고도를 라디안으로 변환
    altitude_sun_rad = math.radians(altitude_sun_deg)

    # 최대 공기 질량 m 값은 500으로 제한
    m_limit = 500

    if altitude_sun_rad > -1:
        # 광학적 공기 질량 m 계산
        m = 1 / (math.cos(math.pi / 2 - altitude_sun_rad) + 0.15 * (3.885 + altitude_sun_rad)**-1.253)
        
        # m 값이 m_limit을 초과하지 않도록 제한
        if m > m_limit:
            m = m_limit

    else:
        # 고도가 -1 라디안 이하인 경우, m = 500
        m = 500
    
    # E_DN_sun 계산
    try:
        E_DN_sun = E_ST * math.exp(-C_atmosphere * m)
    except OverflowError:
        E_DN_sun = 0  # 예외가 발생할 경우, E_DN_sun을 0으로 설정

    return E_DN_sun

def calculate_cos_theta_s_sun(altitude_sun, azimuth_sun):
    """
    태양의 고도와 방위각을 바탕으로 입사각과 표면 법선 사이의 각도 cos(theta_s_sun)를 계산하는 함수.
    
    Parameters:
        altitude_sun: 태양의 고도 (degrees)
        azimuth_sun: 태양의 방위각 (degrees)
    
    Returns:
        cos_theta_s_sun: 입사각과 표면 법선 사이의 각도 cos(theta_s_sun)
    """
    # 표면이 평평한 경우 표면 법선 벡터 (0, 0, 1)
    surface_normal = (0, 0, 1)
    
    # 태양의 고도와 방위각을 바탕으로 빛의 입사 벡터를 계산
    altitude_sun_rad = math.radians(altitude_sun)
    azimuth_sun_rad = math.radians(azimuth_sun)
    
    # 입사 벡터 (빛이 들어오는 방향 벡터) 계산
    incident_vector = (
        math.cos(altitude_sun_rad) * math.cos(azimuth_sun_rad),  # x
        math.cos(altitude_sun_rad) * math.sin(azimuth_sun_rad),  # y
        math.sin(altitude_sun_rad)  # z
    )
    
    # 벡터 내적 계산 (표면 법선 벡터와 입사 벡터의 내적)
    dot_product = (surface_normal[0] * incident_vector[0] +
                   surface_normal[1] * incident_vector[1] +
                   surface_normal[2] * incident_vector[2])
    
    # 표면 법선 벡터와 입사 벡터의 크기
    norm_surface = math.sqrt(surface_normal[0]**2 + surface_normal[1]**2 + surface_normal[2]**2)
    norm_incident = math.sqrt(incident_vector[0]**2 + incident_vector[1]**2 + incident_vector[2]**2)
    
    # cos(theta_s_sun) 계산
    cos_theta_s_sun = dot_product / (norm_surface * norm_incident)
    
    return cos_theta_s_sun

def calculate_E_DV_sun(E_DN_sun, altitude_sun, azimuth_sun):
    """
    표면에서의 태양 조도 E_DV_sun을 계산하는 함수.
    
    Parameters:
        E_DN_sun: 대기를 통과한 태양 조도 (lux)
        altitude_sun: 태양의 고도 (degrees)
        azimuth_sun: 태양의 방위각 (degrees)
        
    Returns:
        E_DV_sun: 표면에서의 태양 조도 (lux)
    """
    if altitude_sun > 0:
        # 벡터 내적을 통해 cos(theta_s_sun) 계산
        cos_theta_s_sun = calculate_cos_theta_s_sun(altitude_sun, azimuth_sun)
        
        # E_DV_sun 계산
        E_DV_sun = E_DN_sun * cos_theta_s_sun
    else:
        E_DV_sun = 0  # 태양이 지평선 아래에 있으면 조도는 0
    
    return E_DV_sun

def calculate_R_light_sun(E_DV_sun):
    """
    반사된 태양광의 양 R_light_sun을 계산하는 함수.
    
    Parameters:
        E_DV_sun: 표면에서의 태양 조도 (lux)
        
    Returns:
        R_light_sun: 반사된 태양광의 양 (lux)
    """
    # 반사된 빛의 양 계산
    R_light_sun = E_DV_sun * K_norm * (1 / math.pi)
    return R_light_sun

def calculate_Twilight_part1(altitude_sun, k=0.7951):
    # E(h) = 400 * e^(kh) for h between 0 and -6
    E_h_1 = 400 * math.exp(k * altitude_sun)
    return E_h_1

def calculate_Twilight_part2(altitude_sun, k=0.4728):
    # E(h) = 3.4 * e^(k*(h+6)) for h between -6 and -12
    E_h_2 = 3.4 * math.exp(k * (altitude_sun + 6))
    return E_h_2

def calculate_R_Twilight_sun(altitude_sun, R_light_sun, E_h_1, E_h_2):
    # 기본값 설정 (모든 조건에 걸리지 않을 경우 기본값 0)
    R_Twilight_sun = 0

    if altitude_sun > 0:
        R_Twilight_sun = R_light_sun + 400
    elif altitude_sun >= -6:
        # E_h_1 값을 계산
        E_h_1 = calculate_Twilight_part1(altitude_sun)
        R_Twilight_sun = E_h_1
    elif altitude_sun >= -12:
        # E_h_2 값을 계산
        E_h_2 = calculate_Twilight_part2(altitude_sun)
        R_Twilight_sun = E_h_2

    return R_Twilight_sun
        

def calculate_sun_position(year, month, day, hour, minute, second, latitude, longitude):
    """
    태양의 위치(고도, 방위각)와 지구-태양 거리(AU), 지표면 조도(E_surface_sun)를 계산합니다.
    모든 시간은 UTC 시간 기준으로 합니다.
    """
    # 줄리안 날짜 및 세기 계산
    JD = julian_day(year, month, day, hour, minute, second)
    T = get_julian_centuries(JD)
    
    # 태양의 평균 황경, 평균 근점, 이심률, 중심차 계산
    L0_sun = solar_mean_longitude(T)
    M_sun = solar_mean_anomaly(T)
    e = eccentricity_earth_orbit(T)  # 이심률 계산
    C_sun = sun_equation_of_center(T, M_sun)
    
    # 태양의 진황경 계산
    lambda_sun = calculate_lambda_sun(T)
    
    # 황도 경사각 계산
    epsilon0_sun = mean_obliquity_of_ecliptic(T)
    epsilon_sun = epsilon0_sun + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * T))
    
    # 적경(RA)과 적위(Dec) 계산
    alpha_sun = math.degrees(math.atan2(math.cos(math.radians(epsilon_sun)) * math.sin(math.radians(lambda_sun)), math.cos(math.radians(lambda_sun))))
    delta_sun = math.degrees(math.asin(math.sin(math.radians(epsilon_sun)) * math.sin(math.radians(lambda_sun))))
    
    # 적경을 0~360도로 조정
    alpha_sun = alpha_sun % 360.0
    
    # 항성시 계산
    GMST = greenwich_mean_sidereal_time(JD, T)
    GAST = apparent_sidereal_time(GMST, T)
    
    # 지역 항성시(LST) 계산
    LST = (GAST + longitude) % 360.0
    
    # 시간각(Hour Angle) 계산 (-180도에서 +180도)
    HA_sun = (LST - alpha_sun + 180) % 360 - 180
    
    # 고도와 방위각 계산
    altitude_sun, azimuth_sun = equatorial_to_horizontal(delta_sun, HA_sun, latitude)
    
    # 대기 굴절 보정 적용
    altitude_sun_corrected = altitude_sun + atmospheric_refraction_correction(altitude_sun)
    
    # 진이각 계산
    v = (M_sun + C_sun) % 360.0  # 진이각 (True Anomaly)
    
    # 지구-태양 거리(AU) 계산
    r_sun_earth = calculate_sun_earth_distance(v, e)
    
    # 태양 외계 조도 계산
    E_ST = calculate_extraterrestrial_solar_illuminance(JD, T)
       
    # 대기를 통과한 태양 조도 E_DN_sun 계산
    E_DN_sun = calculate_E_DN_sun(E_ST, altitude_sun_corrected)
    
    # 표면에서의 태양 조도 E_DV_sun 계산
    cos_theta_s_sun = calculate_cos_theta_s_sun(altitude_sun_corrected, azimuth_sun) 
    E_DV_sun = calculate_E_DV_sun(E_DN_sun, altitude_sun_corrected, azimuth_sun)
    
    # 반사된 태양광 R_light_sun 계산
    R_light_sun = calculate_R_light_sun(E_DV_sun)

    E_h_1 = calculate_Twilight_part1(altitude_sun, k=0.7951)
    
    E_h_2 = calculate_Twilight_part2(altitude_sun, k=0.4728)

    R_Twilight_sun = calculate_R_Twilight_sun(altitude_sun, R_light_sun, E_h_1, E_h_2)
    
    # 데이터를 딕셔너리로 반환
    return {
        'altitude_sun': altitude_sun_corrected,
        'azimuth_sun': azimuth_sun,
        'lambda_sun': lambda_sun,
        'r_sun_earth': r_sun_earth,
        'E_ST': E_ST,
        'E_DN_sun': E_DN_sun,
        'E_DV_sun': E_DV_sun,
        'cos_theta_s_sun': cos_theta_s_sun, 
        'R_light_sun': R_light_sun,
        'R_Twilight_sun': R_Twilight_sun
    }

