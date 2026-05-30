"""
Kei-Net から 2026年度入試結果を取得し、data/data.json に追記するスクリプト。

取得データ: 志願者数・受験者数・合格者数・競争率 (募集人員は非掲載のため None)
マッチング: 学部/学科/日程の名称を正規化して DB レコードと照合
出力:
  - data/data.json を 2026 データで更新
  - scrape_report_2026.md に処理結果レポートを出力
"""

import re
import json
import time
import copy
import sys
import io
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from pathlib import Path

# Windows CP932 端末での絵文字出力エラーを防ぐため stdout を UTF-8 に強制
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── パス ───────────────────────────────────────────────
BASE = Path(__file__).parent
DATA_JSON = BASE / "data" / "data.json"
REPORT_FILE = BASE / "scrape_report_2026.md"

# ─── 大学名 DB → Kei-Net ID マッピング ──────────────────
# DB の大学名をキー、Kei-Net のページ ID を値とする
UNIV_KEINET: dict[str, int] = {
    # 北海道
    "旭川医科大":           1005,
    "小樽商科大":           1010,
    "帯広畜産大":           1015,
    "北見工業大":           1020,
    "北海道大":             1025,
    "北海道教育大":         1030,
    "室蘭工業大":           1035,
    "公立千歳科学技術大":   1509,
    "公立はこだて未来大":   1507,
    "札幌医科大":           1505,
    "札幌市立大":           1506,
    "名寄市立大":           1508,
    "釧路市立大":           1510,   # Kei-Net: 釧路公立大
    # 東北
    "青森県立保健大":       1516,
    "青森公立大":           1513,
    "弘前大":               1040,
    "岩手大":               1045,
    "岩手県立大":           1512,
    "東北大":               1050,
    "宮城大":               1514,
    "宮城教育大":           1055,
    "秋田大":               1060,
    "秋田県立大":           1517,
    "秋田公立美術大":       1522,
    "東北農林専門職大":     1529,
    "山形大":               1065,
    "山形県立保健医療大":   1511,
    "会津大":               1518,
    "福島大":               1070,
    "福島県立医科大":       1515,
    # 関東
    "茨城大":               1075,
    "茨城県立医療大":       1519,
    "筑波大":               1085,
    "宇都宮大":             1090,
    "群馬大":               1095,
    "群馬県立県民健康科学大": 1524,
    "群馬県立女子大":       1525,
    "高崎経済大":           1520,
    "前橋工科大":           1523,
    "埼玉大":               1100,
    "埼玉県立大":           1526,
    "千葉大":               1105,
    "千葉県立保健医療大":   1528,
    "神奈川県立保健福祉大": 1542,
    "川崎市立看護大":       1541,
    "横浜国立大":           1170,
    "横浜市立大":           1540,
    # 東京
    "お茶の水女子大":       1110,
    "電気通信大":           1115,
    "東京大":               1120,
    "東京外国語大":         1130,
    "東京学芸大":           1135,
    "東京藝術大":           1140,   # Kei-Net: 東京芸術大
    "東京都立大":           1532,
    "東京農工大":           1160,
    "一橋大":               1165,
    # 甲信越
    "三条市立大":           1551,
    "上越教育大":           1185,
    "長岡技術科学大":       1175,
    "長岡造形大":           1546,
    "新潟大":               1180,
    "新潟県立大":           1544,
    "新潟県立看護大":       1543,
    "都留文科大":           1560,
    "山梨大":               1215,
    "山梨県立大":           1561,
    "信州大":               1225,
    # 北陸
    "富山大":               1190,
    "富山県立大":           1545,
    "石川県立大":           1547,
    "石川県立看護大":       1549,
    "金沢大":               1200,
    "福井大":               1205,
    "福井県立大":           1555,
    # 東海
    "岐阜大":               1260,
    "岐阜県立看護大":       1564,
    "岐阜薬科大":           1565,
    "静岡大":               1230,
    "静岡県立大":           1570,
    "静岡県農林環境専門職大": 1572,  # Kei-Net: 静岡県立農林環境専門職大
    "静岡文化芸術大":       1571,
    "浜松医科大":           1235,
    "愛知教育大":           1240,
    "豊橋技術科学大":       1245,
    "名古屋大":             1250,
    "名古屋工業大":         1255,
    "名古屋市立大":         1585,
    "三重大":               1265,
    "三重県立看護大":       1586,
    # 近畿
    "滋賀大":               1270,
    "滋賀医科大":           1275,
    "滋賀県立大":           1587,
    "京都大":               1280,
    "京都教育大":           1285,
    "京都工芸繊維大":       1290,
    "京都市立芸術大":       1590,
    "京都府立大":           1595,
    "京都府立医科大":       1600,
    "大阪大":               1295,
    "大阪教育大":           1305,
    "大阪公立大":           1615,
    "神戸大":               1310,
    "兵庫教育大":           1320,
    "兵庫県立大":           1627,
    "奈良教育大":           1325,
    "奈良県立大":           1640,
    "奈良県立医科大":       1635,
    "奈良女子大":           1330,
    "和歌山大":             1335,
    "和歌山県立医科大":     1645,
    # 中国
    "公立鳥取環境大":       1646,
    "鳥取大":               1340,
    "島根大":               1345,
    "島根県立大":           1647,
    "岡山大":               1355,
    "岡山県立大":           1648,
    "広島大":               1360,
    "県立広島大":           1656,
    "広島市立大":           1658,
    "尾道市立大":           1653,
    "山口大":               1365,
    "山口県立大":           1663,
    "山陽小野田市立山口東京理工大": 1661,
    "周南公立大":           1666,
    # 四国
    "徳島大":               1370,
    "鳴門教育大":           1375,
    "香川大":               1380,
    "香川県立保健医療大":   1667,
    "愛媛大":               1390,
    "愛媛県立医療技術大":   1668,
    "高知大":               1395,
    "高知県立大":           1670,
    "高知工科大":           1671,
    # 九州
    "九州大":               1405,
    "九州工業大":           1415,
    "九州歯科大":           1680,
    "福岡教育大":           1420,
    "福岡県立大":           1685,
    "福岡女子大":           1690,
    "佐賀大":               1425,
    "長崎大":               1435,
    "長崎県立大":           1695,
    "熊本大":               1440,
    "熊本県立大":           1700,
    "大分大":               1445,
    "大分県立看護科学大":   1702,
    "宮崎大":               1455,
    "宮崎県立看護大":       1704,
    "宮崎公立大":           1703,
    "鹿児島大":             1465,
    "鹿屋体育大":           1470,
    "沖縄県立芸術大":       1705,
    "名桜大":               1710,
    "琉球大":               1475,
}

