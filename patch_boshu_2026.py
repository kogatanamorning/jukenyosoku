# -*- coding: utf-8 -*-
"""
2026年度 募集人員(boshu) パッチ

方針:
 1) 2025年度boshu -> 2026年度へ繰り越し（変更が無い学科はそのまま）
 2) 駿台「2026年度入試 国公立大 変更点一覧」(2025/12/08版) に記載の
    募集人員変更点で 2026年度boshu を上書き
 3) 後期日程廃止の学科は Kei-Net に 2026 後期データが無く 2026ブロックが
    存在しないため、繰り越し対象外（=自動的に反映済み）

上書きは (大学, 学部キーワード, 学科キーワード, 日程) で部分一致したレコードに適用。
マッチ結果はレポート出力する。
"""
import json, io, sys, datetime

PATH = "data/data.json"

# 上書き定義
# u  : 大学名（完全一致）
# fkw: 学部名 部分一致（''なら無視）
# dkw: 学科名 部分一致（''なら無視）
# dex: 学科名 完全一致（指定時はdkwより優先。空学科 '' を狙う用）
# m  : 日程（完全一致）
# val: 2026年度 boshu
OV = [
    # --- 旭川医科大: 医学科 前期48（後期廃止）---
    dict(u="旭川医科大", fkw="医", dex="", m="前期日程", val=48),
    # --- 北海道大 ---
    dict(u="北海道大", dkw="検査技術科学", m="前期日程", val=30),
    dict(u="北海道大", dkw="作業療法学", m="前期日程", val=14),
    # --- 北海道教育大 ---
    dict(u="北海道教育大", dkw="旭川校／教育発達", m="前期日程", val=32),
    dict(u="北海道教育大", dkw="旭川校／国語教育", m="後期日程", val=3),
    dict(u="北海道教育大", dkw="旭川校／社会科教育", m="後期日程", val=6),
    dict(u="北海道教育大", dkw="旭川校／理科教育", m="後期日程", val=7),
    dict(u="北海道教育大", dkw="旭川校／芸術・保健体育教育専攻－音楽", m="前期日程", val=7),
    dict(u="北海道教育大", dkw="旭川校／芸術・保健体育教育専攻－保健体育", m="前期日程", val=7),
    dict(u="北海道教育大", dkw="岩見沢校／芸術・スポーツ文化専攻－スポーツ文化", m="前期日程", val=28),
    dict(u="北海道教育大", dkw="岩見沢校／芸術・スポーツ文化専攻－スポーツ文化", m="後期日程", val=10),
    dict(u="北海道教育大", dkw="音楽文化分野－声楽", m="前期日程", val=2),
    dict(u="北海道教育大", dkw="音楽文化分野－鍵盤楽器・作曲", m="前期日程", val=7),
    dict(u="北海道教育大", dkw="釧路校／地域学校教育実践", m="前期日程", val=50),
    dict(u="北海道教育大", dkw="釧路校／地域学校教育実践", m="後期日程", val=60),
    dict(u="北海道教育大", dkw="札幌校／芸術体育教育専攻－図画工作・美術教育", m="前期日程", val=6),
    # --- 岩手大 ---
    dict(u="岩手大", dkw="電気電子・情報通信", m="前期日程", val=36),
    dict(u="岩手大", dkw="電気電子・情報通信", m="後期日程", val=11),
    dict(u="岩手大", dkw="機械知能航空", m="前期日程", val=48),
    dict(u="岩手大", dkw="機械知能航空", m="後期日程", val=15),
    dict(u="岩手大", dkw="共同獣医", m="前期日程", val=18),
    # --- 東北大 ---
    dict(u="東北大", dkw="放射線技術科学", m="前期日程", val=23),
    dict(u="東北大", dkw="検査技術科学", m="前期日程", val=23),
    dict(u="東北大", fkw="薬", dex="", m="前期日程", val=52),
    # --- 山形大: 医 前期 一般65+地域8=73（後期廃止）---
    dict(u="山形大", fkw="医", dex="", m="前期日程", val=73),
    # --- 茨城大 教育（後期廃止→前期のみ）---
    dict(u="茨城大", dkw="教科教育コース・英語", m="前期日程", val=5),
    dict(u="茨城大", dkw="教科教育コース・数学", m="前期日程", val=17),
    dict(u="茨城大", dkw="教科教育コース・理科", m="前期日程", val=15),
    dict(u="茨城大", dkw="教科教育コース・技術", m="前期日程", val=11),
    dict(u="茨城大", dkw="特別支援教育", m="前期日程", val=15),
    dict(u="茨城大", dkw="教育実践科学", m="前期日程", val=13),
    dict(u="茨城大", dkw="地域未来共創", m="前期日程", val=28),
    # --- 筑波大 ---
    dict(u="筑波大", dkw="教育学類", m="後期日程", val=2),
    dict(u="筑波大", dkw="心理学類", m="後期日程", val=3),
    dict(u="筑波大", dkw="障害学類", m="前期日程", val=2),
    dict(u="筑波大", dkw="化学類", m="前期日程", val=18),
    dict(u="筑波大", dkw="化学類", m="後期日程", val=5),
    # --- 横浜国立大 ---
    dict(u="横浜国立大", dkw="DSEP", m="前期日程", val=10),
    dict(u="横浜国立大", dkw="DSEP", m="後期日程", val=4),
    dict(u="横浜国立大", dkw="都市社会共生", m="後期日程", val=8),
    # --- 富山大 ---
    dict(u="富山大", fkw="医", dex="", m="前期日程", val=68),
    # --- 金沢大 ---
    dict(u="金沢大", dkw="地球社会基盤", m="前期日程", val=67),
    dict(u="金沢大", dkw="医学類", m="前期日程", val=79),
    # --- 山梨大 ---
    dict(u="山梨大", dkw="言語教育", m="前期日程", val=6),
    dict(u="山梨大", dkw="言語教育", m="後期日程", val=3),
    dict(u="山梨大", dkw="生活社会教育", m="前期日程", val=6),
    dict(u="山梨大", dkw="生活社会教育", m="後期日程", val=2),
    # --- 千葉大 ---
    dict(u="千葉大", dkw="音楽科教育", m="前期日程", val=9),
    dict(u="千葉大", dkw="図画工作・美術科教育", m="前期日程", val=10),
    # --- 名古屋大 ---
    dict(u="名古屋大", dkw="物理工", m="前期日程", val=73),
    dict(u="名古屋大", dkw="マテリアル工", m="前期日程", val=95),
    # --- 三重大 ---
    dict(u="三重大", dkw="電子情報工学", m="前期日程", val=18),
    dict(u="三重大", dkw="電子情報工学", m="後期日程", val=14),
    # --- 京都大 ---
    dict(u="京都大", fkw="理", dex="", m="前期日程", val=274),
    dict(u="京都大", dkw="理工化", m="前期日程", val=215),
    dict(u="京都大", fkw="工", dkw="情報", m="前期日程", val=94),
    dict(u="京都大", dkw="電気電子工", m="前期日程", val=128),
    dict(u="京都大", fkw="工", dkw="物理工", m="前期日程", val=225),
    dict(u="京都大", dkw="地球工", m="前期日程", val=145),
    dict(u="京都大", dkw="森林科学", m="前期日程", val=48),
    # --- 大阪大 ---
    dict(u="大阪大", dkw="情報科学", m="前期日程", val=88),
    dict(u="大阪大", dkw="化学応用科学", m="前期日程", val=71),
    dict(u="大阪大", dkw="システム科学", m="前期日程", val=148),
    dict(u="大阪大", dkw="電子物理科学", m="前期日程", val=90),
    dict(u="大阪大", fkw="歯", dex="", m="前期日程", val=45),
    # --- 神戸大 ---
    dict(u="神戸大", dkw="応用動物学", m="前期日程", val=19),
    dict(u="神戸大", dkw="応用動物学", m="後期日程", val=5),
    dict(u="神戸大", dkw="食料環境経済学", m="前期日程", val=6),
    # --- 鳥取大: 医 前期 一般53+とっとり7=60 ---
    dict(u="鳥取大", fkw="医", dex="", m="前期日程", val=60),
    # --- 岡山大 ---
    dict(u="岡山大", dkw="小学校教育", m="前期日程", val=71),
    dict(u="岡山大", dkw="特別支援教育", m="前期日程", val=8),
    dict(u="岡山大", dkw="幼児教育", m="前期日程", val=8),
    dict(u="岡山大", fkw="医", dex="", m="前期日程", val=95),
    dict(u="岡山大", fkw="農", dex="", m="前期日程", val=100),
    # --- 広島大 ---
    dict(u="広島大", fkw="法", dex="", m="前期日程", val=130),
    dict(u="広島大", dkw="工学特別", m="前期日程", val=30),
    dict(u="広島大", dkw="作業療法学", m="前期日程", val=20),
    dict(u="広島大", fkw="歯", dkw="歯", m="後期日程", val=13),
    dict(u="広島大", dkw="生物生産", m="前期日程", val=67),
    # --- 愛媛大 ---
    dict(u="愛媛大", fkw="医", dkw="看護", m="前期日程", val=30),
    # --- 九州大 ---
    dict(u="九州大", fkw="文", dkw="人文", m="前期日程", val=109),
    # --- 佐賀大: 医 前期51（後期廃止）---
    dict(u="佐賀大", fkw="医", dex="", m="前期日程", val=51),
    # --- 長崎大 ---
    dict(u="長崎大", fkw="医", dkw="医", m="前期日程", val=66),
    dict(u="長崎大", fkw="薬", dkw="薬学", m="前期日程", val=32),
    dict(u="長崎大", dkw="薬科学", m="前期日程", val=36),
    # --- 熊本大 ---
    dict(u="熊本大", fkw="法", dex="", m="前期日程", val=130),
    dict(u="熊本大", fkw="理", dex="", m="前期日程", val=125),
    dict(u="熊本大", fkw="理", dex="", m="後期日程", val=35),
    # --- 鹿児島大 ---
    dict(u="鹿児島大", fkw="医", dkw="医", m="後期日程", val=19),
    # --- 琉球大 ---
    dict(u="琉球大", fkw="医", dkw="医", m="後期日程", val=23),
    # --- 公立 ---
    dict(u="公立小松大", dkw="生産システム科学", m="前期日程", val=30),
    dict(u="横浜市立大", fkw="理", dkw="", m="前期日程", val=55),
    dict(u="京都府立医科大", fkw="医", dkw="医", m="前期日程", val=93),
    dict(u="大阪公立大", dkw="食栄養", m="前期日程", val=35),
]


