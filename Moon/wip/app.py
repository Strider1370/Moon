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
import sys
import subprocess

# PyInstaller에서 리소스 파일 경로를 처리하는 함수
def resource_path(relative_path):
    """ PyInstaller에서 리소스 파일 경로를 처리 """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 실행 파일 내부의 리소스 경로
        return os.path.join(sys._MEIPASS, relative_path)
    # 개발 환경에서의 리소스 경로
    return os.path.join(os.path.abspath("."), relative_path)

# ========================
# Constants & Config
# ========================
CITY_COORDS = {
    "서울": (37.5665, 126.9780),
    "흑산도": (34.6822, 125.4286),
    "임자도": (35.0642, 126.0592),
    "백령도": (37.9697, 124.6300),
    "울릉도": (37.4847, 130.9053),
    "연평도": (37.6667, 124.7000),
    "마라도": (33.1172, 126.2672),
    "거문도": (34.0181, 127.3081),
    "소청도": (37.8036, 124.7372)
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
SHARED_DIR = resource_path(os.path.join("assets", "clouds", tmfc_datetime.strftime("%Y%m%d%H")))
SHARED_FILE = resource_path(os.path.join(SHARED_DIR, f"clouds_all_{tmfc_datetime.strftime('%Y%m%d%H')}.csv"))

# ========================
# App Initialization
# ========================
app = Dash(__name__, external_stylesheets=[resource_path("assets/bootstrap.min.css")], serve_locally=True, suppress_callback_exceptions=True)

# ========================
# Layout
# ========================
main_layout = dbc.Container(
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
                                style={'width': '100px'}
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
                ),
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
                    dcc.Checklist(
                        id='vis-option',
                        options=[{'label': '지상시정', 'value': 'vis'}],
                        value=[],
                        labelStyle={'margin-right': '1rem'}
                    ),
                    width='auto'
                ),
                dbc.Col(
                    dcc.Checklist(
                        id='ws-option',
                        options=[{'label': '지상바람', 'value': 'ws'}],
                        value=[],
                        labelStyle={'margin-right': '1rem'}
                    ),
                    width='auto'
                ),
                dbc.Col(
                    dcc.Checklist(
                        id='chlow-option',
                        options=[{'label': '운저고도', 'value': 'chlow'}],
                        value=[],
                        labelStyle={'margin-right': '1rem'}
                    ),
                    width='auto'
                ),
                dbc.Col(
                    html.Span(id='ntl-label', style={'font-weight': 'bold'}),
                    width='auto'
                ),
                dbc.Col(
                    html.A(
                        dbc.Button(
                            "테이블표",  # 버튼 텍스트
                            id="table-button",  # 버튼 ID
                            color="primary",  # 버튼 색상
                            className="me-2"  # 오른쪽 여백
                        ),
                        href="/table",  # 새 창에서 열릴 URL
                        target="_blank"  # 새 창에서 열리도록 설정
                    ),
                    width="auto"
                )
            ],
            justify='center',
            align='center',
            className='mb-4'
        ),

        dbc.Row(
            [
                # 왼쪽 1/3: 슬라이더 및 (향후) 이미지
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Label("조도-이미지", style={'font-weight': 'bold'}),
                                dcc.Slider(
                                    id='custom-slider',
                                    min=0,
                                    max=12,
                                    step=1,
                                    value=0,
                                    marks={}  # 콜백에서 동적으로 설정
                                                                    ),
                                # 향후 이미지 추가 위치
                                html.Div(id='image-placeholder', style={'margin-top': '2rem'})
                            ],
                            style={'padding': '2rem'}
                        )
                    ],
                    width=4  # 12분할 기준 4/12 = 1/3
                ),
                # 오른쪽 2/3: 그래프
                dbc.Col(
                    dcc.Graph(id='combined-graph'),
                    width=8  # 12분할 기준 8/12 = 2/3
                )
            ]
        )
    ],
    fluid=True
)

# 테이블 페이지 레이아웃
table_layout = dbc.Container(
    [
        html.H2("조도값 테이블", className="my-4"),
        html.Div(id="table-content"),  # 테이블 데이터를 동적으로 업데이트
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

# ── 2. 테이블 페이지로 이동 ────────────────────────────────
# URL 라우팅 설정
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),  # URL 변경 감지
        html.Div(id="page-content"),  # 페이지 내용
    ]
)

