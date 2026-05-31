"use strict";

let DB = null;          // data.json
let RECORD_INDEX = {};  // "大学|学部・学科|方式" → record

// ───────── 初期化 ─────────
async function init() {
  try {
    const res = await fetch("data/data.json");
    DB = await res.json();
  } catch (e) {
    document.getElementById("loadStatus").textContent = "データ読み込み失敗: " + e;
    return;
  }
  // レコード索引を作る
  DB.records.forEach(r => {
    const dept = deptLabel(r.f, r.d);
    RECORD_INDEX[`${r.u}|${dept}|${r.m}`] = r;
  });
  document.getElementById("loadStatus").textContent =
    `データ ${DB.records.length}件 / ${DB.universities.length}大学`;

  // 更新日時を右上に表示
  const updated = DB.meta && DB.meta.updated;
  if (updated) {
    document.getElementById("updateDate").textContent = `データ更新: ${updated}`;
  }

  setupTabs();
  setupBairitsu();
  setupKyotest();
  setupBanzai();
  setupOutput();
}

function deptLabel(f, d) {
  if (f && d) return `${f}・${d}`;
  if (d) return d;
  if (f) return f;
  return "";
}

function fillUnivSelect(sel) {
  DB.universities.forEach(u => {
    const o = document.createElement("option");
    o.value = u; o.textContent = u;
    sel.appendChild(o);
  });
}

// ───────── タブ切替 ─────────
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });
}

// ───────── 倍率検索 ─────────
function setupBairitsu() {
  const uSel = document.getElementById("b_univ");
  const dSel = document.getElementById("b_dept");
  const mSel = document.getElementById("b_method");
  fillUnivSelect(uSel);

  uSel.addEventListener("change", () => {
    fillDeptSelect(dSel, DB.departments[uSel.value] || []);
    renderBairitsu();
  });
  dSel.addEventListener("change", renderBairitsu);
  mSel.addEventListener("change", renderBairitsu);
}

function fillDeptSelect(sel, depts) {
  sel.innerHTML = '<option value="">（すべて）</option>';
  depts.forEach(d => {
    const o = document.createElement("option");
    o.value = d; o.textContent = d;
    sel.appendChild(o);
  });
}

function renderBairitsu() {
  const u = document.getElementById("b_univ").value;
  const d = document.getElementById("b_dept").value;
  const m = document.getElementById("b_method").value;
  const tbody = document.querySelector("#b_table tbody");
  tbody.innerHTML = "";
  if (!u) { document.getElementById("b_count").textContent = ""; return; }

  let rows = [];
  DB.records.forEach(r => {
    if (r.u !== u) return;
    const dept = deptLabel(r.f, r.d);
    if (d && dept !== d) return;
    if (m && r.m !== m) return;
    ["2026","2025","2024","2023"].forEach(y => {
      const b = r.bairitsu[y];
      if (!b) return;
      rows.push({ y, u: r.u, f: r.f, d: r.d, m: r.m, ...b });
    });
  });

  document.getElementById("b_count").textContent = `${rows.length} 件`;
  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${row.y}</td><td class="left">${row.u}</td><td class="left">${row.f}</td>` +
      `<td class="left">${row.d}</td><td>${row.m}</td>` +
      `<td>${fmt(row.boshu)}</td><td>${fmt(row.shigan)}</td><td>${fmt(row.juken)}</td>` +
      `<td>${fmt(row.gokaku)}</td><td>${fmtF(row.ku)}</td><td>${fmtF(row.kuprv)}</td>`;
    tbody.appendChild(tr);
  });
}

// ───────── 共テ検索 ─────────
function setupKyotest() {
  const uSel = document.getElementById("k_univ");
  const dSel = document.getElementById("k_dept");
  const mSel = document.getElementById("k_method");
  fillUnivSelect(uSel);

  uSel.addEventListener("change", () => {
    fillDeptSelect(dSel, DB.departments[uSel.value] || []);
    renderKyotest();
  });
  dSel.addEventListener("change", renderKyotest);
  mSel.addEventListener("change", renderKyotest);
}

function renderKyotest() {
  const u = document.getElementById("k_univ").value;
  const d = document.getElementById("k_dept").value;
  const m = document.getElementById("k_method").value;
  const tbody = document.querySelector("#k_table tbody");
  tbody.innerHTML = "";
  if (!u) { document.getElementById("k_count").textContent = ""; return; }

  let rows = [];
  DB.records.forEach(r => {
    if (r.u !== u) return;
    const dept = deptLabel(r.f, r.d);
    if (d && dept !== d) return;
    if (m && r.m !== m) return;
    if (r.border == null && r.kyo_man == null) return; // 共テ情報なしは除外
    rows.push(r);
  });

  document.getElementById("k_count").textContent = `${rows.length} 件`;
  rows.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>2025</td><td class="left">${r.u}</td><td class="left">${r.f}</td>` +
      `<td class="left">${r.d}</td><td>${r.m}</td>` +
      `<td>${r.border != null ? r.border + "%" : "-"}</td>` +
      `<td>${fmtF(r.hensa)}</td><td>${fmt(r.kyo_man)}</td><td>${fmt(r.ko_man)}</td>` +
      `<td>${r.ratio != null ? r.ratio + "%" : "-"}</td>` +
      `<td class="subj-cell">${r.kyo_subj || "-"}</td>` +
      `<td class="subj-cell">${r.ko_subj || "-"}</td>`;
    tbody.appendChild(tr);
  });
}

