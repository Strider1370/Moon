# ========================
# Imports
# ========================
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone
from calculate3 import get_illuminance_at, get_moon_altitude
import pandas as pd
import os
import subprocess

# ========================
# Constants & Config
# ========================
CITY_COORDS = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대전": (36.3504, 127.3845),
    "제주": (33.4996, 126.5312)
}
DATE_FORMAT = 'YYYY/MM/DD'

# ========================
# Time & File Setup
# ========================
kst = timezone(timedelta(hours=9))
now_kst = datetime.now(timezone.utc).astimezone(kst)
release_hours = [2, 5, 8, 11, 14, 17, 20, 23]
release_times = []
for h in release_hours:
    rt = now_kst.replace(hour=h, minute=0, second=0, microsecond=0)
    if rt > now_kst:
        rt -= timedelta(days=1)
    release_times.append(rt)
tmfc_datetime = max(rt for rt in release_times if rt <= now_kst)
tmfc_utc = tmfc_datetime.astimezone(timezone.utc)
SHARED_DIR = os.path.join("assets", "clouds", tmfc_datetime.strftime("%Y%m%d%H"))
SHARED_FILE = os.path.join(SHARED_DIR, f"clouds_all_{tmfc_datetime.strftime('%Y%m%d%H')}.csv")

# ========================
# App Initialization
# ========================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# ========================
# Layout
# ========================
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                # ── 도시 드롭다운 ──────────────────────────────────
                dbc.Col(
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText("도시"),
                            dcc.Dropdown(
                                id='city-dropdown',
                                options=[{'label': k, 'value': k} for k in CITY_COORDS],
                                value='서울',
                                clearable=False,
                                style={'width': '80px'}
                            )
                        ],
                        size='md'
                    ),
                    width='auto'
                ),

                # ── 위도 입력 ────────────────────────────────────
                dbc.Col(
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText("위도"),
                            dbc.Input(
                                id='lat-input', type='number',
                                step=0.0001, style={'width': '100px'}
                            )
                        ],
                        size='md'
                    ),
                    width='auto'
                ),

                # ── 경도 입력 (기존) ────────────────────────────────
                dbc.Col(
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText("경도"),
                            dbc.Input(
                                id='lon-input', type='number',
                                step=0.0001, style={'width' : '100px'}
                            )
                        ],
                        size='md'
                    ),
                    width='auto'
                ),

                # ──── 날짜: 화살표 버튼 제거 + 상단 라벨 ────
                dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText("날짜"),
                                    dcc.DatePickerSingle(
                                        id='date-picker',
                                        className='dp-md',          # ← 위 CSS가 적용될 대상
                                        date=now_kst.date(),
                                        display_format=DATE_FORMAT,
                                        min_date_allowed=datetime(2000, 1, 1),
                                        max_date_allowed=datetime(2100, 12, 31),
                                        style={'width': '100px'}    # 숫자 입력과 폭 맞추기
                                    )
                                ],
                                size='md'
                            ),
                            width='auto'
                        )
            ],
            justify='center',
            align='center',
            className='my-3'
        ),

        dbc.Row(
            [
                dbc.Col(
                    dcc.Checklist(
                        id='cloud-option',
                        options=[{'label': '구름 데이터', 'value': 'clouds'}],
                        value=[],
                        labelStyle={'margin-right': '1rem'}
                    ),
                    width='auto'
                ),
                dbc.Col(
                    dcc.Checklist(
                        id='impact-option',
                        options=[{'label': '영향평가', 'value': 'impact'}],
                        value=[],
                        labelStyle={'margin-right': '1rem'}
                    ),
                    width='auto'
                ),
                dbc.Col(
                    html.Span(id='ntl-label', style={'font-weight': 'bold'}),
                    width='auto'
                )
            ],
            justify='center',
            align='center',
            className='mb-4'
        ),

        dbc.Row(
            dbc.Col(dcc.Graph(id='combined-graph'))
        )
    ],
    fluid=True
)

# ========================
# Callbacks
# ========================

