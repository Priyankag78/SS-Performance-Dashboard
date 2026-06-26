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
            'ss':              ss,
            'attempted':       g(1), 
            'placementBonus': g(8), 
            'colM':           g(9),
            'colN':           g(10),
            'actualPlaced':   0,    
            'delivered':      0,    
            'inProcess':      0,    
            'returned':       0,    
            'cancelled':      0     
        })
    print(f'Overall: {len(overall)} rows')
    return overall

def parse_detail(csv_text):
    reader_obj = csv.reader(io.StringIO(csv_text))
    
    # Dynamically read headers to find the exact column mappings
    headers = [h.strip().lower() for h in next(reader_obj)]
    
    # Safely search for index by checking standard naming conventions
    def find_idx(possible_names):
        for name in possible_names:
            if name in headers:
                return headers.index(name)
        return -1

    idx_ss = find_idx(['ss', 'ss number', 'ss_number'])
    idx_retailer = find_idx(['retailer', 'retailer number', 'retailer_number'])
    idx_so = find_idx(['so', 'so number', 'so_number'])
    idx_date = find_idx(['form date', 'form_date', 'date'])
    idx_type = find_idx(['type of order', 'type_of_order', 'type'])
    idx_status = find_idx(['order status', 'order_status', 'status'])
    idx_bonus = find_idx(['bonus payment', 'bonus_payment', 'bonus'])
    idx_delivery = find_idx(['delivery payment', 'delivery_payment', 'delivery'])

    # Fallback to defaults if a column name isn't dynamically hit
    if idx_ss == -1: idx_ss = 1
    if idx_retailer == -1: idx_retailer = 0
    if idx_so == -1: idx_so = 16
    if idx_date == -1: idx_date = 3
    if idx_type == -1: idx_type = 21
    if idx_status == -1: idx_status = 22
    if idx_bonus == -1: idx_bonus = 14
    if idx_delivery == -1: idx_delivery = 18

    detail = []
    status_counts = {}
    
    for cols in reader_obj:
        if not cols or len(cols) <= max(idx_ss, idx_retailer): continue
        
        def g(i): return cols[i].strip() if i >= 0 and len(cols) > i else ''
        
        ss = g(idx_ss)
        if not ss: continue
        
        col_t = g(idx_type)    # Type of Order
        col_u = g(idx_status)  # Order Status
        
        if col_u:
            status_counts.setdefault(ss, Counter())[col_u] += 1
            if col_u not in ('Cancelled', 'Order Cancelled'):
                status_counts[ss]['__actual_placed__'] += 1
                
        detail.append({
            'ss':              ss,
            'retailer':        g(idx_retailer),
            'so':              g(idx_so),
            'formDate':        g(idx_date),
            'typeOfOrder':     col_t,
            'orderStatus':     col_u,
            'bonusPayment':    g(idx_bonus),
            'deliveryPayment': g(idx_delivery),
        })
        
    print(f'Detail: {len(detail)} rows mapped successfully.')
    return detail, status_counts

def merge_overall(overall, status_counts):
    for row in overall:
        ss = row['ss']
        sc = status_counts.get(ss, {})
        
        row['actualPlaced'] = str(sc.get('__actual_placed__', 0))
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
