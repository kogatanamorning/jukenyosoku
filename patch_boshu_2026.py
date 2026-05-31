# -*- coding: utf-8 -*-
"""
2026年度 募集人員(boshu) パッチ（区切り文字正規化版）

方針:
 1) 2025年度boshu -> 2026年度へ繰り越し（変更が無い学科はそのまま）
 2) 駿台「2026年度入試 国公立大 変更点一覧」(2025/12/08版) の募集人員変更で上書き
 3) 後期日程廃止学科は Kei-Net に 2026 後期データが無く 2026ブロック非存在のため対象外

マッチング: 大学名は完全一致、日程は完全一致。
学部(fkw)・学科(dkw)は「区切り文字・空白・括弧」を除去して正規化した上で部分一致。
マッチ件数はレポート出力。
"""
import json, io, sys, datetime

PATH = "data/data.json"

_STRIP = "｜／・－−-|/ 　（）()〈〉｜，,、　"


def norm(s):
    s = s or ""
    return "".join(c for c in s if c not in _STRIP)


# u / fkw（学部 正規化部分一致, ''=無視）/ dkw（学科 正規化部分一致, ''=無視）/ m / val
OV = [
    # 旭川医科大
    dict(u="旭川医科大", fkw="医学", dkw="医学科", m="前期日程", val=48),
    # 北海道大
    dict(u="北海道大", dkw="検査技術科学", m="前期日程", val=30),
    dict(u="北海道大", dkw="作業療法学", m="前期日程", val=14),
    # 北海道教育大（キャンパスは学部fに入る）
    dict(u="北海道教育大", fkw="旭川校", dkw="教育発達", m="前期日程", val=32),
    dict(u="北海道教育大", fkw="旭川校", dkw="国語教育", m="後期日程", val=3),
    dict(u="北海道教育大", fkw="旭川校", dkw="社会科教育", m="後期日程", val=6),
    dict(u="北海道教育大", fkw="旭川校", dkw="理科教育", m="後期日程", val=7),
    dict(u="北海道教育大", fkw="旭川校", dkw="芸術保健体育教育専攻音楽", m="前期日程", val=7),
    dict(u="北海道教育大", fkw="旭川校", dkw="保健体育分野", m="前期日程", val=7),
    dict(u="北海道教育大", fkw="岩見沢校", dkw="声楽", m="前期日程", val=2),
    dict(u="北海道教育大", fkw="岩見沢校", dkw="鍵盤楽器", m="前期日程", val=7),
    dict(u="北海道教育大", fkw="釧路校", dkw="地域学校教育実践", m="前期日程", val=50),
    dict(u="北海道教育大", fkw="釧路校", dkw="地域学校教育実践", m="後期日程", val=60),
    dict(u="北海道教育大", fkw="札幌校", dkw="図画工作美術教育", m="前期日程", val=6),
    # 岩手大
    dict(u="岩手大", dkw="電気電子情報通信", m="前期日程", val=36),
    dict(u="岩手大", dkw="電気電子情報通信", m="後期日程", val=11),
    dict(u="岩手大", dkw="機械知能航空", m="前期日程", val=48),
    dict(u="岩手大", dkw="機械知能航空", m="後期日程", val=15),
    dict(u="岩手大", dkw="共同獣医", m="前期日程", val=18),
    # 東北大（薬は f='' d='薬学部'）
    dict(u="東北大", dkw="放射線技術科学", m="前期日程", val=23),
    dict(u="東北大", dkw="検査技術科学", m="前期日程", val=23),
    dict(u="東北大", dkw="薬学部", m="前期日程", val=52),
    # 山形大（医 前期 一般65+地域8=73）
    dict(u="山形大", fkw="医学", dkw="医学科", m="前期日程", val=73),
    # 茨城大（教科教育コース｜○○選修）
    dict(u="茨城大", dkw="教科教育コース英語", m="前期日程", val=5),
    dict(u="茨城大", dkw="教科教育コース数学", m="前期日程", val=17),
    dict(u="茨城大", dkw="教科教育コース理科", m="前期日程", val=15),
    dict(u="茨城大", dkw="教科教育コース技術", m="前期日程", val=11),
    dict(u="茨城大", dkw="特別支援教育", m="前期日程", val=15),
    dict(u="茨城大", dkw="教育実践科学", m="前期日程", val=13),
    # 筑波大（障害科学類）
    dict(u="筑波大", dkw="教育学類", m="後期日程", val=2),
    dict(u="筑波大", dkw="心理学類", m="後期日程", val=3),
    dict(u="筑波大", dkw="障害", m="前期日程", val=2),
    dict(u="筑波大", dkw="化学類", m="前期日程", val=18),
    dict(u="筑波大", dkw="化学類", m="後期日程", val=5),
    # 横浜国立大
    dict(u="横浜国立大", dkw="都市社会共生", m="後期日程", val=8),
    # 富山大
    dict(u="富山大", fkw="医学", dkw="医学科", m="前期日程", val=68),
    # 金沢大
    dict(u="金沢大", dkw="地球社会基盤", m="前期日程", val=67),
    dict(u="金沢大", dkw="医学類", m="前期日程", val=79),
    # 山梨大
    dict(u="山梨大", dkw="言語教育", m="前期日程", val=6),
    dict(u="山梨大", dkw="言語教育", m="後期日程", val=3),
    dict(u="山梨大", dkw="生活社会教育", m="前期日程", val=6),
    dict(u="山梨大", dkw="生活社会教育", m="後期日程", val=2),
    # 千葉大
    dict(u="千葉大", dkw="音楽科教育", m="前期日程", val=9),
    dict(u="千葉大", dkw="図画工作美術科教育", m="前期日程", val=10),
    # 名古屋大
    dict(u="名古屋大", dkw="物理工", m="前期日程", val=73),
    dict(u="名古屋大", dkw="マテリアル工", m="前期日程", val=95),
    # 三重大
    dict(u="三重大", dkw="電子情報工学", m="前期日程", val=18),
    dict(u="三重大", dkw="電子情報工学", m="後期日程", val=14),
    # 京都大（工学部・農森林科学はDBに2026レコードが無いため対象外）
    dict(u="京都大", fkw="理学", dkw="理学科", m="前期日程", val=274),
    # 大阪大
    dict(u="大阪大", dkw="情報科学", m="前期日程", val=88),
    dict(u="大阪大", dkw="化学応用科学", m="前期日程", val=71),
    dict(u="大阪大", dkw="システム科学", m="前期日程", val=148),
    dict(u="大阪大", dkw="電子物理科学", m="前期日程", val=90),
    dict(u="大阪大", fkw="歯学", dkw="歯学科", m="前期日程", val=45),
    # 神戸大
    dict(u="神戸大", dkw="応用動物学", m="前期日程", val=19),
    dict(u="神戸大", dkw="応用動物学", m="後期日程", val=5),
    dict(u="神戸大", dkw="食料環境経済学", m="前期日程", val=6),
    # 鳥取大（医 前期 一般53+とっとり7=60）
    dict(u="鳥取大", fkw="医学", dkw="医学科", m="前期日程", val=60),
    # 岡山大
    dict(u="岡山大", dkw="小学校教育", m="前期日程", val=71),
    dict(u="岡山大", dkw="特別支援教育", m="前期日程", val=8),
    dict(u="岡山大", dkw="幼児教育", m="前期日程", val=8),
    dict(u="岡山大", dkw="医学科", m="前期日程", val=95),
    dict(u="岡山大", dkw="総合農業科学", m="前期日程", val=100),
    # 広島大（法/歯後期はDBが学部集約のため対象外）
    dict(u="広島大", dkw="工学特別", m="前期日程", val=30),
    dict(u="広島大", dkw="作業療法学", m="前期日程", val=20),
    dict(u="広島大", dkw="生物生産", m="前期日程", val=67),
    # 愛媛大
    dict(u="愛媛大", fkw="医", dkw="看護", m="前期日程", val=30),
    # 九州大
    dict(u="九州大", fkw="文", dkw="人文", m="前期日程", val=109),
    # 佐賀大（医 前期51, 後期廃止）
    dict(u="佐賀大", fkw="医", dkw="医学科", m="前期日程", val=51),
    # 長崎大
    dict(u="長崎大", fkw="医", dkw="医学科", m="前期日程", val=66),
    dict(u="長崎大", fkw="薬", dkw="薬学科", m="前期日程", val=32),
    dict(u="長崎大", dkw="薬科学", m="前期日程", val=36),
    # 熊本大
    dict(u="熊本大", fkw="法", dkw="法学科", m="前期日程", val=130),
    dict(u="熊本大", fkw="理", dkw="理学科", m="前期日程", val=125),
    dict(u="熊本大", fkw="理", dkw="理学科", m="後期日程", val=35),
    # 鹿児島大
    dict(u="鹿児島大", fkw="医", dkw="医学科", m="後期日程", val=19),
    # 琉球大
    dict(u="琉球大", fkw="医", dkw="医学科", m="後期日程", val=23),
    # 公立
    dict(u="公立小松大", dkw="生産システム科学", m="前期日程", val=30),
    dict(u="横浜市立大", fkw="理", dkw="", m="前期日程", val=55),
    dict(u="京都府立医科大", fkw="医", dkw="医学科", m="前期日程", val=93),
    dict(u="大阪公立大", dkw="食栄養", m="前期日程", val=35),
]


