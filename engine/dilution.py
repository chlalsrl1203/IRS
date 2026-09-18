"""
희석 드래그 — 주주 지분의 순변화를 재는 독립 진단축 (v3.84, 2026-09-11)

## 무엇을 재는가

`realistic_growth_estimate()`는 **총** FCF/매출 CAGR로 성장을 추정하는데 주주가
실제로 받는 것은 **주당** 흐름이다. 주식수가 늘면 총 FCF가 성장해도 주당 FCF는
정체하거나 감소할 수 있고, 그 차이는 RG 어디에도 반영되지 않는다.

    희석 드래그 = 주당 FCF CAGR − 총 FCF CAGR        (항상 <= 0 이면 희석)

SBC와 중복이 아니다(PHASE 4 실측 순위상관 −0.597):
  - `sbc_to_fcf_pct` : 보상**비용의 크기**
  - 희석 드래그      : 주주 **지분의 순변화**(신주발행 − 자사주매입)
반례 — VRT는 SBC 2.4%인데 드래그 −7.66%p(SBC로는 안 보이는 희석), WDAY는 SBC
58.6%인데 −2.98%p(자사주매입이 상쇄). BRO 정성조사가 지적한 *"M&A 주식대가로
인한 별도 다일루션(SBC와 무관)"* 이 정확히 이 채널이다.

## ⚠️ 공식 판정에 반영하지 않는다

`CORE MODEL CHANGE GATE`의 6번(validation strategy)이 없다 — 이 지표가 실현
수익률과 관계있다는 증거가 **0건**이다. 결정 #29·#33이 확립한 구조 D(독립
진단축)만 유지한다. Gap·판정·등급·비중 어디에도 들어가지 않으며, 그 경계는
테스트로 고정돼 있다(`tests/test_dilution.py`).

## ⚠️ 이 모듈의 존재 이유는 "주식수 시계열은 희석 이외의 사유로도 점프한다"

PHASE 4 초판이 그 검증 없이 계산해 완전히 틀린 값을 냈고 **자본배분 경로에
배선까지 했다가 되돌렸다**:

    TTD  FY2021 x10.2  <- 10:1 주식분할          TCOM FY2021 x8.4 <- ADS 비율변경
    DUOL FY2021 x1.8   <- IPO(2021-07)           MNDY FY2021 x2.5 <- IPO(2021-06)
    PDD  FY2024/25     <- ADS/보통주 단위 혼재

그때 얻은 교훈은 *"커버리지와 상관만 확인하고 원자료 시계열을 눈으로 보지
않았다"* 였다. 그래서 이 모듈은 **정규화한 뒤 다시 점프를 검사**하고, 검사를
통과하지 못하면 값을 내지 않는다(`NOT_MEASURABLE`).

## 정규화 원리 — 계수를 추측하지 않고 회사의 소급재표시에서 읽는다

주식분할은 GAAP상 **소급 재표시**된다. 그래서 SEC companyfacts에는 같은
회계연도가 두 번 들어 있다 — 분할 **전** 공시본과 분할 **후** 비교표. 그 둘의
비율이 곧 분할 계수이며, 이는 회사가 스스로 보고한 사실이지 추정이 아니다.

    TTD FY2019 : 47,806,000 (분할 전 공시) vs 478,061,000 (분할 후 비교표)
                 -> 계수 10.0000

분할 후 10-K는 보통 2~3년치 비교표만 담으므로 그보다 오래된 해는 재표시본이
없다. 그 해들에만 계수를 소급 적용해 전 구간을 **최신 기준**으로 맞춘다.

⚠️ 계수 탐지는 **계산 구간 [base, end] 안으로 한정**한다. 구간 밖의 오래된
분할·단위오류까지 끌어들이면 계수가 서로 달라져 정규화 자체가 무산된다(RLI·
MNST가 실제로 그랬다 — 2010년대 초 단위오류가 2022년 2:1 분할 탐지를 가렸다).

## v3.85에서 더한 두 경로 — 둘 다 "증명되면 쓰고, 아니면 거부한다"

**① 회계연도 재라벨링(FY_LABEL_COLLISION 해소).** 52/53주 결산이 연초로 밀리면
`end_year`가 두 회계연도를 한 라벨로 묶는다(v3.61 CDNS·GEN). v3.61은 **일반적인
자동 재라벨링을 금지**했는데 규약이 회사마다 반대이기 때문이다(CDNS는 1월 초
결산을 전년으로, GEN은 3월 말 결산을 당해로 센다). 그 금지는 그대로 유효하다 —
여기서 답하는 질문이 다르다. 필요한 것은 "이 회사의 규약이 무엇인가"가 아니라
**"이 라벨링이 ledger의 연도 키와 맞는가"** 이고, 그 답은 같은 companyfacts의
매출을 같은 규칙으로 라벨해 `inputs.revenue_by_year`와 대조하면 나온다.
2026-09-12 실측 — 중간일자 라벨링이 CDNS 14/0, EXEL 12/0, LFUS 22/0(일치/불일치)
으로 완전 재현했고 `end_year`는 셋 다 불일치를 냈다.

**② 공시본 스플라이스(공시본 하나가 통째로 다른 단위).** PDD 2025-04-28 20-F가
FY2022~24를 전부 1/1000 스케일로 보고했고 **다음 공시(2026-04-29)가 되돌렸다**.
"연도별 최신값" 규칙은 그 해만 오염된 채로 남긴다. 되돌려진다는 것이 분할(영구
소급재표시)과 구분되는 지점이라, 공시본을 최신 것부터 겹침 비율로 이어붙이면
기준이 통일된다. ⚠️ **마지막 수단으로만** 탄다 — 값을 비율로 재계산하므로 이미
매끄러운 종목의 기존 측정값을 미세하게 흔들고(실측 4~5번째 자리) 겹침 없는
공시본을 버려 오래된 연도를 잃을 수 있다(DSGX 실측).

## 남은 공백은 '아직 안 가져온 것'이 아니다(2026-09-12 전수 진단)

7종목이 남았고 셋 다 이 출처로는 **원리적으로** 못 채운다 — IPO가 RG 창 안에
있어 상장 전/후 가중평균의 기준이 다른 경우(DUOL·MNDY·PATH), 다중클래스·Up-C라
주식수가 클래스별 차원으로 보고돼 무차원 companyfacts에 총계가 없는 경우
(ERIE·HLNE·RYAN, 같은 캐시에 연차 매출은 정상적으로 있어 캐시 누락이 아님을
확인했다), 기준연도에 아직 독립 등록인이 아니었던 경우(NXT, 2023-02 Flex 분사).
"""