KEINET_BASE = "https://www.keinet.ne.jp/exam/past/result/ippan/national/{}.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
}

# ─── 名称正規化 ──────────────────────────────────────────
_STRIP_SUFFIXES = re.compile(
    r"学部|学科|学類|学域|学群|課程|専攻|コース|学院|研究科|選抜群|特別|入試"
)
_STRIP_SEP = re.compile(r"[・｜\-－\s　（）()【】]")
_PAREN = re.compile(r"[（(][^）)]*[）)]")

def normalize(s: str) -> str:
    s = _STRIP_SUFFIXES.sub("", s)
    s = _STRIP_SEP.sub("", s)
    return s.strip()

def strip_parens(s: str) -> str:
    """括弧とその内容を除去"""
    return _PAREN.sub("", s).strip()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# スキップすべき集計行のキーワード
_SKIP_ROW = re.compile(r"日程計|大学計|前期計|後期計|中期計|合計")

# ─── HTML テーブル展開 (rowspan/colspan 対応) ────────────
def expand_table(table) -> list[list[str]]:
    """BeautifulSoup の table 要素を rowspan/colspan を展開した 2D リストに変換"""
    rows_html = table.find_all("tr")
    n_rows = len(rows_html)
    grid: list[list[str | None]] = [[] for _ in range(n_rows)]
    # 使用済みセル: (row, col) -> True
    occupied: dict[tuple[int, int], bool] = {}

    for ri, row_html in enumerate(rows_html):
        ci = 0
        for cell in row_html.find_all(["th", "td"]):
            # 既存の rowspan で埋まっているセルをスキップ
            while (ri, ci) in occupied:
                ci += 1
            text = cell.get_text(strip=True)
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            # rowspan/colspan に応じてマーク
            for dr in range(rowspan):
                for dc in range(colspan):
                    pos = (ri + dr, ci + dc)
                    if dr == 0 and dc == 0:
                        # 値を配置
                        while len(grid[ri + dr]) <= ci + dc:
                            grid[ri + dr].append(None)
                        grid[ri + dr][ci + dc] = text
                    else:
                        occupied[pos] = True
                        # 後の行への伝播: rowspan > 1 の場合
                        if dr > 0:
                            while len(grid[ri + dr]) <= ci + dc:
                                grid[ri + dr].append(None)
                            grid[ri + dr][ci + dc] = text
            ci += colspan

    # None を空文字に変換
    result = []
    for row in grid:
        result.append([c if c is not None else "" for c in row])
    return result

