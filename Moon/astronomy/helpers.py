# astronomy/helpers.py

import math
from datetime import datetime, timezone, timedelta

def julian_day(year, month, day, hour, minute, second):
    """
    주어진 날짜와 시간에 대한 줄리안 날짜를 계산합니다.
    """
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    JD_day = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    JD_fraction = (hour + minute / 60 + second / 3600) / 24.0
    JD = JD_day + JD_fraction
    return JD

def get_datetime_utc(year, month, day, hour, minute, second, timezone_offset):
    """로컬 시간을 UTC datetime으로 변환합니다."""
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc) - timedelta(hours=timezone_offset)

def get_julian_centuries(JD):
    """J2000.0으로부터의 줄리안 세기를 계산합니다."""
    return (JD - 2451545.0) / 36525.0

def greenwich_mean_sidereal_time(JD, T):
    """
    그리니치 평균 항성시(GMST)를 계산합니다.
    """
    GMST = 280.46061837 + 360.98564736629 * (JD - 2451545) + \
           0.000387933 * T**2 - T**3 / 38710000
    return GMST % 360.0

def apparent_sidereal_time(GMST, T):
    """
    겉보기 항성시(GAST)를 계산합니다.
    """
    omega = 125.04 - 1934.136 * T
    delta_psi = -0.00478 * math.sin(math.radians(omega))
    epsilon = mean_obliquity_of_ecliptic(T) + 0.00256 * math.cos(math.radians(omega))
    GAST = GMST + delta_psi * math.cos(math.radians(epsilon))
    return GAST % 360.0

def mean_obliquity_of_ecliptic(T):
    """
    황도 경사각(ε)의 평균 값을 계산합니다.
    """
    seconds = 21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))
    e0 = 23 + (26 + (seconds / 60)) / 60
    return e0

def equatorial_to_horizontal(delta, HA, lat):
    """
    적경(RA)과 적위를 고도와 방위각으로 변환합니다.
    """
    dec_rad = math.radians(delta)
    HA_rad = math.radians(HA)
    lat_rad = math.radians(lat)
    
    altitude = math.degrees(math.asin(math.sin(dec_rad) * math.sin(lat_rad) +
                                     math.cos(dec_rad) * math.cos(lat_rad) * math.cos(HA_rad)))
    
    azimuth = math.degrees(math.atan2(-math.sin(HA_rad),
                                     math.tan(dec_rad) * math.cos(lat_rad) -
                                     math.sin(lat_rad) * math.cos(HA_rad)))
    azimuth = (azimuth + 360) % 360  # 방위각을 0~360도로 조정
    return altitude, azimuth

def atmospheric_refraction_correction(altitude):
    """
    고도에 대한 대기 굴절 보정을 적용합니다.
    Meeus의 공식 기반으로 하되, 고도가 극단적인 값일 때
    보정이 과도하게 적용되지 않도록 일부 경험적 제한을 추가하였습니다.
    """
    if altitude > 85:  # 고도가 85도 이상일 때 굴절 보정을 적용하지 않음
        R = 0.0
    elif altitude > 5:  # 고도가 5도 이상이면 Meeus의 공식 그대로 적용
        R = (58.1 / math.tan(math.radians(altitude))
             - 0.07 / math.pow(math.tan(math.radians(altitude)), 3)
             + 0.000086 / math.pow(math.tan(math.radians(altitude)), 5)) / 3600.0
    elif altitude > -0.575:  # 고도가 낮을 때는 Meeus의 권장식 사용
        R = (1735.0 + altitude * (-518.2 + altitude * (103.4 + altitude * (-12.79 + altitude * 0.711)))) / 3600.0
    else:
        R = 0.0  # 고도가 음수일 경우 굴절 보정을 적용하지 않음
    return R
