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

# 2페이지(실습실) 파일 경로. 파일명을 바꾸면 여기만 고치면 됩니다.
LAB_PAGE_PATH = "pages/2_실습실.py"

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
st.markdown("✨ **안전성(MIT)**과 **효율성(Doench)**을 한눈에 비교하고 최적의 표적 후보를 선별해보세요!")
st.caption("※ 점수는 GC 함량 등을 이용한 교육용 간이 계산이며, 실제 MIT·Doench 알고리즘 결과가 아닙니다.")
st.markdown("---")

# -----------------------------------------------------------------------------
# 4. 예시 데이터 세트 정의
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
    seed_gc =
