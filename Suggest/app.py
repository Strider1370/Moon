# app.py

import dash
from dash import dcc, html, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from astronomy.output import calculate_and_collect_data
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate
import urllib.parse
import os
import sys

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
    title='달빛천사 0.4'
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
        dbc.Col(html.H1("달빛천사 0.4", className="text-start my-4"), width=3),
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
            ),
            # 'clouds' 버튼 추가
            dbc.Button(
                "clouds",
                id='clouds-button',
                className='btn btn-secondary ml-2'
            )
        ], width=12, className="mt-3 d-flex justify-content-start")
    ], className='mb-2'),

    # 그래프 및 이미지 표시 영역에 로딩 스피너 추가
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id='loading-graph',
                type='circle',
                children=[
                    dcc.Graph(id='esurface-graph'),
                    dcc.Graph(id='moon-elevation-graph'),
                    html.Div(id='clouds-animation-container', style={'textAlign': 'center', 'marginTop': '20px'})
                ]
            )
        ], width=12)
    ], className='mt-4'),
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

# 이미지 폴더 경로 설정
image_dir = os.path.join(os.path.dirname(__file__), 'assets', 'cloud_images_3')

image_files = sorted(
    [f for f in os.listdir(image_dir) if f.startswith('final_output_') and f.endswith('.png')],
    key=lambda x: x.split('_')[2].split('.')[0]  # 파일명에서 '2024101716' 형식으로 정렬
)

# 슬라이더 마크 설정: 이미지 파일에서 뒤의 2자리만 추출하여 "XX:00" 형식으로 설정
marks = {i: f.split('_')[2].split('.')[0][-2:] + ':00' for i, f in enumerate(image_files)}

