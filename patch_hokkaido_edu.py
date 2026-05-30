"""
北海道教育大 残余 + その他 追加パッチ
Phase 2 で未取得だった：
  - 函館校 国際協働グループ/前後期
  - 旭川校 芸術3分野（音楽・美術・保健体育）/前期
  - 札幌校 音楽教育/保健体育教育分野/前期
"""
import re, json, time, sys, io
import requests
from bs4 import BeautifulSoup
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = Path(__file__).parent
DATA_JSON = BASE / "data" / "data.json"
KEINET_BASE = "https://www.keinet.ne.jp/exam/past/result/ippan/national/{}.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

_SKIP_ROW = re.compile(r"日程計|大学計|前期計|後期計|中期計|合計")

def expand_table(table):
    rows_html = table.find_all("tr")
    n = len(rows_html)
    grid = [[] for _ in range(n)]
    occ = {}
    for ri, row_html in enumerate(rows_html):
        ci = 0
        for cell in row_html.find_all(["th","td"]):
            while (ri,ci) in occ: ci += 1
            text = cell.get_text(strip=True)
            rs = int(cell.get("rowspan",1))
            cs = int(cell.get("colspan",1))
            for dr in range(rs):
                for dc in range(cs):
                    while len(grid[ri+dr]) <= ci+dc: grid[ri+dr].append(None)
                    if dr==0 and dc==0: grid[ri+dr][ci+dc] = text
                    else: occ[(ri+dr,ci+dc)]=True; grid[ri+dr][ci+dc]=text
            ci += cs
    return [[c or "" for c in r] for r in grid]

def fetch_kn(kid):
    url = KEINET_BASE.format(kid)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = []
    for tbl in soup.find_all("table", class_="kn-tbl"):
        h = tbl.find_previous(["h2","h3"])
        gakubu = h.get_text(strip=True) if h else ""
        grid = expand_table(tbl)
        for row in grid[2:]:
            if len(row) < 6: continue
            if _SKIP_ROW.search(row[0]) or _SKIP_ROW.search(row[1]): continue
            if row[1] not in ("前期","後期","中期"): continue
            def n(s):
                s = s.replace(",","").strip()
                try:
                    v = float(s); return int(v) if v==int(v) else v
                except: return None
            rows.append({"gb":gakubu,"gk":row[0] if row[0] else gakubu,"nt":row[1],
                         "s26":n(row[2]),"j26":n(row[3]),"g26":n(row[4]),"k26":n(row[5]),
                         "k25":n(row[9]) if len(row)>9 else None})
    return rows

def ku(kn):
    kuprv = None
    if kn.get("k26") is not None and kn.get("k25") and kn["k25"]!=0:
        kuprv = round(kn["k26"]/kn["k25"]*100,1)
    return {"boshu":None,"shigan":kn["s26"],"juken":kn["j26"],"gokaku":kn["g26"],"ku":kn["k26"],"kuprv":kuprv}

with open(DATA_JSON, encoding="utf-8") as f:
    db = json.load(f)
records = db["records"]

def find_rec(univ, f, d, m):
    for r in records:
        if r["u"]==univ and r.get("f","")==f and r.get("d","")==d and r["m"]==m:
            return r
    return None

def set26(r, kn_entry):
    if r and "2026" not in r["bairitsu"]:
        r["bairitsu"]["2026"] = kn_entry
        return True
    return False

added = 0

# ── 北海道教育大 ───────────────────────────────────────────
print("北海道教育大 残余パッチ...")
kn_rows = fetch_kn(1030)
time.sleep(0.8)

# KN エントリを辞書に
kn_dict = {(r["gb"], r["gk"], r["nt"]): r for r in kn_rows}