import collections
import statistics
from datetime import date

from engine.data.providers.sec import METRIC_TAGS
from engine.filing_dates import ANNUAL_FORMS, _days_between

# us-gaap 희석주식수를 1순위로, IFRS 발행사(20-F)는 ifrs-full 대응 태그로 대체한다.
# ⚠️ 기본(basic)주식수로는 내려가지 않는다 — 희석/기본을 연도별로 섞으면 그 자체가
#    기준 불일치가 되어 이 모듈이 막으려는 오류를 다른 경로로 재발시킨다.
SHARE_TAGS = (
    "WeightedAverageNumberOfDilutedSharesOutstanding",   # us-gaap
    "AdjustedWeightedAverageShares",                     # ifrs-full (희석)
)

# PHASE 4가 정한 도메인 제약 — 정상적인 연간 희석이 50%를 넘는 것은 사실상
# 불가능하므로 그 이상의 점프는 희석이 아닌 사유로 본다.
# ⚠️ 결과를 보고 조정하지 말 것(이 프로젝트가 LYNCH_TYPE_CAPS·P/B 임계값에서
#    반복 거부해온 수법이다).
STRUCTURAL_JUMP_RATIO = 1.5

# 같은 회계연도의 두 공시본이 이만큼 넘게 다르면 소급 재표시로 본다.
RESTATEMENT_TOL = 0.02
# 재표시 계수가 연도마다 이보다 더 흩어지면 단일 분할이 아니다 -> 정규화 포기.
FACTOR_CONSISTENCY_TOL = 0.05

