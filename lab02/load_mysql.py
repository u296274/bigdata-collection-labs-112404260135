# -*- coding: utf-8 -*-
"""
实验二 第三阶段：把 data/houseinfo.csv 写入 MySQL（不重新采集）
要点：pymysql 连接 → executemany 批量插入 → commit / rollback → 关闭游标和连接
     按8个字段比较库内已有记录，只插入不存在的记录，避免重复运行时重复插入
"""
import csv

import pymysql

CSV_PATH = "/home/pwuser/workspace/lab02/data/houseinfo.csv"
FIELDS = ["title", "house", "address", "struct", "area", "floor", "maketime", "price"]

# ---- 1. 读取CSV，检查表头，按8个字段固定顺序整理记录 ----
with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == FIELDS, f"表头不符：{reader.fieldnames}"
    records = [tuple(row[k] for k in FIELDS) for row in reader]
print(f"CSV数据行数：{len(records)}，每条{len(records[0])}项")

conn = None
cursor = None
try:
    # ---- 2. 连接数据库（autocommit=False，由程序提交事务）----
    conn = pymysql.connect(
        host="mysql", port=3306,
        user="student", password="123456",
        database="smartpark_lab", charset="utf8mb4",
        autocommit=False,
    )
    cursor = conn.cursor()

    # 连接正常性检查：查询一条数据
    cursor.execute("SELECT COUNT(*) FROM houseinfo")
    before_count = cursor.fetchone()[0]
    print(f"入库前 houseinfo 条数：{before_count}")

    # ---- 3. 查询库内已有记录，避免重复插入 ----
    cursor.execute(
        "SELECT title, house, address, struct, area, floor, maketime, price FROM houseinfo"
    )
    existing = set(cursor.fetchall())
    new_records = [r for r in records if r not in existing]
    print(f"与库内比对后需要新插入：{len(new_records)} 条（跳过已存在 {len(records) - len(new_records)} 条）")

    # ---- 4. INSERT：8个字段对应8个 %s 参数位置 ----
    sql = ("INSERT INTO houseinfo "
           "(title, house, address, struct, area, floor, maketime, price) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")

    if new_records:
        # ---- 5. 批量写入 ----
        affected = cursor.executemany(sql, new_records)
        print(f"executemany 受影响行数：{affected}")
        conn.commit()                              # 写入成功后提交
        print("已提交事务 commit()")
    else:
        print("没有新记录需要插入，不执行写入")

    cursor.execute("SELECT COUNT(*) FROM houseinfo")
    after_count = cursor.fetchone()[0]
    print(f"入库后 houseinfo 条数：{after_count}，本次新增：{after_count - before_count}")

except Exception as e:
    print("出错：", repr(e))
    if conn is not None:
        conn.rollback()                            # 写入出错时回滚，撤销未提交修改
        print("已回滚事务 rollback()")
finally:
    # ---- 6. 无论成功失败都释放资源：先游标后连接 ----
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()
    print("游标和连接已关闭")
