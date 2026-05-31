# 引継ぎ資料 — 受験校倍率予測システム
作成日: 2026-05-31

---

## プロジェクト概要

**場所:** `C:\Users\kogat\Documents\Claude\jukenyosoku-web`  
**公開URL:** `https://kogatanamorning.github.io/jukenyosoku/`  
**GitHub:** `https://github.com/kogatanamorning/jukenyosoku`  
**ブランチ:** `main` （GitHub Pages で自動公開）

国公立大学の入試倍率・共通テストボーダー・AI予測用 Markdown を生成する静的 Web アプリ。

---

## ファイル構成

```
jukenyosoku-web/
├── index.html              # メインページ（ヘッダー右上に更新日時表示あり）
├── css/style.css           # スタイル（.update-date クラス追加済み）
├── js/app.js               # アプリロジック（2026年度対応済み）
├── data/
│   ├── data.json           # 全データ (約2.1MB, 3,206レコード, 148大学)
│   └── data.json.bak       # バックアップ（gitignore対象外）
├── scrape_2026_keinet.py       # Phase1スクレイパー（Kei-Net 154大学）
├── patch_unmatched_2026.py     # Phase2パッチ（改良マッチング）
├── patch_hokkaido_edu.py       # 北海道教育大残余パッチ
├── scrape_boshu_2026.py        # boshu取得スクリプト（未完成・要改善）
├── scrape_report_2026.md       # Phase1レポート
├── patch_report_2026.md        # Phase2レポート
└── boshu_report_2026.md        # boshu取得レポート（実行時生成）
```

---

## data.json の構造

```json
{
  "meta": {"records": 3206, "universities": 148, "updated": "2026-05-31"},
  "universities": ["北海道大", "東北大", ...],   // 148大学
  "departments": {"大学名": ["学部・学科", ...]}, // 倍率検索用
  "departments_kyo": {"大学名": [...]},           // 共テ検索用
  "records": [...],                               // 3,206件
  "kyotest_avg": {"2026": {...}, "2025": {...}, ...}
}
```

### record 1件の構造
```json
{
  "u": "北海道大",
  "f": "文学部",
  "d": "人文科学科",
  "m": "前期日程",
  "kind": "一般",
  "bairitsu": {
    "2023": {"boshu":122,"shigan":371,"juken":363,"gokaku":122,"ku":3.0,"kuprv":2.9},
    "2024": {"boshu":122,...},
    "2025": {"boshu":122,...},
    "2026": {"boshu":null,"shigan":312,"juken":308,"gokaku":122,"ku":2.5,"kuprv":3.0}
    //       ^2026はboshuのみNull、他はKei-Netから正確取得済み
    //       kuprv = 前年(2025)の競争率そのまま
  },
  "border": 70,    // 共テボーダー得点率(%)
  "hensa": 62.5,   // 偏差値
  "kyo_man": 900,  // 共テ満点
  "ko_man": 440,   // 二次試験満点
  "ratio": 44,     // 個別比率(%)
  "kyo_subj": "国・数IA・数IIBC・英・理2・地歴公",
  "ko_subj": "数学・理科・英語"
}
```

---

## 2026年度データの現状

### 取得済み
| 項目 | 件数 | 出典 |
|------|------|------|
| shigan (志願者数) | 2,599件 | Kei-Net |
| juken (受験者数) | 2,599件 | Kei-Net |
| gokaku (合格者数) | 2,599件 | Kei-Net |
| ku (競争率) | 2,599件 | Kei-Net (juken/gokaku) |
| kuprv (前年競争率) | 2,599件 | DB 2025年のkuをコピー |

### 未取得
| 項目 | 件数 | 理由 |
|------|------|------|
| boshu (募集人数) | **2,599件全てNull** | Kei-Net非掲載、パスナビ2026未更新 |

### データなし（2026）
- 残り607件：学部再編・廃止・DB品質問題など

### 2026データのカバレッジ
- **2,599件 / 3,206件 = 81.1%**

---

## 未解決の課題（優先度順）

### 🔴 最優先: 2026年度 boshu（募集人数）取得

