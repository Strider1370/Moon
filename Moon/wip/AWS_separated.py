import requests
import datetime
import csv

now = datetime.datetime.now().strftime("%Y%m%d%H")
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
url_aws = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"
url_cloud = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min_cloud?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"
url_vis = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min_vis?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"

def extract_columns(filename, api_type):
    # 열 인덱스 정의 (0부터 시작)
    if api_type == "aws":
        col_idx = [1, 7]          # 2열, 8열
        outname = f"aws_selected_{now}.csv"
        col_names = ["STN", "WS10"]
    elif api_type == "cloud":
        col_idx = [1, 2, 3, 4]    # 2,3,4,5열
        outname = f"cloud_selected_{now}.csv"
        col_names = ["STN", "LON", "LAT", "CH_LOW"]
    elif api_type == "vis":
        col_idx = [1, 2, 3, 5]    # 2,3,4,6열
        outname = f"vis_selected_{now}.csv"
        col_names = ["STN", "LON", "LAT", "VIS"]
    else:
        return

    with open(filename, encoding="utf-8") as infile, open(outname, "w", newline='', encoding="utf-8") as outfile:
        reader = csv.reader((row for row in infile if not row.startswith("#") and row.strip()))
        writer = csv.writer(outfile)
        writer.writerow(col_names)  # 헤더 작성
        for row in reader:
            # 마지막 열이 '='일 경우 제외
            if row and row[-1] == '=':
                row = row[:-1]
            # 열 개수 충분한지 확인
            if max(col_idx) < len(row):
                writer.writerow([row[i] for i in col_idx])
    print(f"Selected columns saved to {outname}")

def run_aws_api(url, tmfc, stn, service_key, filename, api_type):
    formatted_url = url.format(tmfc=tmfc, stn=stn, service_key=service_key)
    try:
        response = requests.get(formatted_url, verify=False, timeout=10)
        response.raise_for_status()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved to {filename}")
        extract_columns(filename, api_type)
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching data from KMA AWS API: {e}")
        return None

if __name__ == "__main__":
    api_type = input("aws, cloud, vis 중 하나를 입력하세요: ").strip().lower()
    tmfc = None
    stn = None

    if api_type == "aws":
        url = url_aws
        filename = f"aws_result_{now}.csv"
    elif api_type == "cloud":
        url = url_cloud
        filename = f"cloud_result_{now}.csv"
    elif api_type == "vis":
        url = url_vis
        filename = f"vis_result_{now}.csv"
    else:
        print("잘못된 입력입니다. aws, cloud, vis 중 하나를 입력하세요.")
        exit(1)

    run_aws_api(url, tmfc, stn, service_key, filename, api_type)