# ─── Kei-Net 1大学分のデータ取得 ────────────────────────
def fetch_keinet_data(keinet_id: int) -> list[dict]:
    """
    戻り値: list of {gakubu, gakka, nittei, s26, j26, g26, k26, s25, j25, g25, k25}
    """
    url = KEINET_BASE.format(keinet_id)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    rows_data = []
    for table in soup.find_all("table", class_="kn-tbl"):
        h = table.find_previous(["h2", "h3"])
        gakubu = h.get_text(strip=True) if h else ""

        grid = expand_table(table)
        # ヘッダー行 (先頭 2 行) をスキップ
        for row in grid[2:]:
            if len(row) < 6:
                continue
            # 集計行スキップ
            if _SKIP_ROW.search(row[0]) or _SKIP_ROW.search(row[1]):
                continue
            # 前期/後期/中期 以外の日程もスキップ
            nittei_raw = row[1]
            if nittei_raw not in ("前期", "後期", "中期"):
                continue

            def to_num(s):
                s = s.replace(",", "").strip()
                try:
                    v = float(s)
                    return int(v) if v == int(v) else v
                except (ValueError, OverflowError):
                    return None

            rows_data.append({
                "gakubu":  gakubu,
                "gakka":   row[0] if row[0] else gakubu,
                "nittei":  nittei_raw,
                "s26": to_num(row[2]),
                "j26": to_num(row[3]),
                "g26": to_num(row[4]),
                "k26": to_num(row[5]),
                "s25": to_num(row[6]) if len(row) > 6 else None,
                "j25": to_num(row[7]) if len(row) > 7 else None,
                "g25": to_num(row[8]) if len(row) > 8 else None,
                "k25": to_num(row[9]) if len(row) > 9 else None,
            })
    return rows_data

# ─── DB レコードのラベル生成 ────────────────────────────
def dept_label(f: str, d: str) -> str:
    if f and d:
        return f"{f}・{d}"
    return d or f or ""

# ─── マッチング ──────────────────────────────────────────
MATCH_THRESHOLD = 0.72

def build_keinet_keys(gakubu: str, gakka: str) -> list[str]:
    """
    Kei-Net の学部/学科から複数の正規化キーを返す（マッチング候補）。
    - gakka == gakubu のケース: 学部+学部 (doubled) も生成して 医学部・医学科 型の
      DB レコードと一致させる
    - 括弧付き名称: 括弧を除いたバージョンも追加 (例: 先導（文系傾斜）→先導)
    """
    seen: set[str] = set()
    keys: list[str] = []

    def add(s: str) -> None:
        n = normalize(s)
        if n and n not in seen:
            seen.add(n)
            keys.append(n)

    if gakka and gakka != gakubu:
        add(gakubu + gakka)          # 学部+学科
        add(gakka)                   # 学科のみ
        gakka_s = strip_parens(gakka)
        if gakka_s and gakka_s != gakka:
            add(gakubu + gakka_s)    # 学部+学科(括弧除去)
            add(gakka_s)             # 学科のみ(括弧除去)
    else:
        # gakka が空だった → gakubu が学部名かつ唯一の手がかり
        # "医学部・医学科" 型 DB キー "医医" にも対応するため doubled key を追加
        add(gakubu + gakubu)         # doubled
        add(gakubu)                  # 単独 fallback

    return keys or [normalize(gakubu)]

def build_db_keys(f: str, d: str) -> list[str]:
    """
    DB の学部/学科から複数の正規化キーを返す（マッチング候補）。
    f単独キーは含めない。学部名が短い場合に複数レコードで "医" 等の共通 f が
    偽陽性マッチを引き起こすことを防ぐ。
    """
    seen: set[str] = set()
    keys: list[str] = []

    def add(s: str) -> None:
        n = normalize(s)
        if n and n not in seen:
            seen.add(n)
            keys.append(n)

    add((f or "") + (d or ""))   # f+d 結合 (primary)
    if d:
        add(d)                   # d のみ (secondary)

    return keys or [""]

METHOD_MAP = {"前期": "前期日程", "後期": "後期日程", "中期": "中期日程"}

def find_best_match(
    kn_row: dict,
    db_records: list[dict],
) -> tuple[dict | None, float, str]:
    """
    Kei-Net 行に最も合致する DB レコードと類似度を返す。
    戻り値: (record | None, score, reason)
    """
    kn_keys = build_keinet_keys(kn_row["gakubu"], kn_row["gakka"])
    kn_method = METHOD_MAP.get(kn_row["nittei"], "")

    best_rec = None
    best_score = 0.0
    best_reason = ""

    for rec in db_records:
        if rec["m"] != kn_method:
            continue
        db_keys = build_db_keys(rec["f"], rec["d"])
        # 全 kn_key × db_key 組み合わせの最高スコアを採用
        score = max(
            similarity(kk, dk)
            for kk in kn_keys
            for dk in db_keys
        )
        if score > best_score:
            best_score = score
            best_rec = rec
            best_reason = f"kn={kn_keys[0]!r} ↔ db={db_keys[0]!r}"

    return best_rec, best_score, best_reason

