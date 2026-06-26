import csv, json, io
from collections import Counter
import urllib.request as req
import urllib.parse as parse


SHEET_ID = '1jjJvuePQNW-S0QAUC0EyVd_Lx0IHYbksOheJEYmwuFA'


def fetch_sheet(sheet_name):

    encoded = parse.quote(sheet_name)

    url = (
        f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/'
        f'tq?tqx=out:csv&sheet={encoded}'
    )

    print(f'Fetching: {sheet_name} ...')

    with req.urlopen(url) as r:
        return r.read().decode('utf-8')



# ---------------- OVERALL PERFORMANCE ---------------- #

def parse_overall(csv_text):

    lines = csv_text.strip().split('\n')

    overall = []

    start = 0


    for i,line in enumerate(lines):

        cols = next(csv.reader(io.StringIO(line)))

        if cols:

            val = cols[0].strip()

            if val.isdigit() and len(val)>=9:
                start=i
                break



    for line in lines[start:]:

        cols = next(csv.reader(io.StringIO(line)))

        if not cols:
            continue


        ss = cols[0].strip()


        if not ss.isdigit() or ss=="0":
            continue



        def g(i):
            return cols[i].strip() if len(cols)>i else ""



        overall.append({

            "ss": ss,

            "attempted": g(1),

            "placementBonus": g(8),

            "deliveryBonus": g(10)

        })


    print("Overall rows:",len(overall))

    return overall





# ---------------- MODEL TAB ---------------- #

def parse_model(csv_text):

    reader = csv.reader(io.StringIO(csv_text))

    next(reader)


    detail=[]

    status_counts={}

    order_counts={}



    for cols in reader:


        if len(cols)<22:
            continue



        def g(i):

            return cols[i].strip() if len(cols)>i else ""



        ss=g(1)


        if not ss:
            continue



        # MODEL COLUMN MAPPING

        type_of_order = g(20)     # Col U

        order_status = g(21)      # Col V



        # Status summary

        if ss not in status_counts:

            status_counts[ss]=Counter()



        if order_status:

            status_counts[ss][order_status]+=1



        # Actual orders

        order_counts[ss]=order_counts.get(ss,0)+1




        detail.append({

            "ss": ss,

            "retailer": g(0),          # Col A

            "so": g(16),               # SO Number

            "formDate": g(3),          # Col D

            "typeOfOrder": type_of_order,

            "orderStatus": order_status,

            "bonusPayment": g(13),     # Col N

            "deliveryPayment": g(17)   # Col R

        })



    print("Model rows:",len(detail))


    return detail,status_counts,order_counts





# ---------------- MERGE ---------------- #

def merge_overall(overall,status_counts,order_counts):


    for row in overall:


        ss=row["ss"]


        sc=status_counts.get(ss,Counter())



        row["actualPlaced"]=str(
            order_counts.get(ss,0)
        )



        row["delivered"]=str(
            sc.get("Delivered",0)
        )


        row["inProcess"]=str(
            sc.get("In Process",0)
            +
            sc.get("In Progress",0)
        )


        row["returned"]=str(
            sc.get("Order Return",0)
        )


        row["cancelled"]=str(
            sc.get("Order Cancelled",0)
        )



    return overall






# ---------------- CREATE HTML ---------------- #

def build_html(overall,detail):


    OVERALL_JS=json.dumps(
        overall,
        separators=(',',':')
    )


    DETAIL_JS=json.dumps(
        detail,
        separators=(',',':')
    )



    with open("template_part1.txt") as f:
        part1=f.read()


    with open("template_part2.txt") as f:
        part2=f.read()



    html = (
        part1
        +
        "const OVERALL="
        +
        OVERALL_JS
        +
        ";\nconst DETAIL="
        +
        DETAIL_JS
        +
        ";"
        +
        part2
    )



    with open("index.html","w") as f:
        f.write(html)



    print("index.html created")






# ---------------- RUN ---------------- #

if __name__=="__main__":


    overall_csv=fetch_sheet(
        "Overall performance"
    )


    model_csv=fetch_sheet(
        "Model"
    )


    overall=parse_overall(
        overall_csv
    )


    detail,status_counts,order_counts=parse_model(
        model_csv
    )


    overall=merge_overall(
        overall,
        status_counts,
        order_counts
    )


    build_html(
        overall,
        detail
    )


    print("Completed")
