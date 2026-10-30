import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib
matplotlib.use("Agg")  # 서버(화면 없는 환경)에서도 그래프를 그릴 수 있게 설정
import matplotlib.pyplot as plt
import random
import os
import platform
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

# PDF 생성을 위한 ReportLab 모듈
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# NCBI 서열 가져오기 / 표적 찾기 (같은 폴더의 ncbi_utils.py)
from ncbi_utils import NCBI_GENES, fetch_refseq_fasta, find_candidates

# 2페이지(실습실) 파일 경로. 파일명을 바꾸면 여기만 고치면 됩니다.
LAB_PAGE_PATH = "pages/2_실습실.py"

MODE_NCBI = "🧬 NCBI 실제 서열로 설계"
MODE_MANUAL = "✍️ 직접 입력 (연습용)"
CUSTOM_LABEL = "직접 번호 입력 (RefSeq)"

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="gRNA Clinical Screening Tool",
    page_icon="🧬",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 연핑크 배경 & Custom CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @font-face {
        font-family: 'NanumSquareRound';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_two@1.0/NanumSquareRound.woff') format('woff');
        font-display: swap;
    }

    /* 아이콘 글자가 깨지지 않도록 '*' 대신 텍스트 요소에만 폰트를 적용 */
    html, body, .stApp, .stMarkdown, button, input, textarea, label, p, h1, h2, h3, h4 {
        font-family: 'NanumSquareRound', sans-serif !important;
    }

    .stApp {
        background-color: #FFF0F5;
        color: #2D3748;
    }

    h1 {
        color: #4A154B !important;
        font-weight: 800;
        font-size: 2.2rem !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.05);
    }
    h2, h3, h4 {
        color: #4A154B !important;
        font-weight: 700;
    }
    p, span, label {
        color: #2D3748 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #FFF5F7 !important;
        border-right: 2px solid #FCE7F3;
    }

    .custom-card {
        background-color: #FFFFFF;
        border: 2px solid #FBCFE8;
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 16px rgba(244, 114, 182, 0.15);
    }

    .badge-best {
        background-color: #FCE7F3;
        color: #DB2777 !important;
        padding: 6px 14px;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(219, 39, 119, 0.1);
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 2px solid #FBCFE8;
        padding: 16px;
        border-radius: 18px;
        box-shadow: 0 6px 12px rgba(244, 114, 182, 0.12);
    }

    .stButton>button, .stDownloadButton>button {
        background-color: #EC4899 !important;
        color: #FFFFFF !important;
        border-radius: 14px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 10px rgba(236, 72, 153, 0.3);
        transition: all 0.2s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(236, 72, 153, 0.4);
        background-color: #DB2777 !important;
    }
    /* 위의 'p, span, label' 규칙 때문에 버튼 글자가 어두워지는 것을 방지 */
    .stButton>button p, .stDownloadButton>button p,
    .stButton>button span, .stDownloadButton>button span {
        color: #FFFFFF !important;
    }

    div[data-baseweb="slider"] div {
        background-color: #EC4899 !important;
    }

    textarea {
        border-radius: 12px !important;
        border: 1.5px solid #FBCFE8 !important;
        background-color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 타이틀 및 안내 Banner
# -----------------------------------------------------------------------------
st.title("🧬 유전자 가위 임상 적합성 스크리닝 도구")
st.markdown("✨ <b>안전성(MIT)</b>과 <b>효율성(Doench)</b>을 한눈에 비교하고 최적의 표적 후보를 선별해보세요!", unsafe_allow_html=True)
st.caption("※ 점수는 GC 함량 등을 이용한 교육용 간이 계산이며, 실제 MIT·Doench 알고리즘 결과가 아닙니다. 표적 서열은 NCBI RefSeq 실제 서열에서 가져옵니다.")
st.markdown("---")

# -----------------------------------------------------------------------------
# 4. 예시 데이터 세트 정의 (직접 입력 연습용)
# -----------------------------------------------------------------------------
DATA_SAMPLES = {
    "HBB (겸상적혈구빈혈증 관련 유전자)": "HBB_1460_rev, GACACCAACTGTCAACTGAT\nHBB_1542_fw, CCTTGCCCCACAGGGCAGTA\nHBB_Exon1_A, CTTGCCCCACAGGGCAGTAA\nHBB_Exon1_B, TGGTCTACCCTTGGACCCAG\nHBB_Exon2_C, AGTCTGCCATCACTGCCCTG",
    "BRCA1 (유방암/난소암 관련 유전자)": "BRCA1_Exon2_1, GAGTAGTCAAGAGAAAGGAC\nBRCA1_Exon11_A, GGAAGAAACCACCAAGGTCC\nBRCA1_Exon11_B, ACAGCTACCCTTCCATCATA\nBRCA1_Exon18_C, CTGATGTGCTTTGTTCTGGA\nBRCA1_Exon24_D, TTACAGTTAGGTGAACAGCA",
    "TP53 (암 억제 유전자)": "TP53_Exon4_1, GTCCCCCTTGCCGTCCCAAG\nTP53_Exon5_A, CCTCAACAAGATGTTTTGCC\nTP53_Exon7_B, GCGCACTGACCACTGGATGG\nTP53_Exon8_C, CCTATCCTGAGTAGTGGTAA\nTP53_Exon10_D, CGTGTTTGTGCCTGTCCTGG"
}

# -----------------------------------------------------------------------------
# 5. 계산 로직
# -----------------------------------------------------------------------------
def validate_grna(sequence: str):
    seq = sequence.strip().upper()
    if len(seq) != 20:
        return False, f"길이 오류 ({len(seq)}bp)"
    valid_bases = ['A', 'T', 'G', 'C']
    for char in seq:
        if char not in valid_bases:
            return False, "유효하지 않은 염기 포함"
    return True, "정상"

def calculate_scores(sequence: str):
    seq = sequence.strip().upper()
    gc_content = ((seq.count('G') + seq.count('C')) / 20) * 100
    doench_score = max(10, 100 - (abs(gc_content - 50) * 2.8))

    seed_region = seq[10:]
    seed_gc = ((seed_region.count('G') + seed_region.count('C')) / 10) * 100
    mit_score = max(15, 95 - abs(seed_gc - 50) * 1.5)

    return {
        "GC_Ratio": round(gc_content, 1),
        "Doench_Score": round(doench_score, 1),
        "MIT_Score": round(mit_score, 1)
    }

def now_kst():
    return datetime.now(ZoneInfo("Asia/Seoul"))

@st.cache_data(ttl=86400, show_spinner=False)
def cached_fetch(accession: str):
    """같은 번호를 반복해서 NCBI 에 요청하지 않도록 하루 동안 캐시"""
    return fetch_refseq_fasta(accession)

# -----------------------------------------------------------------------------
# 6. PDF 생성용 헬퍼 함수 (임시 파일 없이 메모리에서 처리)
# -----------------------------------------------------------------------------
def register_korean_font():
    system_name = platform.system()
    linux_font_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
    ]

    if system_name == "Windows":
        font_path = "C:/Windows/Fonts/malgun.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("KoreanFont", font_path))
            return "KoreanFont"
    elif system_name == "Darwin":
        font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("KoreanFont", font_path))
            return "KoreanFont"

    for path in linux_font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("KoreanFont", path))
            return "KoreanFont"

    return "Helvetica"

