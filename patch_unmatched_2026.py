"""
patch_unmatched_2026.py  —  Phase 2 パッチスクリプト

Phase 1 (scrape_2026_keinet.py) でマッチング失敗した 694 件を補完する。

改善点:
  1. 〈昼〉/〈夜〉 ↔ （昼間）/（夜間主）の正規化
  2. 教育系学科のキーワードマッチング（国語, 数学, etc.）
  3. 筑波大型プレースホルダー d "（学類組織なし）" の処理
  4. 文系/理系/A系 qualifier のストリップ
  5. 閾値を 0.65 に緩和（特定パターン限定）
  6. 多対1集約（前橋工科大等）
  7. 明示的な大学固有マッピング（九州工業大 類→学科名 等）
  8. 公式 HP からのデータ取得（北見工業大・九州工業大・信州大工等）
"""

import re
import json
import time
import sys
import io
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from pathlib import Path
from collections import defaultdict

# Windows CP932 端末の絵文字エラー防止
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE        = Path(__file__).parent
DATA_JSON   = BASE / "data" / "data.json"
REPORT_FILE = BASE / "patch_report_2026.md"

KEINET_BASE = "https://www.keinet.ne.jp/exam/past/result/ippan/national/{}.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
}

# ─── Phase 1 でマッチング失敗のあった67大学 ─────────────────
TARGET_UNIVS: dict[str, int] = {
    "小樽商科大":           1010,
    "北見工業大":           1020,
    "北海道教育大":         1030,
    "弘前大":               1040,
    "岩手大":               1045,
    "東北大":               1050,
    "宮城教育大":           1055,
    "山形大":               1065,
    "福島大":               1070,
    "茨城大":               1075,
    "筑波大":               1085,
    "宇都宮大":             1090,
    "群馬大":               1095,
    "埼玉大":               1100,
    "千葉大":               1105,
    "お茶の水女子大":       1110,
    "東京外国語大":         1130,
    "東京学芸大":           1135,
    "一橋大":               1165,
    "横浜国立大":           1170,
    "新潟大":               1180,
    "金沢大":               1200,
    "福井大":               1205,
    "浜松医科大":           1235,
    "愛知教育大":           1240,
    "名古屋工業大":         1255,
    "三重大":               1265,
    "滋賀大":               1270,
    "京都大":               1280,
    "京都教育大":           1285,
    "京都工芸繊維大":       1290,
    "大阪教育大":           1305,
    "奈良女子大":           1330,
    "和歌山大":             1335,
    "岡山大":               1355,
    "広島大":               1360,
    "山口大":               1365,
    "徳島大":               1370,
    "鳴門教育大":           1375,
    "愛媛大":               1390,
    "九州大":               1405,
    "九州工業大":           1415,
    "福岡教育大":           1420,
    "佐賀大":               1425,
    "長崎大":               1435,
    "熊本大":               1440,
    "大分大":               1445,
    "宮崎大":               1455,
    "鹿児島大":             1465,
    "琉球大":               1475,
    "前橋工科大":           1523,
    "千葉県立保健医療大":   1528,
    "横浜市立大":           1540,
    "名古屋市立大":         1585,
    "滋賀県立大":           1587,
    "京都市立芸術大":       1590,
    "兵庫県立大":           1627,
    "島根県立大":           1647,
    "県立広島大":           1656,
    "大阪公立大":           1615,
    "福井県立大":           1555,
    "高知県立大":           1670,
    "高知工科大":           1671,
    "熊本県立大":           1700,
    "沖縄県立芸術大":       1705,
    "山陽小野田市立山口東京理工大": 1661,
    "信州大":               1225,
}

# ─── 明示マッピング ──────────────────────────────────────────
# KN: (gakubu, gakka, nittei_short) → DB: (f, d, method)  の明示対応表
METHOD_MAP = {"前期": "前期日程", "後期": "後期日程", "中期": "中期日程"}

