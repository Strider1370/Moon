# app.py

import dash
from dash import dcc, html, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from astronomy.output import calculate_and_collect_data
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate
import urllib.parse

# 상수 정의
TIMEZONE_OFFSET = 9  # KST는 UTC+9

# 도시별 위도, 경도 정보
city_coordinates = {
    'Seoul': {'lat': 37.5665, 'lon': 126.9780},
    'Daejeon': {'lat': 36.3504, 'lon': 127.3845},
    'Gangneung': {'lat': 37.7519, 'lon': 128.8761},
    'Busan': {'lat': 35.1796, 'lon': 129.0756},
    'Mokpo': {'lat': 34.8118, 'lon': 126.3922}
}

# Dash 애플리케이션 초기화
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title='달빛천사 0.3'
)
server = app.server

# 공통 스타일 정의
input_style = {'width': '150px'}
common_button_style = {'margin-top': '25px'}

# 헬퍼 함수 정의
def create_input_col(label_text, input_component):
    return dbc.Col([
        dbc.Label(label_text),
        input_component
    ], width="auto")

def parse_inputs(selected_date, latitude, longitude):
    try:
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        latitude = float(latitude)
        longitude = float(longitude)
        return date_obj, latitude, longitude
    except (ValueError, TypeError):
        return None, None, None

def get_calculated_data(selected_date, latitude, longitude, timezone_offset=TIMEZONE_OFFSET):
    date_obj, latitude, longitude = parse_inputs(selected_date, latitude, longitude)
    if date_obj is None:
        return None
    data = calculate_and_collect_data(
        year=date_obj.year,
        month=date_obj.month,
        day=date_obj.day,
        timezone_offset=timezone_offset,
        latitude=latitude,
        longitude=longitude
    )
    return data

# 도시 옵션 동적 생성
city_options = [{'label': city, 'value': city} for city in city_coordinates.keys()]

# 메인 페이지 레이아웃 정의
main_layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("달빛천사 0.3", className="text-start my-4"), width=3),
        dbc.Col([
            dbc.Row([
                # City 드롭다운
                create_input_col("City", dcc.Dropdown(
                    id='city-dropdown',
                    options=city_options,
                    value='Seoul',
                    className='mb-2',
                    style=input_style
                )),
                # Latitude 입력
                create_input_col("Latitude", dbc.Input(
                    id='latitude-input',
                    placeholder='Enter Latitude',
                    type='number',
                    value=city_coordinates['Seoul']['lat'],
                    style=input_style
                )),
                # Longitude 입력
                create_input_col("Longitude", dbc.Input(
                    id='longitude-input',
                    placeholder='Enter Longitude',
                    type='number',
                    value=city_coordinates['Seoul']['lon'],
                    style=input_style
                )),
                # Date 라벨과 입력창, 그리고 날짜 조정 버튼
                dbc.Col([
                    dbc.Label("Date", className="d-block"),
                    dbc.InputGroup([
                        dbc.Button("<", id='prev-day-button', n_clicks_timestamp=0),
                        dcc.DatePickerSingle(
                            id='date-picker',
                            min_date_allowed=datetime(2000, 1, 1),
                            max_date_allowed=datetime(2100, 12, 31),
                            initial_visible_month=datetime.today(),
                            date=datetime.today().strftime('%Y-%m-%d'),
                            display_format='YYYY-MM-DD',
                            className='mx-auto',
                            style=input_style
                        ),
                        dbc.Button(">", id='next-day-button', n_clicks_timestamp=0),
                    ], size="sm")
                ], width="auto", className="d-flex align-items-center"),
            ])
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.A(
                dbc.Button(
                    "timetable",
                    id='timetable-button',
                    className='btn btn-secondary'
                ),
                href="#",
                id='timetable-link',
                target='_blank'
            )
        ], width=12, className="mt-3 d-flex justify-content-start")
    ]),
    # 그래프 표시 영역에 로딩 스피너 추가
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id='loading-graph',
                type='circle',
                children=[
                    dcc.Graph(id='esurface-graph'),
                    dcc.Graph(id='moon-elevation-graph')  # 새로운 그래프 추가
                ]
            )
        ], width=12)
    ], className='mt-4')
], fluid=True)

