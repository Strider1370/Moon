from skyfield.api import load, Topos
import numpy as np

# 관측자 위치와 시간 입력 (서울: 위도 37.57° N, 경도 126.98° E, 시간: 2025년 4월 3일 15:00 UTC)
latitude = 37.57
longitude = 126.98

# 시간 스케일과 시간 객체 생성
ts = load.timescale()
t = ts.utc(2025, 4, 3, 15, 0, 0)

# 로컬에 저장된 de440.bsp 파일 사용
eph = load('de440.bsp')

# 지구 객체와 관측자 위치(서울) 객체 생성
earth = eph['earth']
observer = earth + Topos(latitude_degrees=latitude, longitude_degrees=longitude)

# 태양과 달 객체
sun = eph['sun']
moon = eph['moon']

# 관측자 위치에서 천체 관측 (astrometric → apparent)
sun_apparent = observer.at(t).observe(sun).apparent()
moon_apparent = observer.at(t).observe(moon).apparent()

# 태양의 적경(RA), 적위(Dec), 거리 계산
ra_sun, dec_sun, distance_sun = sun_apparent.radec()
# 달의 적경(RA), 적위(Dec), 거리 계산
ra_moon, dec_moon, distance_moon = moon_apparent.radec()

# 지평 좌표 (고도, 방위각) 계산
alt_sun, az_sun, _ = sun_apparent.altaz()
alt_moon, az_moon, _ = moon_apparent.altaz()

# 달과 태양의 위상각 (두 천체의 각 분리각)
phase_angle = moon_apparent.separation_from(sun_apparent)
# 달의 조명된 면적 비율 (illuminated fraction): (1 + cos(phase_angle))/2
illuminated_fraction = (1 + np.cos(np.radians(phase_angle.degrees))) / 2

# RA를 시간 단위에서 도 단위로 변환 (1시간 = 15°)
ra_sun_deg = ra_sun.hours * 15
ra_moon_deg = ra_moon.hours * 15

print("== 태양 정보 ==")
print("적경 (RA): {:.2f}° (변환)".format(ra_sun_deg))
print("적위 (Dec): {:.2f}°".format(dec_sun.degrees))
print("거리 (AU): {:.6f}".format(distance_sun.au))
print("고도: {:.2f}°".format(alt_sun.degrees))
print("방위각: {:.2f}°".format(az_sun.degrees))
print()

print("== 달 정보 ==")
print("적경 (RA): {:.2f}° (변환)".format(ra_moon_deg))
print("적위 (Dec): {:.2f}°".format(dec_moon.degrees))
print("거리: {}".format(distance_moon))
print("고도: {:.2f}°".format(alt_moon.degrees))
print("방위각: {:.2f}°".format(az_moon.degrees))
print()

print("== 달의 위상 ==")
print("위상각: {:.2f}°".format(phase_angle.degrees))
print("Illuminated fraction: {:.2f}".format(illuminated_fraction))
