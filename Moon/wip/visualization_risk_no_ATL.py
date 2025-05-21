# visualize_illuminance.py
# ------------------------------------
# - Computes latest TMFC based on KMA release hours
# - Ensures cloud CSV exists (runs cloud_api.py if missing)
# - Reads cloud forecast CSV at assets/clouds/{tmfc}/clouds_all_{tmfc}.csv
# - Calculates illuminance at each grid point (parallelized with multiprocessing), applies cloud attenuation,
#   converts to millilux, categorizes into risk levels, and visualizes with scatter plots on Lambert Conformal projection.
# - Uses four discrete categories: Danger, Caution, Warning, Safe
# - Displays terminal progress bars for overall forecasts and illuminance calculation

import os
import logging
import subprocess
from datetime import datetime, timedelta, timezone
import multiprocessing

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from calculate import get_illuminance_at
from tqdm import tqdm
from matplotlib.lines import Line2D

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Grid marker size (approx 5km x 5km)
GRID_MARKER_SIZE = 12
# Marker opacity
MARKER_OPACITY = 1

# Cloud attenuation factors
CLOUD_FACTOR = {1: 0.8, 3: 0.5, 4: 0.2}
DEFAULT_FACTOR = 1.0

# Parser for forecast column labels
def parse_time(ts_str):
    return int(ts_str[:4]), int(ts_str[4:6]), int(ts_str[6:8]), int(ts_str[8:10]), 0

# Worker for multiprocessing pool
def illum_worker(args):
    y, m, d, H, M, lat, lon = args
    return get_illuminance_at(y, m, d, H, M, lat, lon)

# Main execution
def main():
    # 1) Calculate latest TMFC (KST)
    release_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    release_times = []
    for h in release_hours:
        rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
        if rt > now_kst:
            rt -= timedelta(days=1)
        release_times.append(rt)
    tmfc = max(rt for rt in release_times if rt <= now_kst).strftime("%Y%m%d%H")
    logger.info(f"Latest TMFC: {tmfc}")

    # 2) CSV path
    csv_path = os.path.join("assets", "clouds", tmfc, f"clouds_all_{tmfc}.csv")
    logger.info(f"Loading CSV: {csv_path}")
    if not os.path.exists(csv_path):
        logger.warning("CSV missing; running cloud_api.py...")
        subprocess.run(["python", "cloud_api.py"], check=True)
        logger.info("cloud_api.py done")

    # 3) Load data
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} records")

    # 4) Prepare forecast columns
    time_cols = [c for c in df.columns if c.isdigit() and len(c) == 10]
    df[time_cols] = df[time_cols].fillna(0).astype(int)

    # Filter time columns: only UTC hours 09-23
    #filtered_time_cols = [c for c in time_cols if 9 <= int(c[8:10]) <= 23]
    filtered_time_cols = ['2025051423']

    # 5) Map projection and bounds
    LAT_MIN, LAT_MAX = 32.5, 38.5
    LON_MIN, LON_MAX = 125.0, 130.0
    proj = ccrs.LambertConformal(
        central_longitude=126.0,
        central_latitude=38.0,
        standard_parallels=(30.0, 60.0)
    )

    # 6) Multiprocessing setup
    n_workers = multiprocessing.cpu_count()
    logger.info(f"Using {n_workers} processes for illuminance calculation")

    # Risk category definitions
    bins  = [-0.1, 50, 100, 200, float('inf')]
    labels = ['Danger', 'Caution', 'Warning', 'Safe']
    risk_colors = {
        'Danger': 'red',
        'Caution': 'orange',
        'Warning': 'yellow',
        'Safe': 'green'
    }

    # 7) Loop over filtered forecasts
    for tcol in tqdm(filtered_time_cols, desc="Processing forecasts", unit="forecast"):
        y, m, d, H, M = parse_time(tcol)

        # Build args list
        coords = [(y, m, d, H, M, lat, lon) for lat, lon in zip(df['lat'], df['lon'])]
        # Parallel illuminance calculation
        with multiprocessing.Pool(processes=n_workers) as pool:
            R_light = list(
                tqdm(
                    pool.imap(illum_worker, coords),
                    total=len(coords), desc="Calc illuminance", unit="pt"
                )
            )
        df['R_light'] = R_light

        # Apply cloud factor & convert to millilux
        df['illum_mlux'] = (
            df['R_light'] *
            df[tcol].map(CLOUD_FACTOR).fillna(DEFAULT_FACTOR) *
            1000.0
        )

        # Categorize into risk levels
        df['risk_cat'] = pd.cut(df['illum_mlux'], bins=bins, labels=labels)

        # 7b) Render scatter
        logger.info(f"Rendering scatter for {tcol}")
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
        ax.coastlines(resolution='10m')
        ax.add_feature(cfeature.BORDERS.with_scale('10m'))
        ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')

        # Add tick labels at map edges every 1 degree (bottom & left only)
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                          linewidth=0, color='black', alpha=0,
                          xlocs=np.arange(LON_MIN, LON_MAX+1, 1),
                          ylocs=np.arange(LAT_MIN, LAT_MAX+1, 1))

        # Plot discrete risk categories with opacity
        for cat, color in risk_colors.items():
            subset = df[df['risk_cat'] == cat]
            if not subset.empty:
                ax.scatter(
                    subset['lon'], subset['lat'],
                    s=GRID_MARKER_SIZE,
                    marker='s',
                    color=color,
                    alpha=MARKER_OPACITY,
                    transform=ccrs.PlateCarree()
                )

        # Always include all categories in legend, positioned lower right
        handles = [
            Line2D([0], [0], marker='s', color=risk_colors[cat], linestyle='None', markersize=6, alpha=MARKER_OPACITY)
            for cat in labels
        ]
        ax.legend(handles, labels, title='Risk Level', loc='lower right')

        ax.set_title(f"Illuminance at {tcol}")

        # Save figure
        out_fname = os.path.join(os.path.dirname(csv_path), f"illum_risk_{tcol}.png")
        plt.savefig(out_fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"Saved {out_fname}")

    logger.info("All forecasts processed and saved.")

if __name__ == '__main__':
    main()
