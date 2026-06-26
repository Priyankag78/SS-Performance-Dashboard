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

def find_col(headers, name):
    """Find column index by header name (case-insensitive). Returns LAST match to handle duplicates."""
    result = -1
    for i, h in enumerate(headers):
        if h.strip().lower() == name.strip().lower():
            result = i  # keep updating to get LAST match
    return result

def find_col_first(headers, name):
    """Find FIRST column index by header name."""
    for i, h in enumerate(headers):
        if h.strip().lower() == name.strip().lower():
            return i
    return -1

def parse_overall(csv_text):
    lines = csv_text.strip().split('\n')
    # Find header row containing 'SS Number'
    header_idx = 0
    for i, line in enumerate(lines):
        reader = csv.reader(io.StringIO(line))
        cols = [c.strip() for c in next(reader)]
        if any('ss number' in c.lower() for c in cols):
            header_idx = i
            break

    reader = csv.reader(io.StringIO(lines[header_idx]))
    headers = [h.strip() for h in next(reader)]
    print(f'Overall headers at row {header_idx}: {headers}')

    # Map columns by name
    ci = {}
    ci['ss']     = find_col_first(headers, 'SS Number')
    ci['att']    = find_col_first(headers, 'Orders Attempted')
    ci['ground'] = find_col_first(headers, 'Ground Orders')
    ci['placed'] = find_col_first(headers, 'Actual Orders Placed')
    ci['bonus']  = find_col_first(headers, 'Placement Bonus')
    ci['delCnt'] = find_col_first(headers, 'Actual Orders Delivered')
    ci['delBon'] = find_col_first(headers, 'Delivery Bonus')
    print(f'Overall column map: {ci}')

    overall = []
    for line in lines[header_idx+1:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        def g(key):
            idx = ci.get(key, -1)
            return cols[idx].strip() if idx >= 0 and idx < len(cols) else ''
        ss = g('ss')
        if not ss or not ss.isdigit() or ss == '0' or len(ss) < 9: continue
        overall.append({
            'ss': ss, 'attempted': g('att'), 'ground': g('ground'),
            'placed': g('placed'), 'placementBonus': g('bonus'),
            'colM': g('delCnt'), 'colN': g('delBon'),
        })
    print(f'Overall: {len(overall)} rows')
    if overall:
        print(f'Sample: {json.dumps(overall[0])}')
    return overall

def parse_detail(csv_text):
    lines = csv_text.strip().split('\n')
    # Find header row
    header_idx = 0
    for i, line in enumerate(lines):
        reader = csv.reader(io.StringIO(line))
        cols = [c.strip() for c in next(reader)]
        if any('retailer' in c.lower() for c in cols):
            header_idx = i
            break

    reader = csv.reader(io.StringIO(lines[header_idx]))
    headers = [h.strip() for h in next(reader)]
    print(f'Model headers at row {header_idx}: {headers}')

    # Map columns - use LAST match for 'Type of order' to skip Col E duplicate
    ci = {}
    ci['ss']       = find_col_first(headers, 'SS Number')
    ci['retailer'] = find_col_first(headers, 'Retailer Number')
    ci['so']       = find_col_first(headers, 'SO Number')
    ci['formDate'] = find_col_first(headers, 'Form Date')
    ci['typeCol']  = find_col(headers, 'Type of order')       # LAST match = Col T
    ci['statusCol']= find_col(headers, 'Order status')        # LAST match = Col U
    ci['bonus']    = find_col(headers, 'Actual Bonus')         # Col N
    ci['delivery'] = find_col_first(headers, 'RTO')            # Col R as requested
    print(f'Model column map: {ci}')

    detail = []
    type_counts = {}
    status_counts = {}

    for line in lines[header_idx+1:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        def g(key):
            idx = ci.get(key, -1)
            return cols[idx].strip() if idx >= 0 and idx < len(cols) else ''
        ss = g('ss')
        if not ss: continue

        col_type   = g('typeCol')
        col_status = g('statusCol')

        if col_type:
            type_counts.setdefault(ss, Counter())[col_type] += 1
        if col_status:
            status_counts.setdefault(ss, Counter())[col_status] += 1

        detail.append({
            'ss': ss, 'retailer': g('retailer'), 'so': g('so'),
            'formDate': g('formDate'),
            'typeOfOrder': col_type, 'orderStatus': col_status,
            'placedBonus': g('bonus'), 'deliveryBonus': g('delivery'),
        })

    print(f'Detail: {len(detail)} rows')
    if detail:
        print(f'Sample: {json.dumps(detail[0])}')
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