# 타임테이블 페이지 레이아웃
timetable_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Timetable", className="text-center my-4"),
            html.Div(id='selected-date', className="text-center mb-4")
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id='loading-table',
                type='circle',
                children=[html.Div(id='timetable-table')]
            )
        ])
    ])
], fluid=True)

# 애플리케이션 레이아웃 정의
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# 페이지 내용 업데이트 콜백
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname.startswith('/timetable'):
        return timetable_layout
    else:
        return main_layout

# 도시 선택 시 위도와 경도 자동 업데이트 콜백
@app.callback(
    [Output('latitude-input', 'value'),
     Output('longitude-input', 'value')],
    [Input('city-dropdown', 'value')]
)
def update_lat_lon(city):
    if city in city_coordinates:
        return city_coordinates[city]['lat'], city_coordinates[city]['lon']
    return dash.no_update, dash.no_update

# 날짜 조정 버튼 클릭 시 날짜 선택기 업데이트 콜백
@app.callback(
    Output('date-picker', 'date'),
    [Input('prev-day-button', 'n_clicks_timestamp'),
     Input('next-day-button', 'n_clicks_timestamp')],
    [State('date-picker', 'date')]
)
def update_date(prev_ts, next_ts, selected_date):
    if not selected_date:
        selected_date = datetime.today()
    else:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d')

    if not prev_ts and not next_ts:
        raise PreventUpdate

    if (prev_ts or 0) > (next_ts or 0):
        updated_date = selected_date - timedelta(days=1)
    else:
        updated_date = selected_date + timedelta(days=1)

    # 날짜 범위 제한
    min_date = datetime(2000, 1, 1)
    max_date = datetime(2100, 12, 31)
    updated_date = max(min_date, min(updated_date, max_date))

    return updated_date.strftime('%Y-%m-%d')

# 메인 페이지의 'Timetable' 링크 업데이트 콜백
@app.callback(
    Output('timetable-link', 'href'),
    [Input('date-picker', 'date'),
     Input('latitude-input', 'value'),
     Input('longitude-input', 'value')]
)
def update_timetable_link(selected_date, latitude, longitude):
    if not selected_date:
        return "#"

    date_obj, latitude, longitude = parse_inputs(selected_date, latitude, longitude)
    if date_obj is None:
        return "#"

    # 쿼리 파라미터 설정
    query_params = {
        'date': selected_date,
        'latitude': latitude,
        'longitude': longitude,
        'timezone_offset': TIMEZONE_OFFSET
    }
    query_string = urllib.parse.urlencode(query_params)
    return f"/timetable?{query_string}"

# 타임테이블 페이지에서 테이블과 날짜 표시 콜백
@app.callback(
    [Output('selected-date', 'children'),
     Output('timetable-table', 'children')],
    [Input('url', 'search')]
)
def update_timetable_table(search):
    if not search:
        return "", dbc.Alert("필요한 파라미터가 없습니다.", color="danger")

    # 쿼리 파라미터 파싱
    params = urllib.parse.parse_qs(search.lstrip('?'))
    try:
        selected_date = params['date'][0]
        latitude = float(params['latitude'][0])
        longitude = float(params['longitude'][0])
        timezone_offset = float(params['timezone_offset'][0])
    except (KeyError, ValueError, IndexError):
        return "", dbc.Alert("잘못된 파라미터입니다.", color="danger")

    # 데이터 계산 및 수집
    data = get_calculated_data(selected_date, latitude, longitude, timezone_offset)

    if not data:
        return f"Selected Date: {selected_date}", dbc.Alert("데이터를 계산할 수 없습니다.", color="danger")

    # DataFrame으로 변환
    df = pd.DataFrame(data)

    # 'Local Time' 포맷 수정
    df['Local Time'] = df['Local Time'].astype(str) + ' KST'

    # 테이블 생성 (페이지네이션 적용)
    table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        fixed_rows={'headers': True},
        page_size=120,
        style_table={
            'height': '100%',
            'overflowY': 'auto',
            'width': '100%',
            'minWidth': '100%',
        },
        style_cell={
            'textAlign': 'center',
            'minWidth': '100px',
            'width': '100px',
            'maxWidth': '100px',
            'whiteSpace': 'normal',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
        },
    )

    # 선택한 날짜 표시
    formatted_date = f"Selected Date: {selected_date}"

    return formatted_date, table

