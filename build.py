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

def find_col(headers, *names):
    """Find column index by trying multiple possible header names (case-insensitive)"""
    for name in names:
        for i, h in enumerate(headers):
            if h.strip().lower() == name.strip().lower():
                return i
    return -1

def parse_overall(csv_text):
    lines = csv_text.strip().split('\n')
    # Find the header row (contains 'SS Number')
    header_idx = 0
    for i, line in enumerate(lines):
        if 'SS Number' in line or 'ss number' in line.lower():
            header_idx = i
            break
    reader = csv.reader(io.StringIO(lines[header_idx]))
    headers = [h.strip() for h in next(reader)]
    print(f'Overall headers (row {header_idx}): {headers}')

    c = {
        'ss':     find_col(headers, 'SS Number'),
        'att':    find_col(headers, 'Orders Attempted'),
        'ground': find_col(headers, 'Ground Orders'),
        'placed': find_col(headers, 'Actual Orders Placed'),
        'bonus':  find_col(headers, 'Placement Bonus'),
        'delCnt': find_col(headers, 'Actual Orders Delivered'),
        'delBon': find_col(headers, 'Delivery Bonus'),
    }
    print(f'Column indices: {c}')

    overall = []
    for line in lines[header_idx+1:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if not cols or not cols[c['ss']].strip(): continue
        ss = cols[c['ss']].strip()
        if not ss.isdigit() or ss == '0' or len(ss) < 9: continue
        def g(i): return cols[i].strip() if i >= 0 and i < len(cols) else ''
        overall.append({
            'ss': ss, 'attempted': g(c['att']), 'ground': g(c['ground']),
            'placed': g(c['placed']), 'placementBonus': g(c['bonus']),
            'colM': g(c['delCnt']), 'colN': g(c['delBon']),
        })
    print(f'Overall: {len(overall)} rows')
    return overall

def parse_detail(csv_text):
    lines = csv_text.strip().split('\n')
    # Find header row
    header_idx = 0
    for i, line in enumerate(lines):
        if 'SS Number' in line or 'Retailer Number' in line:
            header_idx = i
            break
    reader = csv.reader(io.StringIO(lines[header_idx]))
    headers = [h.strip() for h in next(reader)]
    print(f'Model headers (row {header_idx}): {headers}')

    c = {
        'ss':       find_col(headers, 'SS Number'),
        'retailer': find_col(headers, 'Retailer Number'),
        'so':       find_col(headers, 'SO Number'),
        'formDate': find_col(headers, 'Form Date'),
        'typeCol':  find_col(headers, 'Type of order'),      # Considered/Old Order
        'statusCol':find_col(headers, 'Order status'),       # Delivered/In Process
        'bonus':    find_col(headers, 'Actual Bonus'),
        'delivery': find_col(headers, 'RTO'),                # Col R as requested
    }
    print(f'Column indices: {c}')

    detail = []
    type_counts = {}
    status_counts = {}

    for line in lines[header_idx+1:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if not cols or c['ss'] >= len(cols) or not cols[c['ss']].strip(): continue
        def g(i): return cols[i].strip() if i >= 0 and i < len(cols) else ''
        ss = g(c['ss'])
        if not ss: continue

        col_type   = g(c['typeCol'])
        col_status = g(c['statusCol'])

        if col_type:
            type_counts.setdefault(ss, Counter())[col_type] += 1
        if col_status:
            status_counts.setdefault(ss, Counter())[col_status] += 1

        detail.append({
            'ss': ss, 'retailer': g(c['retailer']), 'so': g(c['so']),
            'formDate': g(c['formDate']),
            'typeOfOrder': col_type, 'orderStatus': col_status,
            'placedBonus': g(c['bonus']), 'deliveryBonus': g(c['delivery']),
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
