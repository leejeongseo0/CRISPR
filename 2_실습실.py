# pages/2_lab.py  (파일명을 pages/2_실습실.py 처럼 바꿔도 됩니다)
# CRISPR-Cas9 유전자 편집 실습실 - 중학생도 따라 할 수 있는 단계별 실습
#
# SyntaxError 방지 설계
#  - HTML/CSS/JS 는 f-string 이 아닌 "일반 문자열" 상수(LAB_HTML)로 둔다. (중괄호 이스케이프 불필요)
#  - 파이썬 데이터는 __CONFIG__ 자리표시자 하나만 JSON 으로 치환해서 넘긴다.

import json
import random

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="유전자 편집 실습실", page_icon="🧬", layout="wide")

# ---------------------------------------------------------------------------
# 1) 1페이지에서 넘어온 gRNA 정보 읽기
# ---------------------------------------------------------------------------
DEMO_SPACER = "CTTGCCCCACAGGGCAGTAA"  # 선택값이 없을 때 쓰는 예시 서열


def _clean(seq):
    s = str(seq).upper().replace("U", "T")
    return "".join(c for c in s if c in "ACGT")


def _to_dict(sel):
    if sel is None:
        return {}
    if isinstance(sel, dict):
        return sel
    if hasattr(sel, "to_dict"):  # pandas Series 등
        try:
            return sel.to_dict()
        except Exception:
            return {}
    if isinstance(sel, str):
        return {"sequence": sel}
    return {}


def _find_number(d, key_part):
    for k, v in d.items():
        if key_part in str(k).lower():
            try:
                return round(float(v), 3)
            except (TypeError, ValueError):
                return None
    return None


def build_config():
    d = _to_dict(st.session_state.get("selected_top_grna"))
    spacer, pam, demo = "", "", False

    for cand in ("grna", "guide", "spacer", "sequence", "seq"):
        for k, v in d.items():
            if cand in str(k).lower() and isinstance(v, str):
                s = _clean(v)
                if len(s) >= 20:
                    spacer = s[:20]
                    if len(s) >= 23 and s[21:23] == "GG":
                        pam = s[20:23]
                    break
        if spacer:
            break

    if not spacer:
        spacer, demo = DEMO_SPACER, True

    # 1페이지(NCBI 모드)에서 넘어온 실제 서열 정보
    if not pam:
        p = _clean(d.get("PAM", ""))
        if len(p) == 3 and p[1:] == "GG":
            pam = p
    left = _clean(d.get("left", ""))
    right = _clean(d.get("right", ""))
    real = (not demo) and len(left) == 8 and len(right) == 6 and len(pam) == 3
    if not real:
        left, right = "", ""

    gene = ""
    for k, v in d.items():
        if "gene" in str(k).lower():
            gene = str(v)
            break

    # 새로고침(rerun)할 때마다 DNA 주변 서열이 바뀌면 실습이 초기화되므로 seed 는 고정
    if "lab_seed" not in st.session_state:
        st.session_state["lab_seed"] = random.randint(1, 10**6)

    return {
        "spacer": spacer,
        "pam": pam,
        "gene": gene or "예시 유전자",
        "mit": _find_number(d, "mit"),
        "doench": _find_number(d, "doench"),
        "demo": demo,
        "real": real,
        "left": left,
        "right": right,
        "accession": str(d.get("accession", "")),
        "strand": str(d.get("strand", "")),
        "start": d.get("start") if isinstance(d.get("start"), (int, float)) else None,
        "end": d.get("end") if isinstance(d.get("end"), (int, float)) else None,
        "seed": st.session_state["lab_seed"],
    }


# ---------------------------------------------------------------------------
# 2) 실습 본체 (일반 문자열: 중괄호 자유롭게 사용 가능)
# ---------------------------------------------------------------------------
LAB_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{
  --bg:#0d1b26; --panel:#14293a; --ink:#e8f1f5; --mute:#8fa6b5; --line:#2a4259;
  --rna:#ff9a2e; --cas:#3ddc84; --dna1:#6fb8ff; --bad:#ff5d6c; --gold:#ffe14d;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--bg); color:var(--ink); padding:14px 16px 20px; border-radius:14px;
  font-family:"Pretendard","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
h1{font-size:20px;margin:0;font-weight:700}
.tgt{font-size:13px;color:var(--mute)}
.tgt b{color:var(--rna);font-family:ui-monospace,Consolas,"D2Coding",monospace;font-weight:600}

#steps{list-style:none;display:flex;flex-wrap:wrap;gap:6px;padding:0;margin:12px 0;counter-reset:s}
#steps li{counter-increment:s;flex:1 1 112px;padding:7px 9px;border:1px solid var(--line);
  border-radius:8px;font-size:12.5px;color:var(--mute);transition:all .3s}
#steps li::before{content:counter(s) ". "}
#steps li.active{border-color:var(--rna);color:var(--ink);background:#1b3248}
#steps li.done{border-color:var(--cas);color:var(--cas)}

.row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
#msg{min-height:46px;padding:10px 12px;border-radius:8px;background:var(--panel);
  font-size:14px;line-height:1.55;margin-bottom:8px;border-left:4px solid var(--dna1)}
#msg.bad{border-left-color:var(--bad)}
#msg.good{border-left-color:var(--cas)}

#explain{display:none;background:#112636;border:1px solid var(--line);border-radius:10px;
  padding:12px 16px;margin-bottom:10px}
#explain h3{margin:0 0 6px;font-size:16px}
#explain h3.sub{margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
#explain p{margin:6px 0;font-size:14px;line-height:1.7}
#explain .real{color:#bcd3e0}

