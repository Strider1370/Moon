import requests
import datetime
import csv

now = datetime.datetime.now().strftime("%Y%m%d%H")
service_key = "boxdzlyoTGWMXc5cqDxlQQ"
url_aws = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"
url_cloud = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min_cloud?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"
url_vis = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min_vis?tm2={tmfc}&stn={stn}&disp=1&help=2&authKey={service_key}"

def fetch_and_parse(url, tmfc, stn, col_idx, key_idx, encoding="utf-8"):
    formatted_url = url.format(tmfc=tmfc, stn=stn, service_key=service_key)
    response = requests.get(formatted_url, verify=False, timeout=10)
    response.raise_for_status()
    lines = [row for row in response.text.splitlines() if not row.startswith("#") and row.strip()]
    data = {}
    first_row_first_col = None
    for idx, row in enumerate(csv.reader(lines)):
        if row and row[-1] == '=':
            row = row[:-1]
        if max(col_idx) < len(row):
            key = row[key_idx].strip()
            values = [row[i].strip() for i in col_idx if i != key_idx]
            data[key] = values
            if first_row_first_col is None:
                first_row_first_col = row[0].strip()
    return data, first_row_first_col

def load_stn_lonlat(filepath):
    stn_lonlat = {}
    with open(filepath, encoding="cp949") as f:  # ← 여기만 cp949로!
        for line in f:
            if line.strip().startswith("#") or not line.strip():
                continue
            parts = line.split()
            try:
                stn = parts[0]
                lon = parts[1]
                lat = parts[2]
                stn_lonlat[stn] = (lon, lat)
            except IndexError:
                continue
    return stn_lonlat

def merge_and_save(aws_data, vis_data, cloud_data, outname, stn_lonlat):
    header = ["STN", "LON", "LAT", "WS10", "VIS", "CH_LOW"]
    stn_list = sorted(aws_data.keys(), key=lambda x: int(x))
    with open(outname, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for stn in stn_list:
            aws_row = aws_data[stn]
            # LON, LAT 우선순위: VIS → CLOUD → aws_stn_info.csv → -99.9
            if stn in vis_data:
                lon, lat = vis_data[stn][0], vis_data[stn][1]
            elif stn in cloud_data:
                lon, lat = cloud_data[stn][0], cloud_data[stn][1]
            elif stn in stn_lonlat:
                lon, lat = stn_lonlat[stn]
            else:
                lon, lat = "-99.9", "-99.9"
            ws10 = aws_row[0]
            vis_val = vis_data[stn][2] if stn in vis_data else "-99.9"
            ch_low = cloud_data[stn][2] if stn in cloud_data else "-99.9"
            row = [stn, lon, lat, ws10, vis_val, ch_low]
            writer.writerow(row)
    print(f"Merged result saved to {outname}")

if __name__ == "__main__":
    tmfc = None
    stn = None

    # AWS: STN(1), WS10(7)
    aws_data, aws_first_col = fetch_and_parse(url_aws, tmfc, stn, [1, 7], key_idx=1)
    # VIS: STN(1), LON(2), LAT(3), VIS(5)
    vis_data, _ = fetch_and_parse(url_vis, tmfc, stn, [1, 2, 3, 5], key_idx=1)
    # CLOUD: STN(1), LON(2), LAT(3), CH_LOW(4)
    cloud_data, _ = fetch_and_parse(url_cloud, tmfc, stn, [1, 2, 3, 4], key_idx=1)

    # STN, LON, LAT 정보 불러오기
    stn_lonlat = load_stn_lonlat("aws_stn_info.csv")

    merge_and_save(aws_data, vis_data, cloud_data, f"merged_result_{aws_first_col}.csv", stn_lonlat)