def match(r, o):
    if r["u"] != o["u"]:
        return False
    if r["m"] != o["m"]:
        return False
    f = r.get("f", "") or ""
    d = r.get("d", "") or ""
    if o.get("fkw") and o["fkw"] not in f:
        return False
    if "dex" in o:
        if d != o["dex"]:
            return False
    elif o.get("dkw"):
        if o["dkw"] not in d:
            return False
    return True


def main():
    with io.open(PATH, encoding="utf-8") as fp:
        db = json.load(fp)
    recs = db["records"]

    # 1) 繰り越し
    carried = 0
    for r in recs:
        b = r.get("bairitsu", {})
        if "2026" in b and b["2026"].get("boshu") is None:
            v25 = b.get("2025", {}).get("boshu")
            if v25 is not None:
                b["2026"]["boshu"] = v25
                carried += 1

    # 2) 上書き
    report = []
    over_applied = 0
    for o in OV:
        hits = [r for r in recs if "2026" in r.get("bairitsu", {}) and match(r, o)]
        for r in hits:
            r["bairitsu"]["2026"]["boshu"] = o["val"]
            over_applied += 1
        label = "%s %s/%s [%s] -> %d" % (
            o["u"], o.get("fkw", ""), o.get("dex", o.get("dkw", "")), o["m"], o["val"])
        report.append("%s  : %d件" % (label, len(hits)))

    # 集計
    b26 = sum(1 for r in recs
              if r.get("bairitsu", {}).get("2026", {}).get("boshu") is not None)
    has26 = sum(1 for r in recs if "2026" in r.get("bairitsu", {}))

    db["meta"]["updated"] = datetime.date.today().isoformat()

    with io.open(PATH, "w", encoding="utf-8") as fp:
        json.dump(db, fp, ensure_ascii=False, separators=(",", ":"))

    lines = []
    lines.append("# 2026年度 boshu パッチ レポート")
    lines.append("")
    lines.append("- 繰り越し(2025->2026): %d件" % carried)
    lines.append("- 上書き適用レコード数: %d件" % over_applied)
    lines.append("- 2026 boshu 非null: %d / 2026ブロック %d件" % (b26, has26))
    lines.append("- meta.updated: %s" % db["meta"]["updated"])
    lines.append("")
    lines.append("## 上書き明細（マッチ件数）")
    zero = [x for x in report if x.endswith(": 0件")]
    for x in report:
        lines.append("- " + x)
    lines.append("")
    lines.append("## 未マッチ（0件）= %d 件" % len(zero))
    for x in zero:
        lines.append("- " + x)
    out = "\n".join(lines)
    with io.open("boshu_patch_report_2026.md", "w", encoding="utf-8") as fp:
        fp.write(out)
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    main()