# 재라벨링을 채택하려면 ledger 매출을 이만큼은 재현해야 한다(불일치는 0이어야 한다).
RELABEL_MIN_MATCHES = 5

# 리포트가 "드래그가 눈에 띈다"고 표시하는 선. PHASE 4(2026-08-21)가 쓰던 값
# 그대로이며 **검증된 컷오프가 아니다** — 실현수익률과의 관계 증거가 0건이라
# 이 선을 넘었다고 해서 배제·감점 근거가 되지 않는다(순수 표시용).
# ⚠️ 두 곳에 따로 적으면 언젠가 갈린다(v3.35 ①에서 판정 경계값이 실제로
#    갈렸다) — 리포트와 포트폴리오 경계검토가 이 상수 하나만 참조한다.
DRAG_MATERIAL_PCT = -0.05

# 이 지표의 인식론적 지위(계약서 40절 5단계 사다리).
VALIDATION_STATUS = {
    "dilution_drag": "IMPLEMENTED_NOT_VALIDATED",  # 성과와의 관계 증거 0건
}

STATUS_OK = "OK"
STATUS_NO_WINDOW = "NO_CAGR_WINDOW"
STATUS_NO_SHARES = "NO_SHARE_DATA"
STATUS_MISSING_YEAR = "MISSING_YEAR"
STATUS_BASE_NONPOSITIVE = "BASE_FCF_NONPOSITIVE"
STATUS_END_NONPOSITIVE = "END_FCF_NONPOSITIVE"
STATUS_JUMP = "STRUCTURAL_SHARE_JUMP"
STATUS_FY_COLLISION = "FY_LABEL_COLLISION"


def end_year(start, end):
    """결산일의 달력연도 — 엔진 전체가 쓰는 기본 라벨 규칙."""
    return int(end[:4])


def midpoint_year(start, end):
    """회계기간 **중간일자**의 달력연도.

    52/53주 결산이 연초로 밀려 `end_year`가 두 회계연도를 한 라벨로 묶을 때의
    대안이다. ⚠️ 이것을 기본으로 삼지 않는다 — `verify_year_labeling()`이
    해당 종목 ledger의 연도 키를 실제로 재현한다고 증명했을 때만 쓴다.
    """
    a = date(int(start[:4]), int(start[5:7]), int(start[8:10]))
    b = date(int(end[:4]), int(end[5:7]), int(end[8:10]))
    return (a + (b - a) / 2).year


def annual_facts(facts, tag, label=end_year):
    """{회계연도: [(공시일, 결산일, 값), ...]} — 같은 해의 모든 공시본을 버리지 않는다.

    소급재표시 계수를 읽으려면 한 해의 여러 공시본이 **전부** 필요하다. 하나만
    고르는 순간(최초든 최신이든) 계수를 복원할 수 없다.
    """
    out = {}
    for _tax, tags in (facts.get("facts") or {}).items():
        if tag not in tags:
            continue
        for _unit, entries in (tags[tag].get("units") or {}).items():
            for e in entries:
                if e.get("form") not in ANNUAL_FORMS:
                    continue
                start, end, filed, val = (e.get("start"), e.get("end"),
                                          e.get("filed"), e.get("val"))
                if not (start and end and filed) or val is None:
                    continue
                try:
                    if not 330 <= _days_between(start, end) <= 400:
                        continue
                except ValueError:
                    continue
                out.setdefault(label(start, end), []).append(
                    (filed, end, float(val)))
    return {y: sorted(v) for y, v in out.items()}


def annual_share_facts(facts, tag):
    """기본(결산일) 라벨로 읽은 연차 주식수."""
    return annual_facts(facts, tag, end_year)