# ─── メイン処理 ─────────────────────────────────────────
def main():
    # data.json 読み込み
    with open(DATA_JSON, encoding="utf-8") as f:
        db = json.load(f)

    records = db["records"]

    # 大学名 → レコードリストのインデックス
    univ_records: dict[str, list[dict]] = {}
    for rec in records:
        univ_records.setdefault(rec["u"], []).append(rec)

    # 統計
    total_updated = 0
    total_skipped_no_id = 0
    total_skipped_no_match = 0
    total_already_have = 0
    report_lines: list[str] = []

    def rpt(s=""):
        report_lines.append(s)
        print(s)

    rpt("# 2026年度データ取得レポート (Kei-Net)")
    rpt(f"\nデータソース: https://www.keinet.ne.jp/exam/past/result/ippan/national/")
    rpt(f"対象大学数: {len(UNIV_KEINET)}\n")
    rpt("---")

    for univ_name, keinet_id in UNIV_KEINET.items():
        recs_for_univ = univ_records.get(univ_name, [])
        if not recs_for_univ:
            rpt(f"\n### {univ_name}  → DB にレコードなし (スキップ)")
            total_skipped_no_id += 1
            continue

        rpt(f"\n### {univ_name}  (Kei-Net ID: {keinet_id})")

        try:
            kn_rows = fetch_keinet_data(keinet_id)
        except Exception as e:
            rpt(f"  ❌ 取得エラー: {e}")
            total_skipped_no_id += 1
            time.sleep(1)
            continue

        time.sleep(0.8)  # rate limit

        matched_count = 0
        unmatched_kn = []
        db_matched_keys: set[str] = set()

        for kn in kn_rows:
            # 2026 データが空なら意味なし
            if kn["s26"] is None and kn["g26"] is None:
                continue

            rec, score, reason = find_best_match(kn, recs_for_univ)

            if rec is None or score < MATCH_THRESHOLD:
                unmatched_kn.append(
                    f"  ⚠ 未マッチ [{kn['gakubu']}]{kn['gakka']}/{kn['nittei']} "
                    f"(最高score={score:.2f})"
                )
                total_skipped_no_match += 1
                continue

            # 既存確認
            rec_key = f"{rec['u']}|{dept_label(rec['f'],rec['d'])}|{rec['m']}"
            if "2026" in rec["bairitsu"]:
                rpt(
                    f"  ✓ 既存 [{kn['gakubu']}]{kn['gakka']}/{kn['nittei']} "
                    f"→ {dept_label(rec['f'],rec['d'])} (score={score:.2f})"
                )
                total_already_have += 1
                db_matched_keys.add(rec_key)
                continue

            # kuprv (前年比競争率) を計算
            kuprv = None
            if kn["k26"] is not None and kn["k25"] is not None and kn["k25"] != 0:
                raw = round(kn["k26"] / kn["k25"] * 100, 1)
                kuprv = raw

            rec["bairitsu"]["2026"] = {
                "boshu":  None,
                "shigan": kn["s26"],
                "juken":  kn["j26"],
                "gokaku": kn["g26"],
                "ku":     kn["k26"],
                "kuprv":  kuprv,
            }
            matched_count += 1
            total_updated += 1
            db_matched_keys.add(rec_key)
            rpt(
                f"  ✅ 追加 [{kn['gakubu']}]{kn['gakka']}/{kn['nittei']} "
                f"→ {dept_label(rec['f'],rec['d'])} "
                f"志願={kn['s26']} 受験={kn['j26']} 合格={kn['g26']} 競争率={kn['k26']} "
                f"(score={score:.2f})"
            )

        for line in unmatched_kn:
            rpt(line)

        # DB にあるが Kei-Net にマッチしなかったレコード
        unmatched_db = [
            dept_label(r["f"], r["d"]) + "/" + r["m"]
            for r in recs_for_univ
            if f"{r['u']}|{dept_label(r['f'],r['d'])}|{r['m']}" not in db_matched_keys
            and "2026" not in r["bairitsu"]
        ]
        if unmatched_db:
            for s in unmatched_db:
                rpt(f"  ℹ DB のみ (Kei-Net 未取得): {s}")

        rpt(f"  → 追加={matched_count}")

    # ─── サマリー ───────────────────────────────────────
    rpt("\n---")
    rpt("## サマリー")
    rpt(f"- 2026データ追加: {total_updated} 件")
    rpt(f"- 既存データ (スキップ): {total_already_have} 件")
    rpt(f"- マッチング失敗: {total_skipped_no_match} 件")
    rpt(f"- 大学取得エラー/DBなし: {total_skipped_no_id} 件")

    # ─── JSON 保存 ───────────────────────────────────────
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
    rpt(f"\ndata.json を更新しました: {DATA_JSON}")

    # ─── レポート保存 ────────────────────────────────────
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nレポート保存: {REPORT_FILE}")


if __name__ == "__main__":
    main()
