import os
import sys
import logging
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
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

GRID_MARKER_SIZE = 12
LAT_MIN, LAT_MAX = 32.5, 38.5
LON_MIN, LON_MAX = 125.0, 130.0

def main():
    # 1) r_light.csv와 merged_result_202506240102.csv 데이터 로드
    csv_path = Path("r_light.csv")
    meteo_path = Path("merged_result_202506240102.csv")
    if not csv_path.exists() or not meteo_path.exists():
        logger.error("필요한 csv 파일이 없습니다.")
        return
    df = pd.read_csv(csv_path)
    df_meteo = pd.read_csv(meteo_path)
    logger.info(f"Loaded {len(df)} records from {csv_path}")
    logger.info(f"Loaded {len(df_meteo)} records from {meteo_path}")

    # 2) 시간 컬럼 추출 (YYYYMMDDHH 형식)
    time_cols = [c for c in df.columns if c.isdigit() and len(c) == 10]
    if not time_cols:
        logger.warning("time_cols가 비어 있습니다. 생성할 이미지가 없습니다. CSV 파일과 시간 조건을 확인하세요.")
        return

    # 3) 지도 투영 설정
    proj = ccrs.LambertConformal(
        central_longitude=126.0,
        central_latitude=38.0,
        standard_parallels=(30.0, 60.0)
    )

    # 4) 리스크 카테고리 정의
    bins   = [-0.1, 50, 100, 200, float('inf')]
    labels = ['위험', '경고', '주의', '관심']
    risk_colors = {
        '위험': '#d9534f',    # muted red
        '경고': '#f0ad4e',    # muted orange
        '주의': '#ffe066',    # soft yellow
        '관심': '#5cb85c'     # muted green
    }

    for tcol in time_cols:
        if tcol not in df.columns:
            logger.warning(f"{tcol} 컬럼이 데이터에 없습니다. 건너뜁니다.")
            continue

        # 조도(mlux) 컬럼 생성
        df['illum_mlux'] = df[tcol] * 1000.0

        # 1. 조도 이미지 렌더링 (그대로)
        logger.info(f"Rendering illuminance map for {tcol} (mlux)")
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
        sc = ax.scatter(
            df['lon'], df['lat'],
            c=df['illum_mlux'],
            s=GRID_MARKER_SIZE,
            marker='s',
            cmap='cividis',
            vmin=0, vmax=300,
            transform=ccrs.PlateCarree()
        )
        cbar = plt.colorbar(sc, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label('Illuminance (mlux)')
        ax.set_title(f"Illuminance at {tcol} (KST)")
        out_fname = csv_path.parent / f"illum_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

        # 2. 영향평가 이미지 렌더링 (그대로)
        logger.info(f"Rendering risk map for {tcol}")
        df['risk_cat'] = pd.cut(df['illum_mlux'], bins=bins, labels=labels)
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
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
        ax.set_title(f"Illuminance Risk at {tcol} (KST)")
        out_fname = csv_path.parent / f"illum_risk_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

        # 3. 조도+풍속(WS10) 이미지 (조도: r_light.csv, 마커: merged_result_202506240102.csv)
        ws10_bins = [0, 5, 10, 15, float('inf')]
        ws10_labels = ['0~5m/s', '5~10m/s', '10~15m/s', '15m/s↑']
        ws10_colors = ['#5cb85c', '#ffe066', '#f0ad4e', '#d9534f']
        df_meteo['ws10_cat'] = pd.cut(df_meteo['WS10'].astype(float), bins=ws10_bins, labels=ws10_labels, right=False)
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
        sc = ax.scatter(
            df['lon'], df['lat'],
            c=df['illum_mlux'],
            s=GRID_MARKER_SIZE,
            marker='s',
            cmap='cividis',
            vmin=0, vmax=300,
            transform=ccrs.PlateCarree()
        )
        plt.colorbar(sc, ax=ax, orientation='vertical', pad=0.02).set_label('Illuminance (mlux)')

        # 풍속 마커
        for label, color in zip(ws10_labels, ws10_colors):
            sub = df_meteo[
                (df_meteo['ws10_cat'] == label) &
                (df_meteo['WS10'] != -99.9) &
                (df_meteo['LAT'] >= LAT_MIN) & (df_meteo['LAT'] <= LAT_MAX) &
                (df_meteo['LON'] >= LON_MIN) & (df_meteo['LON'] <= LON_MAX)
            ]
            if not sub.empty:
                ax.scatter(
                    sub['LON'], sub['LAT'],
                    s=20, marker='o', color=color, edgecolor='k', linewidth=0.5,
                    transform=ccrs.PlateCarree()
                )

        # --- 모든 구간이 범례에 나오도록 handles 생성 ---
        ws10_handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markeredgecolor='k', linewidth=0, markersize=8, label=label)
            for label, color in zip(ws10_labels, ws10_colors)
        ]
        ax.legend(handles=ws10_handles, title='지상풍속', loc='upper right', prop=font_prop)

        ax.set_title(f"Illuminance + Wind (WS10) at {tcol} (KST)")
        out_fname = csv_path.parent / f"illum_ws10_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

        # 4. 조도+시정(VIS) 이미지 (조도: r_light.csv, 마커: merged_result_202506240102.csv)
        vis_bins = [0, 1000, 3000, 5000, float('inf')]
        vis_labels = ['0~1km', '1~3km', '3~5km', '5km↑']
        vis_colors = ['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c']
        df_meteo['vis_cat'] = pd.cut(df_meteo['VIS'].astype(float), bins=vis_bins, labels=vis_labels, right=False)
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
        sc = ax.scatter(
            df['lon'], df['lat'],
            c=df['illum_mlux'],
            s=GRID_MARKER_SIZE,
            marker='s',
            cmap='cividis',
            vmin=0, vmax=300,
            transform=ccrs.PlateCarree()
        )
        plt.colorbar(sc, ax=ax, orientation='vertical', pad=0.02).set_label('Illuminance (mlux)')

        for label, color in zip(vis_labels, vis_colors):
            sub = df_meteo[
                (df_meteo['vis_cat'] == label) &
                (df_meteo['VIS'] != -99.9) &
                (df_meteo['LAT'] >= LAT_MIN) & (df_meteo['LAT'] <= LAT_MAX) &
                (df_meteo['LON'] >= LON_MIN) & (df_meteo['LON'] <= LON_MAX)
            ]
            if not sub.empty:
                ax.scatter(
                    sub['LON'], sub['LAT'],
                    s=20, marker='o', color=color, edgecolor='k', linewidth=0.5,
                    transform=ccrs.PlateCarree()
                )

        vis_handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markeredgecolor='k', linewidth=0, markersize=8, label=label)
            for label, color in zip(vis_labels, vis_colors)
        ]
        ax.legend(handles=vis_handles, title='지상시정', loc='upper right', prop=font_prop)
        ax.set_title(f"Illuminance + Visibility (VIS) at {tcol} (KST)")
        out_fname = csv_path.parent / f"illum_vis_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

        # 5. 조도+운저고도(CH_LOW) 이미지 (조도: r_light.csv, 마커: merged_result_202506240102.csv)
        chlow_bins = [0, 500, 1000, 1500, float('inf')]
        chlow_labels = ['0~500ft', '500~1000ft', '1000~1500ft', '1500ft↑']
        chlow_colors = ['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c']
        df_meteo['chlow_cat'] = pd.cut(df_meteo['CH_LOW'].astype(float), bins=chlow_bins, labels=chlow_labels, right=False)
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
        sc = ax.scatter(
            df['lon'], df['lat'],
            c=df['illum_mlux'],
            s=GRID_MARKER_SIZE,
            marker='s',
            cmap='cividis',
            vmin=0, vmax=300,
            transform=ccrs.PlateCarree()
        )
        plt.colorbar(sc, ax=ax, orientation='vertical', pad=0.02).set_label('Illuminance (mlux)')

        for label, color in zip(chlow_labels, chlow_colors):
            sub = df_meteo[
                (df_meteo['chlow_cat'] == label) &
                (df_meteo['CH_LOW'] != -99.9) &
                (df_meteo['LAT'] >= LAT_MIN) & (df_meteo['LAT'] <= LAT_MAX) &
                (df_meteo['LON'] >= LON_MIN) & (df_meteo['LON'] <= LON_MAX)
            ]
            if not sub.empty:
                ax.scatter(
                    sub['LON'], sub['LAT'],
                    s=20, marker='o', color=color, edgecolor='k', linewidth=0.5,
                    transform=ccrs.PlateCarree()
                )

        chlow_handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markeredgecolor='k', linewidth=0, markersize=8, label=label)
            for label, color in zip(chlow_labels, chlow_colors)
        ]
        ax.legend(handles=chlow_handles, title='운저고도', loc='upper right', prop=font_prop)
        ax.set_title(f"Illuminance + Cloud Base Height (CH_LOW) at {tcol} (KST)")
        out_fname = csv_path.parent / f"illum_chlow_{tcol}.png"
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

    logger.info("All images generated.")

if __name__ == '__main__':
    main()
