#!/usr/bin/env python3
"""Build self-contained interactive HTML dashboard from wc2026_results_v2.json"""
import json

DATA = json.load(open("wc2026_results_v2.json"))
DATA_JS = json.dumps(DATA, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Predictive Model</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0b0f1a; --panel:#121829; --border:#1f2a44;
    --text:#e8ecf4; --muted:#8b96ad; --accent:#36d399; --red:#f87272;
    --gold:#fbbf24; --blue:#5b9cf6;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;padding:24px}
  .wrap{max-width:1280px;margin:0 auto}
  h1{font-size:26px;letter-spacing:-.5px}
  h2{font-size:17px;margin:0 0 14px}
  .sub{color:var(--muted);margin:6px 0 4px;font-size:13px}
  .chips{margin:10px 0 16px}
  .chip{display:inline-block;background:var(--panel);border:1px solid var(--border);border-radius:999px;padding:4px 12px;font-size:12px;color:var(--muted);margin:0 8px 6px 0}
  .chip b{color:var(--text);font-weight:600}
  .seg{display:inline-flex;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:4px;margin-bottom:8px}
  .seg button{background:transparent;border:0;color:var(--muted);font:600 13px inherit;padding:8px 18px;border-radius:9px;cursor:pointer;transition:.15s}
  .seg button.active{background:var(--blue);color:#fff}
  .modedesc{font-size:12.5px;color:var(--muted);margin:0 0 18px 2px}
  .grid-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:22px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:16px 18px}
  .kpi .lab{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted)}
  .kpi .val{font-size:22px;font-weight:700;margin-top:4px}
  .kpi .det{font-size:12px;color:var(--muted);margin-top:2px}
  .pos{color:var(--accent)} .neg{color:var(--red)} .gold{color:var(--gold)}
  .panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:22px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);text-align:right;padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;white-space:nowrap;user-select:none}
  th:first-child,td:first-child{text-align:left}
  th.sorted{color:var(--accent)}
  td{padding:7px 10px;text-align:right;border-bottom:1px solid #161e33;white-space:nowrap}
  tr:hover td{background:#162039}
  .tname{font-weight:600}
  .gtag{display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:5px;background:#1c2742;color:var(--muted);font-size:10px;font-weight:700;margin-right:8px}
  .bar{display:inline-block;height:6px;border-radius:3px;background:var(--blue);vertical-align:middle;margin-right:6px}
  .verdict{display:inline-block;border-radius:6px;padding:1px 8px;font-size:11px;font-weight:700}
  .v-val{background:rgba(54,211,153,.13);color:var(--accent)}
  .v-fair{background:rgba(139,150,173,.13);color:var(--muted)}
  .v-avoid{background:rgba(248,114,114,.12);color:var(--red)}
  .groups{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
  .gcard h3{font-size:13px;color:var(--gold);margin-bottom:10px;letter-spacing:.5px}
  .grow{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px}
  .grow .nm{flex:0 0 130px;overflow:hidden;text-overflow:ellipsis}
  .grow .pct{flex:0 0 96px;text-align:right;color:var(--muted);font-size:12px}
  .gbar{flex:1;height:7px;background:#1a2440;border-radius:4px;overflow:hidden}
  .gbar i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--accent))}
  .finals li{display:flex;justify-content:space-between;padding:7px 4px;border-bottom:1px solid #161e33;list-style:none;font-size:13.5px}
  .daycard{margin-bottom:18px}
  .dayhead{font-size:13px;font-weight:700;color:var(--gold);letter-spacing:.4px;margin:0 0 8px;padding-bottom:6px;border-bottom:1px solid var(--border)}
  .daycard.today .dayhead{color:var(--accent)}
  .daycard.today{border-left:3px solid var(--accent);padding-left:12px;margin-left:-15px}
  .mrow{display:grid;grid-template-columns:54px 24px minmax(180px,1.1fr) minmax(150px,.9fr) 1fr 150px;gap:10px;align-items:center;padding:7px 0;border-bottom:1px solid #141c30;font-size:13px;cursor:pointer}
  .mrow:hover{background:#131b30}
  .pick{display:inline-flex;align-items:center;gap:6px;border-radius:7px;padding:2px 9px;font-size:11.5px;font-weight:700;white-space:nowrap}
  .pk-all{background:rgba(54,211,153,.13);color:var(--accent)}
  .pk-maj{background:rgba(251,191,36,.12);color:var(--gold)}
  .pk-split{background:rgba(139,150,173,.13);color:var(--muted)}
  .pick small{font-weight:400;opacity:.75}
  .mdetail{display:none;background:#0e1526;border:1px solid var(--border);border-radius:10px;margin:4px 0 10px 78px;padding:10px 14px}
  .mdetail.open{display:block}
  .mdetail table{font-size:12.5px}
  .mdetail td,.mdetail th{padding:5px 10px;border-bottom:1px solid #18213a}
  .mdetail tr:last-child td{border-bottom:0}
  .mdetail .mlab{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px;text-align:left}
  .mdetail .picked{color:var(--accent);font-weight:700}
  .mrow .tm{color:var(--muted);font-size:11.5px}
  .mrow .vs b{color:var(--text)}
  .mrow .vs span.venue{color:#5a6580;font-size:11px;display:block}
  .m1x2{display:flex;height:14px;border-radius:4px;overflow:hidden;font-size:0}
  .m1x2 i{display:block;height:100%}
  .m1x2 .w{background:var(--blue)} .m1x2 .d{background:#39435e} .m1x2 .l{background:#7e4a5a}
  .mpct{color:var(--muted);font-size:11.5px;text-align:right;white-space:nowrap}
  .mpct b{color:var(--text)}
  .selwrap{margin:0 0 14px}
  select{background:var(--panel);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:7px 10px;font:inherit}
  .korow{display:grid;grid-template-columns:110px 110px 100px 1fr;gap:10px;align-items:baseline;padding:7px 0;border-bottom:1px solid #141c30;font-size:13px}
  .korow .lab{font-weight:700}
  .korow .pj{color:var(--muted);font-size:12px}
  .stale{display:none;margin:0 0 18px;padding:11px 14px;border:1px solid #4a3a10;background:#211a06;border-radius:10px;color:#fbbf24;font-size:13px}
  .stale.on{display:block}
  .stale code{background:#2e2509;padding:1px 6px;border-radius:5px}
  .ptschip{flex:0 0 64px;text-align:right;color:var(--gold);font-size:11px;font-weight:700;white-space:nowrap}
  .two{display:grid;grid-template-columns:1.7fr 1fr;gap:22px}
  @media(max-width:920px){.two{grid-template-columns:1fr}}
  .meth{font-size:12.5px;color:var(--muted);line-height:1.7}
  .meth b{color:var(--text)}
  .disc{margin-top:14px;padding:12px 14px;border:1px solid #3a2b14;background:#1a1408;border-radius:10px;color:#d8b36a;font-size:12.5px}
  canvas{max-height:540px}
  .note{font-size:11.5px;color:var(--muted);margin-top:8px}
</style>
</head>
<body>
<div class="wrap">
  <h1>🏆 World Cup 2026 — Predictive Model</h1>
  <div class="sub">Elo + market-implied adjustments · 50,000-run Monte Carlo of the full 48-team bracket</div>
  <div class="chips" id="chips"></div>

  <div class="seg" id="modeSeg">
    <button data-m="pure">Pure Elo</button>
    <button data-m="blend" class="active">Blended ★</button>
    <button data-m="market">Market-anchored</button>
  </div>
  <div class="modedesc" id="modeDesc"></div>

  <div class="stale" id="staleBanner"></div>

  <div class="grid-kpi" id="kpis"></div>

  <div class="panel">
    <h2>Title probability — <span id="chartModeLab"></span> vs. market</h2>
    <canvas id="titleChart"></canvas>
    <div class="note">Market = BetMGM outrights de-vigged (power method). In market-anchored mode the bars converge by construction — that's the calibration working.</div>
  </div>

  <div class="two">
    <div class="panel">
      <h2>Value board — outright winner market</h2>
      <table id="valueTable">
        <thead><tr><th>Team</th><th>Odds</th><th>Pure</th><th>Blend</th><th>Market</th><th>EV pure</th><th>EV blend</th><th>¼ Kelly</th><th>Call</th></tr></thead>
        <tbody></tbody>
      </table>
      <div class="note">Verdict uses <b>blended</b> EV — a bet should survive the market adjustment, not just raw Elo. ¼ Kelly = stake as % of bankroll. Teams with blended title prob ≥ 0.3% shown.</div>
    </div>
    <div class="panel">
      <h2>Most likely finals <span style="font-weight:400;color:var(--muted);font-size:12px" id="finModeLab"></span></h2>
      <ul class="finals" id="finals"></ul>
      <h2 style="margin-top:22px">Methodology</h2>
      <div class="meth">
        <b>Ratings:</b> live World Football Elo + per-team <b>market-implied adjustments</b> — offsets calibrated (only for teams with real market signal, ~150-1 or shorter) so simulated title odds reproduce the de-vigged market. The offset is everything the market prices that Elo can't see: injuries, squad selection, manager, form.<br>
        <b>Modes:</b> Pure (α=0) · Blended (α=0.5, recommended) · Market-anchored (α=1).<br>
        <b>Match model:</b> win expectancy 1/(1+10<sup>−Δ/400</sup>); Elo-calibrated draw rate in groups; knockouts by expectancy.<br>
        <b>Home edge:</b> +100 Elo — USA all rounds; Mexico/Canada through R16.<br>
        <b>Bracket:</b> exact FIFA R32 (matches 73–88) with third-place slot constraints solved per simulation.
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>📅 Daily match board — group stage 1X2 <span style="font-weight:400;color:var(--muted);font-size:12px">(times local · follows selected mode)</span></h2>
    <div class="selwrap">
      <select id="grpFilter"><option value="">All groups</option></select>
    </div>
    <div id="matchBoard"></div>
    <div class="note"><b>Click any match</b> to expand who each projection type picks (Pure Elo / Blended / Market) with full percentages and fair odds. Chip = consensus pick: <span class="pick pk-all" style="font-size:10px">green — all 3 agree</span> <span class="pick pk-maj" style="font-size:10px">amber — 2 of 3</span> <span class="pick pk-split" style="font-size:10px">grey — split</span>. Bars: <span style="color:var(--blue)">■</span> home · <span style="color:#6b7693">■</span> draw · <span style="color:#c98296">■</span> away. "Fair" = no-vig odds (1/p) — a side is value only when a book quotes <b>longer</b> than fair.</div>
  </div>

  <div class="panel">
    <h2>🗓️ Knockout schedule — projected Round-of-32 matchups <span style="font-weight:400;color:var(--muted);font-size:12px">(projections from blended sims; pairings firm up as groups finish)</span></h2>
    <div id="koBoard"></div>
  </div>

  <div class="panel">
    <h2>Full projections — all 48 teams <span style="font-weight:400;color:var(--muted);font-size:12px">(click headers to sort · probabilities follow selected mode)</span></h2>
    <div style="overflow-x:auto">
    <table id="mainTable">
      <thead><tr>
        <th data-k="team">Team</th><th data-k="elo">Elo</th><th data-k="offset">Mkt Adj</th>
        <th data-k="group_win">Win Grp</th><th data-k="r32">R32</th><th data-k="r16">R16</th>
        <th data-k="qf">QF</th><th data-k="sf">SF</th><th data-k="final">Final</th>
        <th data-k="champion">🏆 Win</th><th data-k="odds_decimal">Odds</th>
        <th data-k="edge">Edge</th><th data-k="ev">EV/$1</th>
      </tr></thead>
      <tbody></tbody>
    </table>
    </div>
  </div>

  <div class="panel">
    <h2>Group projections — P(advance to R32)</h2>
    <div class="groups" id="groups"></div>
  </div>

  <div class="disc"><b>⚠️ Betting disclaimer:</b> Model estimates, not guarantees. "VALUE" means the model disagrees with the market after absorbing the market's own information — disagreements can still be the model's fault. Single-tournament variance is huge (the favorite has won 1 of the last 6 World Cups). Quarter-Kelly or smaller; never stake what you can't lose. Analysis, not financial advice.</div>

  <div class="sub" style="margin-top:14px">Sources: eloratings.net (live 2026-06-11) · FIFA Final Draw &amp; regulations · BetMGM outrights 2026-06-10 · Built 2026-06-11.</div>
</div>

<script>
const DATA = __DATA__;
const T = DATA.teams;
let MODE = 'blend';
const pct = (x,d=1)=> (x*100).toFixed(d)+'%';
const am = d => '+'+Math.round((d-1)*100);
const P = (t,k)=> t.modes[MODE][k];

const FR = DATA.meta.freshness || {};
const manualN = Object.keys(FR.manual_adjustments||{}).length;
document.getElementById('chips').innerHTML =
  `<span class="chip"><b>${DATA.meta.n_sims.toLocaleString()}</b> sims × 3 modes</span>
   <span class="chip">Elo as of: <b>${FR.elo_as_of||'—'}</b></span>
   <span class="chip">Odds: <b>${FR.odds_source||''} ${FR.odds_as_of||''}</b></span>
   <span class="chip">Results locked: <b>${FR.results_locked||0}/72</b></span>
   <span class="chip">KO fixed: <b>${FR.ko_slots_known||0}/16</b></span>
   ${manualN?`<span class="chip">Manual adj: <b>${manualN}</b></span>`:''}
   <span class="chip">Built: <b>${DATA.meta.generated_at||''}</b></span>`;

let chart;
function render(){
  document.getElementById('modeDesc').textContent = DATA.meta.modes[MODE];
  document.getElementById('chartModeLab').textContent =
    {pure:'pure Elo',blend:'blended model',market:'market-anchored'}[MODE];
  document.getElementById('finModeLab').textContent = '— '+MODE+' mode';

  // KPIs
  const byChamp=[...T].sort((a,b)=>P(b,'champion')-P(a,'champion'));
  const fav=byChamp[0];
  const mfav=[...T].sort((a,b)=>b.market_implied-a.market_implied)[0];
  const vb=[...T].filter(t=>t.modes.blend.champion>=0.003);
  const val=[...vb].sort((a,b)=>b.ev_blend-a.ev_blend)[0];
  const fade=[...T].filter(t=>t.market_implied>=0.02).sort((a,b)=>a.edge_blend-b.edge_blend)[0];
  const topF=DATA.finals[MODE][0];
  document.getElementById('kpis').innerHTML = `
    <div class="card kpi"><div class="lab">Model favorite (${MODE})</div><div class="val gold">${fav.team}</div><div class="det">${pct(P(fav,'champion'))} to win</div></div>
    <div class="card kpi"><div class="lab">Market favorite</div><div class="val">${mfav.team}</div><div class="det">${pct(mfav.market_implied)} implied (${am(mfav.odds_decimal)})</div></div>
    <div class="card kpi"><div class="lab">Best value (blend EV)</div><div class="val pos">${val.team}</div><div class="det">${val.ev_blend>=0?'+':''}${(val.ev_blend*100).toFixed(0)}¢ per $1 at ${am(val.odds_decimal)}</div></div>
    <div class="card kpi"><div class="lab">Model says avoid</div><div class="val neg">${fade.team}</div><div class="det">blend ${pct(fade.modes.blend.champion)} vs market ${pct(fade.market_implied)}</div></div>
    <div class="card kpi"><div class="lab">Most likely final</div><div class="val" style="font-size:17px">${topF.pair[0]} v ${topF.pair[1]}</div><div class="det">${pct(topF.p)} of sims</div></div>`;

  // chart
  const top=byChamp.slice(0,14);
  const cfg={labels:top.map(t=>t.team),datasets:[
    {label:'Model ('+MODE+')',data:top.map(t=>+(P(t,'champion')*100).toFixed(2)),backgroundColor:'#5b9cf6',borderRadius:4},
    {label:'Market (de-vigged)',data:top.map(t=>+(t.market_implied*100).toFixed(2)),backgroundColor:'#36d399',borderRadius:4}]};
  if(chart){chart.data=cfg;chart.update();}
  else chart=new Chart(document.getElementById('titleChart'),{type:'bar',data:cfg,
    options:{indexAxis:'y',responsive:true,plugins:{legend:{labels:{color:'#e8ecf4'}},
      tooltip:{callbacks:{label:c=>` ${c.dataset.label}: ${c.raw}%`}}},
      scales:{x:{ticks:{color:'#8b96ad',callback:v=>v+'%'},grid:{color:'#1c2742'}},
              y:{ticks:{color:'#e8ecf4',font:{size:12}},grid:{display:false}}}}});

  // finals
  document.getElementById('finals').innerHTML = DATA.finals[MODE].map(f=>
    `<li><span>${f.pair[0]} vs ${f.pair[1]}</span><b>${pct(f.p)}</b></li>`).join('');

  renderMain();
  renderGroups();
  renderMatches();
}

// ---------- daily match board ----------
const DOW=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function renderMatches(){
  const gf=document.getElementById('grpFilter').value;
  const list=DATA.matches.filter(m=>!gf||m.group===gf);
  const days={};
  list.forEach(m=>{
    const dt=new Date(m.utc.replace(' ','T'));
    const key=dt.getFullYear()+'-'+String(dt.getMonth()+1).padStart(2,'0')+'-'+String(dt.getDate()).padStart(2,'0');
    (days[key]=days[key]||{dt,ms:[]}).ms.push({...m,dt});
  });
  const now=new Date();
  const todayKey=now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-'+String(now.getDate()).padStart(2,'0');
  document.getElementById('matchBoard').innerHTML=Object.keys(days).sort().map(k=>{
    const{dt,ms}=days[k];
    const head=`${DOW[dt.getDay()]} ${MON[dt.getMonth()]} ${dt.getDate()}`;
    const rows=ms.sort((a,b)=>a.dt-b.dt).map(m=>{
      const t=m.dt.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
      if(m.played){ // real result locked into the simulation
        const[hg,ag]=m.played;
        const nm=`${hg>ag?'<b>'+m.home+'</b>':m.home} v ${ag>hg?'<b>'+m.away+'</b>':m.away}`;
        return `<div class="mrow" style="opacity:.62;cursor:default">
          <span class="tm">${t}</span><span class="gtag">${m.group}</span>
          <span class="vs">M${m.n} · ${nm}<span class="venue">${m.venue}</span></span>
          <span style="font-weight:700;letter-spacing:1px">FT ${hg}–${ag}</span>
          <span></span><span class="mpct">locked into sims</span></div>`;
      }
      const[pw,pd,pl]=m.probs[MODE];
      const rot=(m.rot&&(m.rot[0]||m.rot[1]))?` <span title="Rotation risk: ${m.rot[0]?m.home:''}${m.rot[0]&&m.rot[1]?' & ':''}${m.rot[1]?m.away:''} already locked into top-2 — likely to rest starters (priced in: −60 Elo)">🔄</span>`:'';
      // consensus across the three projection types
      const MODES3=['pure','blend','market'];
      const picks=MODES3.map(md=>{
        const[w,x,l]=m.probs[md];
        return w>=l&&w>=x?{s:m.home,p:w}:(l>=w&&l>=x?{s:m.away,p:l}:{s:'Draw',p:x});
      });
      const names=picks.map(p=>p.s);
      const lead=names.sort((a,b)=>names.filter(x=>x===b).length-names.filter(x=>x===a).length)[0];
      const agree=picks.filter(p=>p.s===lead).length;
      const maxP=Math.max(...picks.filter(p=>p.s===lead).map(p=>p.p));
      const conf=maxP>=0.62?'strong':(maxP>=0.48?'lean':'slight');
      const cls=agree===3?'pk-all':(agree===2?'pk-maj':'pk-split');
      const chip=agree>=2
        ?`<span class="pick ${cls}">${lead} <small>${agree}/3 · ${conf} · ${(maxP*100).toFixed(0)}%</small></span>`
        :`<span class="pick pk-split">models split <small>tap for detail</small></span>`;
      const nm=`M${m.n} · ${m.home} v ${m.away}${rot}`;
      // per-mode detail table
      const MODE_LAB={pure:'Pure Elo',blend:'Blended ★',market:'Market'};
      const det=MODES3.map((md,i)=>{
        const[w,x,l]=m.probs[md];
        const pk=picks[i].s;
        const cell=(nmx,v)=>`<td class="${pk===nmx?'picked':''}">${nmx==='Draw'?'draw':nmx} ${(v*100).toFixed(0)}%</td>`;
        return `<tr><td class="mlab">${MODE_LAB[md]}</td>${cell(m.home,w)}${cell('Draw',x)}${cell(m.away,l)}
          <td style="color:#5a6580">fair ${(1/w).toFixed(2)} / ${(1/x).toFixed(1)} / ${(1/l).toFixed(1)}</td></tr>`;
      }).join('');
      const verdict=agree===3?`All three projections pick <b>${lead}</b>.`
        :agree===2?`Two of three pick <b>${lead}</b>; ${MODE_LAB[MODES3[picks.findIndex(p=>p.s!==lead)]]} disagrees.`
        :`No consensus — treat as a coin flip.`;
      return `<div class="mrow" data-mx="${m.n}">
        <span class="tm">${t}</span><span class="gtag">${m.group}</span>
        <span class="vs">${nm}<span class="venue">${m.venue}</span></span>
        ${chip}
        <span class="m1x2" title="1 ${(pw*100).toFixed(0)}% · X ${(pd*100).toFixed(0)}% · 2 ${(pl*100).toFixed(0)}%">
          <i class="w" style="width:${pw*100}%"></i><i class="d" style="width:${pd*100}%"></i><i class="l" style="width:${pl*100}%"></i></span>
        <span class="mpct"><b>${(pw*100).toFixed(0)}/${(pd*100).toFixed(0)}/${(pl*100).toFixed(0)}</b><br>fair ${(1/pw).toFixed(2)} · ${(1/pd).toFixed(1)} · ${(1/pl).toFixed(1)}</span>
      </div>
      <div class="mdetail" id="md${m.n}">
        <div style="font-size:12.5px;margin-bottom:6px">${verdict}</div>
        <table><tr><th class="mlab">projection</th><th>${m.home}</th><th>draw</th><th>${m.away}</th><th>fair odds 1/X/2</th></tr>${det}</table>
      </div>`;
    }).join('');
    return `<div class="daycard${k===todayKey?' today':''}"><div class="dayhead">${head}${k===todayKey?' — TODAY':''} <span style="color:#5a6580;font-weight:400">(${ms.length} match${ms.length>1?'es':''})</span></div>${rows}</div>`;
  }).join('');
}
const sel=document.getElementById('grpFilter');
[...new Set(DATA.matches.map(m=>m.group))].sort().forEach(g=>{
  const o=document.createElement('option');o.value=g;o.textContent='Group '+g;sel.appendChild(o);
});
sel.onchange=renderMatches;
// click a match row -> expand per-projection verdicts
document.getElementById('matchBoard').addEventListener('click',e=>{
  const row=e.target.closest('.mrow');
  if(!row||!row.dataset.mx)return;
  const det=document.getElementById('md'+row.dataset.mx);
  if(det)det.classList.toggle('open');
});

// ---------- knockout board (static, blend projections) ----------
document.getElementById('koBoard').innerHTML=DATA.ko.map(m=>{
  const dt=new Date(m.utc.replace(' ','T'));
  const when=`${DOW[dt.getDay()]} ${MON[dt.getMonth()]} ${dt.getDate()}`;
  let pj=m.proj&&m.proj.length?m.proj.map(p=>`${p.pair[0]}–${p.pair[1]} ${(p.p*100).toFixed(0)}%`).join(' · '):'';
  if(m.winner) pj=`<span class="pos">✓ ${m.winner} advanced</span>`;
  const lab=m.known?`<span class="gold">M${m.n}: ${m.label}</span>`:`M${m.n}: ${m.label}`;
  return `<div class="korow"><span class="tm">${when}</span><span class="lab">${lab}</span><span class="tm">${m.venue}</span><span class="pj">${pj}</span></div>`;
}).join('');

// value board (mode-independent)
const vbRows=[...T].filter(t=>t.modes.blend.champion>=0.003).sort((a,b)=>b.ev_blend-a.ev_blend);
document.querySelector('#valueTable tbody').innerHTML = vbRows.map(t=>{
  const v=t.ev_blend>0.08?'<span class="verdict v-val">VALUE</span>':(t.ev_blend>-0.12?'<span class="verdict v-fair">FAIR</span>':'<span class="verdict v-avoid">AVOID</span>');
  return `<tr><td class="tname">${t.team}</td><td>${am(t.odds_decimal)}</td>
    <td>${pct(t.modes.pure.champion)}</td><td><b>${pct(t.modes.blend.champion)}</b></td><td>${pct(t.market_implied)}</td>
    <td class="${t.ev_pure>=0?'pos':'neg'}">${t.ev_pure>=0?'+':'−'}$${Math.abs(t.ev_pure).toFixed(2)}</td>
    <td class="${t.ev_blend>=0?'pos':'neg'}">${t.ev_blend>=0?'+':'−'}$${Math.abs(t.ev_blend).toFixed(2)}</td>
    <td>${t.kelly_blend>0?pct(t.kelly_blend/4,2):'—'}</td><td>${v}</td></tr>`;
}).join('');

// main table
let sortK='champion', sortDir=-1;
function val(t,k){
  if(k==='team'||k==='elo'||k==='offset'||k==='odds_decimal') return t[k];
  if(k==='edge') return P(t,'champion')-t.market_implied;
  if(k==='ev') return P(t,'champion')*t.odds_decimal-1;
  return P(t,k);
}
function renderMain(){
  const rows=[...T].sort((a,b)=>{
    const x=val(a,sortK),y=val(b,sortK);
    return (typeof x==='string'? x.localeCompare(y):x-y)*sortDir;
  });
  document.querySelector('#mainTable tbody').innerHTML = rows.map(t=>{
    const edge=P(t,'champion')-t.market_implied, ev=P(t,'champion')*t.odds_decimal-1;
    const adj=t.calibrated?`<span class="${t.offset>=0?'pos':'neg'}">${t.offset>=0?'+':'−'}${Math.abs(t.offset).toFixed(0)}</span>`:'<span style="color:#3d4866">—</span>';
    return `<tr><td class="tname"><span class="gtag">${t.group}</span>${t.team}</td><td>${t.elo}</td><td>${adj}</td>
    <td>${pct(P(t,'group_win'))}</td><td>${pct(P(t,'r32'))}</td><td>${pct(P(t,'r16'))}</td>
    <td>${pct(P(t,'qf'))}</td><td>${pct(P(t,'sf'))}</td><td>${pct(P(t,'final'))}</td>
    <td><span class="bar" style="width:${Math.max(2,P(t,'champion')*220)}px"></span><b>${pct(P(t,'champion'))}</b></td>
    <td>${am(t.odds_decimal)}</td>
    <td class="${edge>=0?'pos':'neg'}">${edge>=0?'+':'−'}${pct(Math.abs(edge))}</td>
    <td class="${ev>=0?'pos':'neg'}">${ev>=0?'+':'−'}$${Math.abs(ev).toFixed(2)}</td></tr>`;
  }).join('');
  document.querySelectorAll('#mainTable th').forEach(th=>th.classList.toggle('sorted',th.dataset.k===sortK));
}
document.querySelectorAll('#mainTable th').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k;
  if(k===sortK) sortDir*=-1; else {sortK=k; sortDir=k==='team'?1:-1;}
  renderMain();
});

function renderGroups(){
  // live standings from locked results
  const ST={};
  DATA.matches.forEach(m=>{
    if(!m.played)return;
    const s=ST[m.group]=ST[m.group]||{};
    s[m.home]=s[m.home]||{p:0,gd:0,n:0}; s[m.away]=s[m.away]||{p:0,gd:0,n:0};
    const[hg,ag]=m.played;
    s[m.home].gd+=hg-ag; s[m.away].gd+=ag-hg; s[m.home].n++; s[m.away].n++;
    if(hg>ag)s[m.home].p+=3; else if(ag>hg)s[m.away].p+=3; else {s[m.home].p++; s[m.away].p++;}
  });
  const byG={};
  T.forEach(t=>{(byG[t.group]=byG[t.group]||[]).push(t)});
  document.getElementById('groups').innerHTML = Object.keys(byG).sort().map(g=>{
    const live=ST[g];
    const sorted=byG[g].sort((a,b)=>{
      if(live){
        const sa=live[a.team]||{p:0,gd:0}, sb=live[b.team]||{p:0,gd:0};
        if(sb.p!==sa.p)return sb.p-sa.p;
        if(sb.gd!==sa.gd)return sb.gd-sa.gd;
      }
      return P(b,'r32')-P(a,'r32');
    });
    const rows=sorted.map(t=>{
      const st=live&&live[t.team];
      const chip=st?`<span class="ptschip">${st.p} pt${st.p!==1?'s':''} · ${st.gd>=0?'+':''}${st.gd}</span>`:'';
      return `<div class="grow"><span class="nm">${t.team}</span>${chip}
      <span class="gbar"><i style="width:${(P(t,'r32')*100).toFixed(1)}%"></i></span>
      <span class="pct">${pct(P(t,'r32'))} · win ${pct(P(t,'group_win'),0)}</span></div>`;
    }).join('');
    return `<div class="card gcard"><h3>GROUP ${g}${live?' <span style="color:#5a6580;font-weight:400;font-size:11px">— live table</span>':''}</h3>${rows}</div>`;
  }).join('');
}

// staleness: finished matches (kickoff + 125 min elapsed) not yet locked into the model
function staleCheck(nowMs){
  return DATA.matches.filter(m=>!m.played &&
    new Date(m.utc.replace(' ','T')).getTime()+125*60000 < nowMs).length;
}
window._staleCheck=staleCheck;
(function(){
  const n=staleCheck(Date.now());
  const el=document.getElementById('staleBanner');
  if(n>0){
    el.className='stale on';
    el.innerHTML=`⏳ <b>${n} match${n>1?'es have':' has'} finished since this dashboard was built</b> — probabilities below don't include ${n>1?'them':'it'} yet. Run <code>python3 update.py</code>, or keep <code>python3 update.py --watch</code> running for automatic per-match rebuilds.`;
  }
})();

document.querySelectorAll('#modeSeg button').forEach(b=>b.onclick=()=>{
  MODE=b.dataset.m;
  document.querySelectorAll('#modeSeg button').forEach(x=>x.classList.toggle('active',x===b));
  render();
});
render();
</script>
</body>
</html>"""

import os
html = HTML.replace("__DATA__", DATA_JS)
with open("wc2026_dashboard.html", "w") as f:
    f.write(html)
os.makedirs("docs", exist_ok=True)          # GitHub Pages serves /docs
with open("docs/index.html", "w") as f:
    f.write(html)
print(f"Dashboard written: {len(html):,} bytes (+ docs/index.html for Pages)")
