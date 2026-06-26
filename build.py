import csv, json, io
from collections import Counter
import urllib.request as req
import urllib.parse as parse

SHEET_ID = '1jjJvuePQNW-S0QAUC0EyVd_Lx0IHYbksOheJEYmwuFA'

def fetch_sheet(sheet_name):
    encoded = parse.quote(sheet_name)
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded}'
    print(f'Fetching: {sheet_name} ...')
    with req.urlopen(url) as r:
        return r.read().decode('utf-8')

def parse_overall(csv_text):
    lines = csv_text.strip().split('\n')
    overall = []
    start = 0
    for i, line in enumerate(lines):
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        val = cols[0].strip() if cols else ''
        if val.isdigit() and len(val) >= 9:
            start = i
            break
    for line in lines[start:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if not cols or not cols[0].strip(): continue
        ss = cols[0].strip()
        if not ss or not ss.isdigit() or ss == '0': continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        overall.append({
            'ss': ss, 'attempted': g(1), 'ground': g(2),
            'placed': g(4), 'placementBonus': g(8),
            'colM': g(9), 'colN': g(10),
        })
    print(f'Overall: {len(overall)} rows')
    return overall

def parse_detail(csv_text):
    reader_obj = csv.reader(io.StringIO(csv_text))
    next(reader_obj)
    detail = []
    type_counts = {}
    status_counts = {}
    for cols in reader_obj:
        if not cols or len(cols) < 2 or not cols[1].strip(): continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        ss = g(1)
        col_t = g(19)  # Type of Order
        col_u = g(20)  # Order Status
        if col_t:
            type_counts.setdefault(ss, Counter())[col_t] += 1
        if col_u:
            status_counts.setdefault(ss, Counter())[col_u] += 1
        detail.append({
            'ss': ss, 'retailer': g(0), 'so': g(16), 'formDate': g(3),
            'typeOfOrder': col_t, 'orderStatus': col_u,
            'placedBonus': g(13), 'deliveryBonus': g(17),
        })
    print(f'Detail: {len(detail)} rows')
    return detail, type_counts, status_counts

def merge_overall(overall, type_counts, status_counts):
    for row in overall:
        ss = row['ss']
        tc = type_counts.get(ss, {})
        sc = status_counts.get(ss, {})
        row['considered'] = str(tc.get('Considered', 0))
        row['oldOrder']   = str(tc.get('Old Order', 0))
        row['groundTeam'] = str(tc.get('Order Placed By Ground Team', 0))
        row['delivered']  = str(sc.get('Delivered', 0))
        row['inProcess']  = str(sc.get('In Process', 0))
        row['inProgress'] = str(sc.get('In Progress', 0))
        row['cancelled']  = str(sc.get('Order Cancelled', 0))
    return overall

def build_html(overall, detail):
    OJ = json.dumps(overall, separators=(',',':'))
    DJ = json.dumps(detail, separators=(',',':'))
    with open('template_part1.txt') as f: p1 = f.read()
    with open('template_part2.txt') as f: p2 = f.read()
    html = p1 + 'const OVERALL=' + OJ + ';\nconst DETAIL=' + DJ + ';' + p2
    with open('index.html', 'w') as f: f.write(html)
    print(f'Built index.html ({len(html)//1024}KB)')

if __name__ == '__main__':
    overall_csv = fetch_sheet('Overall performance')
    detail_csv = fetch_sheet('Model')
    overall = parse_overall(overall_csv)
    detail, tc, sc = parse_detail(detail_csv)
    overall = merge_overall(overall, tc, sc)
    build_html(overall, detail)
    print('Done!')
