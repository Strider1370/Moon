import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta, timezone
import multiprocessing
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from calculate3 import get_illuminance_at
from tqdm import tqdm
from matplotlib.lines import Line2D
import matplotlib.font_manager as fm

# ── 한글 폰트 세팅 ───────────────────────────────────────────
font_path = r"C:\Windows\Fonts\malgun.ttf"
font_prop = fm.FontProperties(fname=font_path, size=10)
plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

# ── 로거 설정 ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── 상수 ───────────────────────────────────────────────────────
GRID_MARKER_SIZE = 12
CLOUD_FACTOR = {1: 0.8, 3: 0.5, 4: 0.2}
DEFAULT_FACTOR = 1.0

# ── 시간 파싱 ─────────────────────────────────────────────────
def parse_time(tcol: str):
    """
    tcol: "YYYYMMDDHH" (KST 기준)
    반환: (year, month, day, hour, minute) UTC 기준
    """
    dt_kst = datetime.strptime(tcol, "%Y%m%d%H")
    dt_utc = dt_kst - timedelta(hours=9)
    return dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute

def illum_worker(args):
    y, m, d, H, M, lat, lon = args
    return get_illuminance_at(y, m, d, H, M, lat, lon)

def main(tmfc_override=None):
    # 1) Calculate or set TMFC (KST)
    release_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    if tmfc_override is not None:
        tmfc = tmfc_override
        logger.info(f"TMFC overridden by user: {tmfc}")
    else:
        release_times = []
        for h in release_hours:
            rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
            if rt > now_kst:
                rt -= timedelta(days=1)
            release_times.append(rt)
        tmfc = max(rt for rt in release_times if rt <= now_kst).strftime("%Y%m%d%H")
        logger.info(f"Latest TMFC: {tmfc}")

    # 2) CSV 경로
    csv_path = Path("assets") / "clouds" / tmfc / f"clouds_all_{tmfc}.csv"
    logger.info(f"Loading CSV: {csv_path}")
    if not csv_path.exists():
        logger.warning("CSV missing; running cloud_api.py...")
        subprocess.run([sys.executable, "cloud_api.py"], check=True)
        logger.info("cloud_api.py done")
    
    # 3) 데이터 로드
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} records")
    
    # 4) 처리할 시간 컬럼 필터링
    all_time_cols = [c for c in df.columns if c.isdigit() and len(c) == 10]

    # 20~23시, 0~8시까지 매시간 (KST)
    evening_hours = list(range(20, 24)) + list(range(0, 9))

    # 구름자료(3시간 간격) 컬럼 추출 (실제 데이터에 맞게)
    cloud_cols = sorted(all_time_cols, key=lambda x: datetime.strptime(x, "%Y%m%d%H"))

    # 1시간 단위 time_cols 생성 (evening_hours만, csv에 없어도 생성)
    if cloud_cols:
        first_cloud_time = datetime.strptime(cloud_cols[0], "%Y%m%d%H")
        last_cloud_time = datetime.strptime(cloud_cols[-1], "%Y%m%d%H")
        time_cols = []
        t = first_cloud_time
        while t <= last_cloud_time:
            if t.hour in evening_hours:
                col = t.strftime("%Y%m%d%H")
                time_cols.append(col)
            t += timedelta(hours=1)
    else:
        time_cols = []

    # 각 시간별로 사용할 구름자료 매핑
    def get_cloud_col(tcol):
        t = datetime.strptime(tcol, "%Y%m%d%H")
        if not cloud_cols:
            raise ValueError("cloud_cols가 비어 있습니다. 구름자료 컬럼을 확인하세요.")
        prev_clouds = [c for c in cloud_cols if datetime.strptime(c, "%Y%m%d%H") <= t]
        if prev_clouds:
            return max(prev_clouds, key=lambda c: datetime.strptime(c, "%Y%m%d%H"))
        else:
            return cloud_cols[0]

    logger.info(f"Forecast times to process (KST hours): {[c[-2:] for c in time_cols]}")
    logger.info(f"all_time_cols: {all_time_cols}")
    logger.info(f"cloud_cols: {cloud_cols}")
    logger.info(f"first_cloud_time: {first_cloud_time if cloud_cols else None}")
    logger.info(f"time_cols: {time_cols}")
    
    # 5) 지도 투영 설정
    LAT_MIN, LAT_MAX = 32.5, 38.5
    LON_MIN, LON_MAX = 125.0, 130.0
    proj = ccrs.LambertConformal(
        central_longitude=126.0,
        central_latitude=38.0,
        standard_parallels=(30.0, 60.0)
    )
    
    # 6) 멀티프로세스 풀 생성 (재사용)
    n_workers = multiprocessing.cpu_count()
    logger.info(f"Using {n_workers} processes for illuminance calculation")
    pool = multiprocessing.Pool(processes=n_workers)
    
    # 7) 리스크 카테고리 정의 (labels ↔ colors 일치)
    bins   = [-0.1, 50, 100, 200, float('inf')]
    labels = ['위험', '경고', '주의', '관심']
    risk_colors = {
        '위험': '#d9534f',    # muted red
        '경고': '#f0ad4e',    # muted orange
        '주의': '#ffe066',    # soft yellow
        '관심': '#5cb85c'     # muted green
    }
    
    # 8) 예측 시각별 반복 처리
    for tcol in tqdm(time_cols, desc="Processing forecasts", unit="forecast"):
        y, m, d, H, M = parse_time(tcol)

        coords = [(y, m, d, H, M, lat, lon) for lat, lon in zip(df['lat'], df['lon'])]
        R_light = list(
            tqdm(
                pool.imap(illum_worker, coords),
                total=len(coords), desc="Calc illuminance", unit="pt"
            )
        )
        df['R_light'] = R_light

        # 사용할 구름자료 컬럼 결정
        cloud_col = get_cloud_col(tcol)
        if cloud_col not in df.columns:
            logger.warning(f"구름자료 컬럼 {cloud_col}이(가) 데이터에 없습니다. 건너뜁니다.")
            continue

        df['illum_mlux'] = (
            df['R_light'] *
            df[cloud_col].map(CLOUD_FACTOR).fillna(DEFAULT_FACTOR) *
            1000.0
        )
        df['risk_cat'] = pd.cut(df['illum_mlux'], bins=bins, labels=labels)
        
        # 시각화
        logger.info(f"Rendering scatter for {tcol}")
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.BORDERS.with_scale('10m'))
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
        
        # 카테고리별 점 그리기
        for cat, color in risk_colors.items():
            sub = df[df['risk_cat'] == cat]
            if not sub.empty:
                ax.scatter(
                    sub['lon'], sub['lat'],
                    s=GRID_MARKER_SIZE,
                    marker='s',
                    color=color,
                    transform=ccrs.PlateCarree()
                )
        
        # 강제 범례 생성 (한글 + 크기 조정)
        legend_elements = [
            Line2D([0], [0], marker='s', color=color, linestyle='', markersize=8, label=label)
            for label, color in risk_colors.items()
        ]
        ax.legend(
            handles=legend_elements,
            title='위험 수준',
            loc='lower right',
            prop=font_prop,
            fontsize=12,
            title_fontsize=14
        )
        
        ax.set_title(f"Illuminance at {tcol} (KST)")
        
        # 파일 저장
        out_fname = csv_path.parent / f"illum_risk_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")
    
    if not time_cols:
        logger.warning("time_cols가 비어 있습니다. 생성할 이미지가 없습니다. CSV 파일과 시간 조건을 확인하세요.")
        return



    pool.close()
    pool.join()
    logger.info("All selected forecasts processed and saved.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tmfc', type=str, default=None, help='TMFC(YYYYMMDDHH) 직접 지정')
    args = parser.parse_args()
    main(tmfc_override=args.tmfc)
