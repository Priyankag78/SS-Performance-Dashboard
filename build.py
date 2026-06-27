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
    # Find first data row (10+ digit SS number)
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
    lines = csv_text.strip().split('\n')
    # Find header row
    header_idx = 0
    for i, line in enumerate(lines):
        if 'Retailer' in line:
            header_idx = i
            break
    reader = csv.reader(io.StringIO(lines[header_idx]))
    headers = [h.strip() for h in next(reader)]
    print(f'Model headers: {headers}')

    # Find columns by name - LAST match for duplicates
    def find_last(name):
        result = -1
        for i, h in enumerate(headers):
            if h.lower() == name.lower():
                result = i
        return result
    def find_first(name):
        for i, h in enumerate(headers):
            if h.lower() == name.lower():
                return i
        return -1

    # Column mapping
    ci_ss       = find_first('SS Number')
    ci_retailer = find_first('Retailer Number')
    ci_so       = find_first('SO Number')
    ci_form     = find_first('Form Date')
    ci_type     = find_last('Type of order')    # LAST match skips Col E
    ci_status   = find_last('Order status')     # Order status
    ci_bonus    = find_first('Actual Bonus')     # Col N
    ci_delivery = find_first('RTO')              # Col R as requested
    print(f'Columns: ss={ci_ss} retailer={ci_retailer} type={ci_type} status={ci_status} bonus={ci_bonus} delivery={ci_delivery}')

    detail = []
    type_counts = {}
    status_counts = {}
    for line in lines[header_idx+1:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if ci_ss >= len(cols) or not cols[ci_ss].strip(): continue
        def g(i): return cols[i].strip() if 0 <= i < len(cols) else ''
        ss = g(ci_ss)
        if not ss: continue
        col_type   = g(ci_type)
        col_status = g(ci_status)
        if col_type: type_counts.setdefault(ss, Counter())[col_type] += 1
        if col_status: status_counts.setdefault(ss, Counter())[col_status] += 1
        detail.append({
            'ss': ss, 'retailer': g(ci_retailer), 'so': g(ci_so),
            'formDate': g(ci_form), 'typeOfOrder': col_type,
            'orderStatus': col_status, 'placedBonus': g(ci_bonus),
            'deliveryBonus': g(ci_delivery),
        })
    print(f'Detail: {len(detail)} rows')
    if detail: print(f'Sample: {json.dumps(detail[0])}')
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
