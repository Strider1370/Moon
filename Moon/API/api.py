import requests

# API 요청
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
tmfc = 2024100108
tmef = 2024100109
vars = "SKY"
api_url = f"https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_shrt_grd?tmfc={tmfc}&tmef={tmef}&vars={vars}&authKey={service_key}"

response = requests.get(api_url)

print(response.text)