def verify_year_labeling(facts, ledger, label):
    """이 라벨 규칙이 **해당 ledger 자신의 연도 키**를 재현하는가.

    희석 드래그가 성립하려면 `shares[y]`와 `fcf[y]`가 같은 회계기간이어야 한다.
    그러므로 검증해야 할 명제는 "이 회사의 회계연도 규약이 무엇인가"라는 일반론이
    아니라 **"이 라벨링이 ledger의 연도 키와 맞는가"** 다. companyfacts 매출을
    같은 규칙으로 라벨해 ledger `inputs.revenue_by_year`와 대조한다.

    반환 (일치, 불일치). ⚠️ 불일치가 하나라도 있으면 채택하지 않는다.
    """
    want = {int(k): v for k, v in
            ((ledger.get("inputs") or {}).get("revenue_by_year") or {}).items()}
    if not want:
        return 0, 0
    hits = misses = 0
    for tag in METRIC_TAGS["revenue"]:
        got = annual_facts(facts, tag, label)
        for y, v in want.items():
            if y not in got:
                continue
            if any(abs(x[2] - v) <= max(1.0, abs(v) * 1e-9) for x in got[y]):
                hits += 1
            else:
                misses += 1
    return hits, misses


def detect_fy_label_collision(per_year):
    """한 회계연도 라벨에 60일 이상 떨어진 결산일이 섞였는지.

    52/53주 회계연도 기업은 결산일이 연초로 밀리면 `int(end[:4])` 규칙이 두
    회계연도를 같은 라벨로 묶는다(v3.61이 CDNS·GEN에서 실측). 그 상태에서
    한쪽을 고르면 한 해씩 밀린 값이 조용히 들어간다.

    ⚠️ 자동 재라벨링은 하지 않는다 — 규약이 회사마다 반대이고(CDNS는 1월 초
    결산을 전년으로, GEN은 3월 말 결산을 당해로 센다) 관측이 2종목뿐이다.
    사실만 드러내고 해당 종목은 측정 불가로 남긴다.
    """
    bad = []
    for fy, rows in per_year.items():
        ends = sorted({end for _f, end, _v in rows})
        if len(ends) >= 2 and _days_between(ends[0], ends[-1]) > 60:
            bad.append(fy)
    return sorted(bad)


def normalize_to_latest_basis(per_year, base, end):
    """[base, end] 구간을 하나의 보고 기준으로 맞춘다.

    반환: (series, meta). 계수를 못 찾으면 최신 공시본을 그대로 쓴다(구간 안에
    분할이 없으면 그것이 이미 일관된 기준이다).

    ⚠️ **정규화는 스스로를 검증한 뒤에만 채택된다** — `consistent_share_series()`
    참고. 이 함수 단독으로는 한 해짜리 단위 오타를 분할 계수로 오인할 수 있다
    (BRO FY2021이 실제로 그랬다: 277,414 -> 277,400,000).
    """
    latest = {y: rows[-1][2] for y, rows in per_year.items()}
    earliest = {y: rows[0][2] for y, rows in per_year.items()}

    restated = {}
    for y in per_year:
        if not (base <= y <= end) or not earliest[y]:
            continue
        ratio = latest[y] / earliest[y]
        if abs(ratio - 1.0) > RESTATEMENT_TOL:
            restated[y] = ratio

    if not restated:
        return latest, {"restated_years": {}, "factor": None,
                        "basis": "latest_filed"}

    factor = statistics.median(restated.values())
    if not all(abs(r / factor - 1.0) <= FACTOR_CONSISTENCY_TOL
               for r in restated.values()):
        return latest, {
            "restated_years": restated, "factor": None, "basis": "latest_filed",
            "note": ("재표시 계수가 연도마다 달라 단일 분할로 볼 수 없다 "
                     "— 정규화하지 않고 원본 최신 공시본을 쓴다"),
        }

    oldest = min(restated)
    series = {y: (v * factor if y < oldest else v) for y, v in latest.items()}
    return series, {"restated_years": restated, "factor": factor,
                    "oldest_restated_year": oldest,
                    "basis": f"latest_filed x{factor:.4f} (FY{oldest} 이전)"}


