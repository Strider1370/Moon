import requests

# API 요청
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
tmfc = 2024100208
tmef = 2024100210
vars = "SKY"
api_url = f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}&vars={vars}&authKey={service_key}"

response = requests.get(api_url)

# API 응답 데이터를 텍스트 파일로 저장
file_path = "api_response.txt"  # 저장할 파일 경로 및 이름
with open(file_path, 'w') as file:
    file.write(response.text)

print(f"API 응답 데이터가 {file_path}로 저장되었습니다.")
