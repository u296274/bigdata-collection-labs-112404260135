# -*- coding: utf-8 -*-
"""
实验二 第二阶段：安居客教学站房源采集 + CSV 保存
字段顺序：title → house → address → struct → area → floor → maketime → price
"""
import csv
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://www.bspider.top/anjuke/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}
MAX_PAGES = 20        # 安全页数上限，防止无限循环
DELAY = 1.5           # 每次翻页至少等待1秒
CSV_PATH = "/home/pwuser/workspace/lab02/data/houseinfo.csv"
FIELDS = ["title", "house", "address", "struct", "area", "floor", "maketime", "price"]


def fetch_soup(session, url):
    """请求当前页，检查响应内容；验证页视为结构异常。"""
    r = session.get(url, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")
    if "User_Common_Antispam" in r.text or "访问验证" in soup.title.get_text():
        raise RuntimeError(f"遇到访问验证页，停止采集：{url}")
    return soup


def parse_row(row):
    """解析一条房源，返回按 FIELDS 顺序的列表。"""
    # 1. 标题：房源容器内的 h3（相对选择器）
    node = row.select_one("h3")
    title = node.get_text(strip=True) if node else ""

    # 2. 楼盘
    node = row.select_one("p.property-content-info-comm-name")
    house = node.get_text(strip=True) if node else ""

    # 3. 地址：文字分散在多个 span 中，直接拼接，不插入空格
    node = row.select_one("p.property-content-info-comm-address")
    address = "".join(s.get_text(strip=True) for s in node.select("span")) if node else ""

    # 4-7. 户型/面积/楼层/建造年代：属性组 p 列表
    #      顺序固定为 户型、面积、朝向、楼层、建造年代，但建造年代可能缺失，
    #      因此按下标取值前必须检查长度，并按文字特征分类，防止把朝向当成楼层
    info = row.select_one("div.property-content-info:not(.property-content-info-comm)")
    ps = info.select("p.property-content-info-text") if info else []

    struct = ps[0].get_text(strip=True) if len(ps) > 0 else ""   # 第1项：户型，如 3室2厅1卫
    area = ps[1].get_text(strip=True) if len(ps) > 1 else ""     # 第2项：面积，保留单位

    floor, maketime = "", ""
    for p in ps[2:]:                                             # 第3项起：朝向/楼层/年代
        text = p.get_text(strip=True)
        if text.endswith("建造"):
            maketime = text
        elif "层" in text:
            floor = text
        # 其余为朝向，本实验不需要

    # 8. 单价：每平方米价格（不是 property-price-total 的总价）
    node = row.select_one("p.property-price-average")
    price = node.get_text(strip=True) if node else ""

    return [title, house, address, struct, area, floor, maketime, price]


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    current_url = BASE_URL
    visited = set()
    records = []
    page_no = 0
    stop_reason = None

    while True:
        page_no += 1
        if page_no > MAX_PAGES:                       # 达到安全上限只能记为中止
            stop_reason = f"达到安全页数上限 {MAX_PAGES}，中止（不算采集完成）"
            break

        soup = fetch_soup(session, current_url)
        rows = soup.select("div.property")
        if not rows:                                  # 空列表视为结构异常
            stop_reason = f"第{page_no}页未解析到任何房源，结构异常"
            break

        for row in rows:
            records.append(parse_row(row))
        print(f"第{page_no}页 | {current_url} | 本页{len(rows)}条 | 累计{len(records)}条")

        # ---- 找下一页 ----
        nxt = soup.select_one("a.next.next-active")   # 活动的下一页按钮
        if nxt is None:
            disabled = soup.select_one("a.next")      # 下一页按钮存在但已禁用
            if disabled is not None:
                stop_reason = f"第{page_no}页为末页：下一页按钮已禁用，采集完成"
            else:
                stop_reason = f"第{page_no}页分页区域消失，结构异常（不能算采集完成）"
            break

        # ---- 补全地址 ----
        href = nxt.get("href")                        # get_text() 是“下一页”，href 才是地址
        next_url = urljoin(current_url, href)
        print(f"    下一页 href={href} -> 补全为 {next_url}")

        # ---- 停止条件：越界 / 重复 ----
        if not next_url.startswith(BASE_URL):
            stop_reason = f"下一页地址越出教学站：{next_url}"
            break
        if next_url in visited:
            stop_reason = f"下一页地址重复：{next_url}"
            break

        visited.add(current_url)
        time.sleep(DELAY)                             # 至少等待1秒
        current_url = next_url

    print("\n==== 采集结束 ====")
    print("停止原因：", stop_reason)
    print("采集总条数（去重前）：", len(records))

    # ---- 去重：按8个字段完全相同 ----
    seen = set()
    unique_records = []
    for rec in records:
        key = tuple(rec)
        if key not in seen:
            seen.add(key)
            unique_records.append(rec)
    print(f"去重前 {len(records)} 条，去重后 {len(unique_records)} 条，"
          f"重复 {len(records) - len(unique_records)} 条")

    # ---- 保存 CSV ----
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(unique_records)
    print("已保存：", CSV_PATH)

    # ---- 用 DictReader 回读核对 ----
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS, f"表头不符：{reader.fieldnames}"
        data = list(reader)
    print(f"回读数据行数（不含表头）：{len(data)}")
    for i in (0, 60, len(data) - 1):                  # 第一条、跨页一条、最后一条
        print(f"样本第{i + 1}条：", {k: data[i][k] for k in FIELDS})


if __name__ == "__main__":
    main()