# 레이아웃 설정
clouds_layout = dbc.Container([
    dbc.Row([
        dbc.Col([  
            html.H2("야간조도 시각화", className="text-center my-4", style={'fontSize': '24px', 'fontWeight': 'bold'})
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Slider(
                id='image-slider',
                min=0,
                max=len(image_files) - 1,
                step=1,
                value=0,
                marks=marks,  # 날짜 마크
                tooltip=None
            ),
            html.Div([
                # 이미지 1과 제목
                html.Div([
                    html.Img(id='cloud-image-1', src='', style={'width': '100%', 'height': 'auto', 'marginTop': '20px'}),
                    html.P("천체력에 의한 조도", className='text-center', style={'fontSize': '30px', 'fontWeight': 'bold'})  # 이미지 1 제목
                ], style={'width': '33%', 'textAlign': 'center'}),

                # 이미지 2와 제목
                html.Div([
                    html.Img(id='cloud-image-2', src='', style={'width': '100%', 'height': 'auto', 'marginTop': '20px'}),
                    html.P("기상청 구름예보(운량)", className='text-center', style={'fontSize': '30px', 'fontWeight': 'bold'})  # 이미지 2 제목
                ], style={'width': '33%', 'textAlign': 'center'}),

                # 이미지 3과 제목
                html.Div([
                    html.Img(id='cloud-image-3', src='', style={'width': '100%', 'height': 'auto', 'marginTop': '20px'}),
                    html.P("천체력과 운량을 적용한 조도", className='text-center', style={'fontSize': '30px', 'fontWeight': 'bold'})  # 이미지 3 제목
                ], style={'width': '33%', 'textAlign': 'center'})
            ], style={'display': 'flex', 'justifyContent': 'space-around'}),
            html.Div(id='image-caption', className='text-center mt-2')
        ], width=12)
    ], className='mt-4')
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
    elif pathname.startswith('/clouds'):
        return clouds_layout
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
    if 'Local Time' in df.columns:
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
    if 'E_surface (millilux)' not in df.columns or 'Local Time' not in df.columns:
        return {'data': [], 'layout': {}}, {'data': [], 'layout': {}}

    df['E_surface (millilux)'] = pd.to_numeric(df['E_surface (millilux)'], errors='coerce')
    df['Local Time'] = pd.to_datetime(df['Local Time'], format='%Y-%m-%d %H:%M')

    # x축 범위를 설정하기 위해 시작 시간과 종료 시간을 지정
    start_time = df['Local Time'].iloc[0]
    end_time = df['Local Time'].iloc[-1]
  
    traces = [{
        'x': df['Local Time'],
        'y': df['E_surface (millilux)'] + 0.5,  
        'type': 'line',
        'name': 'E_surface (millilux)',  # 그래프 레이블
        'marker': {'color': 'blue'}  # 기본 색상 설정
    }]

    fig = {
        'data': traces,
        'layout': {
            'title': 'Nighttime Illuminance by sun and moon',
            'xaxis': {
                'title': 'Time (KST)',
                'tickformat': '%H:%M',
                'tickmode': 'linear',
                'dtick': 3600000 * 2,  # 2시간 간격
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
            'shapes': [  # y=2.2 빨간색 선 추가
               {
                   'type': 'line',
                   'xref': 'x',
                   'yref': 'y',
                   'x0': df['Local Time'].iloc[0],
                   'x1': df['Local Time'].iloc[-1],
                   'y0': 2.2,
                   'y1': 2.2,
                   'line': {
                       'color': 'red',
                       'width': 2,
                       'dash': 'dash'
                   }
               }
           ],            
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
    if 'Moon Alt (°)' not in df.columns:
        return fig, {'data': [], 'layout': {}}

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
            'title': 'Moon Elevation',
            'xaxis': {
                'title': 'Time (KST)',
                'tickformat': '%H:%M',
                'tickmode': 'linear',
                'dtick': 3600000 * 2,  # 2시간 간격
                'range': [start_time, end_time]
            },
            'yaxis': {
                'title': 'Moon Elevation (°)',
                'range': [0, 90],
                'autorange': False,
                'tickvals': [0, 30, 60, 90],
                'ticktext': ['0', '30', '60', '90']
            },
        'shapes': [
            {
                'type': 'line',
                'xref': 'x',
                'yref': 'y',
                'x0': df['Local Time'].iloc[0],
                'x1': df['Local Time'].iloc[-1],
                'y0': 30,
                'y1': 30,
                'line': {
                    'color': 'red',
                    'width': 2,
                    'dash': 'dash'
                }
            }
        ],            
            'margin': {'l': 50, 'r': 20, 't': 50, 'b': 80},
            'height': 400
        }
    }

    return fig, moon_fig

@app.callback(
    [Output('cloud-image-1', 'src'),
     Output('cloud-image-2', 'src'),
     Output('cloud-image-3', 'src'),
     Output('image-caption', 'children')],
    [Input('image-slider', 'value')]

)

def update_cloud_images(slider_value):
    # 실행 파일이 압축된 경우와 개발 환경에서 경로 처리
    if getattr(sys, 'frozen', False):  # PyInstaller로 빌드된 경우
        base_path = sys._MEIPASS
    else:  # 개발 환경에서 실행되는 경우
        base_path = os.path.dirname(__file__)

    # 각 폴더 경로 설정
    image_dir_1 = os.path.join(base_path, 'assets', 'cloud_images_1')
    image_dir_2 = os.path.join(base_path, 'assets', 'cloud_images_2')
    image_dir_3 = os.path.join(base_path, 'assets', 'cloud_images_3')

    # 폴더 경로가 존재하는지 확인
    if not os.path.exists(image_dir_1) or not os.path.exists(image_dir_2) or not os.path.exists(image_dir_3):
        return '', '', '', '디렉토리 경로가 존재하지 않습니다.'

    # 이미지 파일 목록을 가져옴
    image_files_1 = [f for f in os.listdir(image_dir_1) if f.startswith('E_surface') and f.endswith('.png')]
    image_files_2 = [f for f in os.listdir(image_dir_2) if f.startswith('output_') and f.endswith('.png')]
    image_files_3 = [f for f in os.listdir(image_dir_3) if f.startswith('final_output_') and f.endswith('.png')]

    # 이미지가 없다면 반환
    if not image_files_1 or not image_files_2 or not image_files_3:
        return '', '', '', '이미지를 찾을 수 없습니다.'

    # 슬라이더 값에 맞는 이미지 파일 선택
    if slider_value < 0 or slider_value >= len(image_files_1) or slider_value >= len(image_files_2) or slider_value >= len(image_files_3):
        return '', '', '', '잘못된 이미지 인덱스입니다.'

    image_filename_1 = image_files_1[slider_value]
    image_filename_2 = image_files_2[slider_value]
    image_filename_3 = image_files_3[slider_value]

    # 각 이미지 경로 생성
    image_src_1 = app.get_asset_url(f'cloud_images_1/{image_filename_1}')
    image_src_2 = app.get_asset_url(f'cloud_images_2/{image_filename_2}')
    image_src_3 = app.get_asset_url(f'cloud_images_3/{image_filename_3}')

    # 캡션 생성: 날짜와 시간 정보
    date_time_str = image_filename_3.split('_')[2].split('.')[0]  # "2024101716" -> "2024101716"
    date_str = date_time_str[:8]  # "20241017"
    time_str = date_time_str[8:]  # "16"

    caption = f"{date_str}{time_str}KST"

    return image_src_1, image_src_2, image_src_3, caption

@app.callback(
    Output('url', 'pathname'),
    [Input('clouds-button', 'n_clicks')],
    prevent_initial_call=True
)
def navigate_to_clouds(n_clicks):
    if n_clicks is None:
        raise PreventUpdate  # 버튼이 클릭되지 않으면 콜백이 실행되지 않음
    return '/clouds'

# 애플리케이션 실행
if __name__ == '__main__':
    app.run_server(debug=True)