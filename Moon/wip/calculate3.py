import math
from datetime import datetime, timezone, timedelta

# ------------------------ helpers.py 내용 ------------------------
def julian_day(year, month, day, hour, minute, second):
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    JD_day = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    JD_fraction = (hour + minute / 60 + second / 3600) / 24.0
    JD = JD_day + JD_fraction
    return JD

def get_julian_centuries(JD):
    return (JD - 2451545.0) / 36525.0

def mean_obliquity_of_ecliptic(T):
    seconds = 21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))
    e0 = 23 + (26 + (seconds / 60)) / 60
    return e0

def greenwich_mean_sidereal_time(JD, T):
    GMST = 280.46061837 + 360.98564736629 * (JD - 2451545) + \
           0.000387933 * T**2 - T**3 / 38710000
    return GMST % 360.0

def apparent_sidereal_time(GMST, T):
    omega = 125.04 - 1934.136 * T
    delta_psi = -0.00478 * math.sin(math.radians(omega))
    epsilon = mean_obliquity_of_ecliptic(T) + 0.00256 * math.cos(math.radians(omega))
    GAST = GMST + delta_psi * math.cos(math.radians(epsilon))
    return GAST % 360.0

def equatorial_to_horizontal(delta, HA, lat):
    dec_rad = math.radians(delta)
    HA_rad = math.radians(HA)
    lat_rad = math.radians(lat)

    altitude = math.degrees(math.asin(math.sin(dec_rad) * math.sin(lat_rad) +
                                     math.cos(dec_rad) * math.cos(lat_rad) * math.cos(HA_rad)))

    azimuth = math.degrees(math.atan2(-math.sin(HA_rad),
                                     math.tan(dec_rad) * math.cos(lat_rad) -
                                     math.sin(lat_rad) * math.cos(HA_rad)))
    azimuth = (azimuth + 360) % 360
    return altitude, azimuth

# ------------------------ sun.py 내용 ------------------------
def solar_mean_anomaly(T):
    return (357.52911 + 35999.05029 * T - 0.0001537 * T**2) % 360.0

def sun_equation_of_center(T, M_sun):
    M_rad = math.radians(M_sun)
    C_sun = (1.914602 - 0.004817 * T - 0.000014 * T**2) * math.sin(M_rad) \
            + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) \
            + 0.000289 * math.sin(3 * M_rad)
    return C_sun

def calculate_lambda_sun(T):
    L0_sun = (280.46646 + 36000.76983 * T + 0.0003032 * T**2) % 360.0
    M_sun = solar_mean_anomaly(T)
    C_sun = sun_equation_of_center(T, M_sun)
    omega = 125.04 - 1934.136 * T
    lambda_sun = L0_sun + C_sun - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return lambda_sun % 360.0

# ------------------------ moon.py 일부 ------------------------
def moon_mean_anomaly(T):
    return (134.96340251 + 477198.8675613 * T + 0.0087423 * T**2 +
            T**3 / 69699 - T**4 / 14712000) % 360.0

def moon_mean_longitude(T):
    return (218.3164477 + 481267.88123421 * T - 0.0015786 * T**2 +
            T**3 / 538841 - T**4 / 65194000) % 360.0

def moon_mean_elongation(T):
    return (297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 +
            T**3 / 545868 - T**4 / 113065000) % 360.0

def moon_equation_of_center(T, M_moon, D_moon, F_moon):
    M_rad = math.radians(M_moon)
    D_rad = math.radians(D_moon)
    F_rad = math.radians(F_moon)
    C = (
        6.289 * math.sin(M_rad)
        + 1.274 * math.sin(2 * D_rad - M_rad)
        + 0.658 * math.sin(2 * D_rad)
        + 0.214 * math.sin(2 * M_rad)
        + 0.11 * math.sin(D_rad)
        + 0.046 * math.sin(M_rad + F_rad)
        + 0.014 * math.sin(2 * D_rad - 2 * M_rad)
        + 0.011 * math.sin(M_rad - F_rad)
    )
    return C

def moon_ecliptic_latitude(T):
    F_moon = (93.272 + 483202.0175 * T) % 360.0
    beta_moon = 5.128 * math.sin(math.radians(F_moon))
    return beta_moon

def moon_distance(T, D_moon, M_moon, F_moon):
    return 385000.56 - 20905.355 * math.cos(math.radians(M_moon))

def sun_illuminance(altitude_sun_deg):
    if altitude_sun_deg >= 0:
        return 400
    elif altitude_sun_deg >= -6:
        return 400 * math.exp(0.7951 * altitude_sun_deg)
    elif altitude_sun_deg >= -12:
        return 3.4 * math.exp(0.4728 * (altitude_sun_deg + 6))
    elif altitude_sun_deg >= -18:
        return 0.25 * math.exp(0.920244 * (altitude_sun_deg + 12))
    else:
        return 0