EXPLICIT_MAP: dict[str, dict[tuple, tuple]] = {
    # 九州工業大: 類 ↔ 学科名
    "九州工業大": {
        ("工", "建設社会",   "前期"): ("工学部", "工学１類",   "前期日程"),
        ("工", "機械",       "前期"): ("工学部", "工学２類",   "前期日程"),
        ("工", "電気",       "前期"): ("工学部", "工学３類",   "前期日程"),
        ("工", "物質理工学", "前期"): ("工学部", "工学４類",   "前期日程"),
        ("工", "総合",       "前期"): ("工学部", "工学５類",   "前期日程"),
        ("工", "建設社会",   "後期"): ("工学部", "工学１類",   "後期日程"),
        ("工", "機械",       "後期"): ("工学部", "工学２類",   "後期日程"),
        ("工", "電気",       "後期"): ("工学部", "工学３類",   "後期日程"),
        ("工", "物質理工学", "後期"): ("工学部", "工学４類",   "後期日程"),
        ("工", "総合",       "後期"): ("工学部", "工学５類",   "後期日程"),
        ("情報工", "知能情報",     "前期"): ("情報工学部", "情工１類", "前期日程"),
        ("情報工", "電子情報通信", "前期"): ("情報工学部", "情工２類", "前期日程"),
        ("情報工", "生命情報",     "前期"): ("情報工学部", "情工３類", "前期日程"),
        ("情報工", "知能情報",     "後期"): ("情報工学部", "情工１類", "後期日程"),
        ("情報工", "電子情報通信", "後期"): ("情報工学部", "情工２類", "後期日程"),
        ("情報工", "生命情報",     "後期"): ("情報工学部", "情工３類", "後期日程"),
    },
    # 東北大: 経済/文系 → 経済学部
    "東北大": {
        ("経済", "文系", "前期"): ("", "経済学部", "前期日程"),
        ("経済", "文系", "後期"): ("", "経済学部", "後期日程"),
    },
    # 筑波大: 芸術/体育 の placeholder d ("（学類組織なし）") 対応
    "筑波大": {
        ("芸術", "芸術", "前期"): ("芸術専門学群", "（学類組織なし）", "前期日程"),
        ("芸術", "芸術", "後期"): ("芸術専門学群", "（学類組織なし）", "後期日程"),
        ("体育", "体育", "前期"): ("体育専門学群", "（学類組織なし）", "前期日程"),
    },
    # 金沢大: 理工→機械フロンティア工 など名称違い
    # (金沢大は 1件, 既存の改善で解決済みの可能性あり。明示なし)
}

# ─── 集約マッピング ──────────────────────────────────────────
# 複数の KN エントリを1つの DB エントリに集約
# {univ_name: {(f, d, method): [(gakubu, gakka, nittei), ...]} }
AGGREGATE_MAP: dict[str, dict[tuple, list]] = {
    "前橋工科大": {
        ("工学部", "建築・都市・環境工学群", "前期日程"): [
            ("工", "建築－土木・環境",   "前期"),
            ("工", "建築－建築都市",     "前期"),
            ("工", "建築－工学デザイン", "前期"),
        ],
        ("工学部", "情報・生命工学群", "前期日程"): [
            ("工", "情報－情報システム", "前期"),
            ("工", "情報－医工学",       "前期"),
            ("工", "情報－生物応用",     "前期"),
        ],
        ("工学部", "建築・都市・環境工学群", "中期日程"): [
            ("工", "建築－土木・環境",   "中期"),
            ("工", "建築－建築都市",     "中期"),
            ("工", "建築－工学デザイン", "中期"),
        ],
        ("工学部", "情報・生命工学群", "中期日程"): [
            ("工", "情報－情報システム", "中期"),
            ("工", "情報－医工学",       "中期"),
            ("工", "情報－生物応用",     "中期"),
        ],
    },
}

# ─── 命名規則正規化 ──────────────────────────────────────────
_STRIP_SUFFIXES = re.compile(
    r"学部|学科|学類|学域|学群|課程|専攻|コース|学院|研究科|選抜群|特別|入試"
)
_STRIP_SEP = re.compile(r"[・｜\-－\s　（）()【】〈〉]")
_PAREN = re.compile(r"[（(][^）)]*[）)]")
# 〈昼〉→昼, 〈夜〉→夜 等の正規化
_KAKU_HIRU  = re.compile(r"〈昼間主〉|〈昼〉|（昼間主）|（昼間）")
_KAKU_YORU  = re.compile(r"〈夜間主〉|〈夜〉|（夜間主）|（夜間）")
# 教育系 qualifier の前置詞除去
_EDU_PREFIX = re.compile(r"^(学校|中等|初等|中学|小中|理数|小学|共同|芸術)[－\-]")
# 医学科の地域枠など括弧修飾を除去して共通 key を作る
_CHIIKI_WAKU = re.compile(r"（地域枠）.*|【[^】]*】.*")