def match(r, o):
    if r["u"] != o["u"] or r["m"] != o["m"]:
        return False
    if "2026" not in r.get("bairitsu", {}):
        return False
    f = norm(r.get("f", ""))
    d = norm(r.get("d", ""))
    if o.get("fkw") and norm(o["fkw"]) not in f:
        return False
    if o.get("dkw") and norm(o["dkw"]) not in d:
        return False
    return True


def main():
    with io.open(PATH, encoding="utf-8") as fp:
        db = json.load(fp)
    recs = db["records"]

    carried = 0
    for r in recs:
        b = r.get("bairitsu", {})
        if "2026" in b and b["2026"].get("boshu") is None:
            v25 = b.get("2025", {}).get("boshu")
            if v25 is not None:
                b["2026"]["boshu"] = v25
                carried += 1

    report, over_applied = [], 0
    for o in OV:
        hits = [r for r in recs if match(r, o)]
        for r in hits:
            r["bairitsu"]["2026"]["boshu"] = o["val"]
            over_applied += 1
        report.append("%s %s/%s [%s] -> %d : %d件" % (
            o["u"], o.get("fkw", ""), o.get("dkw", ""), o["m"], o["val"], len(hits)))

    b26 = sum(1 for r in recs
              if r.get("bairitsu", {}).get("2026", {}).get("boshu") is not None)
    has26 = sum(1 for r in recs if "2026" in r.get("bairitsu", {}))

    db["meta"]["updated"] = datetime.date.today().isoformat()
    with io.open(PATH, "w", encoding="utf-8") as fp:
        json.dump(db, fp, ensure_ascii=False, separators=(",", ":"))

    zero = [x for x in report if x.endswith(": 0件")]
    lines = ["# 2026年度 boshu パッチ レポート", "",
             "- 繰り越し(2025->2026): %d件" % carried,
             "- 上書き適用レコード数: %d件" % over_applied,
             "- 上書きルール: %d（うち未マッチ %d）" % (len(OV), len(zero)),
             "- 2026 boshu 非null: %d / 2026ブロック %d件" % (b26, has26),
             "- meta.updated: %s" % db["meta"]["updated"], "",
             "## 上書き明細"]
    lines += ["- " + x for x in report]
    lines += ["", "## 未マッチ（0件） %d 件" % len(zero)]
    lines += ["- " + x for x in zero]
    out = "\n".join(lines)
    with io.open("boshu_patch_report_2026.md", "w", encoding="utf-8") as fp:
        fp.write(out)
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    main()