# 메인 페이지에서 그래프를 업데이트하는 콜백
@app.callback(
    [Output('esurface-graph', 'figure'),
     Output('moon-elevation-graph', 'figure')],
    [Input('date-picker', 'date'),
     Input('latitude-input', 'value'),
     Input('longitude-input', 'value')]
)
def update_graphs(selected_date, latitude, longitude):
    if not selected_date or latitude is None or longitude is None:
        raise PreventUpdate

    data = get_calculated_data(selected_date, latitude, longitude)
    if not data:
        return {'data': [], 'layout': {}}, {'data': [], 'layout': {}}

    df = pd.DataFrame(data)
    df['E_surface (millilux)'] = pd.to_numeric(df['E_surface (millilux)'], errors='coerce')
    df['Local Time'] = pd.to_datetime(df['Local Time'], format='%Y-%m-%d %H:%M')

    # x축 범위를 설정하기 위해 시작 시간과 종료 시간을 지정
    start_time = df['Local Time'].iloc[0]
    end_time = df['Local Time'].iloc[-1]

    # 첫 번째 그래프 생성 코드
    conditions = pd.DataFrame({
        'weight': [1, 0.5, 0.2, 0.05],
        'color': ['blue', 'green', 'orange', 'red'],
        'name': ['Clear', 'SCT', 'BKN', 'OVC']
    })

    traces = []
    for _, row in conditions.iterrows():
        y_values = (df['E_surface (millilux)'] + 0.2) * row['weight'] + 0.3
        trace = {
            'x': df['Local Time'],
            'y': y_values,
            'type': 'line',
            'name': row['name'],
            'marker': {'color': row['color']}
        }
        traces.append(trace)

    fig = {
        'data': traces,
        'layout': {
            'title': 'Nighttime Illuminance by sun and moon',
            'xaxis': {
                'title': 'Time (KST)',
                'tickformat': '%H:%M',
                'tickmode': 'linear',
                'dtick': 3600000 * 2,
                'range': [start_time, end_time]
            },
            'yaxis': {
                'title': 'Illuminance (millilux)',
                'type': 'log',
                'range': [-1, 3],
                'tickvals': [0.1, 1, 10, 100, 1000],
                'ticktext': ['0.1', '1', '10', '100', '1000'],
                'autorange': False,
                'cliponaxis': False
            },
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.3,
                'xanchor': 'center',
                'x': 0.5
            },
            'margin': {'l': 50, 'r': 20, 't': 50, 'b': 80},
            'height': 400
        }
    }

    # 두 번째 그래프 생성 코드
    df['Moon Alt (°)'] = pd.to_numeric(df['Moon Alt (°)'], errors='coerce')

    moon_fig = {
    'data': [{
        'x': df['Local Time'],
        'y': df['Moon Alt (°)'],
        'type': 'line',
        'name': 'Moon Elevation',
        'marker': {'color': 'black'}
    }],
    'layout': {
        'title': 'Moon_sky_location',
        'xaxis': {
            'title': 'Time (KST)',
            'tickformat': '%H:%M',
            'tickmode': 'linear',
            'dtick': 3600000 * 2,
            'range': [start_time, end_time]
        },
        'yaxis': {
            'title': 'Moon_elevation(degree)',
            'range': [0, 90],
            'autorange': False,
            'tickvals': [0, 30, 60, 90],  # 여기에서 y축 눈금을 설정합니다.
        },
        'margin': {'l': 50, 'r': 20, 't': 50, 'b': 80},
        'height': 400
        }
    }


    return fig, moon_fig

# 애플리케이션 실행
if __name__ == '__main__':
    app.run_server(debug=True)
