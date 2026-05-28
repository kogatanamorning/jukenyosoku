# 受験校 倍率予測システム

国公立大学の入試倍率・共通テストボーダー・科目別平均を検索し、AI予測用の Markdown を生成する静的 Web アプリ。

## 機能

- **倍率検索**: 大学・学部学科・方式で過去3年(2023-2025)の倍率を検索
- **共テ検索**: 共通テストボーダー得点率・偏差値・必要科目を検索
- **ばんざい入力**: 河合塾ばんざいシステムの数値を入力（ブラウザに自動保存）
- **AI出力**: 受験校＋関連校(5校)を選び、AIに渡す Markdown を生成

## データ出典

- 倍率・共テボーダー・必要科目: 旺文社パスナビ
- 共テ科目別平均: 大学入試センター

---

## GitHub Pages での公開手順

### 1. GitHub リポジトリを作成

1. https://github.com/new を開く
2. Repository name: `jukenyosoku`（任意）
3. **Public** を選択
4. 「Create repository」

### 2. ファイルをアップロード

**方法A: ブラウザでアップロード（簡単）**
1. 作成したリポジトリページで「uploading an existing file」をクリック
2. このフォルダ (`jukenyosoku-web`) の中身を**すべて**ドラッグ&ドロップ
   - `index.html`, `css/`, `js/`, `data/`, `convert_to_json.py`, `README.md`
3. 「Commit changes」

**方法B: git コマンド**
```bash
cd jukenyosoku-web
git init
git add .
git commit -m "初版"
git branch -M main
git remote add origin https://github.com/<あなたのユーザー名>/jukenyosoku.git
git push -u origin main
```

### 3. GitHub Pages を有効化

1. リポジトリの **Settings** → 左メニュー **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / **/(root)** → Save
4. 1〜2分待つと `https://<ユーザー名>.github.io/jukenyosoku/` で公開される

### 4. アクセス

- PC・iPad・スマホのブラウザで上記 URL を開くだけ
- ばんざい入力データは各端末のブラウザに保存される（外部に出ない）

---

## データ更新方法（年1回）

新年度のデータを追加したら、以下で `data/data.json` を再生成：

```bash
python convert_to_json.py
```

その後 GitHub に push（または data.json を再アップロード）すれば、数分で反映される。

```bash
git add data/data.json
git commit -m "2026年度データ更新"
git push
```

---

## ファイル構成

```
jukenyosoku-web/
├── index.html          # メインページ
├── css/style.css       # スタイル
├── js/app.js           # アプリロジック
├── data/data.json      # 全データ (約2.8MB)
├── convert_to_json.py  # Excel→JSON 変換 (要 入試データベース.xlsx)
└── README.md
```