def splice_filings_to_latest_basis(per_year):
    """공시본을 최신 것부터 겹침 비율로 이어붙여 하나의 기준으로 맞춘다.

    `normalize_to_latest_basis()`는 "연도별 최신값"을 쓰므로 **특정 공시본 하나가
    통째로 잘못된 단위**로 보고하면 그 해만 오염된 채로 남는다. PDD 2025-04-28
    20-F가 실측 사례다 — FY2022/23/24를 전부 1/1000 스케일로 보고했고 바로 다음
    공시(2026-04-29)가 원래 단위로 되돌렸다:

        2024-04-25  FY2023 = 5,839,629,562
        2025-04-28  FY2023 =     5,839,630   <- 이 공시본만 1/1000
        2026-04-29  FY2023 = 5,839,630,000

    겹침 비율로 이어붙이면 그 공시본의 고유 연도(FY2022)도 x1000으로 되돌아와
    전 구간이 하나의 기준이 된다. 비율은 회사 자신의 겹침에서 읽으므로 추측이
    아니다. ⚠️ 값의 **절대 크기**는 최신 공시본 기준을 따르지만 드래그는
    `shares[end]/shares[base]` 비율만 쓰므로 그 선택에 영향받지 않는다.
    """
    by_filing = collections.defaultdict(dict)
    for y, rows in per_year.items():
        for filed, _e, v in rows:
            by_filing[filed][y] = v
    filings = sorted(by_filing, reverse=True)
    if not filings:
        return {}, {}
    series = dict(by_filing[filings[0]])
    ratios = {}
    for filed in filings[1:]:
        rows = by_filing[filed]
        overlap = [series[y] / rows[y] for y in rows if y in series and rows[y]]
        if not overlap:
            continue  # 겹침이 없으면 기준을 맞출 수단이 없다 - 이어붙이지 않는다
        r = statistics.median(overlap)
        # ⚠️ 1에 가까운 비율은 그냥 1로 둔다 — 재표시 반올림 차이(예: 5,839,629,562
        #    vs 5,839,630,000)로 생긴 1.00000008 배를 곱하면 **어느 공시본에도
        #    없는 숫자**가 기록에 남는다. 기준이 실제로 바뀐 경우에만 재계산한다.
        if abs(r - 1.0) <= RESTATEMENT_TOL:
            r = 1.0
        ratios[filed] = r
        for y, v in rows.items():
            series.setdefault(y, v * r if r != 1.0 else v)
    return series, ratios


def consistent_share_series(per_year, base, end):
    """정규화를 **실제로 더 매끄러워질 때만** 채택한다.

    소급재표시 탐지는 한 해짜리 단위 오타와 진짜 분할을 구분하지 못한다 — 한
    해만 재표시됐으면 계수 일관성 검사가 자동으로 통과해버리기 때문이다. 그래서
    계수를 믿는 대신 **결과로 판정**한다: 조정 전/후의 남은 점프 수를 세어 더
    적은 쪽을 쓰고, 같으면 조정하지 않는다(근거 없이 손대지 않는다).

    실측 효과 — NOW/RLI/MNST/DECK/TCOM은 조정이 점프를 없애 채택되고, BRO는
    조정이 오히려 점프를 만들어 기각된다.
    """
    raw = {y: rows[-1][2] for y, rows in per_year.items()}
    adjusted, meta = normalize_to_latest_basis(per_year, base, end)

    n_raw = len(structural_jumps(raw, base, end))
    n_adj = len(structural_jumps(adjusted, base, end))
    if meta.get("factor") is not None and n_adj < n_raw:
        meta["adopted"] = True
        meta["jumps_before_after"] = [n_raw, n_adj]
        return adjusted, meta

    if meta.get("factor") is not None:
        meta["note"] = (f"소급재표시 계수 x{meta['factor']:.4f}를 찾았으나 적용해도 "
                        f"점프가 줄지 않아({n_raw} -> {n_adj}) 기각했다 — "
                        f"단위 오타를 분할로 오인하는 경로를 막는다")
    meta["adopted"] = False
    meta["basis"] = "latest_filed"
    meta["jumps_before_after"] = [n_raw, n_adj]

    # 위 두 경로로도 점프가 남을 때만 공시본 스플라이스를 시도한다.
    # ⚠️ 마지막 수단으로 두는 이유 — 스플라이스는 값을 비율로 재계산하므로
    #    이미 매끄러운 종목의 기존 측정값을 미세하게 흔들고(실측 4~5번째 자리),
    #    겹침이 없는 공시본을 버려 오래된 연도를 잃을 수 있다(DSGX 실측).
    #    근거 없이 손대지 않는다는 이 모듈의 원칙 그대로다.
    if min(n_raw, n_adj) > 0:
        spliced, ratios = splice_filings_to_latest_basis(per_year)
        n_sp = len(structural_jumps(spliced, base, end))
        if n_sp < min(n_raw, n_adj) and base in spliced and end in spliced:
            return spliced, {
                "adopted": True, "basis": "spliced_filings",
                "filing_ratios": {k: v for k, v in ratios.items()
                                  if abs(v - 1.0) > RESTATEMENT_TOL},
                "jumps_before_after": [min(n_raw, n_adj), n_sp],
                "note": ("공시본별 겹침 비율로 이어붙여 기준을 통일했다 — "
                         "공시본 하나가 통째로 다른 단위로 보고한 경우"),
            }
    return raw, meta