// ───────── ばんざい入力 ─────────
const BZ_KEY = "banzai_data_v1";
const BZ_COLS = ["univ","dept","method","shukei","first","zen","border","jA","jB","jC","jD","jE"];

function loadBanzai() {
  try { return JSON.parse(localStorage.getItem(BZ_KEY)) || []; }
  catch { return []; }
}
function saveBanzai(rows) {
  localStorage.setItem(BZ_KEY, JSON.stringify(rows));
  const ind = document.getElementById("bz_saved");
  ind.textContent = "✓ 保存しました";
  setTimeout(() => ind.textContent = "", 1500);
}

function setupBanzai() {
  let rows = loadBanzai();
  if (rows.length === 0) rows = [emptyBanzaiRow()];
  renderBanzai(rows);

  document.getElementById("bz_add").addEventListener("click", () => {
    const cur = collectBanzai();
    cur.push(emptyBanzaiRow());
    renderBanzai(cur);
    saveBanzai(cur);
  });
  document.getElementById("bz_export").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(collectBanzai(), null, 2)], {type:"application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "banzai_data.json";
    a.click();
  });
  document.getElementById("bz_import_btn").addEventListener("click", () =>
    document.getElementById("bz_import").click());
  document.getElementById("bz_import").addEventListener("change", e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const data = JSON.parse(ev.target.result);
        renderBanzai(data);
        saveBanzai(data);
      } catch(err) { alert("読み込み失敗: " + err); }
    };
    reader.readAsText(file);
  });
}

function emptyBanzaiRow() {
  return {univ:"",dept:"",method:"",shukei:"",first:"",zen:"",border:"",jA:"",jB:"",jC:"",jD:"",jE:""};
}

function renderBanzai(rows) {
  const tbody = document.querySelector("#bz_table tbody");
  tbody.innerHTML = "";
  rows.forEach((row, i) => {
    const tr = document.createElement("tr");
    // 大学 select
    const uTd = document.createElement("td");
    const uSel = document.createElement("select");
    uSel.innerHTML = '<option value="">選択</option>';
    DB.universities.forEach(u => {
      const o = document.createElement("option");
      o.value = u; o.textContent = u;
      if (u === row.univ) o.selected = true;
      uSel.appendChild(o);
    });
    uTd.appendChild(uSel); tr.appendChild(uTd);
    // 学部学科 select
    const dTd = document.createElement("td");
    const dSel = document.createElement("select");
    fillDeptSelect(dSel, DB.departments[row.univ] || []);
    dSel.value = row.dept || "";
    dTd.appendChild(dSel); tr.appendChild(dTd);
    // 方式 select
    const mTd = document.createElement("td");
    const mSel = document.createElement("select");
    mSel.innerHTML = '<option value="">-</option><option>前期日程</option><option>後期日程</option><option>中期日程</option>';
    mSel.value = row.method || "";
    mTd.appendChild(mSel); tr.appendChild(mTd);
    // 数値入力
    const numFields = ["shukei","first","zen","border","jA","jB","jC","jD","jE"];
    numFields.forEach(f => {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.type = "number"; inp.value = row[f] ?? "";
      inp.addEventListener("change", () => saveBanzai(collectBanzai()));
      td.appendChild(inp); tr.appendChild(td);
    });
    // 削除ボタン
    const delTd = document.createElement("td");
    const del = document.createElement("button");
    del.className = "del-btn"; del.textContent = "×";
    del.addEventListener("click", () => {
      const cur = collectBanzai();
      cur.splice(i, 1);
      renderBanzai(cur.length ? cur : [emptyBanzaiRow()]);
      saveBanzai(cur);
    });
    delTd.appendChild(del); tr.appendChild(delTd);

    // 大学変更時、学部学科を更新
    uSel.addEventListener("change", () => {
      fillDeptSelect(dSel, DB.departments[uSel.value] || []);
      saveBanzai(collectBanzai());
    });
    dSel.addEventListener("change", () => saveBanzai(collectBanzai()));
    mSel.addEventListener("change", () => saveBanzai(collectBanzai()));

    tbody.appendChild(tr);
  });
}

