from dash import Dash, html, dcc, Input, Output, State, callback_context
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
from calculate3 import get_illuminance_at, get_moon_altitude
import pandas as pd
import os
import subprocess

# 1) 최근 기상청 릴리즈 시각 계산
release_hours = [2, 5, 8, 11, 14, 17, 20, 23]
now_utc = datetime.now(timezone.utc)
now_kst = now_utc + timedelta(hours=9)
release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)
tmfc_datetime = max(rt for rt in release_times if rt <= now_kst)
tmfc = tmfc_datetime.strftime("%Y%m%d%H")
tmfc_utc = tmfc_datetime - timedelta(hours=9)

# CSV 파일 경로
SHARED_DIR = os.path.join("assets", "clouds", tmfc)
SHARED_FILE = os.path.join(SHARED_DIR, f"clouds_all_{tmfc}.csv")

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.Label("Latitude:"), 
        dcc.Input(id="lat-input", type="number", value=37.5665, step=0.0001),
        html.Label("Longitude:"), 
        dcc.Input(id="lon-input", type="number", value=126.9780, step=0.0001),
        html.Button("<", id="prev-day", n_clicks=0),
        dcc.DatePickerSingle(id="date-picker", date=now_kst.date()),
        html.Button(">", id="next-day", n_clicks=0),
    ], style={"display": "flex", "gap": "0.5rem", "alignItems": "center"}),
    html.Div([
        dcc.Checklist(
            id="data-options",
            options=[
                {"label":"clouds", "value":"clouds"},
                {"label":"artificial_lights", "value":"artificial_lights"}
            ],
            value=[],
            labelStyle={"display":"inline-block","margin-right":"1rem"}
        ),
        html.Span(id="atl-label", style={"margin-left":"1rem"})
    ], style={"margin":"1rem 0","display":"flex","alignItems":"center"}),
    dcc.Graph(id="combined-graph")
])

@app.callback(
    Output("date-picker","date"),
    Input("prev-day","n_clicks"), Input("next-day","n_clicks"),
    State("date-picker","date")
)
def shift_date(prev_clicks, next_clicks, current_date):
    ctx = callback_context
    if not ctx.triggered:
        return current_date
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    d = datetime.fromisoformat(current_date)
    return (d - timedelta(days=1) if btn=="prev-day" else d + timedelta(days=1)).date()

@app.callback(
    [Output("combined-graph","figure"), Output("atl-label","children")],
    Input("lat-input","value"),
    Input("lon-input","value"),
    Input("date-picker","date"),
    Input("data-options","value")
)
def update_graph(lat, lon, date_str, options):
    date = datetime.fromisoformat(date_str)
    hours_utc = list(range(9,24))  # 09–23 UTC
    times_kst, illum_values, moon_alts, cloud_texts = [], [], [], []

    # CSV 로드
    df = pd.read_csv(SHARED_FILE) if os.path.exists(SHARED_FILE) else None
    cloud_vals, ntl_val = None, 0
    if df is not None:
        lat_c = "lat" if "lat" in df.columns else "latitude"
        lon_c = "lon" if "lon" in df.columns else "longitude"
        d2 = (df[lat_c]-lat)**2 + (df[lon_c]-lon)**2
        row = df.loc[d2.idxmin()]
        if "clouds" in options:
            fc = sorted(c for c in df.columns if c not in [lat_c, lon_c])
            cloud_vals = row[fc].tolist()
        if "artificial_lights" in options:
            ntl_val = int(row.get("ntl", row.get("NTL",0)))

    # 조도·달고도 계산
    for hr in hours_utc:
        lux = get_illuminance_at(date.year,date.month,date.day,hr,0,lat,lon)
        mlux = lux*1000 + 1
        cl_lbl = ""
        if cloud_vals is not None:
            lead = int((datetime(date.year,date.month,date.day,hr,tzinfo=timezone.utc)
                        - tmfc_utc).total_seconds()/3600)
            idx = lead // 3
            if 0 <= idx < len(cloud_vals):
                v = cloud_vals[idx]
                mlux *= {1:0.8,3:0.5,4:0.2}.get(v,1)
                cl_lbl = {1:'맑음',3:'구름 많음',4:'흐림'}[v]
        illum_values.append(mlux)
        moon_alts.append(get_moon_altitude(date.year,date.month,date.day,hr,0,lat,lon))
        times_kst.append((datetime(date.year,date.month,date.day,hr,tzinfo=timezone.utc)
                           + timedelta(hours=9)).strftime("%H:%M"))
        cloud_texts.append(cl_lbl)

    # 4단계 색상 매핑
    colors = []
    for v in illum_values:
        if v <= 50:      colors.append("red")
        elif v <= 100:   colors.append("orange")
        elif v <= 200:   colors.append("yellow")
        else:            colors.append("green")

    # 서브플롯 생성
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    # --- 배경용 Bar trace (row=1) ---
    max_bar_h = 10**3
    fig.add_trace(
        go.Bar(
            x=times_kst,
            y=[max_bar_h]*len(times_kst),
            marker_color=colors,
            opacity=0.5,
            showlegend=False,
            hoverinfo='none',
            marker_line_width=0,
            width=1
        ),
        row=1, col=1
    )

    # Illuminance 선+마커+텍스트
    fig.add_trace(
        go.Scatter(
            x=times_kst,
            y=illum_values,
            mode="lines+markers+text",
            text=[f"{v:.1f}" for v in illum_values],
            textposition="bottom center",
            marker=dict(color="black", size=6),
            line=dict(color="black"),
            showlegend=False,            
            customdata=cloud_texts,
            hovertemplate="Time: %{x}<br>Illuminance: %{y:.2f} mlux<br>Cloud: %{customdata}<extra></extra>"
        ),
        row=1, col=1
    )

    # Moon altitude 선 그래프
    fig.add_trace(
        go.Scatter(
            x=times_kst,
            y=moon_alts,
            mode="lines",
            showlegend=False,    
            hovertemplate="Time: %{x}<br>Moon Altitude: %{y:.2f}°<extra></extra>"
        ),
        row=2, col=1
    )

    # --- Legend용 더미 trace ---
    legend_map = {"위험":"red", "경고":"orange", "주의":"yellow", "관심":"green"}
    for name, col in legend_map.items():
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=col),
                name=name
            )
        )

    # --- 범례 글자 크기 조정 ---
    fig.update_layout(
        legend=dict(
            font=dict(size=24)
        )
    )

    # 축 설정 & 레이아웃
    fig.update_xaxes(title_text="Time (KST)", row=1, col=1, showticklabels=True, tickangle=0)
    fig.update_xaxes(title_text="Time (KST)", row=2, col=1, showticklabels=True, tickangle=0)
    fig.update_yaxes(title_text="Illuminance (millilux)", row=1, col=1,
                     type="log", range=[0,3], autorange=False)
    fig.update_yaxes(title_text="Altitude (°)", row=2, col=1,
                     range=[0,70], autorange=False)

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.00, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=40, b=40),
        height=650,
        bargap=0,
        bargroupgap=0
    )

    atl_text = f"artificial lights: {ntl_val}" if "artificial_lights" in options else ""
    return fig, atl_text

if __name__ == "__main__":
    if not os.path.exists(SHARED_FILE):
        os.makedirs(SHARED_DIR, exist_ok=True)
        try:
            subprocess.run(["python", "cloud_api.py"], check=True)
        except Exception as e:
            print("Failed to generate cloud CSV:", e)
    app.run(debug=True)