def structural_jumps(series, base, end):
    """정규화 **후** 남은 점프 — 남아 있으면 이 계산은 희석을 재지 못한다."""
    years = [y for y in sorted(series) if base <= y <= end]
    out = []
    for prev, cur in zip(years, years[1:]):
        if not series[prev]:
            continue
        ratio = series[cur] / series[prev]
        if ratio >= STRUCTURAL_JUMP_RATIO or ratio <= 1 / STRUCTURAL_JUMP_RATIO:
            out.append({"fy": cur, "ratio": ratio})
    return out


def resolve_cagr_window(ledger):
    """RG가 실제로 쓴 5년 창을 돌려준다 — 비교가 성립하려면 같은 구간이어야 한다.

    v3.19판 ledger에는 `cagr_5y_base_year`가 없다(v3.21에서 신설). 그 경우
    엔진과 같은 규칙(`years[-6]`)으로 파생하되, **저장된 `fcf_cagr_5y`를
    재현하는지 확인**한다 — 재현하지 못하면 창을 특정할 수 없다는 뜻이므로
    추측해서 쓰지 않고 거부한다.
    """
    dv = ledger["derived"]
    fcf = {int(k): v for k, v in dv["fcf_by_year"].items()}
    base, span = dv.get("cagr_5y_base_year"), dv.get("cagr_5y_span") or 5
    if base is not None:
        return base, span, "ledger", fcf

    years = sorted(fcf)
    if len(years) < 6:
        return None, None, "연차 6개년 미만이라 5년 창을 만들 수 없다", fcf
    base = years[-6]
    stored = dv.get("fcf_cagr_5y")
    if stored is None or fcf[base] <= 0:
        return None, None, "저장된 fcf_cagr_5y가 없어 파생 창을 검증할 수 없다", fcf
    check = (fcf[base + 5] / fcf[base]) ** (1 / 5) - 1
    if abs(check - stored) > 1e-9:
        return None, None, (f"파생 창(FY{base}~{base + 5})이 저장된 fcf_cagr_5y를 "
                            f"재현하지 못한다({check:.10f} vs {stored:.10f})"), fcf
    return base, 5, "derived_and_verified", fcf