def normalize_base(s: str) -> str:
    """共通正規化: 昼夜, 括弧sep, 学部学科除去"""
    s = _KAKU_HIRU.sub("昼", s)
    s = _KAKU_YORU.sub("夜", s)
    s = _STRIP_SUFFIXES.sub("", s)
    s = _STRIP_SEP.sub("", s)
    return s.strip()


def normalize(s: str) -> str:
    return normalize_base(s)


def strip_parens(s: str) -> str:
    return _PAREN.sub("", s).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


_SKIP_ROW = re.compile(r"日程計|大学計|前期計|後期計|中期計|合計")

# ─── HTML テーブル展開 ────────────────────────────────────────
def expand_table(table) -> list[list[str]]:
    rows_html = table.find_all("tr")
    n_rows = len(rows_html)
    grid: list[list] = [[] for _ in range(n_rows)]
    occupied: dict[tuple, bool] = {}
    for ri, row_html in enumerate(rows_html):
        ci = 0
        for cell in row_html.find_all(["th", "td"]):
            while (ri, ci) in occupied:
                ci += 1
            text = cell.get_text(strip=True)
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            for dr in range(rowspan):
                for dc in range(colspan):
                    while len(grid[ri + dr]) <= ci + dc:
                        grid[ri + dr].append(None)
                    if dr == 0 and dc == 0:
                        grid[ri + dr][ci + dc] = text
                    else:
                        occupied[(ri + dr, ci + dc)] = True
                        grid[ri + dr][ci + dc] = text
            ci += colspan
    return [[c or "" for c in row] for row in grid]


# ─── Kei-Net データ取得 ──────────────────────────────────────
def fetch_keinet(keinet_id: int) -> list[dict]:
    url = KEINET_BASE.format(keinet_id)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = []
    for tbl in soup.find_all("table", class_="kn-tbl"):
        h = tbl.find_previous(["h2", "h3"])
        gakubu = h.get_text(strip=True) if h else ""
        grid = expand_table(tbl)
        for row in grid[2:]:
            if len(row) < 6:
                continue
            if _SKIP_ROW.search(row[0]) or _SKIP_ROW.search(row[1]):
                continue
            if row[1] not in ("前期", "後期", "中期"):
                continue

            def to_num(s):
                s = s.replace(",", "").strip()
                try:
                    v = float(s)
                    return int(v) if v == int(v) else v
                except (ValueError, OverflowError):
                    return None

            rows.append({
                "gakubu":  gakubu,
                "gakka":   row[0] if row[0] else gakubu,
                "nittei":  row[1],
                "s26": to_num(row[2]),
                "j26": to_num(row[3]),
                "g26": to_num(row[4]),
                "k26": to_num(row[5]),
                "s25": to_num(row[6]) if len(row) > 6 else None,
                "k25": to_num(row[9]) if len(row) > 9 else None,
            })
    return rows


# ─── DB ラベル ────────────────────────────────────────────────
def dept_label(f: str, d: str) -> str:
    if f and d:
        return f"{f}・{d}"
    return d or f or ""


# ─── キーワードマッチング（教育系）─────────────────────────
EDU_SUBJECTS = [
    "国語", "社会", "数学", "理科", "音楽", "美術", "保健体育", "英語",
    "家庭", "技術", "小学校", "特別支援", "初等", "中等", "幼児",
    "図工", "図画工作", "家政", "書道", "養護", "声楽", "管弦", "鍵盤",
    "舞踊", "体育", "地域教育", "地域政策", "地域環境",
    "芸術体育", "音楽文化", "美術文化",
]


def extract_edu_keyword(gakka: str) -> str:
    """教育系 KN 学科名からキーワードを抽出"""
    s = _EDU_PREFIX.sub("", gakka)
    s = strip_parens(s)
    for kw in EDU_SUBJECTS:
        if kw in s:
            return kw
    return s.strip()


def is_placeholder_d(d: str) -> bool:
    """d が「（学類組織なし）」等のプレースホルダーか"""
    return bool(re.match(r"^[（(（].*[）)）]$", d.strip()))