function collectBanzai() {
  const rows = [];
  document.querySelectorAll("#bz_table tbody tr").forEach(tr => {
    const sels = tr.querySelectorAll("select");
    const inps = tr.querySelectorAll("input");
    rows.push({
      univ: sels[0].value, dept: sels[1].value, method: sels[2].value,
      shukei: inps[0].value, first: inps[1].value, zen: inps[2].value,
      border: inps[3].value, jA: inps[4].value, jB: inps[5].value,
      jC: inps[6].value, jD: inps[7].value, jE: inps[8].value,
    });
  });
  return rows;
}

function findBanzai(u, dept, m) {
  const rows = loadBanzai();
  return rows.find(r => r.univ === u && r.dept === dept && r.method === m);
}

// ───────── 統合出力 ─────────
const SLOT_LABELS = ["受験","関連1","関連2","関連3","関連4","関連5"];

function setupOutput() {
  const container = document.getElementById("o_slots");
  SLOT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "slot-row" + (i === 0 ? " target" : "");
    row.innerHTML = `<span class="slot-label">${label}</span>`;
    const uSel = document.createElement("select");
    uSel.innerHTML = '<option value="">▼ 大学</option>';
    DB.universities.forEach(u => {
      const o = document.createElement("option"); o.value = u; o.textContent = u; uSel.appendChild(o);
    });
    const dSel = document.createElement("select");
    dSel.innerHTML = '<option value="">（すべて）</option>';
    const mSel = document.createElement("select");
    mSel.innerHTML = '<option value="">-</option><option>前期日程</option><option>後期日程</option><option>中期日程</option>';
    uSel.addEventListener("change", () => fillDeptSelect(dSel, DB.departments[uSel.value] || []));
    row.appendChild(uSel); row.appendChild(dSel); row.appendChild(mSel);
    container.appendChild(row);
  });

  document.getElementById("o_generate").addEventListener("click", generateMarkdown);
  document.getElementById("o_copy").addEventListener("click", () => {
    const ta = document.getElementById("o_markdown");
    ta.select();
    navigator.clipboard.writeText(ta.value).then(() => {
      const ind = document.getElementById("o_copied");
      ind.textContent = "✓ コピーしました";
      setTimeout(() => ind.textContent = "", 1500);
    });
  });
}

