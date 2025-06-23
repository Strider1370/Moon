import requests

url = "https://apihub.kma.go.kr/api/typ01/url/stn_inf.php?inf=AWS&help=2&authKey=boxdzlyoTGWMXc5cqDxlQQ"

response = requests.get(url, verify=False, timeout=10)
response.raise_for_status()

try:
    response.encoding = response.apparent_encoding
    text = response.text
except Exception:
    response.encoding = "utf-8"
    text = response.text

with open("aws_stn_info.csv", "w", encoding=response.encoding, newline='') as f:
    f.write(text)

print("CSV 파일로 저장 완료: aws_stn_info.csv")