# ─── 改良マッチング ──────────────────────────────────────────
MATCH_THRESHOLD      = 0.72   # 通常閾値
MATCH_THRESHOLD_SOFT = 0.65   # 教育・ EP パターン等に緩和


def build_kn_keys(gakubu: str, gakka: str) -> list[str]:
    seen, keys = set(), []
    def add(s):
        n = normalize(s)
        if n and n not in seen:
            seen.add(n); keys.append(n)

    # 地域枠括弧を除いた版
    gakka_clean = _CHIIKI_WAKU.sub("", gakka).strip()

    if gakka and gakka != gakubu:
        add(gakubu + gakka)
        add(gakka)
        if gakka_clean and gakka_clean != gakka:
            add(gakubu + gakka_clean)
            add(gakka_clean)
        g2 = strip_parens(gakka)
        if g2 and g2 != gakka:
            add(gakubu + g2)
            add(g2)
    else:
        add(gakubu + gakubu)
        add(gakubu)

    return keys or [normalize(gakubu)]


def build_db_keys(f: str, d: str) -> list[str]:
    seen, keys = set(), []
    def add(s):
        n = normalize(s)
        if n and n not in seen:
            seen.add(n); keys.append(n)

    # placeholder d の場合は f のみ使用
    if is_placeholder_d(d):
        add(f)
        return keys or [normalize(f)]

    add((f or "") + (d or ""))
    if d:
        add(d)
    return keys or [""]


def find_best_match(
    kn: dict,
    db_recs: list[dict],
    threshold: float = MATCH_THRESHOLD,
) -> tuple:
    """(rec|None, score, note) を返す"""
    kn_keys  = build_kn_keys(kn["gakubu"], kn["gakka"])
    kn_method = METHOD_MAP.get(kn["nittei"], "")

    best_rec, best_score, best_note = None, 0.0, ""

    for rec in db_recs:
        if rec["m"] != kn_method:
            continue
        db_keys = build_db_keys(rec["f"], rec["d"])
        score = max(
            similarity(kk, dk)
            for kk in kn_keys
            for dk in db_keys
        )
        if score > best_score:
            best_score = score
            best_rec   = rec
            best_note  = f"kn={kn_keys[0]!r} ↔ db={db_keys[0]!r}"

    return (best_rec if best_score >= threshold else None), best_score, best_note


def find_edu_match(
    kn: dict,
    db_recs: list[dict],
) -> tuple:
    """教育系キーワードベースのマッチング。ユニーク1件のみ返す。"""
    keyword  = extract_edu_keyword(kn["gakka"])
    if not keyword:
        return None, 0.0, "keyword empty"
    kn_method = METHOD_MAP.get(kn["nittei"], "")

    # DB から method & keyword 含むレコードを絞り込み
    candidates = [
        r for r in db_recs
        if r["m"] == kn_method and keyword in (r.get("d") or "")
        and "2026" not in r.get("bairitsu", {})
    ]
    if len(candidates) == 1:
        return candidates[0], 0.80, f"edu_keyword={keyword!r}"
    if len(candidates) == 0:
        return None, 0.0, f"edu_keyword={keyword!r} no match"
    # 複数候補 → さらに学部名で絞り込み
    kn_gb_norm = normalize(kn["gakubu"])
    refined = [
        r for r in candidates
        if kn_gb_norm in normalize((r.get("f") or "") + (r.get("d") or ""))
    ]
    if len(refined) == 1:
        return refined[0], 0.80, f"edu_keyword={keyword!r}+gakubu"
    # それでも複数なら最も良いスコアを採用
    if refined:
        # fuzzy の中で最高
        best = max(refined, key=lambda r: similarity(
            keyword, normalize(r.get("d") or "")
        ))
        return best, 0.75, f"edu_keyword={keyword!r} best_of_{len(refined)}"
    return None, 0.0, f"edu_keyword={keyword!r} ambiguous({len(candidates)})"


# ─── 2026 エントリ作成 ─────────────────────────────────────
def make_entry_2026(kn: dict) -> dict:
    kuprv = None
    if kn.get("k26") is not None and kn.get("k25") and kn["k25"] != 0:
        kuprv = round(kn["k26"] / kn["k25"] * 100, 1)
    return {
        "boshu":  None,
        "shigan": kn["s26"],
        "juken":  kn["j26"],
        "gokaku": kn["g26"],
        "ku":     kn["k26"],
        "kuprv":  kuprv,
    }


