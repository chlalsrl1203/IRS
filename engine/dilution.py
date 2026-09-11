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
"""

import statistics

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


def annual_share_facts(facts, tag):
    """{회계연도: [(공시일, 값), ...]} — 같은 해의 모든 공시본을 버리지 않는다.

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
                out.setdefault(int(end[:4]), []).append((filed, end, float(val)))
    return {y: sorted(v) for y, v in out.items()}


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
        return {"ticker": ticker, "status": STATUS_NO_SHARES,
                "detail": f"주식수 태그 {SHARE_TAGS} 어느 것도 연차 보고가 없다"}

    collisions = [y for y in detect_fy_label_collision(per_year) if base <= y <= end]
    if collisions:
        return {"ticker": ticker, "status": STATUS_FY_COLLISION, "share_tag": used_tag,
                "detail": (f"회계연도 라벨 충돌 FY{collisions} — 52/53주 결산이 "
                           f"같은 라벨로 묶여 어느 해 값인지 특정 불가(v3.61)")}

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
        "shares_base": shares[base], "shares_end": shares[end],
        "share_count_change_pct": shares[end] / shares[base] - 1,
        "fcf_cagr_total": total, "fcf_cagr_per_share": per,
        "dilution_drag": per - total,
        "per_share_declined": per < 0 <= total,
    }