# ── 1. 도시 선택 → 위·경도 자동 입력 ────────────────────────────
@app.callback(
    [Output('lat-input', 'value'), Output('lon-input', 'value')],
    Input('city-dropdown', 'value')
)
def callback_update_coords(city):
    return CITY_COORDS.get(city, (37.5665, 126.9780))

# ── 2. 그래프+NTL 라벨 업데이트 ────────────────────────────────
@app.callback(
    [Output('combined-graph', 'figure'),
     Output('ntl-label', 'children')],
    [Input('lat-input',   'value'),
     Input('lon-input',   'value'),
     Input('date-picker', 'date'),
     Input('cloud-option','value'),
     Input('impact-option','value')]
)

def callback_update_graph(lat, lon, date_str, cloud_opt, impact_opt):
    # ===============================================================
    # ① 공통 부분 ─ 데이터 준비 (타임스탬프·구름·조도·달 고도 계산)
    # ===============================================================
    show_bg    = 'impact' in impact_opt
    show_cloud = 'clouds' in cloud_opt
    date       = datetime.fromisoformat(date_str)

    # 10 분 간격(UTC 09–23) 타임스탬프
    start_utc  = datetime(date.year, date.month, date.day, 9, 0, tzinfo=timezone.utc)
    times_utc  = [start_utc + timedelta(minutes=10 * i)
                  for i in range(((23 - 9) * 60 // 10) + 1)]

    # 구름·NTL(인공광) 데이터
    df   = pd.read_csv(SHARED_FILE) if os.path.exists(SHARED_FILE) else None
    vals, ntl = None, 0
    if df is not None and lat is not None and lon is not None:
        latc, lonc = ('lat', 'lon') if 'lat'  in df.columns else ('latitude', 'longitude')
        row        = df.loc[((df[latc] - lat)**2 + (df[lonc] - lon)**2).idxmin()]
        ntl        = int(row.get('ntl', row.get('NTL', 0)))
        if show_cloud:
            vals = [row[c] for c in df.columns if c not in [latc, lonc, 'ntl', 'NTL']]

    illum_vals, moon_alts, cloud_lbls = [], [], []
    for t in times_utc:
        lux = get_illuminance_at(t.year, t.month, t.day, t.hour, t.minute, lat, lon)
        ml  = lux * 1000 + 1                                    # mlux (log 축의 0 회피용 +1)
        lbl = '데이터 없음'
        if vals is not None:
            idx = int((t - tmfc_utc).total_seconds() / 3600 / 3)
            if 0 <= idx < len(vals):
                ml  *= {1: 0.8, 3: 0.5, 4: 0.2}.get(vals[idx], 1)
                lbl  = {1: '맑음', 3: '구름 많음', 4: '흐림'}.get(vals[idx], '데이터없음')
        illum_vals.append(ml)
        moon_alts.append(get_moon_altitude(t.year, t.month, t.day, t.hour, t.minute, lat, lon))
        cloud_lbls.append(lbl)

    # KST 라벨 및 1 시간 간격 추출
    times_kst    = [(t + timedelta(hours=9)).strftime('%H:%M') for t in times_utc]
    hourly_idx   = [i for i, t in enumerate(times_utc) if t.minute == 0]
    hourly_times = [times_kst[i]    for i in hourly_idx]
    hourly_illum = [illum_vals[i]   for i in hourly_idx]
    hourly_moon  = [moon_alts[i]    for i in hourly_idx]
    hourly_cloud = [cloud_lbls[i]   for i in hourly_idx]
    colors_10min = ['red' if v<=50 else 'orange' if v<=100 else 'yellow' if v<=200 else 'green'
                    for v in illum_vals]

    # ===============================================================
    # ② 첫번째 그래프 ─ 조도(mlux)
    #     • 배경 막대 : 10 분 위험등급
    #     • 선 그래프 : 10 분 조도
    #     • 마커      : 1 시간 조도(+구름 툴팁)
    # ===============================================================
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.1)

    # (a) 배경 막대
    fig.add_trace(
        go.Bar(
            x=times_kst, y=[1000]*len(times_kst),
            marker_color=colors_10min, opacity=0.5, marker_line_width=0,
            width=1, showlegend=False, visible=show_bg, hoverinfo='skip'
        ), row=1, col=1
    )

    # (b) 10 분 선 그래프
    fig.add_trace(
        go.Scatter(
            x=times_kst, y=illum_vals, mode='lines',
            line=dict(color='#1f77b4'), hoverinfo='skip', showlegend=False
        ), row=1, col=1
    )

    # --- 2.2 mlux 기준선 -------------------------------------------
    fig.add_hline(
        y=2.2,                       # y 값
        line_dash='longdash',             # 점선
        line_color='red',
        row=1, col=1                 # 첫 번째 그래프에만
    )

    # (c) 1 시간 마커
    fig.add_trace(
        go.Scatter(
            x=hourly_times, y=hourly_illum, mode='markers',
            marker=dict(color='#1f77b4', size=6),
            customdata=hourly_cloud,
            hovertemplate=('시간: %{x}<br>조도: %{y:.2f} mlux'
                           + ('<br>구름: %{customdata}' if show_cloud else '')
                           + '<extra></extra>'),
            showlegend=False
        ), row=1, col=1
    )

    # 위험도 범례
    for name, color in {'위험':'red','경고':'orange','주의':'yellow','안전':'green'}.items():
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers',
                                 marker=dict(color=color, size=14),
                                 name=name, visible=show_bg))

    # ===============================================================
    # ③ 두번째 그래프 ─ 달 고도(°)
    #     • 선 그래프 : 10 분 달 고도
    #     • 마커      : 1 시간 달 고도
    # ===============================================================
        
    # (a) 10 분 선 그래프
    
    fig.add_trace(
        go.Scatter(
            x=times_kst, y=moon_alts, mode='lines',
            line=dict(color='black'), hoverinfo='skip', showlegend=False
        ), row=2, col=1
    )

    # (b) 1 시간 마커
    fig.add_trace(
        go.Scatter(
            x=hourly_times, y=hourly_moon, mode='markers',
            marker=dict(color='black', size=6),
            hovertemplate='시간: %{x}<br>달 고도: %{y:.2f}°<extra></extra>',
            showlegend=False
        ), row=2, col=1
    )

    fig.add_hline(
        y=30,                       # y 값
        line_dash='longdash',             # 점선
        line_color='red',
        row=2, col=1                 # 첫 번째 그래프에만
    )

    # ===============================================================
    # ④ 축·레이아웃 공통 설정
    # ===============================================================
    axis_opts = dict(showline=False, showgrid=True, gridcolor='whitesmoke', gridwidth=1)
    fig.update_xaxes(tickmode='array', tickvals=hourly_times, ticktext=hourly_times,
                     title_text='시간 (KST)', row=1, col=1, **axis_opts)
    fig.update_xaxes(tickmode='array', tickvals=hourly_times, ticktext=hourly_times,
                     title_text='시간 (KST)', row=2, col=1, **axis_opts)

    fig.update_yaxes(title_text='달빛 밝기 (millilux)', row=1, col=1,
                     type='log', range=[0, 3], autorange=False,
                     tickmode='array', tickvals=[1,10,100,1000], **axis_opts)
    fig.update_yaxes(title_text='달 고도각 (°)', row=2, col=1,
                     range=[0, 70], autorange=False, **axis_opts)
   
    # ── 간격 확보용 domain 조정 ──
    fig.update_yaxes(domain=[0.50, 1.00], row=1, col=1)
    fig.update_yaxes(domain=[0.00, 0.40], row=2, col=1)

    fig.update_layout(
        legend=dict(font=dict(size=24), orientation='h', y=1.15,
                    x=0.5, xanchor='center'),
        margin=dict(l=40, r=40, t=40, b=40),
        height=650, bargap=0, bargroupgap=0,
        plot_bgcolor='white', paper_bgcolor='white'
    )

    ntl_text = '인공광 있음 (1)' if ntl else '인공광 없음 (0)'
    return fig, ntl_text


# ========================
# Run Server
# ========================
if __name__ == "__main__":
    if not os.path.exists(SHARED_FILE):
        os.makedirs(SHARED_DIR, exist_ok=True)
        try:
            subprocess.run(["python", "cloud_api.py"], check=True)
        except Exception as e:
            print("Failed to generate cloud CSV:", e)
    app.run(debug=True)
