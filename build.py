#!/usr/bin/env python3
"""
Build script: fetches both Google Sheet tabs and builds index.html
Run locally or via GitHub Actions - auto-triggers daily
"""
import csv, json, sys, io
import urllib.request as req

SHEET_ID = '1jjJvuePQNW-S0QAUC0EyVd_Lx0IHYbksOheJEYmwuFA'

def fetch_sheet(sheet_name):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    print(f'Fetching: {sheet_name}...')
    with req.urlopen(url) as r:
        return r.read().decode('utf-8')

def parse_overall(csv_text):
    """
    Overall performance tab:
    Col A=SS Number, Col B=Attempted, Col C=Ground, Col D=Old,
    Col E=Placed, Col F=Delivered, Col G=RTO, Col H=Cancelled,
    Col I=Placement Bonus, Col M=Delivery Bonus Online,
    Col N=Delivery Bonus Offline, Col P=Type of order, Col Q=Order status
    Header on row 3, data from row 4
    """
    lines = csv_text.strip().split('\n')
    data = []
    for line in lines[3:]:
        reader = csv.reader(io.StringIO(line))
        cols = next(reader)
        if not cols or not cols[0].strip(): continue
        ss = cols[0].strip()
        if not ss or not ss.isdigit() or ss == '0': continue
        def g(i): return cols[i].strip() if len(cols) > i else ''
        data.append({
            'ss':             ss,
            'attempted':      g(1),
            'ground':         g(2),
            'old':            g(3),
            'placed':         g(4),
            'delivered':      g(5),
            'rto':            g(6),
            'cancelled':      g(7),
            'placementBonus': g(8),   # Col I
            'colM':           g(12),  # Col M = Delivery Bonus Online
            'colN':           g(13),  # Col N = Delivery Bonus Offline
            'typeOfOrder':    g(15),  # Col P
            'orderStatus':    g(16),  # Col Q
        })
    print(f'Overall: {len(data)} rows')
    return data

def parse_detail(csv_text):
    """
    Model tab:
    Col A=Retailer, Col B=SS Number, Col D=Form Date,
    Col E=Type of Order, Col N=Actual Bonus (Placed Bonus),
    Col Q=SO Number, Col R=RTO (Delivery Bonus as requested),
    Col T=Type of order, Col U=Order status
    """
    reader = csv.reader(io.StringIO(csv_text))
    headers = next(reader)
    data = []
    for cols in reader:
        if not cols or not cols[1].strip(): continue
        ss = cols[1].strip()
        def g(i): return cols[i].strip() if len(cols) > i else ''
        data.append({
            'ss':            ss,
            'retailer':      g(0),   # Col A
            'so':            g(16),  # Col Q = SO Number
            'formDate':      g(3),   # Col D
            'type':          g(4),   # Col E = Type of Order
            'orderStatus':   g(20),  # Col U = Order status
            'placedBonus':   g(13),  # Col N = Actual Bonus
            'deliveryBonus': g(17),  # Col R = RTO (as requested)
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