svg{width:100%;height:auto;display:block;border-radius:12px;background:#0a1620;touch-action:none;user-select:none}
.lt{font-family:ui-monospace,Consolas,"D2Coding",monospace;font-weight:700;font-size:13px;fill:#0b1620;pointer-events:none}
.cap{font-size:12px;fill:#8fa6b5}

.base{transition:transform .7s cubic-bezier(.3,1.5,.5,1)}
.base .t{transition:transform .8s cubic-bezier(.3,1.4,.5,1)}
.base .r{opacity:0;transition:opacity .6s .25s}
.base.open .t{transform:translateY(-46px)}
.base.open .r{opacity:1}
.base.left{transform:translateX(-16px)}
.base.right{transform:translateX(16px)}
.finding .base .t{cursor:pointer}
.finding .base .t:hover rect{stroke:#ffffff;stroke-width:2}

.drag{cursor:grab}
.grab{cursor:grabbing}
.glow{filter:drop-shadow(0 0 12px #3ddc84)}
.pulse{animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.4}}
.burst{transform-box:fill-box;transform-origin:center;animation:burst .9s ease-out forwards}
@keyframes burst{from{transform:scale(.1);opacity:1}to{transform:scale(1);opacity:0}}
.shake{animation:shake .4s}
@keyframes shake{25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.fx{animation:fx 1.5s forwards}
@keyframes fx{0%{opacity:0}20%{opacity:1}80%{opacity:1}100%{opacity:0}}

#ctrl{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.btn{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:9px 14px;
  border-radius:8px;font-size:14px;cursor:pointer;font-family:inherit}
.btn:hover{border-color:var(--dna1)}
.btn:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.btn.main{background:var(--rna);border-color:var(--rna);color:#2a1700;font-weight:700}
.btn.help{border-color:#4aa8a0;color:#9fe3dc}

#result{margin-top:12px}
#result .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
#result h2{margin:0 0 8px;font-size:17px}
#result p{margin:6px 0;font-size:14px;line-height:1.65}
.seq{font-family:ui-monospace,Consolas,"D2Coding",monospace;font-size:14px;letter-spacing:1px;
  background:#0a1620;border-radius:6px;padding:8px 10px;overflow-x:auto;white-space:nowrap}
.seq .m{background:var(--rna);color:#2a1700;border-radius:2px}
.seq .del{background:var(--bad);color:#2a0008;border-radius:2px}
.lbl{font-size:12px;color:var(--mute);margin-top:8px}

@media (prefers-reduced-motion: reduce){
  .base,.base .t,.base .r{transition:none}
  .pulse,.burst,.shake,.fx{animation:none}
}
</style>
</head>
<body>
<header>
  <h1>유전자 편집 실습실</h1>
  <div class="tgt" id="tgt"></div>
</header>

<ol id="steps">
  <li>표적 찾기</li>
  <li>RNP 만들기</li>
  <li>세포 안으로 전달</li>
  <li>표적 결합</li>
  <li>DNA 절단</li>
  <li>세포의 수리</li>
  <li>결과 확인</li>
</ol>

<div class="row">
  <button class="btn help" id="btnExplain">📖 이 단계 설명 보기</button>
  <button class="btn help" id="btnAll">🗂 전체 과정 한눈에 보기</button>
</div>
<div id="explain"></div>

<div id="msg"></div>

<svg id="stage" viewBox="0 0 900 600" role="img" aria-label="유전자 편집 실습 화면">
  <defs>
    <radialGradient id="casG" cx="50%" cy="40%" r="70%">
      <stop offset="0" stop-color="#4be59a"/>
      <stop offset="1" stop-color="#1c8f56"/>
    </radialGradient>
    <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.2" fill="#16303f"/>
    </pattern>
  </defs>
</svg>

<div id="ctrl"></div>
<div id="result"></div>

<script>
(function(){
"use strict";
var CFG = __CONFIG__;

/* =====================================================================
   설명글 (중학생 눈높이 + 실제 실험 방법)
   ===================================================================== */
var EXPLAIN = [
  {
    t: "1단계. 고칠 곳(표적) 찾기",
    easy: "유전자는 A, T, G, C 네 글자로 쓰인 아주 긴 글이에요. 책에서 틀린 글자를 고치려면 먼저 그 쪽수와 줄을 찾아야 하죠. 유전자 편집도 같아요. gRNA에 적힌 20글자와 똑같은 곳을 DNA에서 찾고, 그 바로 뒤에 N-G-G(아무 글자 하나 + GG)가 있는지 확인합니다. 이 NGG를 PAM이라고 부르고, Cas9가 가위질을 시작하는 신호 역할을 해요.",
    real: "연구자는 컴퓨터 프로그램으로 표적 주변의 PAM을 모두 찾고, 후보 gRNA를 여러 개 설계합니다. 이때 엉뚱한 곳을 자를 위험(오프타깃)이 낮은지(MIT 점수), 표적을 잘 자르는지(Doench 점수)를 비교해 가장 좋은 gRNA를 고릅니다. 1페이지의 스크리닝이 바로 이 과정이에요."
  },
  {
    t: "2단계. Cas9와 gRNA를 합쳐 RNP 만들기",
    easy: "Cas9는 DNA를 자르는 가위 단백질이고, gRNA는 어디를 자를지 알려 주는 길잡이(내비게이션)예요. 가위 혼자서는 어디를 잘라야 할지 모르고, 길잡이 혼자서는 자를 수 없어요. 둘이 합쳐진 덩어리를 RNP(리보핵산단백질 복합체)라고 해요. RNA에서는 T 대신 U가 쓰이는 점도 기억해 두세요.",
    real: "정제한 Cas9 단백질과 합성한 gRNA를 시험관에서 섞고 실온에서 10~20분 정도 두면 RNP가 만들어집니다. 이렇게 미리 조립한 RNP를 쓰면 세포 안에서 빨리 작동하고 금방 분해되어, 엉뚱한 곳을 자를 가능성이 줄어드는 장점이 있습니다."
  },
  {
    t: "3단계. RNP를 세포 안으로 전달하기",
    easy: "세포는 얇은 막으로 둘러싸여 있어서 RNP가 저절로 들어가지 못해요. 문이 닫힌 집에 택배를 넣어 주는 것과 비슷해서, 들여보내는 방법이 따로 필요합니다. 세포 안에 들어온 Cas9는 몸에 붙어 있는 핵 신호(NLS, 핵으로 들어가는 출입증) 덕분에 DNA가 있는 핵 안까지 들어갈 수 있어요.",
    real: "전기천공(짧은 전기 자극으로 막에 잠깐 구멍을 냄), 리포펙션(지방 방울로 감싸 막과 합침), 미세주입(아주 가는 유리 바늘로 직접 넣음) 같은 방법을 씁니다. 몸속에서 치료할 때는 무해하게 만든 바이러스(AAV 등)에 실어 보내는 연구도 있어요."
  },
  {
    t: "4단계. 표적에 결합하기",
    easy: "Cas9는 DNA 위를 돌아다니며 PAM(NGG)부터 찾아요. PAM을 만나면 멈춰서 DNA 두 가닥을 살짝 풀고, 그 틈에서 gRNA가 아래 가닥과 글자가 맞는지 하나씩 확인해요. A-T, G-C처럼 짝이 맞으면 단단히 붙고, 많이 틀리면 떨어져 나가요. 그래서 PAM과 20글자가 둘 다 맞는 곳에만 결합합니다.",
    real: "풀린 DNA 가닥과 gRNA가 짝을 이룬 구조를 R-loop라고 합니다. 글자가 한두 개 틀려도 붙는 경우가 있는데, 이것이 원하지 않는 곳이 잘리는 오프타깃의 원인이에요. 그래서 gRNA를 고를 때 비슷한 서열이 게놈에 또 있는지 꼭 확인합니다."
  },
  {
    t: "5단계. DNA 자르기",
    easy: "결합이 끝나면 Cas9의 가위 부위 두 곳(HNH와 RuvC)이 DNA 두 가닥을 각각 잘라요. 위치는 PAM에서 3글자 앞이에요. 두 가닥이 모두 끊어진 것을 이중가닥절단(DSB)이라고 합니다. 세포 입장에서는 DNA가 끊어진 비상 상황이라서 곧바로 고치기 시작해요.",
    real: "SpCas9는 대부분 두 가닥을 같은 자리에서 끊어 평평한 끝(평활 말단)을 만듭니다. 이 단계까지는 DNA를 자르기만 했을 뿐, 어떻게 바뀌는지는 이어지는 세포의 수리 방식이 결정해요."
  },
  {
    t: "6단계. 세포의 수리 (NHEJ 또는 HDR)",
    easy: "끊어진 DNA는 세포가 스스로 고쳐요. NHEJ는 끊어진 두 끝을 급하게 이어 붙이는 방법이라, 그 과정에서 글자가 끼어들거나 빠지는 실수가 잘 생겨요. 이 실수 때문에 유전자가 제대로 읽히지 않으면 유전자 기능이 꺼집니다(녹아웃). HDR는 우리가 설계도(도너 DNA)를 함께 주면 그대로 베껴서 정확하게 고쳐 써요. 책의 틀린 글자를 지우개로 지우고 정답을 써 넣는 것과 비슷합니다.",
    real: "세포가 분열을 준비하는 시기에 주로 일어나는 HDR는 NHEJ보다 효율이 훨씬 낮은 편이에요. 또 같은 시험관 속 세포라도 세포마다 수리 결과가 달라서, 실제로는 여러 종류의 결과가 섞여 나옵니다."
  },
  {
    t: "7단계. 편집이 잘 됐는지 확인하기",
    easy: "DNA 글자 하나가 바뀐 것은 눈으로 볼 수 없어요. 그래서 표적 부위의 DNA를 PCR로 아주 많이 복사한 다음, 글자를 하나씩 읽어(시퀀싱) 원래 서열과 비교합니다. 이렇게 해야 편집이 일어났는지, 어떻게 바뀌었는지 알 수 있어요.",
    real: "샌거 시퀀싱이나 차세대 시퀀싱(NGS)으로 편집된 세포의 비율(편집 효율)을 계산합니다. 안전성을 위해 오프타깃으로 예상되는 다른 위치도 함께 읽어서 원치 않는 변화가 없는지 검사해요."
  }
];

/* =====================================================================
   기본 상수
   ===================================================================== */
var NS = "http://www.w3.org/2000/svg";
var svg = document.getElementById("stage");
var msgEl = document.getElementById("msg");
var ctrl = document.getElementById("ctrl");
var resEl = document.getElementById("result");
var explainEl = document.getElementById("explain");
var btnExplain = document.getElementById("btnExplain");
var btnAll = document.getElementById("btnAll");
var stepEls = Array.prototype.slice.call(document.querySelectorAll("#steps li"));

var W = 900;
var DX = 22;
var YT = 450, YB = 492;          // 위/아래 가닥 y
var FL = 8, FR = 6;              // 표적 앞/뒤 여분 서열 길이
var PAM_START = FL + 20;         // 28
var CUT_AFTER = FL + 16;         // 24: 이 인덱스까지 왼쪽, 다음부터 오른쪽
var MEMBRANE_Y = 170;
var NUC_TOP = 270;

var GR_HOME = {x: 150, y: 92};
var CAS_HOME = {x: 690, y: 92};
var CAS_IN = {x: 450, y: 226};   // 세포 안(세포질) 위치
var CAS_BOUND_Y = 332;
var CAS_SCALE = 0.8, GR_SCALE = 0.85;

var COMP = {A: "T", T: "A", G: "C", C: "G"};
var COLORS = {A: "#ff8fa3", T: "#ffd166", G: "#67e3a5", C: "#74c0ff"};

/* ---------- 서열 만들기 ---------- */
function hashStr(s){
  var h = 2166136261;
  for (var i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function mulberry(a){
  return function(){
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
var rnd = mulberry(hashStr(CFG.spacer) ^ CFG.seed);
function randBase(){ return "ACGT".charAt(Math.floor(rnd() * 4)); }
function randSeq(n){ var s = ""; for (var i = 0; i < n; i++) s += randBase(); return s; }

var SP = CFG.spacer;
var PAM = (CFG.pam && CFG.pam.length === 3) ? CFG.pam : (randBase() + "GG");
var REAL = !!(CFG.real && CFG.left && CFG.right && CFG.left.length === FL && CFG.right.length === FR);
var LEFT = REAL ? CFG.left : randSeq(FL);
var RIGHT = REAL ? CFG.right : randSeq(FR);
var FULL = LEFT + SP + PAM + RIGHT;
var N = FULL.length;
var X0 = (W - N * DX) / 2;
var TARGET_X = X0 + (FL + 11.5) * DX;
var CUT_X = X0 + (CUT_AFTER + 1) * DX;

/* ---------- 도우미 ---------- */
function el(name, attrs, parent){
  var e = document.createElementNS(NS, name);
  for (var k in attrs){ if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]); }
  if (parent) parent.appendChild(e);
  return e;
}
function svgPt(ev){
  var p = svg.createSVGPoint();
  p.x = ev.clientX; p.y = ev.clientY;
  return p.matrixTransform(svg.getScreenCTM().inverse());
}
function setPos(g, x, y){
  g._x = x; g._y = y;
  g.setAttribute("transform", "translate(" + x + " " + y + ") scale(" + (g._s || 1) + ")");
}
function tween(g, x, y, ms, cb){
  var x0 = g._x, y0 = g._y, t0 = performance.now();
  function f(t){
    var k = Math.min(1, (t - t0) / ms);
    var e = 1 - Math.pow(1 - k, 3);
    setPos(g, x0 + (x - x0) * e, y0 + (y - y0) * e);
    if (k < 1) requestAnimationFrame(f); else if (cb) cb();
  }
  requestAnimationFrame(f);
}
function clamp(v, a, b){ return Math.max(a, Math.min(b, v)); }
function dist(a, b){ return Math.hypot(a._x - b._x, a._y - b._y); }
function shake(node){
  node.classList.remove("shake");
  void node.getBoundingClientRect();
  node.classList.add("shake");
  setTimeout(function(){ node.classList.remove("shake"); }, 450);
}
function removeLater(node, ms){
  setTimeout(function(){ if (node.parentNode) node.parentNode.removeChild(node); }, ms);
}

/* ---------- 상태 ---------- */
var state, penalty, cur = 0, pending = null;
var cas, gr, gDNA, cutLine, hintEl, protoBox, pamBox, pamLbl, scanner, banner, bases;
var explainMode = "";   // "", "step", "all"

function setMsg(t, kind){ msgEl.textContent = t; msgEl.className = kind || ""; }
function setStep(k){
  cur = k;
  stepEls.forEach(function(li, i){
    li.className = i < k ? "done" : (i === k ? "active" : "");
  });
  renderExplain();
}
function setCtrl(list){
  ctrl.innerHTML = "";
  list.forEach(function(b){
    var x = document.createElement("button");
    x.className = "btn " + (b.cls || "");
    x.textContent = b.label;
    x.onclick = b.fn;
    ctrl.appendChild(x);
  });
}

/* ---------- 설명 패널 ---------- */
function renderExplain(){
  if (explainMode === ""){
    explainEl.style.display = "none";
    btnExplain.textContent = "📖 이 단계 설명 보기";
    btnAll.textContent = "🗂 전체 과정 한눈에 보기";
    return;
  }
  var html = "";
  if (explainMode === "step"){
    var e = EXPLAIN[Math.min(cur, EXPLAIN.length - 1)];
    html = "<h3>" + e.t + "</h3><p>" + e.easy + "</p><p class='real'><b>실제 실험에서는</b> " + e.real + "</p>";
    btnExplain.textContent = "📖 설명 닫기";
    btnAll.textContent = "🗂 전체 과정 한눈에 보기";
  } else {
    EXPLAIN.forEach(function(e, i){
      html += "<h3" + (i ? " class='sub'" : "") + ">" + e.t + "</h3><p>" + e.easy +
              "</p><p class='real'><b>실제 실험에서는</b> " + e.real + "</p>";
    });
    btnExplain.textContent = "📖 이 단계 설명 보기";
    btnAll.textContent = "🗂 전체 설명 닫기";
  }
  explainEl.innerHTML = html;
  explainEl.style.display = "block";
}
btnExplain.addEventListener("click", function(){
  explainMode = (explainMode === "step") ? "" : "step";
  renderExplain();
});
btnAll.addEventListener("click", function(){
  explainMode = (explainMode === "all") ? "" : "all";
  renderExplain();
});

/* ---------- 타일(염기 글자 블록) ---------- */
function tile(parent, cls, cx, cy, ch, fill){
  var g = el("g", {"class": cls}, parent);
  el("rect", {x: cx - 9.5, y: cy - 11, width: 19, height: 22, rx: 4, fill: fill}, g);
  var t = el("text", {x: cx, y: cy + 4.5, "text-anchor": "middle", "class": "lt"}, g);
  t.textContent = ch;
  return g;
}

/* =====================================================================
   장면 만들기
   ===================================================================== */
function build(){
  Array.prototype.slice.call(svg.children).forEach(function(c){
    if (c.tagName.toLowerCase() !== "defs") svg.removeChild(c);
  });
  state = "find"; penalty = 0; bases = []; pending = null;
  resEl.innerHTML = "";
  svg.classList.add("finding");

  var tg = document.getElementById("tgt");
  tg.innerHTML = "";
  tg.appendChild(document.createTextNode("표적 유전자: " + CFG.gene + " · gRNA "));
  var b = document.createElement("b"); b.textContent = SP; tg.appendChild(b);
  var extra = "";
  if (CFG.mit !== null && CFG.mit !== undefined) extra += " · MIT " + CFG.mit;
  if (CFG.doench !== null && CFG.doench !== undefined) extra += " · Doench " + CFG.doench;
  if (CFG.demo) extra += " (예시 서열)";
  if (REAL) extra += " · NCBI " + CFG.accession + " " + CFG.start + "-" + CFG.end + (CFG.strand === "-" ? " (반대 가닥)" : " (코딩 가닥)");
  tg.appendChild(document.createTextNode(extra));

  // 배경: 세포 밖 / 세포 / 핵
  el("rect", {x: 0, y: 0, width: 900, height: 600, fill: "url(#dots)"}, svg);
  var t0 = el("text", {x: 24, y: 28, "class": "cap"}, svg); t0.textContent = "세포 밖 (시험관 속 용액)";
  el("rect", {x: 6, y: MEMBRANE_Y, width: 888, height: 424, rx: 26, fill: "#0e2230", stroke: "#5aa6c9", "stroke-width": 3}, svg);
  el("rect", {x: 12, y: MEMBRANE_Y + 6, width: 876, height: 412, rx: 22, fill: "none", stroke: "#3a7391",
    "stroke-width": 1.5, "stroke-dasharray": "3 4"}, svg);
  var t1 = el("text", {x: 880, y: MEMBRANE_Y - 6, "text-anchor": "end", "class": "cap"}, svg); t1.textContent = "세포막";
  var t2 = el("text", {x: 28, y: MEMBRANE_Y + 30, "class": "cap"}, svg); t2.textContent = "세포 안 (세포질)";
  el("rect", {x: 14, y: NUC_TOP, width: 872, height: 312, rx: 22, fill: "#0f2c3d", stroke: "#4aa8a0",
    "stroke-width": 2, "stroke-dasharray": "8 5"}, svg);
  var t3 = el("text", {x: 30, y: NUC_TOP + 24, "class": "cap"}, svg);
  t3.textContent = REAL
    ? "세포핵 · " + CFG.gene + " 실제 서열 (NCBI " + CFG.accession + ", " + CFG.start + "-" + CFG.end + ")"
    : "세포핵 · DNA (" + CFG.gene + ", 주변 서열은 가상)";

  // DNA
  gDNA = el("g", {}, svg);
  var t5 = el("text", {x: X0 - 8, y: YT + 4, "text-anchor": "end", "class": "cap"}, gDNA); t5.textContent = "5'";
  var t3b = el("text", {x: X0 + N * DX + 8, y: YT + 4, "class": "cap"}, gDNA); t3b.textContent = "3'";
  var b3 = el("text", {x: X0 - 8, y: YB + 4, "text-anchor": "end", "class": "cap"}, gDNA); b3.textContent = "3'";
  var b5 = el("text", {x: X0 + N * DX + 8, y: YB + 4, "class": "cap"}, gDNA); b5.textContent = "5'";

  for (var i = 0; i < N; i++){
    var cx = X0 + (i + 0.5) * DX;
    var ch = FULL.charAt(i);
    var g = el("g", {"class": "base"}, gDNA);
    el("line", {x1: cx, x2: cx, y1: YT + 11, y2: YB - 11, stroke: "#3b5a75", "stroke-width": 2}, g);
    tile(g, "b", cx, YB, COMP[ch], COLORS[COMP[ch]]);
    var tt = tile(g, "t", cx, YT, ch, COLORS[ch]);
    if (i >= FL && i < FL + 20){
      tile(g, "r", cx, YT, ch === "T" ? "U" : ch, "#ff9a2e");
    }
    bases.push(g);
  }

  // 표적(20 nt) 상자 - 찾기 전에는 숨김
  protoBox = el("rect", {x: X0 + FL * DX + 1, y: YT - 18, width: 20 * DX - 2, height: 36, rx: 8, fill: "none",
    stroke: "#3ddc84", "stroke-width": 2.5, opacity: 0}, gDNA);
  var pcx = X0 + (PAM_START + 1.5) * DX;
  pamBox = el("rect", {x: X0 + PAM_START * DX + 1, y: YT - 18, width: 3 * DX - 2, height: 36, rx: 8, fill: "none",
    stroke: "#ff9a2e", "stroke-width": 2.5, "stroke-dasharray": "4 3", opacity: 0}, gDNA);
  pamLbl = el("text", {x: pcx, y: YT - 28, "text-anchor": "middle", "class": "cap", opacity: 0}, gDNA);
  pamLbl.setAttribute("style", "fill:#ff9a2e");
  pamLbl.textContent = "PAM (NGG)";

  var bx1 = X0 + FL * DX + 2, bx2 = X0 + (FL + 20) * DX - 2;
  el("path", {d: "M" + bx1 + " " + (YB + 24) + " v6 H" + bx2 + " v-6", fill: "none", stroke: "#4c6f8a", "stroke-width": 1.5}, gDNA);
  var bt = el("text", {x: (bx1 + bx2) / 2, y: YB + 48, "text-anchor": "middle", "class": "cap"}, gDNA);
  bt.textContent = "gRNA와 짝이 맞는 표적 서열 (20글자)";

  // 찾기 단계 안내판
  banner = el("g", {}, svg);
  el("rect", {x: 130, y: 308, width: 640, height: 62, rx: 12, fill: "#1b3248", stroke: "#3b5a75"}, banner);
  var bn1 = el("text", {x: 450, y: 331, "text-anchor": "middle", "class": "cap"}, banner);
  bn1.textContent = "찾을 서열 (gRNA와 똑같은 20글자)";
  var bn2 = el("text", {x: 450, y: 357, "text-anchor": "middle", "font-size": 20, "font-weight": 700, fill: "#ffb85c",
    "font-family": "ui-monospace,Consolas,monospace", "letter-spacing": 2}, banner);
  bn2.textContent = SP;

  // 절단선, 힌트, 스캐너
  cutLine = el("line", {x1: CUT_X, x2: CUT_X, y1: YT - 64, y2: YB + 18, stroke: "#ffe14d",
    "stroke-width": 3, "stroke-dasharray": "6 4", opacity: 0}, svg);
  hintEl = el("ellipse", {cx: TARGET_X, cy: CAS_BOUND_Y, rx: 112, ry: 56, fill: "none", stroke: "#3ddc84",
    "stroke-width": 2, "stroke-dasharray": "8 6", visibility: "hidden", "class": "pulse"}, svg);
  scanner = el("line", {x1: 0, x2: 0, y1: 0, y2: 0, stroke: "#3ddc84", "stroke-width": 2,
    "stroke-dasharray": "3 4", opacity: 0}, svg);

  cas = makeCas9();
  gr = makeGRNA();
  [protoBox, pamBox, pamLbl, hintEl, scanner, cutLine, banner].forEach(function(n){ n.style.pointerEvents = "none"; });

  setStep(0);
  setMsg("아래 DNA에서 위쪽 «찾을 서열»과 똑같은 20글자 구간을 찾아, 그 구간의 글자 아무거나 하나를 클릭하세요.");
  setCtrl([{label: "힌트", fn: hint}]);
}

/* ---------- Cas9 (초록 가위) ---------- */
function makeCas9(){
  var g = el("g", {"class": "drag"}, svg);
  g._s = CAS_SCALE;
  var inner = el("g", {}, g);
  el("ellipse", {cx: 0, cy: 0, rx: 130, ry: 64, fill: "url(#casG)", stroke: "#1f9e5c", "stroke-width": 2}, inner);
  el("ellipse", {cx: -62, cy: -20, rx: 66, ry: 46, fill: "#2fbf74", opacity: 0.85}, inner);
  el("ellipse", {cx: 70, cy: 12, rx: 58, ry: 40, fill: "#59e79b", opacity: 0.7}, inner);
  var guide = el("path", {d: "M-100 26 C -70 0, -50 52, -20 26 S 30 0, 60 26 S 90 44, 104 22",
    fill: "none", stroke: "#ff9a2e", "stroke-width": 6, "stroke-linecap": "round", opacity: 0}, inner);
  var t1 = el("text", {x: 0, y: -8, "text-anchor": "middle", "font-size": 24, "font-weight": 800, fill: "#06301b"}, inner);
  t1.textContent = "Cas9";
  var t2 = el("text", {x: 0, y: 54, "text-anchor": "middle", "font-size": 14, "font-weight": 700, fill: "#06301b", opacity: 0}, inner);
  t2.textContent = "RNP (Cas9 + gRNA)";
  g._inner = inner; g._guide = guide; g._tag = t2;
  setPos(g, CAS_HOME.x, CAS_HOME.y);
  attachDrag(g, {
    can: function(){ return state === "dock"; },
    denied: function(){
      if (state === "cut"){ doCut(); return; }
      var m = {
        find: "먼저 DNA에서 표적 서열을 찾아야 합니다.",
        merge: "먼저 gRNA를 Cas9에 결합시켜 RNP를 만드세요.",
        deliver: "RNP가 아직 세포 밖에 있어요. 아래에서 전달 방법을 골라 세포 안으로 넣어 주세요."
      }[state];
      if (m){ setMsg(m, "bad"); shake(g._inner); }
    },
    move: function(x, y){
      var inNuc = y > 300;
      scanner.setAttribute("x1", x); scanner.setAttribute("x2", x);
      scanner.setAttribute("y1", y + 52); scanner.setAttribute("y2", YT - 18);
      scanner.setAttribute("opacity", inNuc ? 0.7 : 0);
    },
    drop: onCasDrop
  });
  return g;
}

/* ---------- gRNA (주황 길잡이) ---------- */
function makeGRNA(){
  var g = el("g", {"class": "drag"}, svg);
  g._s = GR_SCALE;
  el("rect", {x: -100, y: -44, width: 220, height: 92, fill: "transparent"}, g);
  el("path", {d: "M-80 0 H 10", stroke: "#ff9a2e", "stroke-width": 9, "stroke-linecap": "round", fill: "none"}, g);
  for (var i = 0; i < 6; i++){
    el("circle", {cx: -70 + i * 13, cy: 0, r: 2.6, fill: "#2a1700"}, g);
  }
  el("path", {d: "M10 0 C 25 -30, 45 30, 60 0 S 92 -30, 104 0", fill: "none", stroke: "#ffc27a",
    "stroke-width": 6, "stroke-linecap": "round"}, g);
  var a = el("text", {x: 12, y: -30, "text-anchor": "middle", "font-size": 16, "font-weight": 800, fill: "#ff9a2e"}, g);
  a.textContent = "gRNA (길잡이)";
  var s = el("text", {x: 12, y: 34, "text-anchor": "middle", "font-size": 11, fill: "#ffd9a8",
    "font-family": "ui-monospace,Consolas,monospace"}, g);
  s.textContent = "5'-" + SP + "-3'";
  setPos(g, GR_HOME.x, GR_HOME.y);
  attachDrag(g, {
    can: function(){ return state === "merge"; },
    denied: function(){
      if (state === "find") setMsg("먼저 DNA에서 표적 서열을 찾아야 합니다.", "bad");
    },
    move: function(){
      if (dist(g, cas) < 120) cas.classList.add("glow"); else cas.classList.remove("glow");
    },
    drop: onGrDrop
  });
  return g;
}

function attachDrag(g, h){
  var dragging = false, off = {x: 0, y: 0};
  g.style.touchAction = "none";
  g.addEventListener("pointerdown", function(e){
    if (!h.can()){ if (h.denied) h.denied(); return; }
    e.preventDefault();
    g.setPointerCapture(e.pointerId);
    var p = svgPt(e);
    off = {x: p.x - g._x, y: p.y - g._y};
    dragging = true;
    g.classList.add("grab");
  });
  g.addEventListener("pointermove", function(e){
    if (!dragging) return;
    var p = svgPt(e);
    var x = clamp(p.x - off.x, 60, 840);
    var y = clamp(p.y - off.y, 40, 430);
    setPos(g, x, y);
    if (h.move) h.move(x, y);
  });
  function end(){
    if (!dragging) return;
    dragging = false;
    g.classList.remove("grab");
    if (h.drop) h.drop(g._x, g._y);
  }
  g.addEventListener("pointerup", end);
  g.addEventListener("pointercancel", end);
}

/* =====================================================================
   1단계: 표적 찾기 (DNA 글자 클릭)
   ===================================================================== */
function onFind(i){
  if (state !== "find") return;
  if (i >= FL && i < FL + 20){
    state = "merge";
    svg.classList.remove("finding");
    if (banner.parentNode) banner.parentNode.removeChild(banner);
    protoBox.setAttribute("opacity", 1);
    protoBox.setAttribute("class", "");
    pamBox.setAttribute("opacity", 1);
    pamBox.setAttribute("class", "pulse");
    pamLbl.setAttribute("opacity", 1);
    hintEl.setAttribute("visibility", "hidden");
    setStep(1);
    setMsg("정답! 초록 상자가 gRNA와 같은 20글자이고, 바로 뒤 주황 상자(" + PAM + ")가 PAM이에요. 이제 gRNA를 Cas9에 끌어다 붙여 RNP를 만드세요.", "good");
    setCtrl([{label: "힌트", fn: hint}]);
    return;
  }
  penalty++;
  var text;
  if (i >= PAM_START && i < PAM_START + 3){
    text = "여기는 표적 바로 뒤(PAM 자리)예요. 찾을 서열은 이보다 앞쪽에 있습니다.";
  } else {
    text = "이 부분의 글자는 gRNA와 달라요. 위쪽 «찾을 서열»의 처음 몇 글자와 DNA 글자를 비교해 보세요.";
  }
  setMsg(text, "bad");
  if (penalty >= 2) hint();
}

/* =====================================================================
   2단계: gRNA + Cas9 = RNP
   ===================================================================== */
function onGrDrop(){
  cas.classList.remove("glow");
  if (dist(gr, cas) < 120){
    state = "busy";
    tween(gr, cas._x, cas._y + 8, 350, function(){
      gr.style.display = "none";
      cas._guide.setAttribute("opacity", 1);
      cas._tag.setAttribute("opacity", 1);
      cas.classList.add("glow");
      setTimeout(function(){ cas.classList.remove("glow"); }, 900);
      state = "deliver";
      setStep(2);
      setMsg("RNP가 완성됐어요! 하지만 아직 세포 밖이에요. 세포막을 통과시킬 전달 방법을 하나 고르세요.", "good");
      setCtrl([
        {label: "전기천공", cls: "main", fn: function(){ deliver("electro"); }},
        {label: "리포펙션", cls: "main", fn: function(){ deliver("lipo"); }},
        {label: "미세주입", cls: "main", fn: function(){ deliver("micro"); }}
      ]);
    });
  } else {
    setMsg("gRNA가 Cas9에 닿지 않았어요. 초록색 Cas9 위에 겹치도록 놓아 보세요.", "bad");
    tween(gr, GR_HOME.x, GR_HOME.y, 350);
  }
}

/* =====================================================================
   3단계: 세포 안으로 전달
   ===================================================================== */
function deliver(kind){
  if (state !== "deliver") return;
  state = "busy";
  setCtrl([]);
  var fx = el("g", {"class": "fx"}, svg);
  svg.insertBefore(fx, cas);
  var text;
  if (kind === "electro"){
    el("polyline", {points: "380,120 398,146 384,160 404,190", fill: "none", stroke: "#ffe14d", "stroke-width": 4}, fx);
    el("polyline", {points: "520,120 502,146 516,160 496,190", fill: "none", stroke: "#ffe14d", "stroke-width": 4}, fx);
    el("ellipse", {cx: 450, cy: MEMBRANE_Y, rx: 38, ry: 7, fill: "#0a1620", stroke: "#ffe14d", "stroke-width": 2}, fx);
    text = "전기천공: 아주 짧은 전기 자극으로 세포막에 작은 구멍이 잠깐 열렸고, 그 틈으로 RNP가 들어갑니다.";
  } else if (kind === "lipo"){
    el("circle", {cx: 450, cy: 110, r: 78, fill: "rgba(255,217,168,0.08)", stroke: "#ffd9a8", "stroke-width": 3}, fx);
    el("circle", {cx: 380, cy: 150, r: 9, fill: "none", stroke: "#ffd9a8", "stroke-width": 2}, fx);
    el("circle", {cx: 525, cy: 140, r: 12, fill: "none", stroke: "#ffd9a8", "stroke-width": 2}, fx);
    text = "리포펙션: 지방 성분의 작은 방울이 RNP를 감싼 뒤 세포막과 합쳐지면서 RNP를 세포 안에 내려놓습니다.";
  } else {
    el("line", {x1: 450, y1: 8, x2: 450, y2: 150, stroke: "#b8c7d1", "stroke-width": 6, "stroke-linecap": "round"}, fx);
    el("polygon", {points: "444,150 456,150 450,182", fill: "#b8c7d1"}, fx);
    text = "미세주입: 아주 가는 유리 바늘로 세포 안에 RNP를 직접 넣습니다. 정확하지만 세포를 하나씩 해야 해서 오래 걸려요.";
  }
  removeLater(fx, 1600);
  setTimeout(function(){
    tween(cas, CAS_IN.x, CAS_IN.y, 900, function(){
      state = "dock";
      setStep(3);
      setMsg(text + " 이제 Cas9의 핵 신호(NLS) 덕분에 핵 안으로 들어갈 수 있어요. RNP를 끌어다 핵 속 DNA의 표적 위에 올려놓으세요.", "good");
      setCtrl([{label: "힌트", fn: hint}]);
    });
  }, 350);
}

/* =====================================================================
   4단계: 표적 결합
   ===================================================================== */
function onCasDrop(x, y){
  scanner.setAttribute("opacity", 0);
  if (y < 300){
    setMsg("DNA는 핵 안에 있어요. 점선으로 된 핵 안쪽까지 RNP를 끌고 내려가세요.");
    return;
  }
  if (Math.abs(x - TARGET_X) <= 33){
    bindTarget();
    return;
  }
  penalty++;
  var s = Math.round((x - X0) / DX - 0.5 - 11);
  var text;
  if (s < 0 || s + 23 > N){
    text = "DNA 가장자리입니다. 표적 서열이 있는 가운데 쪽으로 옮겨 보세요.";
  } else if (FULL.charAt(s + 21) !== "G" || FULL.charAt(s + 22) !== "G"){
    text = "이 위치에는 PAM(NGG)이 없어 Cas9가 DNA를 풀지 못하고 지나갑니다.";
  } else {
    var mm = 0;
    for (var i = 0; i < 20; i++){ if (FULL.charAt(s + i) !== SP.charAt(i)) mm++; }
    text = "PAM은 있지만 gRNA와 " + mm + "개 글자가 맞지 않아요. 짝이 맞지 않아 단단히 붙지 못합니다.";
  }
  setMsg(text + " 다시 시도해 보세요.", "bad");
  tween(cas, CAS_IN.x, CAS_IN.y, 450);
  if (penalty >= 2) hint();
}

function bindTarget(){
  state = "busy";
  hintEl.setAttribute("visibility", "hidden");
  pamBox.setAttribute("class", "");
  setCtrl([]);
  tween(cas, TARGET_X, CAS_BOUND_Y, 450, function(){
    svg.insertBefore(cas, gDNA);
    cas.classList.add("glow");
    for (var i = FL; i < FL + 20; i++){
      (function(idx){
        setTimeout(function(){ bases[idx].classList.add("open"); }, (idx - FL) * 40);
      })(i);
    }
    setTimeout(function(){
      cas.classList.remove("glow");
      state = "cut";
      setStep(4);
      setMsg("Cas9가 PAM을 알아보고 DNA 두 가닥을 풀었어요. 주황색 gRNA(U)가 아래 가닥과 짝을 이뤘습니다. Cas9를 클릭하거나 버튼을 눌러 자르세요.", "good");
      setCtrl([{label: "Cas9로 DNA 자르기", cls: "main", fn: doCut}]);
    }, 20 * 40 + 700);
  });
}

/* =====================================================================
   5단계: 절단
   ===================================================================== */
function doCut(){
  if (state !== "cut") return;
  state = "busy";
  setCtrl([]);
  var burst = el("circle", {cx: CUT_X, cy: (YT + YB) / 2, r: 46, fill: "none", stroke: "#ffe14d", "stroke-width": 4}, svg);
  burst.setAttribute("class", "burst");
  cutLine.setAttribute("opacity", 1);
  setTimeout(function(){
    for (var i = 0; i < N; i++){
      bases[i].classList.add(i <= CUT_AFTER ? "left" : "right");
    }
  }, 250);
  setTimeout(function(){
    if (burst.parentNode) burst.parentNode.removeChild(burst);
    state = "repair";
    setStep(5);
    setMsg("DNA 두 가닥이 모두 끊어졌어요(이중가닥절단, DSB). PAM에서 3글자 앞이 잘렸습니다. 세포는 곧 수리를 시작해요. 어떤 방법으로 고쳐지게 할까요?", "good");
    setCtrl([
      {label: "NHEJ (급하게 이어 붙이기)", cls: "main", fn: function(){ repair("nhej"); }},
      {label: "HDR (설계도를 보고 정확히 고치기)", fn: function(){ repair("hdr"); }}
    ]);
  }, 1300);
}

/* =====================================================================
   6단계: 수리  →  7단계: 시퀀싱으로 확인
   ===================================================================== */
function spans(items){
  return items.map(function(o){
    return o.k ? "<span class='" + o.k + "'>" + o.c + "</span>" : o.c;
  }).join("");
}
function toItems(str){ return str.split("").map(function(c){ return {c: c}; }); }

function repair(kind){
  if (state !== "repair") return;
  state = "verify";
  setCtrl([]);
  for (var i = 0; i < N; i++){ bases[i].classList.remove("left", "right"); }
  cutLine.setAttribute("opacity", 0);

  var cutIdx = CUT_AFTER + 1;
  var before = toItems(FULL), after, title, body;

  if (kind === "nhej"){
    var left = toItems(FULL.slice(0, cutIdx));
    var right = toItems(FULL.slice(cutIdx));
    if (rnd() < 0.5){
      var ins = randBase();
      after = left.concat([{c: ins, k: "m"}], right);
      title = "NHEJ 결과: 글자 1개가 끼어들었어요 (+1)";
    } else {
      var k = 1 + Math.floor(rnd() * 2);
      for (var j = 0; j < k; j++){ before[cutIdx + j].k = "del"; }
      var gap = [];
      for (var q = 0; q < k; q++) gap.push({c: "-", k: "del"});
      after = left.concat(gap, right.slice(k));
      title = "NHEJ 결과: 글자 " + k + "개가 사라졌어요 (-" + k + ")";
    }
    body = "끊어진 두 끝을 서둘러 이어 붙이다가 실수가 생겼어요. 글자 수가 3의 배수가 아니면 그 뒤의 읽는 틀이 모두 밀려서(프레임시프트) 단백질이 제대로 만들어지지 않고, 이렇게 유전자 기능을 끄는 것을 녹아웃이라고 해요. 실제 세포에서는 세포마다 결과가 달라 여러 종류의 변화가 섞여 나옵니다.";
  } else {
    var pos = cutIdx + 1;
    var orig = FULL.charAt(pos);
    var choices = "ACGT".replace(orig, "");
    var nb = choices.charAt(Math.floor(rnd() * 3));
    before[pos].k = "m";
    after = toItems(FULL);
    after[pos] = {c: nb, k: "m"};
    title = "HDR 결과: 설계도(도너 DNA)대로 글자 1개가 교정됐어요 (" + orig + " → " + nb + ")";
    body = "도너 DNA를 본보기 삼아 끊어진 자리가 정확하게 고쳐졌어요. 다만 HDR는 세포가 분열을 준비하는 시기에 주로 일어나서, 실제로는 NHEJ보다 성공하는 세포가 훨씬 적습니다. 그래서 정밀한 교정은 효율을 높이는 연구가 활발해요.";
  }

  pending = {before: before, after: after, title: title, body: body, kind: kind};
  setStep(6);
  setMsg("세포가 끊어진 DNA를 이어 붙였어요. 그런데 어떻게 바뀌었는지는 눈으로 볼 수 없어요. 실제 연구처럼 PCR로 표적 부위를 복사해 글자를 읽어(시퀀싱) 확인해 봅시다.", "good");
  setCtrl([{label: "PCR + 시퀀싱으로 확인하기", cls: "main", fn: showResult}]);
}

function showResult(){
  if (state !== "verify" || !pending) return;
  state = "done";
  var score = Math.max(40, 100 - penalty * 10);
  var grade = penalty === 0 ? "한 번도 틀리지 않았어요!" : (penalty < 3 ? "훌륭해요!" : "연습할수록 좋아져요.");
  resEl.innerHTML =
    "<div class='card'><h2>" + pending.title + "</h2>" +
    "<div class='lbl'>편집 전 서열</div><div class='seq'>" + spans(pending.before) + "</div>" +
    "<div class='lbl'>편집 후 서열 (시퀀싱 결과)</div><div class='seq'>" + spans(pending.after) + "</div>" +
    "<p>" + pending.body + "</p>" +
    "<p>실제 연구에서는 이 결과를 바탕으로 편집된 세포의 비율(편집 효율)을 계산하고, 엉뚱한 곳이 바뀌지 않았는지(오프타깃)도 함께 검사합니다.</p>" +
    "<p><b>실습 점수 " + score + "점</b> · 틀린 시도 " + penalty + "회 · " + grade + "</p></div>";
  setStep(7);
  setMsg("실습 완료! NHEJ와 HDR 결과가 어떻게 다른지 다시 해 보며 비교해 보세요.", "good");
  setCtrl([{label: "처음부터 다시 하기", cls: "main", fn: build}]);
  resEl.scrollIntoView({behavior: "smooth", block: "nearest"});
}

/* =====================================================================
   힌트
   ===================================================================== */
function hint(){
  if (state === "find"){
    protoBox.setAttribute("opacity", 0.9);
    protoBox.setAttribute("class", "pulse");
    setMsg("힌트: 깜빡이는 초록 상자 안의 글자를 클릭해 보세요. 위쪽 서열과 같은 순서인지 확인해 보세요.");
  } else if (state === "merge"){
    setMsg("힌트: 왼쪽 위의 주황색 gRNA를 오른쪽 위의 초록색 Cas9 위로 가져가세요.");
    cas.classList.add("glow");
    setTimeout(function(){ cas.classList.remove("glow"); }, 1500);
  } else if (state === "dock"){
    hintEl.setAttribute("visibility", "visible");
    setMsg("힌트: 점선 타원 안으로 RNP를 옮기세요. 오른쪽 끝이 주황색 PAM 상자에 닿아야 해요.");
  }
}

svg.addEventListener("pointerup", function(e){
  if (state !== "find") return;
  var p = svgPt(e);
  if (Math.abs(p.y - YT) > 16) return;
  var i = Math.floor((p.x - X0) / DX);
  if (i >= 0 && i < N) onFind(i);
});

build();
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 3) 설명글 (버튼을 누르면 펼쳐짐)
# ---------------------------------------------------------------------------
GUIDE_MD = """
### 유전자 편집이란?
유전자 편집은 DNA라는 **생명의 설계도에서 원하는 부분만 정확히 찾아 고치는 기술**입니다.
이 실습의 **CRISPR-Cas9**는 두 부품으로 이루어져 있어요.

- **Cas9** : DNA를 자르는 **가위 단백질**
- **gRNA(가이드 RNA)** : 어디를 자를지 알려 주는 **길잡이(내비게이션)**

### 실제 유전자 편집 연구는 이렇게 진행돼요
| 단계 | 무슨 일이 일어나나요? | 실제 연구에서 쓰는 방법 |
|---|---|---|
| 1. 표적 찾기 | 고치고 싶은 곳 근처에서 **PAM(NGG)** 을 찾고 gRNA를 설계해요. | 컴퓨터로 gRNA 후보 설계, MIT(안전성)·Doench(효율) 점수로 선별 (1페이지) |
| 2. RNP 만들기 | Cas9와 gRNA를 합쳐 **RNP** 를 만들어요. | 정제한 Cas9 단백질 + 합성 gRNA를 실온에서 10~20분 반응 |
| 3. 세포 안으로 전달 | 세포막을 통과시켜 RNP를 세포 안에 넣어요. | 전기천공, 리포펙션, 미세주입 등 |
| 4. 표적 결합 | Cas9가 PAM을 찾고 DNA를 풀어 gRNA와 글자를 맞춰 봐요. | (세포 안에서 자동으로 일어남) |
| 5. 절단 | 표적에서 PAM 3글자 앞의 DNA 두 가닥이 끊어져요(DSB). | (세포 안에서 자동으로 일어남) |
| 6. 세포의 수리 | 세포가 스스로 DNA를 고쳐요. **NHEJ**는 빠르지만 실수가 생기고, **HDR**는 설계도를 따라 정확히 고쳐요. | 유전자 끄기는 NHEJ, 정밀 교정은 도너 DNA와 함께 HDR |
| 7. 결과 확인 | 정말 바뀌었는지 DNA 글자를 읽어 확인해요. | PCR 증폭 + 시퀀싱(샌거, NGS) |

### 용어 사전
- **염기(A, T, G, C)** : DNA를 이루는 네 가지 글자. A-T, G-C끼리 짝을 이룹니다.
- **PAM** : 표적 바로 뒤에 있는 NGG. Cas9가 "여기서 자르면 돼"라고 알아보는 신호입니다.
- **RNP** : Cas9(단백질) + gRNA(RNA)가 합쳐진 덩어리.
- **DSB(이중가닥절단)** : DNA 두 가닥이 모두 끊어진 상태.
- **NHEJ** : 끊어진 끝을 서둘러 이어 붙이는 수리. 글자가 끼거나 빠지는 실수가 생길 수 있어요.
- **HDR** : 도너 DNA(설계도)를 보고 정확히 고쳐 쓰는 수리.
- **오프타깃** : 원래 목표가 아닌, 비슷하게 생긴 다른 곳이 잘못 잘리는 일.

### 함께 생각해 봐요
- 왜 연구자들은 **오프타깃이 적은 gRNA**를 고르려고 애쓸까요?
- 유전자 편집을 질병 치료에 쓸 때 어떤 점을 조심하고, 어떤 규칙이 필요할까요?

> 이 실습은 이해를 돕기 위해 실제 과정을 **단순화한 시뮬레이션**입니다. 실제 연구는 전문 시설에서 안전 규정을 지켜 진행됩니다.
"""


def _toggle_guide():
    st.session_state["show_guide"] = not st.session_state.get("show_guide", False)


# ---------------------------------------------------------------------------
# 4) 페이지 렌더링
# ---------------------------------------------------------------------------
st.title("🧬 유전자 편집 실습실")
st.caption(
    "실제 CRISPR-Cas9 유전자 편집 순서대로 7단계를 직접 해 보는 실습입니다. "
    "PC 화면에서 하면 가장 잘 보여요."
)

cfg = build_config()
if cfg["demo"]:
    st.info(
        "1페이지에서 선택된 gRNA가 없어 예시 서열로 실습합니다. "
        "스크리닝 도구에서 후보를 고르면 그 서열로 이어집니다."
    )
elif cfg["real"]:
    st.success(
        f"NCBI RefSeq {cfg['accession']} 실제 서열의 {cfg['start']}-{cfg['end']}번 위치로 실습합니다. "
        "화면의 DNA 글자는 모두 실제 염기서열입니다."
    )
    st.caption(
        "이 서열은 RefSeq 전사체(mRNA의 cDNA) 서열입니다. 실제 게놈 DNA에는 중간에 인트론이 있지만, "
        "엑손 안에 있는 표적이라면 글자가 같습니다."
    )
else:
    st.caption("직접 입력한 서열이라 표적 20글자 외의 주변 DNA는 설명을 위한 가상 서열입니다.")

show_guide = st.session_state.get("show_guide", False)
st.button(
    "📘 실제 유전자 편집 과정 설명 닫기" if show_guide else "📘 실제 유전자 편집 과정 설명 보기",
    on_click=_toggle_guide,
)

# 설명 칸을 항상 같은 위치에 만들어 두면, 열고 닫아도 아래 실습 화면이 초기화되지 않는다
guide_slot = st.container()
with guide_slot:
    if show_guide:
        with st.container(border=True):
            st.markdown(GUIDE_MD)

# '</' 가 들어 있어도 <script> 블록이 끊기지 않도록 이스케이프
config_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
html = LAB_HTML.replace("__CONFIG__", config_json)

components.html(html, height=1250, scrolling=True)