def get_illuminance_at(year, month, day, hour, minute, latitude, longitude):
    astro = calculate_positions(year, month, day, hour, minute, 0, latitude, longitude)

    altitude_deg = astro['Alt_moon']
    distance_moon_km = astro['Distance_moon']
    phase_angle = astro['Phase_angle']
    z_deg = 90 - altitude_deg
    pressure_pa = 101325

    if altitude_deg <= 0:
        Ev_G = 0.0
    else:
        separation = 180 - phase_angle
        m = -12.73 + 0.026 * abs(phase_angle) + 4e-9 * phase_angle**4
        X = (-0.140194 * z_deg / (-91.674385 + z_deg)) - 0.03
        Ev_A = 10**(-0.4 * (m + X + 16.57)) * 10.7637
        Ev_B = Ev_A * max(0.0, math.sin(math.radians(altitude_deg)))
        if abs(phase_angle) < 6:
            Ev_C = Ev_B * (1 + 0.4 * (6 - abs(phase_angle)) / 6)
        else:
            Ev_C = Ev_B
        is_waning = False  # 위상 변화 정보 없으므로 생략 또는 추정 필요
        if is_waning:
            Ev_D = Ev_C * (1 - 0.00026 * abs(phase_angle))
        else:
            Ev_D = Ev_C
        Ev_E = Ev_D * (384400 / distance_moon_km)**2
        Ev_F = Ev_E * ((18.964 * math.exp(-0.229 * (pressure_pa / 101325))) / 15.083)
        Ev_G = (Ev_F + 0.0008) * 0.863

    R_light_sun = sun_illuminance(astro['Alt_sun'])
    R_light_total = Ev_G + R_light_sun
    return R_light_total

def calculate_positions(year, month, day, hour, minute, second, latitude, longitude):
    JD = julian_day(year, month, day, hour, minute, second)
    T = get_julian_centuries(JD)

    lambda_sun = calculate_lambda_sun(T)
    epsilon = mean_obliquity_of_ecliptic(T)
    alpha_sun = math.degrees(math.atan2(
        math.cos(math.radians(epsilon)) * math.sin(math.radians(lambda_sun)),
        math.cos(math.radians(lambda_sun))
    )) % 360.0
    delta_sun = math.degrees(math.asin(
        math.sin(math.radians(epsilon)) * math.sin(math.radians(lambda_sun))
    ))

    M_moon = moon_mean_anomaly(T)
    L_moon = moon_mean_longitude(T)
    D_moon = moon_mean_elongation(T)
    F_moon = (93.272 + 483202.0175 * T) % 360.0
    C_moon = moon_equation_of_center(T, M_moon, D_moon, F_moon)
    lambda_moon = L_moon + C_moon
    beta_moon = moon_ecliptic_latitude(T)
    alpha_moon = math.degrees(math.atan2(
        math.cos(math.radians(epsilon)) * math.sin(math.radians(lambda_moon)),
        math.cos(math.radians(lambda_moon))
    )) % 360.0
    delta_moon = math.degrees(math.asin(
        math.sin(math.radians(epsilon)) * math.sin(math.radians(lambda_moon))
    ))
    distance = moon_distance(T, D_moon, M_moon, F_moon)

    cos_psi = math.cos(math.radians(beta_moon)) * math.cos(math.radians(lambda_moon - lambda_sun))
    psi = math.degrees(math.acos(cos_psi))

    GMST = greenwich_mean_sidereal_time(JD, T)
    GAST = apparent_sidereal_time(GMST, T)
    LST = (GAST + longitude) % 360
    HA_sun = (LST - alpha_sun + 180) % 360 - 180
    HA_moon = (LST - alpha_moon + 180) % 360 - 180

    alt_sun, az_sun = equatorial_to_horizontal(delta_sun, HA_sun, latitude)
    alt_moon, az_moon = equatorial_to_horizontal(delta_moon, HA_moon, latitude)

    return {
        'JD': JD,
        'T': T,
        'RA_sun': alpha_sun,
        'Dec_sun': delta_sun,
        'RA_moon': alpha_moon,
        'Dec_moon': delta_moon,
        'Distance_moon': distance,
        'Phase_angle': psi,
        'LST': LST,
        'HA_sun': HA_sun,
        'HA_moon': HA_moon,
        'Alt_sun': alt_sun,
        'Az_sun': az_sun,
        'Alt_moon': alt_moon,
        'Az_moon': az_moon
    }

if __name__ == '__main__':
    lux = get_illuminance_at(2025, 7, 15, 12, 0, 37.57, 126.98)
    alt_moon = calculate_positions(2025, 7, 15, 12, 0, 0, 37.57, 126.98)['Alt_moon']
    distance_moon = calculate_positions(2025, 7, 15, 12, 0, 0, 37.57, 126.98)['Distance_moon']
    print(f"Total illuminance: {lux:.2f} lux, Moon altitude: {alt_moon:.2f}°, moon_distance: {distance_moon:.2f} km")
