"""
QSI 심화 개정 — S등급 10종목, as_of 2026-10-10

기존 수집기(sec_events/phase2/ecd/...)가 채우지 못한 **최신 분기 공시 사실**과 **반증조건 직접 대조 근거**를
종목별 claim으로 추가한다. 모든 quote는 SEC 원문(8-K 보도자료·6-K·위임장)과 글자 단위로 대조한다(없으면 예외).

원칙: 사실의 인용만 한다. 좋고 나쁨은 effect(weakens/neutral/strengthens)로만 표시하며, effect는
**반증조건이 이미 명시한 지표**에 한해 weakens를 쓴다. 판정·비중·ledger는 건드리지 않는다.
실행: python -m scripts.qsi_deep_claims_2026_10_10 [--dry-run] [TICKER ...]
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from engine.filing_dates import _http_json, _http_text  # noqa: E402
from scripts import qsi_rollout_2026_10_06 as R  # noqa: E402
from scripts.qsi_sec_events import _claim, _ev, merge  # noqa: E402

AS_OF = "2026-10-10"
_TXT = {}


def body(url):
    if url not in _TXT:
        raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", _http_text(url))
        _TXT[url] = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    return _TXT[url]


def cit(doc, location, url, quote):
    q = re.sub(r"\s+", " ", quote).strip()
    if q not in body(url):
        raise ValueError(f"{doc}: 인용문이 원문에 없다 — {q[:90]!r}")
    return {"source_key": "sec_edgar", "document": doc, "location": location,
            "observed_date": AS_OF, "url": url, "quote": q}


def sec_url(ticker, form, filed, name):
    cik = R.cik_of(ticker)
    sub = _http_json(f"https://data.sec.gov/submissions/CIK{cik}.json")["filings"]["recent"]
    for i, f in enumerate(sub["form"]):
        if f == form and sub["filingDate"][i] == filed:
            return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{sub['accessionNumber'][i].replace('-', '')}/{name}")
    raise LookupError(f"{ticker} {form} {filed}")


def E(summary, doc, loc, url, quote, direction="neutral", metric=None, value=None, note=""):
    """증거 방향(supports/neutral)은 '인용문이 claim 문장을 뒷받침하는가'이다.
    논거 방향(weakens/strengthens)은 증거가 아니라 lens finding의 effect이므로 note에만 남긴다."""
    ev_dir = "neutral" if direction == "neutral" else "supports"
    tag = "" if direction == "neutral" else f"[논거 방향: {direction}] "
    return _ev(summary, cit(doc, loc, url, quote), ev_dir, metric, value, tag + note)


def build_all():
    out = {}

    # ---------------- TTD ----------------
    u_q2 = "https://www.sec.gov/Archives/edgar/data/0001671933/000167193326000085/ttd-20260806x8kexx991.htm"
    d_q2 = "TTD 8-K Ex.99.1 (2026 Q2 실적, 2026-08-06)"
    _, u_px, _ = R.doc_of("TTD", "DEF 14A")
    d_px = "TTD DEF 14A 특별총회 위임장 (2026-09-18)"
    out["TTD"] = dict(
        claims=[
            _claim("TTD.Q2GROWTH", "Q2 2026 매출 +3%(전년 +19%)로 급감속, Q3 가이던스는 하한 $650M — 전년 동기 대비 역성장", "HIGH",
                   E("Q2 매출 증가율 3% (전년 동기 19%)", d_q2, "Financial table", u_q2,
                     "Increase in revenue year over year 3 % 19 % 7 % 22 %", "weakens",
                     metric="revenue_growth_yoy", value=0.03,
                     note="회사 공시 표. 반증조건 (3) '미국 매출성장률 낮은 한자릿수 밑' 지표와는 범위가 다르다(전사)"),
                   E("Q3 2026 매출 가이던스 하한 $650M", d_q2, "2026 Financial Guidance", u_q2,
                     "Revenue at least $650 million", "weakens", metric="q3_revenue_floor_usd", value=650e6,
                     note="전년 Q3 매출 대비 약 -12%(전년 값은 이 문서에 없고 외부 보도 기준)")),
            _claim("TTD.REPRICE", "이사회가 임원 포함 임직원의 행사가 초과 스톡옵션 최대 15,582,540주를 현재 주가로 재가격하는 안건을 상정(2026-10-19 특별총회)", "HIGH",
                   E("재가격 대상 옵션 규모", d_px, "Proposal One", u_px,
                     "up to 15,582,540 shares of our Class A common stock", "weakens",
                     metric="options_repriced_shares", value=15582540,
                     note="주가 폭락 후 옵션을 현재가로 낮추는 것은 주주 입장에서 보상-성과 정렬을 약화시킨다는 것이 일반적 관점이나 이 문서는 '유지·유인 효과 복원'이라 설명한다"),
                   E("대상에 임원 포함", d_px, "Proposal One", u_px,
                     "including our executive officers and employees", "weakens"),
                   E("CEO Green의 성과옵션은 대상에서 제외", d_px, "Proposal One", u_px,
                     "Performance Options, ISOs, and awards held by our non-employee members of the board of directors remain ineligible",
                     "neutral", note="CEO 성과옵션이 제외된다는 점은 반대 증거 — 임원 일반은 포함")),
        ],
        findings=[
            {"lens": "competitive_landscape", "effect": "weakens", "claim_ids": ["TTD.Q2GROWTH"],
             "summary": "Q2 매출 +3%, Q3 가이던스 역성장 — 반증조건 (3)(4)와 같은 방향의 실측"},
            {"lens": "governance", "effect": "weakens", "claim_ids": ["TTD.REPRICE"],
             "summary": "임원 포함 옵션 재가격 안건 상정(특별총회 10/19)"}],
        inversion=["Amazon DSP 등 대형 플랫폼으로의 광고예산 이동이 지속돼 매출이 역성장(Q3 가이던스 하한이 전년 대비 -12%)하는 시나리오",
                   "옵션 재가격·성과옵션 신규 부여로 보상이 주가 하락과 분리돼 희석과 거버넌스 신뢰가 동시에 훼손되는 시나리오"])

    # ---------------- DLO ----------------
    base = "https://www.sec.gov/Archives/edgar/data/1846832/000184683226000031/"
    u_pr, u_6k = base + "ex_991-dlocalxearningsxres.htm", base + "dlo-20260630.htm"
    d_pr, d_6k = "DLO 6-K Ex.99.1 (2026 Q2 실적, 2026-08-13)", "DLO 6-K 반기 재무제표 (2026-08-13)"
    out["DLO"] = dict(
        claims=[
            _claim("DLO.TAKERATE", "총이익/TPV가 0.72%로 하락 — 전분기 0.84%, 전년 1.07% (회사 설명: 현지간 거래 비중·대형 가맹점 램프업·규모의 자연스러운 마진 역학)", "HIGH",
                   E("총이익/TPV 0.72%", d_pr, "Highlights", u_pr,
                     "Gross profit over TPV was at 0.72%, decreasing from 1.07% in the second quarter of 2025 and from 0.84% in the first quarter of 2026",
                     "weakens", metric="gross_profit_over_tpv", value=0.0072,
                     note="반증조건 (2) '순 테이크레이트 두 분기 연속 하락'과 지표 정의가 다르다(총이익/TPV vs net take rate). Q4'25 0.88%는 Q1 공시 기준(별도 확인 필요)"),
                   E("총이익 +29%, 가이던스 하단 25%는 상회", d_pr, "Highlights", u_pr,
                     "Record gross profit: US$127 million (+29% year-over-year)", "neutral",
                     metric="gross_profit_growth_yoy", value=0.29, note="Q1 +40%에서 둔화")),
            _claim("DLO.OCF", "반기 영업현금흐름 +$233.3M이나 매입채무(가맹점 정산 예수) 증가 +$700.5M가 섞여 있다", "HIGH",
                   E("영업현금흐름", d_6k, "Cash flow statement", u_6k,
                     "Net cash generated from operating activities 233,304 219,872", "neutral",
                     metric="ocf_h1_usd_thousands", value=233304),
                   E("무역 및 기타 채무 증가", d_6k, "Cash flow statement", u_6k,
                     "Increase in trade and other payables 700,507 93,294", "neutral",
                     note="가맹점 대기자금 증가 — 영업현금흐름이 회사 자체 이익보다 정산 타이밍에 좌우됨(ledger 한계와 일치)")),
            _claim("DLO.GUIDE", "가이던스 상향: TPV 60–70%, 총이익 25–30%", "MEDIUM",
                   E("가이던스", d_pr, "Guidance update", u_pr,
                     "TPV guidance raised to 60–70% year-over-year and Gross profit to 25–30% year-over-year",
                     "strengthens", note="총이익 Q2 +29%가 이 범위 상단 근처")),
        ],
        findings=[
            {"lens": "competitive_landscape", "effect": "weakens", "claim_ids": ["DLO.TAKERATE", "DLO.GUIDE"],
             "summary": "총이익/TPV 0.88→0.84→0.72% 하락(마진 압력), 단 물량 +92%·가이던스 상향"},
            {"lens": "accounting_quality", "effect": "neutral", "claim_ids": ["DLO.OCF"],
             "summary": "영업현금흐름이 가맹점 정산 예수 증감에 크게 좌우"}],
        inversion=["대형 가맹점 비중 확대로 총이익/TPV가 계속 내려 물량 성장(+92%)이 총이익 성장(+29%)으로 환산되지 못하는 시나리오",
                   "가맹점 정산 예수가 줄어드는 국면에서 영업현금흐름이 급반전하는 시나리오"])

    # ---------------- PGR ----------------
    u_pgr = sec_url("PGR", "8-K", "2026-09-18", "pgr202608ex99earningsrelea.htm")
    d_pgr = "PGR 8-K Ex.99 (2026년 8월 월간 실적, 2026-09-18)"
    out["PGR"] = dict(
        claims=[_claim("PGR.AUGCR", "2026년 8월 합산비율 89.3(전년 83.1, +6.2pt)", "HIGH",
                       E("월간 합산비율", d_pgr, "Monthly results", u_pgr, "Combined ratio 89.3 83.1 6.2 pts.",
                         "weakens", metric="combined_ratio_aug_2026", value=89.3,
                         note="반증조건 (3)은 분기 합산비율 90 이상 — 월간 수치라 직접 충족은 아니다. 전년 83.1이 이례적으로 낮았던 비교 기저 효과 포함"))],
        findings=[{"lens": "underwriting_discipline", "effect": "weakens", "claim_ids": ["PGR.AUGCR"],
                   "summary": "8월 합산비율 89.3로 올해 최악 — 반증조건 임계(90)에 근접"}],
        inversion=["손해율 반등이 보험료 인상 둔화와 겹쳐 합산비율이 90대로 정착, 텔레매틱스 모트가 손해율 우위로 이어지지 않는 시나리오"])

    # ---------------- ACGL ----------------
    u_a = "https://www.sec.gov/Archives/edgar/data/0000947484/000094748426000118/ex-991release63026.htm"
    d_a = "ACGL 8-K Ex.99.1 (2026 Q2 실적, 2026-07-28)"
    out["ACGL"] = dict(
        claims=[
            _claim("ACGL.Q2CAT", "Q2 2026 당해연도 재해손실 $201M(재보험·재가입보험료 차감 후)", "HIGH",
                   E("당해연도 재해손실", d_a, "Highlights", u_a,
                     "Pre-tax current accident year catastrophic losses for the Company’s insurance and reinsurance segments, net of reinsurance and reinstatement premiums, of $201 million",
                     metric="cat_losses_q2_usd", value=201e6)),
            _claim("ACGL.UW", "재해·전기발전 제외 합산비율 82.5%(전년 80.9%), 재보험 순보험료 -10.4%", "HIGH",
                   E("ex-cat 합산비율", d_a, "Highlights", u_a,
                     "of 82.5%, compared to 80.9% for the 2025 second quarter", "weakens",
                     metric="combined_ratio_ex_cat_pyd", value=0.825,
                     note="반증조건 (1)은 재보험 부문 ex-cat 세 분기 연속 악화 — 부문 수치는 이 문서에서 대조하지 않았다"),
                   E("재보험 순보험료 감소", d_a, "Reinsurance segment", u_a,
                     "net premiums written were 10.4% lower than in the 2025 second quarter", "neutral",
                     note="회사는 일부 비갱신·지분 축소를 원인으로 든다(선별적 언더라이팅일 수도, 연화 시장일 수도 있다)")),
        ],
        findings=[{"lens": "catastrophe_risk", "effect": "neutral", "claim_ids": ["ACGL.Q2CAT"],
                   "summary": "Q2 재해손실 $201M — 분기 세전이익 적자로 이어지지 않음(반증조건 (2) 미충족)"},
                  {"lens": "underwriting_discipline", "effect": "weakens", "claim_ids": ["ACGL.UW"],
                   "summary": "ex-cat 합산비율 +1.6pt 악화, 재보험 순보험료 -10.4%"}],
        answers=[{"qid": "cat.cat_exposure", "status": "answered", "claim_ids": ["ACGL.Q2CAT"],
                  "answer": "Q2 2026 당해연도 재해손실 $201M(재보험 차감 후). 1차 확인은 이 분기 수치뿐이며 보호 구조(재보험 한도·보유) 자체는 대조하지 않았다",
                  "note": "연간 PML·재보험 프로그램 구조는 미확인"}],
        inversion=["대재해(허리케인·산불)로 분기 세전손실이 나는 시나리오 — 평활화된 FCF가 이 위험을 반영하지 못한다(반증조건 (2))"])

    # ---------------- CINF ----------------
    u_c = "https://www.sec.gov/Archives/edgar/data/0000020286/000002028626000043/exhibit9912q26.htm"
    d_c = "CINF 8-K Ex.99.1 (2026 Q2 실적, 2026-07-27)"
    out["CINF"] = dict(
        claims=[
            _claim("CINF.Q2CAT", "Q2 재해손실이 Ohio에서 5년 평균의 약 4배 — 합산비율 100.8%의 주원인", "HIGH",
                   E("Ohio 재해손실", d_c, "CEO commentary", u_c,
                     "Ohio was particularly impacted by bad weather this Spring with catastrophe losses reaching nearly four times higher than our 5-year second-quarter average for the state",
                     "neutral")),
            _claim("CINF.UW", "Q2 합산비율 100.8%(전년 94.9%), 신규계약 -13%", "HIGH",
                   E("Q2 합산비율", d_c, "Insurance operations highlights", u_c,
                     "100.8% second-quarter 2026 property casualty combined ratio, increased from 94.9% for the second quarter of 2025",
                     "weakens", metric="combined_ratio_q2", value=1.008,
                     note="반증조건 (1) 임계는 하반기 105% — 아직 미충족"),
                   E("신규계약 감소", d_c, "Insurance operations highlights", u_c,
                     "second-quarter 2026 property casualty new business written premiums, down 13%", "weakens")),
        ],
        findings=[{"lens": "catastrophe_risk", "effect": "neutral", "claim_ids": ["CINF.Q2CAT"],
                   "summary": "Q2 재해 집중(Ohio) — 회사는 포트폴리오 분산을 완화책으로 제시"},
                  {"lens": "underwriting_discipline", "effect": "weakens", "claim_ids": ["CINF.UW"],
                   "summary": "Q2 합산비율 100.8%, 신규계약 -13%"}],
        answers=[{"qid": "cat.cat_exposure", "status": "answered", "claim_ids": ["CINF.Q2CAT"],
                  "answer": "Q2 재해손실이 Ohio에서 5년 평균의 약 4배로 합산비율을 100.8%로 끌어올렸다. 연간 노출·재보험 구조는 대조하지 않았다",
                  "note": "분기 사실만 1차 확인"}],
        inversion=["재해 집중 지역(Ohio 등) 반복 피해로 합산비율이 105%를 넘고 신규계약 감소가 이어지는 시나리오(반증조건 (1))"])

    # ---------------- SIGI ----------------
    u_s = "https://www.sec.gov/Archives/edgar/data/230557/000023055726000018/q22026pressreleaseexh991.htm"
    d_s = "SIGI 8-K Ex.99.1 (2026 Q2 실적, 2026-07-23)"
    out["SIGI"] = dict(
        claims=[
            _claim("SIGI.Q2CAT", "Q2 재해손실 5.6pt, 전기 신탁준비금 발전 없음", "HIGH",
                   E("재해손실", d_s, "Highlights", u_s,
                     "Catastrophe losses were 5.6 points", "neutral", metric="cat_points_q2", value=5.6)),
            _claim("SIGI.UW", "Q2 합산비율 98.0%(전년 100.2%)로 개선, 순보험료(NPW) -5%", "HIGH",
                   E("합산비율 개선", d_s, "Highlights", u_s,
                     "The GAAP combined ratio was 98.0%, compared to 100.2% in the second quarter of 2025", "strengthens",
                     metric="combined_ratio_q2", value=0.98),
                   E("순보험료 감소", d_s, "Highlights", u_s,
                     "NPW decreased 5% from a year ago", "weakens",
                     note="반증조건 (1)은 NPW 역성장 추가 확대 — 이후 분기 데이터 필요")),
        ],
        findings=[{"lens": "catastrophe_risk", "effect": "neutral", "claim_ids": ["SIGI.Q2CAT"],
                   "summary": "Q2 재해손실 5.6pt"},
                  {"lens": "underwriting_discipline", "effect": "neutral", "claim_ids": ["SIGI.UW"],
                   "summary": "합산비율은 개선(98.0%), 순보험료는 -5% — 수익성 방어와 규모 축소가 같이 나타난다"}],
        answers=[{"qid": "cat.cat_exposure", "status": "answered", "claim_ids": ["SIGI.Q2CAT"],
                  "answer": "Q2 재해손실 5.6pt(합산비율 98.0% 중). 연간 노출·재보험 프로그램은 대조하지 않았다",
                  "note": "분기 사실만 1차 확인"}],
        inversion=["순보험료 역성장이 확대되며 규모의 경제와 투자수익 기반이 줄어드는 시나리오(반증조건 (1))"])

    # ---------------- DUOL ----------------
    u_d = "https://www.sec.gov/Archives/edgar/data/0001562088/000162828026053299/q2fy26duolingo6-30x26share.htm"
    d_d = "DUOL 8-K Ex.99 (2026 Q2 주주서한, 2026-08-05)"
    out["DUOL"] = dict(
        claims=[_claim("DUOL.Q2", "DAU +23%, 유료구독자 12.7M(+17%)이나 총 bookings +8%, 순이익 $33.2M(전년 $44.8M)", "HIGH",
                       E("DAU", d_d, "Q2 Highlights", u_d, "Daily Active Users 47.7M 58.7M 23% YoY", "strengthens",
                         metric="dau_growth_yoy", value=0.23, note="반증조건 (2) 임계 20% 위"),
                       E("총 bookings", d_d, "Q2 Highlights", u_d, "Total Bookings $268.0M $289.1M 8% YoY", "weakens",
                         metric="bookings_growth_yoy", value=0.08,
                         note="엔진 Realistic Growth 25%(캡)와 괴리 — 1개년 지표라 override 자격은 없다"),
                       E("순이익", d_d, "Q2 Highlights", u_d, "Net Income $44.8M $33.2M", "weakens"))],
        findings=[{"lens": "competitive_landscape", "effect": "neutral", "claim_ids": ["DUOL.Q2"],
                   "summary": "사용자 성장은 가속(DAU +23%)이나 수익화 지표(bookings +8%·순이익 감소)는 둔화"}],
        inversion=["DAU는 늘지만 수익화가 따라오지 못해 bookings 성장이 한자릿수에 머무는 시나리오(엔진 25% 가정과 괴리)"])

    # ---------------- MNDY ----------------
    u_m = "https://www.sec.gov/Archives/edgar/data/0001845338/000117891326003971/exhibit_99-1.htm"
    d_m = "MNDY 6-K Ex.99.1 (2026 Q2 실적, 2026-08-10)"
    out["MNDY"] = dict(
        claims=[_claim("MNDY.Q2", "고액 고객 NDR 115%(임계 110% 위), 그러나 Q3 매출 가이던스 +16~17%로 둔화", "HIGH",
                       E("고액 고객 NDR", d_m, "Business highlights", u_m,
                         "Net dollar retention rate for customers with more than $50,000 in ARR was 115%", "strengthens",
                         metric="ndr_50k_plus", value=1.15, note="반증조건 (1) 충족 안 됨"),
                       E("Q3 가이던스", d_m, "Financial outlook", u_m,
                         "representing year-over-year growth of 16% to 17%", "weakens",
                         note="Q2 +22%에서 둔화, 엔진 RG 25%(캡)와 괴리 — 1개 분기 가이던스")),],
        findings=[{"lens": "competitive_landscape", "effect": "neutral", "claim_ids": ["MNDY.Q2"],
                   "summary": "고액 고객 유지율 건전, 다만 매출 성장 가이던스가 16~17%로 감속"}],
        inversion=["고액 고객 NDR은 유지되나 신규 고객 유입이 줄어 매출 성장이 10%대 중반으로 정착하는 시나리오"])

    # ---------------- PDD ----------------
    u_p = "https://www.sec.gov/Archives/edgar/data/0001737806/000110465926100534/tm2623874d1_ex99-1.htm"
    d_p = "PDD 6-K Ex.99.1 (2026 Q2 실적, 2026-08-24)"
    out["PDD"] = dict(
        claims=[_claim("PDD.Q2", "Q2 매출 +8%, 순이익 -12%", "HIGH",
                       E("매출", d_p, "Highlights", u_p, "an increase of 8% from RMB104.0 billion", "neutral",
                         metric="revenue_growth_yoy", value=0.08, note="반증조건 (1) 임계 5% 위"),
                       E("순이익", d_p, "Highlights", u_p, "a decrease of 12% from RMB30.8 billion in the same quarter of 2025",
                         "weakens", metric="net_income_growth_yoy", value=-0.12,
                         note="반증조건 (1) 임계 -15%보다 덜 나쁘지만 근접"))],
        findings=[{"lens": "competitive_landscape", "effect": "neutral", "claim_ids": ["PDD.Q2"],
                   "summary": "매출은 임계 위, 순이익 -12%로 임계에 근접"}],
        inversion=["규제·경쟁 비용으로 순이익 감소폭이 -15%를 넘어서고 매출 성장이 5% 아래로 내려가는 시나리오(반증조건 (1))"])

    # ---------------- PINS ----------------
    u_n1 = sec_url("PINS", "8-K", "2026-08-28", "pins-20260826.htm")
    u_n2 = sec_url("PINS", "8-K", "2026-10-05", "pins-20261001.htm")
    out["PINS"] = dict(
        claims=[_claim("PINS.CFO", "CFO Donnelly 사임 발표(2026-08-26) → 후임 James Dibbo(Amazon 출신) 2026-10-26 취임", "HIGH",
                       E("CFO 사임", "PINS 8-K (2026-08-28)", "Item 5.02", u_n1,
                         "Julia Brau Donnelly, the Company's Chief Financial Officer, submitted her resignation", "weakens"),
                       E("후임 선임", "PINS 8-K (2026-10-05)", "Item 5.02", u_n2,
                         "appointed James Dibbo, age 56, as its Chief Financial Officer, effective October 26, 2026",
                         "neutral", note="후임이 빠르게 확정된 점은 승계 공백 우려를 줄인다"))],
        findings=[{"lens": "governance", "effect": "neutral", "claim_ids": ["PINS.CFO"],
                   "summary": "CFO 교체(후임 확정) — 11/4 실적이 첫 점검"}],
        inversion=["광고 성장이 경쟁사 대비 다시 둔화되는 가운데 SBC가 FCF의 70%를 넘어 주당 가치가 정체하는 시나리오"])
    return out


def main(argv):
    dry = "--dry-run" in argv
    only = [a for a in argv if not a.startswith("--")]
    data = build_all()
    for t, d in data.items():
        if only and t not in only:
            continue
        prior = Q.latest_record(t)
        if prior is None:
            print(f"{t:5} 기존 기록 없음 — 건너뜀")
            continue
        core, changed = merge(prior, d["claims"], d.get("answers", []), d["findings"], AS_OF)
        # 사업 붕괴 시나리오를 처음 적는 종목은 '미조사' 자리표시 문구를 대체한다.
        old = [x for x in core.get("inversion", []) if "미조사" not in x]
        core["inversion"] = old + [x for x in d["inversion"] if x not in old]
        rec = Q.build_record(core)
        c, p = rec["coverage"], prior["coverage"]
        print(f"{t:5} 답 {p['n_answered']:>2}/{p['n_questions']:<2} -> {c['n_answered']:>2}/{c['n_questions']:<2}  claims {len(prior['claims'])}->{len(rec['claims'])}")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
