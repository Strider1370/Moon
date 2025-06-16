import math
import numpy as np
from skyfield.api import load, Topos
from datetime import datetime, timedelta
import pandas as pd

#--------------------------------------
# SPICE Ephemeris 불러오기
eph = load('de440.bsp')
ts  = load.timescale()
pressure_pa = 101325  # Pa
#--------------------------------------

def sun_illuminance(alt_sun_deg):
    if alt_sun_deg >= 0:
        return 400
    elif alt_sun_deg >= -6:
        return 400 * math.exp(0.7951 * alt_sun_deg)
    elif alt_sun_deg >= -12:
        return 3.4 * math.exp(0.4728 * (alt_sun_deg + 6))
    elif alt_sun_deg >= -18:
        return 0.25 * math.exp(0.920244 * (alt_sun_deg + 12))
    else:
        return 0

def get_illuminance_details(year, month, day, hour, minute, lat, lon):
    t      = ts.utc(year, month, day, hour, minute)
    t_prev = ts.utc(t.utc_datetime() - timedelta(days=1))

    earth    = eph['earth']
    moon     = eph['moon']
    sun      = eph['sun']
    observer = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)

    moon_app = observer.at(t).observe(moon).apparent()
    sun_app  = observer.at(t).observe(sun).apparent()

    alt_m, az_m, dist_m = moon_app.altaz()
    alt_s, az_s, _      = sun_app.altaz()
    alt_m_deg           = alt_m.degrees
    dist_m_km           = dist_m.km
    z_deg               = 90 - alt_m_deg

    if alt_m_deg <= 0:
        # 달이 지평선 아래
        return {
            'hour_utc': hour,
            'm': None, 'X': None,
            'Ev_A': 0, 'Ev_B': 0, 'Ev_C': 0,
            'Ev_D': 0, 'Ev_E': 0, 'Ev_F': 0,
            'Ev_G': 0,
            'R_sun': sun_illuminance(alt_s.degrees),
            'R_total': sun_illuminance(alt_s.degrees)
        }

    # 위상각 & magnitude
    separation  = moon_app.separation_from(sun_app).degrees
    phase_angle = 180 - separation

    illuminated_fraction = moon_app.fraction_illuminated(sun)

    m = -12.73 + 0.026 * abs(phase_angle) + 4e-9 * phase_angle**4

    # 대기감쇠 X
    X = (-0.140194 * z_deg / (-91.674385 + z_deg)) - 0.03

    Ev_A = 10**(-0.4 * (m + X + 16.57)) * 10.7637
    Ev_B = Ev_A * math.sin(math.radians(alt_m_deg))
    if abs(phase_angle) < 6:
        Ev_C = Ev_B * (1 + 0.4 * (6 - abs(phase_angle)) / 6)
    else:
        Ev_C = Ev_B

    frac_t   = moon_app.fraction_illuminated(sun)
    frac_prev= observer.at(t_prev).observe(moon).apparent().fraction_illuminated(sun)
    waning   = frac_t < frac_prev

    Ev_D = Ev_C * (1 - 0.00026 * abs(phase_angle)) if waning else Ev_C
    Ev_E = Ev_D * (384400 / dist_m_km)**2
    Ev_F = Ev_E * ((18.964 * math.exp(-0.229 * (pressure_pa / 101325))) / 15.083)
    Ev_G = (Ev_F + 0.0008) * 0.863

    R_sun     = sun_illuminance(alt_s.degrees)
    R_total   = Ev_G + R_sun

    return {
        'hour_utc': hour, 'alt_m_deg': alt_m_deg,
        'm': m, 'X': X, 'dist_m_km': dist_m_km, 'illuminated_fraction': illuminated_fraction,
        'Ev_A': Ev_A, 'Ev_B': Ev_B, 'Ev_C': Ev_C,
        'Ev_D': Ev_D, 'Ev_E': Ev_E, 'Ev_F': Ev_F,
        'Ev_G': Ev_G,
        'R_sun': R_sun,
        'R_total': R_total
    }

if __name__ == "__main__":
    date_str = input("Enter date (YYYYMMDD): ").strip()
    year  = int(date_str[0:4])
    month = int(date_str[4:6])
    day   = int(date_str[6:8])

    # 서울 좌표
    lat, lon = 37.5665, 126.9780

    records = []
    for hour in range(11, 24):           # 11UTC부터 23UTC까지
        rec = get_illuminance_details(year, month, day, hour, 0, lat, lon)
        records.append(rec)

    df = pd.DataFrame(records)
    csv_file = f"{date_str}_illuminance_seoul.csv"
    df.to_csv(csv_file, index=False, float_format="%.6f")
    print(f"Saved results to {csv_file}")