# 明示マッピング: (KN gakubu, gakka, nittei) → (DB f, d, method)
HKKEDU_MAP = [
    # 函館校 国際協働グループ
    ("教育函館校", "国際－国際協働",    "前期", "函館校", "国際地域学科｜地域協働専攻｜国際協働グループ",    "前期日程"),
    ("教育函館校", "国際－国際協働",    "後期", "函館校", "国際地域学科｜地域協働専攻｜国際協働グループ",    "後期日程"),
    ("教育函館校", "国際－地域政策",    "後期", "函館校", "国際地域学科｜地域協働専攻｜地域政策グループ",    "後期日程"),
    ("教育函館校", "国際－地域環境科学","後期", "函館校", "国際地域学科｜地域協働専攻｜地域環境科学グループ","後期日程"),
    # 旭川校 芸術・保健体育3分野
    ("教育旭川校", "教員－芸術（音楽）","前期", "旭川校", "教員養成課程｜芸術・保健体育教育専攻｜音楽分野",    "前期日程"),
    ("教育旭川校", "教員－芸術（美術）","前期", "旭川校", "教員養成課程｜芸術・保健体育教育専攻｜美術分野",    "前期日程"),
    ("教育旭川校", "教員－保健体育",    "前期", "旭川校", "教員養成課程｜芸術・保健体育教育専攻｜保健体育分野","前期日程"),
    # 札幌校 音楽・保健体育
    ("教育札幌校", "教員－音楽教育",    "前期", "札幌校", "教員養成課程｜芸術体育教育専攻｜音楽教育分野",      "前期日程"),
    ("教育札幌校", "教員－保健体育教育","前期", "札幌校", "教員養成課程｜芸術体育教育専攻｜保健体育教育分野",  "前期日程"),
]

for (gb, gk, nt, f, d, m) in HKKEDU_MAP:
    kn_e = kn_dict.get((gb, gk, nt))
    if kn_e is None or kn_e["s26"] is None:
        print(f"  KN なし: [{gb}]{gk}/{nt}")
        continue
    r = find_rec("北海道教育大", f, d, m)
    if r is None:
        print(f"  DB なし: {f}・{d}/{m}")
        continue
    if set26(r, ku(kn_e)):
        added += 1
        print(f"  ✅ {f}・{d[:30]}/{m} 志願={kn_e['s26']} 合格={kn_e['g26']}")
    else:
        print(f"  ✓ 既存: {d[:30]}")

# ── 北見工業大: 先進工学部 公式HP ─────────────────────────
print("\n北見工業大 公式HP...")
for url in [
    "https://www.kitami-it.ac.jp/admission/r7/nyushi_kekka/",
    "https://www.kitami-it.ac.jp/entrance/past/",
    "https://www.kitami-it.ac.jp/admission/",
]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, "html.parser")
        # リンクを探す
        found_link = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = a.get_text().strip()
            if ("入試結果" in txt or "入試状況" in txt or "合格" in txt) and ("2026" in txt or "7年" in txt or "令和7" in txt):
                found_link = href
                break
        if found_link:
            if not found_link.startswith("http"):
                base_url = "/".join(url.split("/")[:3])
                found_link = base_url + found_link
            print(f"  見つかったリンク: {found_link}")
            resp2 = requests.get(found_link, headers=HEADERS, timeout=15)
            soup2 = BeautifulSoup(resp2.content, "html.parser")
            # テーブルから数値抽出
            for tbl in soup2.find_all("table"):
                grid = expand_table(tbl)
                for row in grid:
                    joined = " ".join(row)
                    for nt_kw, m_db in [("前期","前期日程"),("後期","後期日程")]:
                        if nt_kw in joined:
                            nums = [int(c.replace(",","")) for c in row if c.replace(",","").isdigit()]
                            if len(nums) >= 3:
                                entry = {"boshu":None,"shigan":nums[0],"juken":nums[1],"gokaku":nums[2],
                                         "ku":round(nums[1]/nums[2],1) if nums[2] else None,"kuprv":None}
                                # 新規レコード
                                new_rec = {"u":"北見工業大","f":"先進工学部","d":"（2026年統合）","m":m_db,
                                          "kind":"一般","bairitsu":{"2026":entry},
                                          "border":{},"hensa":{},"kyo_man":None,"ko_man":None,
                                          "ratio":None,"kyo_subj":None,"ko_subj":None}
                                records.append(new_rec)
                                added += 1
                                print(f"  ✅ 北見工業大 先進工/{m_db} 志願={nums[0]} 合格={nums[2]}")
            break
        time.sleep(0.5)
    except Exception as e:
        print(f"  HP取得失敗 {url}: {e}")
        time.sleep(0.3)

# ── サマリー ──────────────────────────────────────────────
print(f"\n追加: {added} 件")
count_2026 = sum(1 for r in records if "2026" in r.get("bairitsu",{}))
print(f"2026データ合計: {count_2026} / {len(records)} 件")

db["records"] = records
with open(DATA_JSON, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, separators=(",",":"))
print("data.json 保存完了")