function generateMarkdown() {
  const slots = document.querySelectorAll("#o_slots .slot-row");
  let md = "# 倍率予測リクエスト\n\n";
  let hasTarget = false;

  slots.forEach((row, i) => {
    const sels = row.querySelectorAll("select");
    const u = sels[0].value, dept = sels[1].value, m = sels[2].value;
    if (!u || !dept || !m) return;
    hasTarget = true;
    const rec = RECORD_INDEX[`${u}|${dept}|${m}`];
    md += `### ${SLOT_LABELS[i]}: ${u} ${dept} ${m}\n`;
    if (!rec) { md += "(データなし)\n\n"; return; }

    md += "**過去倍率**\n";
    md += "| 年度 | 募集 | 志願 | 受験 | 合格 | 競争率 | 前年競争率 |\n|---|---|---|---|---|---|---|\n";
    ["2026","2025","2024","2023"].forEach(y => {
      const b = rec.bairitsu[y];
      if (b) md += `| ${y} | ${fmt(b.boshu)} | ${fmt(b.shigan)} | ${fmt(b.juken)} | ${fmt(b.gokaku)} | ${fmtF(b.ku)} | ${fmtF(b.kuprv)} |\n`;
    });
    md += "\n**共テボーダー & 必要科目**\n";
    md += `- ボーダー得点率: ${rec.border != null ? rec.border+"%" : "-"} / 偏差値 ${fmtF(rec.hensa)}\n`;
    md += `- 共テ満点 ${fmt(rec.kyo_man)} / 2次満点 ${fmt(rec.ko_man)} / 個別比率 ${rec.ratio != null ? rec.ratio+"%" : "-"}\n`;
    if (rec.kyo_subj) md += `- 共テ科目: ${rec.kyo_subj}\n`;
    if (rec.ko_subj) md += `- 2次科目: ${rec.ko_subj}\n`;

    // ばんざい
    const bz = findBanzai(u, dept, m);
    if (bz && bz.shukei) {
      md += "\n**ばんざい今年データ**\n";
      md += `- 集計人数 ${bz.shukei} (第1志望 ${bz.first || "-"})\n`;
      md += `- 前年比 ${bz.zen || "-"}% / 河合予想ボーダー ${bz.border || "-"}%\n`;
      md += `- 判定分布: A=${bz.jA||"-"}, B=${bz.jB||"-"}, C=${bz.jC||"-"}, D=${bz.jD||"-"}, E=${bz.jE||"-"}\n`;
    }
    md += "\n";
  });

  if (!hasTarget) { md = "受験大学(と関連大学)を選択してください。各スロットで大学・学部学科・方式すべて選択が必要です。"; }
  else {
    // 共テ全国平均テーブル
    md += "**共テ全国平均 (新課程, 100点換算)**\n";
    md += "| 科目 | 2026 | 2025 | 前年比 |\n|---|---|---|---|\n";
    const subjects = [
      ["国語","国語"],["数IA","数学Ⅰ，数学Ａ"],["数IIBC","数学Ⅱ，数学Ｂ，数学Ｃ"],
      ["英語R","英語（リーディング）"],["英語L","英語（リスニング）"],
      ["物理基礎","【出題範囲】物理基礎"],["化学基礎","【出題範囲】化学基礎"],
      ["生物基礎","【出題範囲】生物基礎"],["地学基礎","【出題範囲】地学基礎"],
      ["物理","物理"],["化学","化学"],["生物","生物"],["地学","地学"],
      ["日本史探究","歴史総合，日本史探究"],["世界史探究","歴史総合，世界史探究"],
      ["地理探究","地理総合，地理探究"],["公共・倫理","公共，倫理"],
      ["公共・政経","公共，政治・経済"],["情報Ⅰ","情報Ⅰ"],
    ];
    const a26 = DB.kyotest_avg["2026"] || {};
    const a25 = DB.kyotest_avg["2025"] || {};
    subjects.forEach(([disp, key]) => {
      const v26 = a26[key]?.avg, v25 = a25[key]?.avg;
      const diff = (v26 != null && v25 != null) ? (v26 - v25).toFixed(2) : "-";
      const sign = (diff !== "-" && diff >= 0) ? "+" : "";
      md += `| ${disp} | ${v26 ?? "-"} | ${v25 ?? "-"} | ${sign}${diff} |\n`;
    });

    md += "\n## AI への指示\n";
    md += "- 隔年現象 (前年高倍率の翌年に敬遠) を考慮\n";
    md += "- 共テ全国平均テーブルから今年の難易度動向を把握し、ボーダー予測の補正に使う\n";
    md += "- ばんざい集計人数前年比は実志願者数の前年比と相関するが、出願率の補正を行う\n";
    md += "- 関連大学との比較でシフト (他大が下がり目→受験校に流入) の兆候を探る\n";
    md += "- 受験大学・関連大学の入試変更情報を最新ウェブで確認してから予測\n";
    md += "- 必要科目が空欄の大学は公式入試要項を確認すること\n";
    md += "- 出力: 予測競争率 (中央値・上振れ・下振れ) と根拠\n";
  }

  document.getElementById("o_markdown").value = md;
}

// ───────── ユーティリティ ─────────
function fmt(v) { return (v == null || v === "") ? "-" : Number(v).toLocaleString(); }
function fmtF(v) { return (v == null || v === "") ? "-" : Number(v).toFixed(1); }

init();
