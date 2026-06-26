import csv, json, io
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
    data = []
    # Auto-detect first row where col A is a 10-digit SS number
    start = 0
    for i, line in enumerate(lines):
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        val = cols[0].strip() if cols else ''
        if val.isdigit() and len(val) >= 9:
            start = i
            break
    print(f'Overall data starts at line index {start}')
    for line in lines[start:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if not cols or not cols[0].strip(): continue
        ss = cols[0].strip()
        if not ss or not ss.isdigit() or ss == '0': continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        data.append({
            'ss':             ss,
            'attempted':      g(1),   # Col B - Orders Attempted
            'ground':         g(2),   # Col C - Ground Orders
            'old':            g(3),   # Col D - Old Orders
            'placed':         g(4),   # Col E - Actual Orders Placed
            'delivered':      g(5),   # Col F - Delivered Orders
            'rto':            g(6),   # Col G - RTO
            'cancelled':      g(7),   # Col H - Cancelled
            'placementBonus': g(8),   # Col I - Placement Bonus
            'colM':           g(9),   # Col J - Actual Orders Delivered
            'colN':           g(10),  # Col K - Delivery Bonus
            'typeOfOrder':    '',
            'orderStatus':    '',
        })
    print(f'Overall: {len(data)} rows')
    return data

def parse_detail(csv_text):
    reader = csv.reader(io.StringIO(csv_text))
    next(reader)
    data = []
    for cols in reader:
        if not cols or len(cols) < 2 or not cols[1].strip(): continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        data.append({
            'ss':            g(1),
            'retailer':      g(0),
            'so':            g(16),
            'formDate':      g(3),
            'type':          g(4),
            'orderStatus':   g(20),
            'placedBonus':   g(13),
            'deliveryBonus': g(17),
        })
    print(f'Detail: {len(data)} rows')
    return data

def build_html(overall, detail):
    OVERALL_JS = json.dumps(overall, separators=(',',':'))
    DETAIL_JS  = json.dumps(detail,  separators=(',',':'))
    with open('template_part1.txt') as f:
        part1 = f.read()
    with open('template_part2.txt') as f:
        part2 = f.read()
    html = part1 + 'const OVERALL=' + OVERALL_JS + ';\nconst DETAIL=' + DETAIL_JS + ';' + part2
    with open('index.html', 'w') as f:
        f.write(html)
    print(f'Built index.html ({len(html)//1024}KB)')

if __name__ == '__main__':
    overall_csv = fetch_sheet('Overall performance')
    detail_csv  = fetch_sheet('Model')
    overall     = parse_overall(overall_csv)
    detail      = parse_detail(detail_csv)
    build_html(overall, detail)
    print('Done!')