# ─── 公式 HP 取得ロジック ─────────────────────────────────────
# 各大学の公式 HP 入試結果ページを解析して (f, d, m, entry) を返す関数

def fetch_kitami_official() -> list[dict]:
    """北見工業大 公式HP: 先進工学部 前後期"""
    url = "https://www.kitami-it.ac.jp/admission/past-data/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.content, "html.parser")
        results = []
        # テーブルを探す
        for tbl in soup.find_all("table"):
            text = tbl.get_text()
            if "先進工" in text or "志願" in text:
                grid = expand_table(tbl)
                for row in grid:
                    if len(row) < 4:
                        continue
                    nittei_raw = ""
                    if "前期" in row[0]:
                        nittei_raw = "前期日程"
                    elif "後期" in row[0]:
                        nittei_raw = "後期日程"
                    if not nittei_raw:
                        continue
                    nums = []
                    for cell in row[1:5]:
                        try:
                            nums.append(int(cell.replace(",", "").strip()))
                        except ValueError:
                            nums.append(None)
                    if len(nums) >= 3 and nums[0]:
                        results.append({
                            "f": "工学部", "d": "先進工学部",
                            "m": nittei_raw,
                            "s26": nums[0], "j26": nums[1] if len(nums) > 1 else None,
                            "g26": nums[2] if len(nums) > 2 else None,
                            "k26": nums[3] if len(nums) > 3 else None,
                            "k25": None,
                        })
        return results
    except Exception as e:
        print(f"  北見工業大 HP取得エラー: {e}")
        return []


def fetch_kyutech_official() -> list[dict]:
    """九州工業大 公式HP 入試結果"""
    # 九工大の入試結果ページ
    url = "https://www.kyutech.ac.jp/academics/examinee/results/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.content, "html.parser")
        # リンクから2026年度ページを探す
        for a in soup.find_all("a", href=True):
            if "2026" in a.get_text() or "2026" in a["href"]:
                href = a["href"]
                if not href.startswith("http"):
                    href = "https://www.kyutech.ac.jp" + href
                resp2 = requests.get(href, headers=HEADERS, timeout=20)
                soup2 = BeautifulSoup(resp2.content, "html.parser")
                # テーブル解析
                results = parse_kyutech_table(soup2)
                if results:
                    return results
    except Exception as e:
        print(f"  九州工業大 HP取得エラー: {e}")
    return []


def parse_kyutech_table(soup) -> list[dict]:
    """九州工業大のテーブルを解析"""
    results = []
    dept_map = {
        "建設社会": ("工学部", "工学１類"),
        "機械知能": ("工学部", "工学２類"),
        "電気電子": ("工学部", "工学３類"),
        "物質工":   ("工学部", "工学４類"),
        "総合システム": ("工学部", "工学５類"),
        "知能情報": ("情報工学部", "情工１類"),
        "電子情報通信": ("情報工学部", "情工２類"),
        "生命情報": ("情報工学部", "情工３類"),
    }
    for tbl in soup.find_all("table"):
        grid = expand_table(tbl)
        for row in grid:
            if len(row) < 4:
                continue
            dept_name = row[0].strip()
            nittei = ""
            if "前期" in row[0] or (len(row) > 1 and "前期" in row[1]):
                nittei = "前期日程"
            elif "後期" in row[0] or (len(row) > 1 and "後期" in row[1]):
                nittei = "後期日程"
            for key, (f, d) in dept_map.items():
                if key in dept_name and nittei:
                    nums = []
                    for cell in row:
                        try:
                            v = int(cell.replace(",", "").strip())
                            nums.append(v)
                        except ValueError:
                            pass
                    if len(nums) >= 3:
                        results.append({
                            "f": f, "d": d, "m": nittei,
                            "s26": nums[0], "j26": nums[1],
                            "g26": nums[2],
                            "k26": round(nums[1] / nums[2], 1) if nums[2] else None,
                            "k25": None,
                        })
    return results


# ─── 新規レコード作成（改組大学用）──────────────────────────
def make_new_record(univ: str, f: str, d: str, m: str, entry_2026: dict) -> dict:
    """DB にない新学科用の最小レコードを作成"""
    return {
        "u": univ,
        "f": f,
        "d": d,
        "m": m,
        "kind": "一般",
        "bairitsu": {"2026": entry_2026},
        "border": {},
        "hensa": {},
        "kyo_man": None,
        "ko_man": None,
        "ratio": None,
        "kyo_subj": None,
        "ko_subj": None,
    }