# URL에 따라 다른 레이아웃 표시
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/table":
        return table_layout  # 테이블 페이지
    else:
        return main_layout  # 메인 페이지

# ── 3. 테이블 버튼 클릭 → 테이블 데이터 업데이트 ────────────────
# 테이블 데이터 생성 콜백
@app.callback(
    Output("table-content", "children"),
    [Input("lat-input", "value"),
     Input("lon-input", "value"),
     Input("date-picker", "date")]
)
def update_table(lat, lon, date_str):
    print(f"update_table 실행됨: lat={lat}, lon={lon}, date_str={date_str}")  # 콜백 실행 확인
    if lat is None or lon is None or date_str is None:
        return html.Div("위도, 경도, 날짜를 선택하세요.", style={"color": "red", "font-size": "1.5rem"})

    try:
        # 날짜 및 시간 범위 설정
        date = datetime.fromisoformat(date_str)
        start_time = datetime(date.year, date.month, date.day, 18, 0)  # 18시
        end_time = start_time + timedelta(days=1, hours=2)  # 다음날 20시
        times = [start_time + timedelta(hours=i) for i in range((end_time - start_time).seconds // 3600 + 1)]

        # 조도값 계산
        table_data = []
        for t in times:
            try:
                r_light = get_illuminance_at(t.year, t.month, t.day, t.hour, t.minute, lat, lon)
                print(f"시간: {t}, 조도값: {r_light}")  # 조도값 확인
                table_data.append({"시간": t.strftime("%Y-%m-%d %H:%M"), "조도값 (R_lights)": round(r_light, 2)})
            except Exception as e:
                print(f"조도값 계산 중 오류 발생: {e}")
                table_data.append({"시간": t.strftime("%Y-%m-%d %H:%M"), "조도값 (R_lights)": "오류"})

        # 테이블 데이터 확인
        print(f"테이블 데이터: {table_data}")

        # 테이블 생성
        table = dbc.Table.from_dataframe(
            pd.DataFrame(table_data),
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
        )
        return table

    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {e}")
        return html.Div("테이블 데이터를 생성하는 중 오류가 발생했습니다.", style={"color": "red", "font-size": "1.5rem"})
    
# ── 4. 그래프+NTL 라벨 업데이트 ────────────────────────────────
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
    show_cloud = 'clouds' in cloud_opt
    show_impact = 'impact' in impact_opt
    date = datetime.fromisoformat(date_str)
    start_utc  = datetime(date.year, date.month, date.day, 9, 0, tzinfo=timezone.utc)
    times_utc  = [start_utc + timedelta(minutes=10 * i) for i in range(((23 - 9) * 60 // 10) + 1)]

    # 1. TMFC 폴더 최신순 정렬
    clouds_root = resource_path("assets/clouds")
    subdirs = sorted(
        [d for d in os.listdir(clouds_root) if os.path.isdir(os.path.join(clouds_root, d))],
        reverse=True
    )
    # 2. TMFC별로 csv 미리 읽기
    csv_dfs = {}
    for subdir in subdirs:
        csv_path = os.path.join(clouds_root, subdir, f"clouds_all_{subdir}.csv")
        if os.path.exists(csv_path):
            try:
                csv_dfs[subdir] = pd.read_csv(csv_path)
            except Exception:
                continue

    # 3. ntl은 최신 TMFC에서 한 번만 읽기
    ntl = 0
    for subdir in subdirs:
        df = csv_dfs.get(subdir)
        if df is not None and lat is not None and lon is not None:
            latc, lonc = ('lat', 'lon') if 'lat' in df.columns else ('latitude', 'longitude')
            row = df.loc[((df[latc] - lat)**2 + (df[lonc] - lon)**2).idxmin()]
            ntl = int(row.get('ntl', row.get('NTL', 0)))
            break

    # 4. 각 시간대별로 최신 TMFC에서 구름값 찾기
    cloud_val_map = {}
    for t in times_utc:
        col = (t + timedelta(hours=9)).strftime("%Y%m%d%H")
        for subdir in subdirs:
            df = csv_dfs.get(subdir)
            if df is not None and col in df.columns and lat is not None and lon is not None:
                latc, lonc = ('lat', 'lon') if 'lat' in df.columns else ('latitude', 'longitude')
                row = df.loc[((df[latc] - lat)**2 + (df[lonc] - lon)**2).idxmin()]
                cloud_val_map[col] = row[col]
                break
        else:
            cloud_val_map[col] = None

    # 5. 기존 조도 계산 루프에서 cloud_val_map 사용
    illum_vals, moon_alts, cloud_lbls = [], [], []
    # 1. 모든 구름 데이터 컬럼(3시간 간격) 리스트 만들기
    cloud_cols = []
    for subdir in subdirs:
        df = csv_dfs.get(subdir)
        if df is not None:
            latc, lonc = ('lat', 'lon') if 'lat' in df.columns else ('latitude', 'longitude')
            for col in df.columns:
                if col.isdigit() and len(col) == 10:  # YYYYMMDDHH 형식
                    cloud_cols.append(col)
    cloud_cols = sorted(set(cloud_cols))

    # 2. 각 10분 단위 시간에 대해 가장 가까운 구름 컬럼 찾기
    def find_nearest_cloud_col(t_kst, cloud_cols):
        # t_kst: datetime (KST, offset-aware)
        t_strs = [col for col in cloud_cols]
        t_dts = [datetime.strptime(col, "%Y%m%d%H").replace(tzinfo=kst) for col in t_strs]  # ← 수정
        diffs = [abs((t_kst - dt).total_seconds()) for dt in t_dts]
        idx = diffs.index(min(diffs))
        return t_strs[idx]

    # 3. 기존 루프에서 적용
    for t in times_utc:
        t_kst = t + timedelta(hours=9)
        lux = get_illuminance_at(t.year, t.month, t.day, t.hour, t.minute, lat, lon)
        ml  = lux * 1000 + 1
        lbl = '데이터 없음'
        if show_cloud and cloud_cols:
            nearest_col = find_nearest_cloud_col(t_kst, cloud_cols)
            # 최신 TMFC부터 탐색
            for subdir in subdirs:
                df = csv_dfs.get(subdir)
                if df is not None and nearest_col in df.columns and lat is not None and lon is not None:
                    latc, lonc = ('lat', 'lon') if 'lat' in df.columns else ('latitude', 'longitude')
                    row = df.loc[((df[latc] - lat)**2 + (df[lonc] - lon)**2).idxmin()]
                    cloud_val = row[nearest_col]
                    ml  *= {1: 1.0, 3: 0.5, 4: 0.2}.get(cloud_val, 1)
                    lbl = {1: '맑음', 3: '구름 많음', 4: '흐림'}.get(cloud_val, '데이터없음')
                    break
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

    # 2시간 간격 라벨 생성
    twohour_idx = [i for i, t in enumerate(times_utc) if t.minute == 0 and (t.hour % 2 == 0)]
    twohour_times = [times_kst[i] for i in twohour_idx]

    # 위험도 색상 분기
    if show_impact:
        colors_10min = ['red' if v<=50 else 'orange' if v<=100 else 'yellow' if v<=200 else 'green'
                        for v in illum_vals]
    else:
        colors_10min = ['#b3e6ff'] * len(illum_vals)  # 단일색(밝은 파랑 등)

    # ===============================================================
    # ② 첫번째 그래프 ─ 조도(mlux)
    #     • 배경 막대 : 10 분 위험등급
    #     • 선 그래프 : 10 분 조도
    #     • 마커      : 1 시간 조도(+구름 툴팁)
    # ===============================================================
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.1)

    # show_bg: 배경 막대 표시 여부 (구름 옵션과 동일하게)
    show_bg = show_impact

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
    if show_impact:
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
    fig.update_xaxes(tickmode='array', tickvals=twohour_times, ticktext=twohour_times,
                     title_text='시간 (KST)', row=1, col=1, **axis_opts)
    fig.update_xaxes(tickmode='array', tickvals=twohour_times, ticktext=twohour_times,
                     title_text='시간 (KST)', row=2, col=1, **axis_opts)

    fig.update_yaxes(title_text='달빛 밝기 (millilux)', row=1, col=1,
                     type='log', range=[0, 3], autorange=False,
                     title_standoff=20,   # y축과의 간격(px)
                     tickmode='array', tickvals=[1,10,100,1000], **axis_opts)
    fig.update_yaxes(title_text='달 고도각 (°)', row=2, col=1,
                     title_standoff=40,   # y축과의 간격(px)
                     range=[0, 80], autorange=False, **axis_opts)
   
    fig.update_layout(font=dict(size=20))  # 전체 텍스트 크기
    fig.update_xaxes(title_font=dict(size=20), tickfont=dict(size=18))
    fig.update_yaxes(title_font=dict(size=20), tickfont=dict(size=18))
    fig.update_layout(legend=dict(font=dict(size=22)))
    fig.update_layout(hoverlabel=dict(font_size=20))

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

from dash.dependencies import Input, Output, State
import os

@app.callback(
    [Output('custom-slider', 'marks'),
     Output('custom-slider', 'min'),
     Output('custom-slider', 'max'),
     Output('custom-slider', 'value'),
     Output('image-placeholder', 'children')],
    [Input('date-picker', 'date'),
     Input('custom-slider', 'value'),
     Input('impact-option', 'value'),
     Input('vis-option',    'value'),
     Input('ws-option',     'value'),
     Input('chlow-option',  'value')]
)
def update_slider_and_image(date_str, slider_idx, impact_opt, vis_opt, ws_opt, chlow_opt):
    # 어떤 토글이 눌렸나 우선순위대로 검사
    if 'impact' in impact_opt:
        prefix = "illum_risk_"
    elif 'vis' in vis_opt:
        prefix = "illum_vis_"
    elif 'ws' in ws_opt:
        prefix = "illum_ws10_"
    elif 'chlow' in chlow_opt:
        prefix = "illum_chlow_"
    else:
        prefix = "illum_"

    # 1. 시간 리스트 생성 (20시~08시)
    date = datetime.fromisoformat(date_str)
    hours = list(range(20, 24)) + list(range(0, 9))
    time_labels = []
    time_keys = []
    for h in hours:
        if h >= 20:
            dt = datetime(date.year, date.month, date.day, h)
        else:
            dt = datetime(date.year, date.month, date.day, h) + timedelta(days=1)
        key = dt.strftime("%Y%m%d%H")
        label = dt.strftime("%H")
        time_labels.append(label)
        time_keys.append(key)

    # 2. clouds 폴더 내 모든 이미지 파일 탐색, 폴더명 내림차순(최신 우선)
    image_map = {}
    clouds_root = os.path.join("assets", "clouds")
    if os.path.exists(clouds_root):
        subdirs = sorted(
            [d for d in os.listdir(clouds_root) if os.path.isdir(os.path.join(clouds_root, d))],
            reverse=True
        )
        for subdir in subdirs:
            folder = os.path.join(clouds_root, subdir)
            for fname in os.listdir(folder):
                if fname.startswith(prefix) and fname.endswith(".png"):
                    key = fname.replace(prefix, "").replace(".png", "")
                    if key not in image_map:
                        image_map[key] = os.path.join(folder, fname)

    # 3. 슬라이더 marks/min/max/value
    marks = {i: label for i, label in enumerate(time_labels)}
    min_val = 0
    max_val = len(time_labels) - 1
    value = slider_idx if slider_idx is not None else 0

    # 4. 이미지 파일 경로 (가장 최근 폴더 기준)
    img_key = time_keys[value]
    img_path = image_map.get(img_key)

    if img_path and os.path.exists(img_path):
        # src 경로를 /assets/... 형식으로 설정
        relative_path = os.path.relpath(img_path, "assets")
        img_div = html.Div(
            html.Img(src=f"/assets/{relative_path.replace(os.sep, '/')}", style={'width': '100%', 'max-width': '400px'}),
            style={'display': 'flex', 'justifyContent': 'center'}
        )
    else:
        img_div = html.Div(
            "no-image",
            style={
                'color': 'gray',
                'font-size': '2rem',
                'text-align': 'center',
                'margin-top': '2rem',
                'display': 'flex',
                'justifyContent': 'center'
            }
        )

    return marks, min_val, max_val, value, img_div

# ========================
# Run Server
# ========================
if __name__ == "__main__":
    app.run(debug=True)
    input("Press Enter to exit...")