**背景:**
- `boshu = null` のため倍率画面で「-」表示
- 競争率(ku)はjuken/gokakuで計算するためboshuに依存しないが、志願倍率の計算や情報としての完全性に影響

**調査済みの結論:**
- **Kei-Net**: 募集人員列なし（志願・受験・合格・倍率のみ）
- **パスナビ**: 2025年度データのみ（2026年度は未更新、通常8〜10月更新）
- **大学公式HP**: URLが大学ごとに異なり、多くが404またはJSレンダリング不可

**推奨対応:**
```python
# パスナビが2026年度に更新したら以下で全大学取得可能
# パスナビURL: https://passnavi.obunsha.co.jp/univ/{ID}/bairitsu/
# IDマッピング例:
PASSNAVI_IDS = {
    "北海道大": "0010",
    "東北大": "0020",
    "東京大": "0030",
    "名古屋大": "0040",
    "京都大": "0050",
    "大阪大": "0060",
    "九州大": "0070",
    # ... 全大学のIDが必要
}
```

パスナビページのテーブル形式（解析済み）:
```
学部・学科 | 入試名 | 倍率(今年) | 倍率(前年) | 募集人員 | 志願者数 | 受験者数 | 合格者数
```

### 🟡 DBデータ品質問題（スポーンタスクあり）

以下2大学のDB記録が別大学のデータ混入済み（別セッションのスポーンタスクで修正推奨）:

| DB上の大学名 | 実際のデータ | 件数 |
|---|---|---|
| 一橋大 | 東京科学大（旧東工大+医科歯科大） | 15件 |
| 浜松医科大 | 岐阜大 | 45件 |

⚠️ 上記は既に修正済み（`u`フィールドを正しい大学名に変更）。
ただし元の Excel（`入試データベース.xlsx`）も修正が必要（gitignore対象）。

**一橋大の本来のデータ（社会・法・経済・商・SDS）がDBに存在しない問題も未解決。**

### 🟢 完了済みの作業

1. ✅ 2026年度倍率データを Kei-Net から取得（2,599件）
2. ✅ 前年比倍率(kuprv)の定義修正（パーセント→前年の競争率実値）
3. ✅ DBデータ品質修正（浜松医科大→岐阜大、一橋大→東京科学大）
4. ✅ 岐阜大・東京科学大の2026データ追加
5. ✅ 信州大 工学部 新設7学科を新規レコード追加
6. ✅ app.js に2026年度を追加（["2026","2025","2024","2023"]）
7. ✅ 更新日時をヘッダー右上に表示（data.json の meta.updated から）
8. ✅ GitHubへプッシュ・Pages公開確認済み

---

## スクレイピングスクリプトの使い方

### Phase1: 全大学 Kei-Net スクレイピング（再実行用）
```bash
cd "C:\Users\kogat\Documents\Claude\jukenyosoku-web"
python scrape_2026_keinet.py
```
- 154大学をKei-Netから取得
- 結果: `scrape_report_2026.md`

### Phase2: 未マッチ補完
```bash
python patch_unmatched_2026.py
```
- 67大学の命名規則違いを改良マッチングで補完
- 結果: `patch_report_2026.md`

### boshu取得（パスナビ更新後に実行）
```bash
python scrape_boshu_2026.py
```
- 現在は多くの大学でURL不一致のため取得できない
- パスナビが2026年度に更新されたら、パスナビからの取得に切り替えが必要

---

## app.js の主要な変更点

```javascript
// 倍率検索（renderBairitsu）
["2026","2025","2024","2023"].forEach(y => { ... })  // 2026追加済み

// AI出力（generateMarkdown）
["2026","2025","2024","2023"].forEach(y => { ... })  // 2026追加済み

// 更新日時表示
const updated = DB.meta && DB.meta.updated;
if (updated) {
    document.getElementById("updateDate").textContent = `データ更新: ${updated}`;
}
```

---

## パスナビからのboshu取得スクリプト（将来用テンプレート）

パスナビが2026年度に更新されたら、以下のスクリプトを参考に作成:

```python
import requests, json, re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

HEADERS = {"User-Agent": "Mozilla/5.0 ..."}

# パスナビIDマッピング（全大学分が必要）
PASSNAVI_IDS = {
    "北海道大": "0010",
    "東北大":   "0020",
    # ... 要完成
}

def scrape_passnavi_boshu(univ_name, pn_id):
    url = f"https://passnavi.obunsha.co.jp/univ/{pn_id}/bairitsu/"
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    # テーブル形式:
    # 学部・学科 | 入試名 | 倍率(今年) | 倍率(前年) | 募集人員 | 志願者数 | 受験者数 | 合格者数
    for tbl in soup.find_all('table'):
        rows = tbl.find_all('tr')
        for row in rows[1:]:
            cols = [c.get_text(strip=True) for c in row.find_all(['th','td'])]
            if len(cols) >= 7:
                dept = cols[0]
                nittei = cols[1]
                boshu = int(cols[4]) if cols[4].isdigit() else None
                # ... マッチングしてDBに格納
```

---

## Kei-Net の大学ID（主要なもの）

```python
UNIV_KEINET = {
    "旭川医科大": 1005, "小樽商科大": 1010, "帯広畜産大": 1015,
    "北見工業大": 1020, "北海道大":   1025, "北海道教育大": 1030,
    "弘前大": 1040, "岩手大": 1045, "東北大": 1050,
    "宮城教育大": 1055, "秋田大": 1060, "山形大": 1065,
    "福島大": 1070, "茨城大": 1075, "筑波大": 1085,
    "宇都宮大": 1090, "群馬大": 1095, "埼玉大": 1100,
    "千葉大": 1105, "お茶の水女子大": 1110, "電気通信大": 1115,
    "東京大": 1120, "東京外国語大": 1130, "東京学芸大": 1135,
    "東京藝術大": 1140, "東京農工大": 1160, "横浜国立大": 1170,
    "新潟大": 1180, "金沢大": 1200, "福井大": 1205,
    "山梨大": 1215, "信州大": 1225, "浜松医科大": 1235,
    "愛知教育大": 1240, "名古屋大": 1250, "名古屋工業大": 1255,
    "三重大": 1265, "滋賀大": 1270, "京都大": 1280,
    "大阪大": 1295, "神戸大": 1310, "奈良女子大": 1330,
    "和歌山大": 1335, "岡山大": 1355, "広島大": 1360,
    "山口大": 1365, "徳島大": 1370, "香川大": 1380,
    "愛媛大": 1390, "高知大": 1395, "九州大": 1405,
    "九州工業大": 1415, "福岡教育大": 1420, "佐賀大": 1425,
    "長崎大": 1435, "熊本大": 1440, "大分大": 1445,
    "宮崎大": 1455, "鹿児島大": 1465, "琉球大": 1475,
    # 公立大
    "東京科学大": 1150,  # 旧東工大+東京医科歯科大
    "大阪公立大": 1615,
    "名古屋市立大": 1585,
    # ... 他多数 scrape_2026_keinet.py に全リストあり
}
```

---

## 次のセッションでやること

1. **boshu取得（最優先）**
   - パスナビ更新（8〜10月予定）まで待つ
   - OR 大学公式HPから手動スクレイピング
   - パスナビIDマッピングを完成させる（現在は主要7大学のみ）

2. **一橋大の本来データを追加**
   - 現在DBに一橋大（社会・法・経済・商・SDS）のレコードが存在しない
   - Kei-Net ID: 1165 に正しい一橋大データあり（社会/法/経済/商/SDS）
   - 新規レコードとして追加が必要

3. **元Excelの修正**
   - `入試データベース.xlsx` の浜松医科大・一橋大エントリを修正
   - `convert_to_json.py` を再実行して正しい data.json を生成

---

## 注意事項

- `data/data.json.bak` → gitignore対象外、コミットしないこと
- `*.xlsx` → .gitignore に含まれる、コミット不可
- パスナビのスクレイピングは robots.txt 的に問題ない範囲で
- Kei-Net へのリクエストは 0.8秒以上間隔を空けること（rate limit）