def create_pdf_report(df_results, top_cand, gene_name, source_text, mit_w, doench_w, min_cutoff):
    """PDF를 만들어 bytes 로 돌려준다."""
    fig_mat, ax = plt.subplots(figsize=(7, 3.5))
    scatter = ax.scatter(
        df_results["효율성 (Doench)"],
        df_results["안전성 (MIT)"],
        c=df_results["종합 점수"],
        cmap="PuRd",
        s=df_results["종합 점수"] * 2.5,
        alpha=0.8,
        edgecolors="#EC4899"
    )

    for _, row in df_results.iterrows():
        ax.annotate(row["후보명"], (row["효율성 (Doench)"], row["안전성 (MIT)"]),
                    fontsize=8, ha='center', va='bottom', color='#4A154B', fontweight='bold')

    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Doench Score (Efficiency)", fontsize=9, color='#4A154B')
    ax.set_ylabel("MIT Score (Safety)", fontsize=9, color='#4A154B')
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.colorbar(scatter, ax=ax, label="Total Score")
    plt.tight_layout()

    img_buf = BytesIO()
    fig_mat.savefig(img_buf, format="png", dpi=200)
    plt.close(fig_mat)
    img_buf.seek(0)

    font_name = register_korean_font()

    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName=font_name, fontSize=20, leading=24, textColor=colors.HexColor('#4A154B'), spaceAfter=10)
    h2_style = ParagraphStyle('DocH2', parent=styles['Heading2'], fontName=font_name, fontSize=13, leading=16, textColor=colors.HexColor('#EC4899'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor('#2D3748'))

    elements = []
    elements.append(Paragraph("gRNA Clinical Screening Summary Report", title_style))
    elements.append(Paragraph(f"<b>생성 일시:</b> {now_kst().strftime('%Y-%m-%d %H:%M:%S')} (KST) | <b>대상 유전자:</b> {gene_name}", body_style))
    elements.append(Paragraph(f"<b>서열 출처:</b> {source_text}", body_style))
    elements.append(Spacer(1, 10))

    summary_data = [
        [Paragraph("<b>구분</b>", body_style), Paragraph("<b>설정 및 결과 값</b>", body_style)],
        [Paragraph("가중치 설정", body_style), Paragraph(f"안전성 (MIT) {mit_w}% : 효율성 (Doench) {doench_w}%", body_style)],
        [Paragraph("최소 안전성 컷오프", body_style), Paragraph(f"{min_cutoff} 점", body_style)],
        [Paragraph("스크리닝 통과 후보", body_style), Paragraph(f"총 {len(df_results)} 개", body_style)],
        [Paragraph("<b>최우수 추천 후보 (TOP 1)</b>", body_style), Paragraph(f"<b>{top_cand['후보명']}</b> ({top_cand['Sequence']}) - <b>종합 {top_cand['종합 점수']}점</b>", body_style)]
    ]

    t_summary = Table(summary_data, colWidths=[150, 390])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FCE7F3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#DB2777')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FBCFE8')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_summary)

    elements.append(Paragraph("2D 스크리닝 분석 맵", h2_style))
    elements.append(Image(img_buf, width=540, height=270))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("후보 리스트 (종합 점수 순)", h2_style))

    table_data = [[
        Paragraph("<b>순위</b>", body_style),
        Paragraph("<b>후보명</b>", body_style),
        Paragraph("<b>Sequence (20bp)</b>", body_style),
        Paragraph("<b>안전성</b>", body_style),
        Paragraph("<b>효율성</b>", body_style),
        Paragraph("<b>종합점수</b>", body_style)
    ]]

    for idx, row in df_results.iterrows():
        table_data.append([
            Paragraph(str(idx + 1), body_style),
            Paragraph(str(row['후보명']), body_style),
            Paragraph(str(row['Sequence']), body_style),
            Paragraph(str(row['안전성 (MIT)']), body_style),
            Paragraph(str(row['효율성 (Doench)']), body_style),
            Paragraph(f"<b>{row['종합 점수']}</b>", body_style)
        ])

    t_results = Table(table_data, colWidths=[35, 120, 180, 65, 65, 75])
    t_results.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FFF0F5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FBCFE8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(t_results)
    doc.build(elements)

    return pdf_buf.getvalue()

