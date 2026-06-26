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
        
        # Section 1 & 4 from Overall Performance
        overall.append({
            'ss':              ss,
            'attempted':       g(1), # Keeping Attempted
            'placementBonus': g(8), # Section 4 Data
            'colM':           g(9),
            'colN':           g(10),
            'actualPlaced':   0,    # Will be computed from Model tab
            'delivered':      0,    # Will be computed from Model tab
            'inProcess':      0,    # Will be computed from Model tab
            'returned':       0,    # Will be computed from Model tab
            'cancelled':      0     # Will be computed from Model tab
        })
    print(f'Overall: {len(overall)} rows')
    return overall

def parse_detail(csv_text):
    reader_obj = csv.reader(io.StringIO(csv_text))
    next(reader_obj) # Skip header row
    detail = []
    
    # Track status metric counters per SS
    status_counts = {}
    
    for cols in reader_obj:
        if not cols or len(cols) < 2 or not cols[1].strip(): continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        
        ss = g(1)          # Col B
        col_u = g(20)      # Col U (Type of Order)
        col_v = g(21)      # Col V (Order Status)
        
        if col_v:
            status_counts.setdefault(ss, Counter())[col_v] += 1
            # If the order is not cancelled, count it as a successfully placed order
            if col_v not in ('Cancelled', 'Order Cancelled'):
                status_counts[ss]['__actual_placed__'] += 1
                
        # Building detailed retailer scorecard using requested columns from Model tab
        detail.append({
            'ss':              ss,              # Col B
            'retailer':        g(0),            # Col A
            'so':              g(16),           # Col Q (if needed, otherwise can adjust)
            'formDate':        g(3),            # Col D
            'typeOfOrder':     col_u,           # Col U
            'orderStatus':     col_v,           # Col V
            'bonusPayment':    g(13),           # Col N
            'deliveryPayment': g(17),           # Col R
        })
    print(f'Detail: {len(detail)} rows')
    return detail, status_counts

def merge_overall(overall, status_counts):
    for row in overall:
        ss = row['ss']
        sc = status_counts.get(ss, {})
        
        # Section 1 Update
        row['actualPlaced'] = str(sc.get('__actual_placed__', 0))
        
        # Section 3 Update (Calculated entirely from Model tab metrics)
        row['delivered']  = str(sc.get('Delivered', 0))
        row['inProcess']  = str(sc.get('In Process', 0) + sc.get('In Progress', 0))
        row['returned']   = str(sc.get('Order Return', 0) + sc.get('Returned', 0))
        row['cancelled']  = str(sc.get('Cancelled', 0) + sc.get('Order Cancelled', 0))
        
    return overall

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
    detail, status_counts = parse_detail(detail_csv)
    
    overall     = merge_overall(overall, status_counts)
    build_html(overall, detail)
    print('Done!')