def dilution_drag(ticker, ledger, facts):
    """한 종목의 희석 드래그. 잴 수 없으면 사유를 담아 돌려준다(0으로 채우지 않는다)."""
    base, span, how, fcf = resolve_cagr_window(ledger)
    if base is None:
        return {"ticker": ticker, "status": STATUS_NO_WINDOW, "detail": how}
    end = base + span

    if facts is None:
        return {"ticker": ticker, "status": STATUS_NO_SHARES,
                "detail": "companyfacts 캐시 없음"}

    per_year, used_tag = {}, None
    for tag in SHARE_TAGS:
        got = annual_share_facts(facts, tag)
        if base in got and end in got:
            per_year, used_tag = got, tag
            break
        if got and not per_year:
            per_year, used_tag = got, tag

    if not per_year:
        rev_years = sum(len(annual_facts(facts, t)) for t in METRIC_TAGS["revenue"])
        return {"ticker": ticker, "status": STATUS_NO_SHARES,
                "annual_revenue_years_in_facts": rev_years,
                "detail": (f"주식수 태그 {SHARE_TAGS} 어느 것도 연차 보고가 없다"
                           + (f" — 같은 companyfacts에 연차 매출은 {rev_years}건 "
                              "있으므로 캐시 누락이 아니다(다중클래스·Up-C 종목은 "
                              "클래스별 차원 데이터로 보고되는데 companyfacts는 "
                              "무차원 사실만 담는다)" if rev_years else ""))}

    labeling = "end_year"
    collisions = [y for y in detect_fy_label_collision(per_year) if base <= y <= end]
    if collisions:
        # ⚠️ 일반적인 자동 재라벨링이 아니다(v3.61이 금지한 것) — 이 라벨링이
        #    **이 ledger의 연도 키를 실제로 재현하는지** 매출로 증명될 때만 쓴다.
        alt = annual_facts(facts, used_tag, midpoint_year)
        hits, misses = verify_year_labeling(facts, ledger, midpoint_year)
        base_hits, base_misses = verify_year_labeling(facts, ledger, end_year)
        ok = (misses == 0 and hits >= RELABEL_MIN_MATCHES and hits > base_hits
              and not detect_fy_label_collision(alt)
              and base in alt and end in alt)
        if not ok:
            return {"ticker": ticker, "status": STATUS_FY_COLLISION,
                    "share_tag": used_tag,
                    "labeling_check": {"midpoint": [hits, misses],
                                       "end_year": [base_hits, base_misses]},
                    "detail": (f"회계연도 라벨 충돌 FY{collisions} — 52/53주 결산이 "
                               f"같은 라벨로 묶였고, 중간일자 재라벨링이 ledger "
                               f"매출을 재현하지 못해 어느 해 값인지 특정 불가(v3.61)")}
        per_year, labeling = alt, "midpoint"
        labeling_meta = {"midpoint": [hits, misses], "end_year": [base_hits, base_misses],
                         "collided_years": collisions}

    missing = [y for y in (base, end) if y not in per_year or y not in fcf]
    if missing:
        return {"ticker": ticker, "status": STATUS_MISSING_YEAR, "share_tag": used_tag,
                "detail": f"주식수 또는 FCF 미확보 연도 {missing}"}
    if fcf[base] <= 0:
        return {"ticker": ticker, "status": STATUS_BASE_NONPOSITIVE,
                "detail": f"기준연도 FCF <= 0 ({fcf[base]:,.0f}) - CAGR 정의불가"}
    if fcf[end] <= 0:
        # ⚠️ 파이썬은 음수의 실수제곱을 **복소수로 조용히 돌려준다**(v3.19가 잡은
        #    함정). 여기서 막지 않으면 복소수가 결과에 섞여 들어간다.
        return {"ticker": ticker, "status": STATUS_END_NONPOSITIVE,
                "detail": f"종료연도 FCF <= 0 ({fcf[end]:,.0f}) - CAGR 정의불가"}

    shares, meta = consistent_share_series(per_year, base, end)
    jumps = structural_jumps(shares, base, end)
    if jumps:
        return {"ticker": ticker, "status": STATUS_JUMP, "share_tag": used_tag,
                "normalization": meta, "jumps": jumps,
                "detail": ("정규화 후에도 남은 점프(주식분할·IPO·ADS비율변경·단위혼재): "
                           + ", ".join(f"FY{j['fy']} x{j['ratio']:.2f}" for j in jumps)
                           + " — 희석으로 해석할 수 없다")}

    total = (fcf[end] / fcf[base]) ** (1 / span) - 1
    per = ((fcf[end] / shares[end]) / (fcf[base] / shares[base])) ** (1 / span) - 1
    return {
        "ticker": ticker, "status": STATUS_OK,
        "base_year": base, "end_year": end, "span": span,
        "window_source": how, "share_tag": used_tag, "normalization": meta,
        "year_labeling": labeling,
        **({"year_labeling_check": labeling_meta} if labeling == "midpoint" else {}),
        "shares_base": shares[base], "shares_end": shares[end],
        "share_count_change_pct": shares[end] / shares[base] - 1,
        "fcf_cagr_total": total, "fcf_cagr_per_share": per,
        "dilution_drag": per - total,
        "per_share_declined": per < 0 <= total,
    }