# -----------------------------------------------------------------------------
# 7. 사이드바 - 설정 및 입력
# -----------------------------------------------------------------------------
st.sidebar.header("⚙ 스크리닝 설정")

st.sidebar.subheader("1. ⚖️ 가중치 비율 설정")
if "mit_w" not in st.session_state:
    st.session_state["mit_w"] = 60
if "doench_w" not in st.session_state:
    st.session_state["doench_w"] = 40

def on_mit_change():
    st.session_state["doench_w"] = 100 - st.session_state["mit_w"]

def on_doench_change():
    st.session_state["mit_w"] = 100 - st.session_state["doench_w"]

mit_weight = st.sidebar.slider("🛡 안전성 (MIT) 가중치 (%)", 0, 100, key="mit_w", on_change=on_mit_change)
doench_weight = st.sidebar.slider("⚡ 효율성 (Doench) 가중치 (%)", 0, 100, key="doench_w", on_change=on_doench_change)

st.sidebar.markdown("---")
st.sidebar.subheader("2. 🎯 최소 품질 컷오프")
min_mit_cutoff = st.sidebar.slider("최소 요구 안전성 점수", 0, 100, 50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("3. 🧬 표적 서열")

input_mode = st.sidebar.radio(
    "서열 입력 방식",
    [MODE_NCBI, MODE_MANUAL],
    key="input_mode",
    label_visibility="collapsed",
)

# 이번 실행에서 만들어지는 결과물
parsed_results = []        # 점수 계산을 통과한 후보들
context_by_name = {}       # 후보명 -> 실제 주변 서열 정보 (실습실로 넘김)
invalid_lines = []         # 직접 입력 모드에서 형식이 틀린 줄
source_text = ""           # 서열 출처 설명
gene_label = ""            # 화면/리포트에 표시할 유전자 이름
gene_symbol = ""           # 실습실로 넘길 짧은 이름 (예: HBB)
accession_used = ""
ready = False              # 후보를 만들 준비가 되었는가
info_lines = []            # 화면에 보여 줄 안내 문구

if input_mode == MODE_NCBI:
    gene_key = st.sidebar.selectbox(
        "유전자",
        list(NCBI_GENES.keys()) + [CUSTOM_LABEL],
        key="ncbi_gene",
    )

    if gene_key == CUSTOM_LABEL:
        accession_used = st.sidebar.text_input(
            "RefSeq 전사체 번호",
            placeholder="예: NM_000518",
            key="ncbi_acc_custom",
        ).strip()
        gene_symbol = accession_used
        gene_label = accession_used or "직접 번호 입력"
    else:
        accession_used = NCBI_GENES[gene_key]["accession"]
        gene_symbol = NCBI_GENES[gene_key]["symbol"]
        gene_label = gene_key

    ref_header, ref_seq = "", ""
    if accession_used:
        try:
            with st.spinner("NCBI에서 실제 서열을 불러오는 중입니다..."):
                ref_header, ref_seq = cached_fetch(accession_used)
        except Exception as e:
            st.error(f"NCBI에서 서열을 가져오지 못했습니다: {e}")
            st.info("잠시 후 다시 시도하거나, 사이드바에서 '직접 입력 (연습용)'을 선택해 주세요.")
    else:
        st.info("👈 사이드바에 RefSeq 전사체 번호(예: NM_000518)를 입력해 주세요.")

    if ref_seq:
        total_len = len(ref_seq)
        if total_len < 80:
            st.error("서열이 너무 짧아 표적을 찾을 수 없습니다.")
        else:
            default_end = min(total_len, 1500)
            region = st.sidebar.slider(
                "탐색 구간 (전사체 염기 위치)",
                1, total_len, (1, default_end),
                key=f"region_{accession_used}",
            )
            top_n = st.sidebar.slider("표시할 후보 수", 5, 30, 10, key="top_n")

            all_cands = find_candidates(ref_seq, start=region[0], end=region[1])
            passed = []
            for c in all_cands:
                sc = calculate_scores(c["protospacer"])
                if sc["MIT_Score"] < min_mit_cutoff:
                    continue
                weighted = (sc["MIT_Score"] * (mit_weight / 100.0)) + (sc["Doench_Score"] * (doench_weight / 100.0))
                name = f"{gene_symbol}_{c['start']}({c['strand']})"
                passed.append((weighted, name, c, sc))

            passed.sort(key=lambda x: x[0], reverse=True)
            for weighted, name, c, sc in passed[:top_n]:
                parsed_results.append({
                    "후보명": name,
                    "Sequence": c["protospacer"],
                    "PAM": c["pam"],
                    "위치": f"{c['start']}–{c['end']}",
                    "가닥": c["strand"],
                    "GC 함량 (%)": sc["GC_Ratio"],
                    "안전성 (MIT)": sc["MIT_Score"],
                    "효율성 (Doench)": sc["Doench_Score"],
                    "종합 점수": round(weighted, 1),
                })
                context_by_name[name] = c

            source_text = f"NCBI RefSeq {accession_used} ({ref_header}), 탐색 구간 {region[0]}-{region[1]}"
            info_lines.append(
                f"서열 출처: NCBI RefSeq {accession_used} · {ref_header} · 전체 {total_len:,} 염기"
            )
            info_lines.append(
                f"탐색 구간 {region[0]}–{region[1]}에서 NGG(PAM) 표적 {len(all_cands)}개를 찾았고, "
                f"컷오프를 통과한 {len(passed)}개 중 상위 {min(top_n, len(passed))}개를 보여 줍니다."
            )
            ready = True

else:  # 직접 입력 (연습용)
    if "grna_input_text_area" not in st.session_state:
        st.session_state["grna_input_text_area"] = DATA_SAMPLES["HBB (겸상적혈구빈혈증 관련 유전자)"]
        st.session_state["current_gene_name"] = "HBB (겸상적혈구빈혈증 관련 유전자)"

    def change_random_example_data():
        gene_list = list(DATA_SAMPLES.keys())
        available_genes = [g for g in gene_list if g != st.session_state.get("current_gene_name")]
        selected_gene = random.choice(available_genes)

        st.session_state["grna_input_text_area"] = DATA_SAMPLES[selected_gene]
        st.session_state["current_gene_name"] = selected_gene

    st.sidebar.button(
        "🎲 다른 예시 데이터 불러오기",
        use_container_width=True,
        on_click=change_random_example_data
    )

    if "current_gene_name" in st.session_state:
        st.sidebar.caption(f"📌 현재 선택된 유전자: **{st.session_state['current_gene_name']}**")

    user_input = st.sidebar.text_area(
        "후보 목록 (`후보명, 20bp_서열`)",
        height=150,
        key="grna_input_text_area"
    )

    current = st.session_state.get("current_gene_name")
    is_sample = bool(current) and current in DATA_SAMPLES and user_input.strip() == DATA_SAMPLES[current].strip()
    gene_label = current if is_sample else "직접 입력 서열"
    gene_symbol = gene_label.split(" (")[0]
    source_text = "사용자 입력 서열 (실제 게놈 서열과 대조하지 않은 연습용 데이터)"

    if user_input.strip():
        for idx, line in enumerate(user_input.strip().split("\n"), 1):
            if not line.strip():
                continue
            if "," not in line:
                invalid_lines.append(f"{idx}번째 줄: 쉼표(,)가 없습니다")
                continue
            parts = line.split(",")
            name, seq = parts[0].strip(), parts[1].strip().upper()

            is_valid, reason = validate_grna(seq)
            if not is_valid:
                invalid_lines.append(f"{idx}번째 줄({name}): {reason}")
                continue

            sc = calculate_scores(seq)
            weighted = (sc["MIT_Score"] * (mit_weight / 100.0)) + (sc["Doench_Score"] * (doench_weight / 100.0))
            if sc["MIT_Score"] >= min_mit_cutoff:
                parsed_results.append({
                    "후보명": name,
                    "Sequence": seq,
                    "GC 함량 (%)": sc["GC_Ratio"],
                    "안전성 (MIT)": sc["MIT_Score"],
                    "효율성 (Doench)": sc["Doench_Score"],
                    "종합 점수": round(weighted, 1),
                })
        ready = True
        info_lines.append("직접 입력한 서열입니다. 실습실의 주변 DNA는 설명을 위한 가상 서열로 표시됩니다.")
    else:
        st.info("👈 사이드바에서 gRNA 후보 서열을 입력해 주세요.")

# -----------------------------------------------------------------------------
# 8. 메인 화면 구성
# -----------------------------------------------------------------------------
if ready:
    if invalid_lines:
        st.warning("형식이 맞지 않아 제외된 줄이 있습니다.\n\n" + "\n".join(f"- {m}" for m in invalid_lines))

    if parsed_results:
        df = pd.DataFrame(parsed_results).sort_values(by="종합 점수", ascending=False).reset_index(drop=True)
        top = df.iloc[0]

        for line in info_lines:
            st.caption(line)

        # 2페이지(실습실)로 넘길 데이터
        selected = top.to_dict()
        selected["gene"] = gene_symbol
        ctx = context_by_name.get(top["후보명"])
        if ctx:
            selected["PAM"] = ctx["pam"]
            selected["left"] = ctx["left"]
            selected["right"] = ctx["right"]
            selected["strand"] = ctx["strand"]
            selected["start"] = int(ctx["start"])
            selected["end"] = int(ctx["end"])
            selected["accession"] = accession_used
            selected["source"] = f"NCBI RefSeq {accession_used}"
        st.session_state["selected_top_grna"] = selected
        st.session_state["all_candidates_df"] = df

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔬 표시 후보", f"{len(df)}개")
        m2.metric("🏆 최상위 후보", top["후보명"])
        m3.metric("⭐ 최고 종합점수", f"{top['종합 점수']}점")
        m4.metric("🛡️ 평균 안전성", f"{round(df['안전성 (MIT)'].mean(), 1)}점")

        st.markdown("<br>", unsafe_allow_html=True)

        pam_text = f" + PAM {ctx['pam']}" if ctx else ""
        st.markdown(f"""
        <div class="custom-card">
            <span class="badge-best">🏆 TOP CANDIDATE</span>
            <h3 style="margin: 6px 0 12px 0;">{top['후보명']} <span style="font-size:0.95rem; color:#64748B;">({top['Sequence']}{pam_text})</span></h3>
            <p style="margin:0; font-size:1rem; color:#334155;">
                <b>GC 함량:</b> {top['GC 함량 (%)']}% &nbsp;|&nbsp;
                <b>안전성 점수:</b> {top['안전성 (MIT)']}점 &nbsp;|&nbsp;
                <b>효율성 점수:</b> {top['효율성 (Doench)']}점 &nbsp;|&nbsp;
                <b>최종 종합 점수:</b> <span style="color:#EC4899; font-weight:800; font-size:1.1rem;">{top['종합 점수']}점</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🧪 이 gRNA 후보로 유전자 편집 실습 시작하기", use_container_width=True):
            st.switch_page(LAB_PAGE_PATH)

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📊 2D 스크리닝 맵", "📋 상세 결과 데이터"])

        fig = px.scatter(
            df,
            x="효율성 (Doench)",
            y="안전성 (MIT)",
            size="종합 점수",
            color="종합 점수",
            hover_name="후보명",
            text="후보명",
            color_continuous_scale="PuRd",
            range_x=[0, 105],
            range_y=[0, 105]
        )
        fig.update_traces(textposition='top center')
        fig.update_layout(
            height=460,
            paper_bgcolor='#FFF0F5',
            plot_bgcolor='#FFFFFF',
            margin=dict(l=20, r=20, t=20, b=20)
        )

        with tab1:
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 스크리닝 결과 CSV 다운로드", data=csv, file_name="screening_results.csv", mime="text/csv")

        st.markdown("---")
        st.subheader("📄 PDF 리포트 출력")

        col_pdf1, col_pdf2 = st.columns([2, 5])
        with col_pdf1:
            if st.button("📑 PDF 요약 리포트 생성", use_container_width=True):
                with st.spinner("그래프 이미지 포함 PDF 리포트를 생성하는 중입니다..."):
                    st.session_state["pdf_bytes"] = create_pdf_report(
                        df, top, gene_label, source_text, mit_weight, doench_weight, min_mit_cutoff
                    )
                    st.success("PDF 생성이 완료되었습니다!")

        if "pdf_bytes" in st.session_state:
            st.download_button(
                label="📥 PDF 리포트 다운로드",
                data=st.session_state["pdf_bytes"],
                file_name=f"gRNA_Screening_Report_{now_kst().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

    else:
        st.session_state.pop("selected_top_grna", None)
        for line in info_lines:
            st.caption(line)
        st.warning("⚠️ 조건을 충족하는 후보가 없습니다. 최소 안전성 점수를 낮추거나 탐색 구간을 넓혀 보세요.")
else:
    st.session_state.pop("selected_top_grna", None)
