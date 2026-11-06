# -*- coding: utf-8 -*-
"""第三阶段核对：CSV 第1、61、498条 与数据库 id=1、61、498 逐字段比较。"""
import csv

import pymysql

CSV_PATH = "/home/pwuser/workspace/lab02/data/houseinfo.csv"
FIELDS = ["title", "house", "address", "struct", "area", "floor", "maketime", "price"]

with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == FIELDS
    csv_rows = list(reader)

conn = pymysql.connect(host="mysql", port=3306, user="student", password="123456",
                       database="smartpark_lab", charset="utf8mb4")
try:
    with conn.cursor() as cur:
        cur.execute("SELECT id,title,house,address,struct,area,floor,maketime,price "
                    "FROM houseinfo WHERE id IN (1,61,498) ORDER BY id")
        db_rows = cur.fetchall()
finally:
    conn.close()

for idx, db in zip((0, 60, len(csv_rows) - 1), db_rows):
    c = csv_rows[idx]
    d = db[1:]
    ok = all(c[k] == d[j] for j, k in enumerate(FIELDS))
    print(f"id={db[0]} CSV第{idx + 1}条 逐字段一致: {ok}")
    for j, k in enumerate(FIELDS):
        mark = "OK " if c[k] == d[j] else "DIFF"
        print(f"  [{mark}] {k}: csv={c[k]!r} db={d[j]!r}")