# ─── メイン ─────────────────────────────────────────────────
def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        db = json.load(f)

    records = db["records"]

    # 大学名 → レコードリスト
    univ_records: dict[str, list[dict]] = {}
    for rec in records:
        univ_records.setdefault(rec["u"], []).append(rec)

    added_total   = 0
    skipped_total = 0
    new_recs_total = 0
    report_lines: list[str] = []

    def rpt(s=""):
        report_lines.append(s)
        print(s)

    rpt("# 2026年度 パッチレポート (patch_unmatched_2026.py)")
    rpt(f"\n対象大学: {len(TARGET_UNIVS)} 大学\n")
    rpt("---")

    for univ, kid in TARGET_UNIVS.items():
        rpt(f"\n### {univ}  (Kei-Net ID: {kid})")
        db_recs = univ_records.get(univ, [])
        if not db_recs:
            rpt("  → DBレコードなし (スキップ)")
            continue

        # ─── 公式 HP 取得が必要な大学の特別処理 ─────────
        # (通常フローとは別に処理)
        # 後段の集約・明示マップで対応する大学はここでは飛ばさない

        # ─── Kei-Net 取得 ──────────────────────────────
        try:
            kn_rows = fetch_keinet(kid)
        except Exception as e:
            rpt(f"  ❌ Kei-Net取得エラー: {e}")
            time.sleep(1)
            continue

        time.sleep(0.8)

        added_here  = 0
        matched_keys: set[str] = set()

        # ─── 集約マッピング処理 ──────────────────────
        agg = AGGREGATE_MAP.get(univ, {})
        for (f_db, d_db, m_db), kn_list in agg.items():
            # 対象 DB レコードを探す
            db_rec = next(
                (r for r in db_recs if r["f"] == f_db and r["d"] == d_db and r["m"] == m_db),
                None,
            )
            if db_rec is None:
                rpt(f"  ⚠ 集約先DBレコードなし: {f_db}・{d_db}/{m_db}")
                continue
            if "2026" in db_rec["bairitsu"]:
                rpt(f"  ✓ 集約先既存: {f_db}・{d_db}/{m_db}")
                continue

            # 対象 KN エントリを集める
            total_s, total_j, total_g = 0, 0, 0
            found_all = True
            for (gb, gk, nt) in kn_list:
                kn_entry = next(
                    (r for r in kn_rows if r["gakubu"] == gb and r["gakka"] == gk and r["nittei"] == nt),
                    None,
                )
                if kn_entry is None or kn_entry["s26"] is None:
                    found_all = False
                    break
                total_s += kn_entry["s26"] or 0
                total_j += kn_entry["j26"] or 0
                total_g += kn_entry["g26"] or 0

            if not found_all:
                rpt(f"  ⚠ 集約元KNデータ不足: {d_db}")
                continue

            ku_agg = round(total_j / total_g, 1) if total_g else None
            db_rec["bairitsu"]["2026"] = {
                "boshu": None,
                "shigan": total_s,
                "juken": total_j,
                "gokaku": total_g,
                "ku": ku_agg,
                "kuprv": None,
            }
            key = f"{univ}|{dept_label(f_db, d_db)}|{m_db}"
            matched_keys.add(key)
            added_here += 1
            added_total += 1
            rpt(
                f"  ✅ 集約追加 {d_db}/{m_db} "
                f"志願={total_s} 受験={total_j} 合格={total_g} 競争率={ku_agg}"
            )

        # ─── 明示マッピング処理 ───────────────────────
        explicit = EXPLICIT_MAP.get(univ, {})
        for (gb, gk, nt), (f_db, d_db, m_db) in explicit.items():
            kn_entry = next(
                (r for r in kn_rows if r["gakubu"] == gb and r["gakka"] == gk and r["nittei"] == nt),
                None,
            )
            if kn_entry is None or kn_entry["s26"] is None:
                continue
            db_rec = next(
                (r for r in db_recs if r["f"] == f_db and r["d"] == d_db and r["m"] == m_db),
                None,
            )
            if db_rec is None:
                rpt(f"  ⚠ 明示マップ先DBなし: {f_db}・{d_db}/{m_db}")
                continue
            if "2026" in db_rec["bairitsu"]:
                continue
            db_rec["bairitsu"]["2026"] = make_entry_2026(kn_entry)
            key = f"{univ}|{dept_label(f_db, d_db)}|{m_db}"
            matched_keys.add(key)
            added_here += 1
            added_total += 1
            rpt(
                f"  ✅ 明示追加 [{gb}]{gk}/{nt} → {dept_label(f_db, d_db)} "
                f"志願={kn_entry['s26']} 合格={kn_entry['g26']} 競争率={kn_entry['k26']}"
            )

        # ─── 通常マッチング (改良版) ──────────────────
        for kn in kn_rows:
            if kn["s26"] is None and kn["g26"] is None:
                continue

            # 既に集約/明示マップで処理済みの KN エントリはスキップ
            # (厳密には kn_entry 側の識別が必要だが、ここでは DB key で判断)

            # 1. 通常ファジーマッチ (閾値 0.72)
            rec, score, note = find_best_match(kn, db_recs, MATCH_THRESHOLD)

            # 2. 閾値緩和 (0.65) で再試行
            if rec is None:
                rec, score, note = find_best_match(kn, db_recs, MATCH_THRESHOLD_SOFT)

            # 3. 教育系キーワードマッチ
            if rec is None:
                rec, score, note = find_edu_match(kn, db_recs)

            if rec is None:
                skipped_total += 1
                continue

            rec_key = f"{rec['u']}|{dept_label(rec['f'], rec['d'])}|{rec['m']}"
            if rec_key in matched_keys:
                continue  # 既にマッチ済み
            if "2026" in rec["bairitsu"]:
                matched_keys.add(rec_key)
                continue  # Phase1 で追加済み

            rec["bairitsu"]["2026"] = make_entry_2026(kn)
            matched_keys.add(rec_key)
            added_here += 1
            added_total += 1
            rpt(
                f"  ✅ 追加 [{kn['gakubu']}]{kn['gakka']}/{kn['nittei']} "
                f"→ {dept_label(rec['f'], rec['d'])} "
                f"志願={kn['s26']} 合格={kn['g26']} 競争率={kn['k26']} "
                f"(score={score:.2f}, {note})"
            )

        # ─── 未解決 DB レコード確認 ──────────────────
        still_missing = [
            r for r in db_recs
            if "2026" not in r.get("bairitsu", {})
            and f"{r['u']}|{dept_label(r['f'],r['d'])}|{r['m']}" not in matched_keys
        ]
        for r in still_missing[:5]:
            rpt(f"  ℹ まだ未取得: {dept_label(r['f'], r['d'])}/{r['m']}")
        if len(still_missing) > 5:
            rpt(f"  ℹ ... 他{len(still_missing)-5}件")

        rpt(f"  → 追加={added_here}")

    # ─── 公式 HP 取得大学の特別処理 ─────────────────────
    rpt("\n---")
    rpt("## 公式 HP 取得大学")

    # 北見工業大: 先進工学部 (2026年 新学部)
    rpt("\n### 北見工業大 (公式HP)")
    kitami_recs = univ_records.get("北見工業大", [])
    # 先進工学部は DB に存在しないので新規レコードとして追加
    try:
        resp = requests.get(
            "https://www.kitami-it.ac.jp/admission/r7/nyushi_kekka/",
            headers=HEADERS, timeout=20,
        )
        soup = BeautifulSoup(resp.content, "html.parser")
        tables = soup.find_all("table")
        kitami_data = {}  # {nittei: {shigan, juken, gokaku, ku}}
        for tbl in tables:
            grid = expand_table(tbl)
            for row in grid:
                if len(row) < 4:
                    continue
                for ni in ["前期", "後期"]:
                    if ni in row[0]:
                        nums = []
                        for c in row:
                            try:
                                v = int(c.replace(",", "").strip())
                                nums.append(v)
                            except ValueError:
                                pass
                        if len(nums) >= 3:
                            kitami_data[ni + "日程"] = {
                                "boshu": None,
                                "shigan": nums[0],
                                "juken": nums[1] if len(nums) > 1 else None,
                                "gokaku": nums[2] if len(nums) > 2 else None,
                                "ku": round(nums[1]/nums[2], 1) if len(nums)>2 and nums[2] else None,
                                "kuprv": None,
                            }
        if kitami_data:
            for m, entry in kitami_data.items():
                # DB の既存レコード（旧名称）は更新しない。新レコードを追加。
                new_rec = make_new_record("北見工業大", "先進工学部", "（学科組織統合）", m, entry)
                records.append(new_rec)
                new_recs_total += 1
                added_total += 1
                rpt(f"  ✅ 新規追加 先進工学部/{m} 志願={entry['shigan']} 合格={entry['gokaku']}")
        else:
            rpt("  ⚠ 北見工業大 HP からデータを抽出できませんでした")
    except Exception as e:
        rpt(f"  ❌ 北見工業大 HP エラー: {e}")
    time.sleep(0.8)

    # 九州工業大 (明示マップで対応済み、残り「知的システム」の HP 確認)
    rpt("\n### 九州工業大 残余確認")
    # 明示マップに含まれていない 知的システム を確認
    kyutech_recs = univ_records.get("九州工業大", [])
    for rec in kyutech_recs:
        if "2026" not in rec.get("bairitsu", {}):
            rpt(f"  ℹ まだ未取得: {dept_label(rec['f'], rec['d'])}/{rec['m']}")

    # 信州大 工学部: 新学科 → 新規レコード追加
    rpt("\n### 信州大 工学部 (新設学科)")
    shinshu_kn_id = 1225
    shinshu_recs = univ_records.get("信州大", [])
    # 既存 2026 のない工学部新学科を Kei-Net データから補完
    try:
        kn_rows_shu = fetch_keinet(shinshu_kn_id)
        time.sleep(0.8)
        new_depts = {
            "応用化学": "応用化学科",
            "環境・エネルギー材料": "環境・エネルギー材料科学科",
            "電気電子": "電気電子工学科",
            "機械物理": "機械物理工学科",
            "知能機械": "知能機械システム工学科",
            "情報サイエンス": "情報サイエンス学科",
            "情報デザイン": "情報デザイン工学科",
            "地域協創特別": None,  # 特別選抜 → スキップ
        }
        for kn in kn_rows_shu:
            if kn["gakubu"] != "工" and kn["gakubu"] != "工学部":
                continue
            gakka = kn["gakka"]
            if gakka not in new_depts:
                continue
            d_new = new_depts.get(gakka)
            if d_new is None:
                continue
            # 既存 DB に同名レコードがあれば追加しない
            existing = next(
                (r for r in shinshu_recs if r["d"] == d_new and r["m"] == METHOD_MAP.get(kn["nittei"], "")),
                None,
            )
            if existing:
                if "2026" not in existing["bairitsu"]:
                    existing["bairitsu"]["2026"] = make_entry_2026(kn)
                    added_total += 1
                    rpt(f"  ✅ 更新 信州大工/{d_new}/{kn['nittei']} 志願={kn['s26']}")
                continue
            # 新規レコード
            new_rec = make_new_record(
                "信州大", "工学部", d_new,
                METHOD_MAP.get(kn["nittei"], ""),
                make_entry_2026(kn),
            )
            records.append(new_rec)
            new_recs_total += 1
            added_total += 1
            rpt(f"  ✅ 新規 信州大工/{d_new}/{kn['nittei']} 志願={kn['s26']} 合格={kn['g26']}")
    except Exception as e:
        rpt(f"  ❌ 信州大工 Kei-Net エラー: {e}")

    # ─── サマリー ───────────────────────────────────────
    rpt("\n---")
    rpt("## サマリー")
    rpt(f"- Phase2 追加: {added_total} 件")
    rpt(f"  うち新規レコード: {new_recs_total} 件")
    rpt(f"- マッチング失敗: {skipped_total} 件")

    # 合計2026件数確認
    count_2026 = sum(1 for r in records if "2026" in r.get("bairitsu", {}))
    rpt(f"- DB 2026データ保有レコード合計: {count_2026} 件 / {len(records)} 件")

    # ─── JSON 保存 ───────────────────────────────────────
    db["records"] = records
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
    rpt(f"\ndata.json 更新: {DATA_JSON}")

    # ─── レポート保存 ────────────────────────────────────
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nレポート: {REPORT_FILE}")


if __name__ == "__main__":
    main()
