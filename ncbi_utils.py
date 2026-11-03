# ncbi_utils.py
# NCBI(E-utilities)에서 실제 유전자 서열(RefSeq 전사체)을 가져오고,
# 그 서열 안에서 실제로 존재하는 SpCas9 표적(20 nt + NGG PAM)을 찾아 주는 도우미.
# streamlit 에 의존하지 않으므로 main.py, pages/ 어디서든 import 해서 쓸 수 있다.

import re

import requests

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 기본 제공 유전자 (사람, RefSeq mRNA). 번호에 버전(.x)을 붙이지 않으면 NCBI가 최신 버전을 준다.
NCBI_GENES = {
    "HBB (겸상적혈구빈혈증 관련 유전자)": {"symbol": "HBB", "accession": "NM_000518"},
    "BRCA1 (유방암/난소암 관련 유전자)": {"symbol": "BRCA1", "accession": "NM_007294"},
    "TP53 (암 억제 유전자)": {"symbol": "TP53", "accession": "NM_000546"},
}

# 염색체 전체(NC_)처럼 아주 큰 서열을 실수로 받지 않도록 '전사체' 번호만 허용
_ACCESSION_RE = re.compile(r"^(NM|NR|XM|XR)_[0-9]{6,9}(\.[0-9]+)?$")

FLANK_LEFT = 8   # 실습 화면에서 표적 앞쪽에 보여 줄 실제 서열 길이
FLANK_RIGHT = 6  # 실습 화면에서 PAM 뒤쪽에 보여 줄 실제 서열 길이

_COMP = str.maketrans("ACGTN", "TGCAN")


def revcomp(seq: str) -> str:
    """역상보 서열"""
    return seq.translate(_COMP)[::-1]


def is_valid_accession(acc: str) -> bool:
    return bool(_ACCESSION_RE.match(acc.strip()))


def fetch_refseq_fasta(accession: str, timeout: int = 20):
    """NCBI nuccore 에서 FASTA 를 받아 (헤더, 염기서열) 로 돌려준다."""
    acc = accession.strip()
    if not is_valid_accession(acc):
        raise ValueError(
            "RefSeq 전사체 번호 형식이 아닙니다. NM_000518 처럼 NM_, NR_, XM_, XR_ 로 시작해야 합니다."
        )

    params = {
        "db": "nuccore",
        "id": acc,
        "rettype": "fasta",
        "retmode": "text",
        "tool": "grna_screening_app",
    }
    resp = requests.get(
        EFETCH_URL,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "grna-screening-education-app"},
    )
    resp.raise_for_status()

    text = resp.text.strip()
    if not text.startswith(">"):
        raise ValueError("NCBI에서 서열(FASTA)을 받지 못했습니다. 번호를 확인해 주세요.")

    lines = text.splitlines()
    header = lines[0][1:].strip()
    seq = "".join(line.strip() for line in lines[1:]).upper().replace("U", "T")

    if not seq or re.search(r"[^ACGTN]", seq):
        raise ValueError("받은 서열에 염기(A, C, G, T)가 아닌 문자가 있습니다.")
    if len(seq) > 300000:
        raise ValueError("서열이 너무 깁니다(30만 염기 초과).")

    return header, seq


def find_candidates(seq: str, start: int = 1, end: int = None,
                    flank_l: int = FLANK_LEFT, flank_r: int = FLANK_RIGHT):
    """
    서열의 두 가닥에서 'NGG' PAM 앞의 20 nt 표적을 모두 찾는다.

    - start, end : 1부터 시작하는 탐색 구간(전사체 위치). 23 nt 가 구간 안에 완전히 들어와야 한다.
    - 반대 가닥(-)에서 찾은 표적은 역상보로 뒤집어, 표적+PAM 이 항상 '위쪽 가닥'에 오게 맞춘다.
    - 실습 화면용으로 앞(flank_l)·뒤(flank_r) 실제 서열도 함께 돌려준다.
    - 'TTTT' 를 포함한 표적은 제외한다(U6 프로모터 종결 신호가 되어 gRNA 발현에 불리).
    """
    total = len(seq)
    if end is None:
        end = total

    results = []
    seen = set()
    acgt = set("ACGT")

    for strand, s in (("+", seq), ("-", revcomp(seq))):
        for i in range(flank_l, len(s) - 23 - flank_r + 1):
            window = s[i:i + 23]
            if window[21:23] != "GG":
                continue
            proto, pam = window[:20], window[20:23]
            left = s[i - flank_l:i]
            right = s[i + 23:i + 23 + flank_r]
            if set(proto + pam + left + right) - acgt:
                continue
            if "TTTT" in proto:
                continue

            # 앞쪽(+) 가닥 기준의 위치(1부터)
            if strand == "+":
                p1, p2 = i + 1, i + 23
            else:
                p1, p2 = total - (i + 23) + 1, total - i
            if p1 < start or p2 > end:
                continue

            key = (proto, pam)
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "protospacer": proto,
                "pam": pam,
                "strand": strand,
                "start": p1,
                "end": p2,
                "left": left,
                "right": right,
            })

    return results
