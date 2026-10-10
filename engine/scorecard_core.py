"""
IRS 스코어카드 모듈 (표준 라이브러리 전용, v2.1)

이 저장소의 원칙을 따른다: 런타임 의존성 0개(pandas/numpy/scipy 없음), 단일 종합
점수 없음, 판정에 자동 배선하지 않음. 기존 engine/accounting_quality.py와 겹치는
재무회계(A) 모듈은 여기 없다. 기존 모듈을 그대로 쓴다.

이 파일이 내는 것은 B(해자)와 D(경영진) 두 모듈의 "하위 지표들"이다. 모듈 내부
가중합(B_score, D_cap 등)은 계산해서 반환하지만, 그걸 다른 모듈과 합쳐 하나의
순위나 우선순위로 만드는 함수는 이 파일에 없다. 그건 사람이 각 숫자를 보고 판단할
영역이다(accounting_quality.py가 계산은 하되 verdict에 배선하지 않은 것과 같은 이유).

알려진 근사와 이유
- normal_cdf: math.erf로 정확히 계산(근사 아님, stdlib 내장).
- inv_normal_cdf: Acklam(2003) 유리함수 근사. 절대오차 약 1.15e-9, scipy.stats.norm.ppf
  대비 테스트에서 1e-9 이내로 확인(아래 test_scorecard_core.py). QMJ 요소 합성에만
  쓰이고, 이 값 자체가 최종 수치로 노출되지는 않는다.
- managerial_efficiency_proxy: Demerjian, Lev, McVay(2012)의 1단계는 업종별 DEA
  (선형계획법)다. 검증되지 않은 LP 솔버를 새로 짜는 위험을 피하기 위해, 대신
  log(출력)을 log(입력들)에 OLS 회귀한 잔차를 쓴다. 이것은 DEA가 아니라 콥-더글러스형
  생산함수 잔차이며, DEA가 포착하는 비선형 효율 경계를 반영하지 못한다. 결과를
  "managerial_efficiency_proxy"라고 부르고 "MA-score"라고 부르지 않는 이유다. DEA를
  나중에 제대로 구현하려면 pandas 없이도 가능한 LP 솔버(예: scipy 없이 단체법 직접
  구현)가 필요하며, 그 작업은 이 파일에 포함되지 않았다.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence

MIN_PEERS = 10
FF_RHO_PRIOR = 0.62       # Fama and French (2000) 연 약 38% 평균회귀에서 유도. 한국 데이터로 재추정 전까지 사전값.
SHRINK_K = 5.0
SHRINK_K_MEAN = 10.0
SPREAD_FLOOR = 0.01
DURATION_CAP = 20
MAG_CAP = 0.05


# ---------------------------------------------------------------------------
# 0. 수치 기초 (stdlib만 사용)
# ---------------------------------------------------------------------------

def normal_cdf(x: float) -> float:
    """표준정규 누적분포함수. math.erf 기반으로 정확히 계산한다(근사 아님)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def inv_normal_cdf(p: float) -> float:
    """표준정규 분위수함수. Acklam(2003) 유리함수 근사, 절대오차 약 1.15e-9.
    출처: Peter J. Acklam, "An algorithm for computing the inverse normal
    cumulative distribution function" (2003, 공개 알고리즘, 저널 미게재).
    p는 (0,1) 구간이어야 하며, 범위 밖이면 ValueError."""
    if not (0.0 < p < 1.0):
        raise ValueError(f"p는 (0,1) 구간이어야 함: {p}")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def rank_pct(values: Sequence[float]) -> List[float]:
    """평균순위 기반 백분위(0~1], 동점은 평균 순위 공유. 입력 순서를 유지해서 반환."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1  # 1-based 평균 순위
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return [r / n for r in ranks]


def group_percentile(items: List[dict], value_key: str, group_key: str,
                     fallback_group_key: Optional[str] = None,
                     higher_is_better: bool = True, min_peers: int = MIN_PEERS) -> Dict[int, Optional[float]]:
    """items 인덱스 -> 그룹 내 백분위(0~1] 또는 None. 표본이 min_peers 미만이면
    fallback_group_key로 올리고, 그래도 부족하면 None([Data Missing])."""
    out: Dict[int, Optional[float]] = {i: None for i in range(len(items))}

    def _assign(key: str):
        groups: Dict[object, List[int]] = {}
        for i, it in enumerate(items):
            if out[i] is not None or it.get(value_key) is None:
                continue
            groups.setdefault(it.get(key), []).append(i)
        for _, idx in groups.items():
            if len(idx) < min_peers:
                continue
            vals = [items[i][value_key] for i in idx]
            pr = rank_pct(vals)
            for pos, i in enumerate(idx):
                out[i] = pr[pos] if higher_is_better else (1 - pr[pos] + 1.0 / len(idx))
    _assign(group_key)
    if fallback_group_key:
        _assign(fallback_group_key)
    return out


def _mean(xs: Iterable[Optional[float]]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def ols(X: List[List[float]], y: List[float]) -> Optional[List[float]]:
    """다중회귀 X*beta=y를 정규방정식 (X'X)beta = X'y 로 풀어 beta를 반환.
    X의 각 행은 [1, x1, x2, ...] (절편 포함). stdlib Gaussian elimination.
    표본이 변수 수보다 적거나 특이행렬이면 None."""
    n, p = len(X), len(X[0])
    if n < p:
        return None
    XtX = [[sum(X[k][i] * X[k][j] for k in range(n)) for j in range(p)] for i in range(p)]
    Xty = [sum(X[k][i] * y[k] for k in range(n)) for i in range(p)]
    A = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for col in range(p):
        piv = max(range(col, p), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) < 1e-12:
            return None
        A[col], A[piv] = A[piv], A[col]
        pivval = A[col][col]
        A[col] = [v / pivval for v in A[col]]
        for r in range(p):
            if r != col and abs(A[r][col]) > 0:
                factor = A[r][col]
                A[r] = [A[r][k] - factor * A[col][k] for k in range(p + 1)]
    return [A[i][p] for i in range(p)]


def ar1_shrinkage_duration(spreads: Optional[Sequence[float]]) -> Dict[str, Optional[float]]:
    """ROIC-WACC 스프레드(오래된 순)로 초과수익 지속성을 추정.
    1) rho* = w*rho_firm + (1-w)*0.62, w=n/(n+5)
    2) s_inf* = v*s_inf_firm, v=n/(n+10) (사전값 0=경쟁균형)
    3) s_(k+1) = s_inf* + rho*(s_k - s_inf*) 로 20년 투영
    4) T: 투영이 1%p를 넘는 연수, Q: 크기가중 연속 지속도(0~1), trend: 최근5년 OLS 기울기
    관측 5개 미만이면 전부 None."""
    empty = {"T": None, "Q": None, "rho": None, "s_inf": None, "trend": None, "n": 0}
    if not spreads:
        return empty
    s = [float(v) for v in spreads if v is not None and not math.isnan(v)]
    if len(s) < 5:
        return {**empty, "n": len(s)}
    x, y = s[:-1], s[1:]
    n = len(y)
    mx, my = sum(x) / n, sum(y) / n
    varx = sum((xi - mx) ** 2 for xi in x) / n
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
    rho_f = FF_RHO_PRIOR if varx < 1e-12 else cov / varx
    rho_f = max(-0.5, min(0.99, rho_f))
    rho = (n / (n + SHRINK_K)) * rho_f + (1 - n / (n + SHRINK_K)) * FF_RHO_PRIOR
    a = my - rho * mx
    s_inf = (n / (n + SHRINK_K_MEAN)) * (a / (1 - rho))
    path, v = [], s[-1]
    for _ in range(DURATION_CAP):
        v = s_inf + rho * (v - s_inf)
        path.append(v)
    T = float(sum(1 for v in path if v > SPREAD_FLOOR)) if s[-1] > SPREAD_FLOOR else 0.0
    Q = sum(max(0.0, min(1.0, v / MAG_CAP)) for v in path) / DURATION_CAP
    recent = s[-5:]
    rx = list(range(len(recent)))
    mrx, mry = sum(rx) / len(rx), sum(recent) / len(recent)
    vrx = sum((xi - mrx) ** 2 for xi in rx)
    trend = (sum((rx[i] - mrx) * (recent[i] - mry) for i in range(len(rx))) / vrx) if vrx > 1e-12 else 0.0
    return {"T": T, "Q": Q, "rho": rho, "s_inf": s_inf, "trend": trend, "n": len(s)}


# ---------------------------------------------------------------------------
# B. 해자 (하위지표 + 모듈 내부 가중합. 다른 모듈과 합치지 않음)
# ---------------------------------------------------------------------------

def moat_subscores(companies: List[dict]) -> List[dict]:
    """companies[i]는 최소 {'spread_series': [...] or None, 'industry': str, 'sector': str,
    'gm_cv_10y': float|None, 'gm_change_shock': float|None, 'share_trend_5y': float|None,
    'lifecycle_shakeout_or_decline': bool, 'share_instability_top25': bool,
    'key_person_no_succession': bool} 를 담은 dict.
    반환: 각 회사의 하위지표와 B_score(모듈 내부 가중합, 0~100 또는 None), B_cap50(bool)."""
    n = len(companies)
    dur = [ar1_shrinkage_duration(c.get("spread_series")) for c in companies]
    for c, d in zip(companies, dur):
        c["_S_dur"] = d["Q"]
        avg = _mean(c.get("spread_series")) if c.get("spread_series") and d["n"] >= 5 else None
        c["_avg_spread"] = avg
        c["_S_mag"] = max(0.0, math.tanh(avg / 0.10)) if avg is not None else None
        c["_S_trend"] = max(0.0, min(1.0, 0.5 + d["trend"] / 0.02)) if d["trend"] is not None else None
    stab = group_percentile(companies, "gm_cv_10y", "industry", "sector", higher_is_better=False)
    for i, c in enumerate(companies):
        if c.get("gm_change_shock") is not None:
            med_pool = [x["gm_change_shock"] for x in companies
                       if x.get("industry") == c.get("industry") and x.get("gm_change_shock") is not None]
            c["_rel_shock"] = c["gm_change_shock"] - (sorted(med_pool)[len(med_pool) // 2] if med_pool else 0)
        else:
            c["_rel_shock"] = None
    price = group_percentile(companies, "_rel_shock", "industry", "sector", higher_is_better=True)
    share = group_percentile(companies, "share_trend_5y", "industry", "sector", higher_is_better=True)

    out = []
    for i, c in enumerate(companies):
        parts = {"S_dur": (c["_S_dur"], 35), "S_trend": (c["_S_trend"], 15), "S_mag": (c["_S_mag"], 10),
                 "S_stab": (stab[i], 15), "S_price": (price[i], 15), "S_share": (share[i], 10)}
        core = ["S_dur", "S_trend", "S_mag"]
        if any(parts[k][0] is None for k in core):
            score = None
        else:
            wsum = sum(w for v, w in parts.values() if v is not None)
            score = 100 * sum(v * w for v, w in parts.values() if v is not None) / wsum
            trig = bool(c.get("lifecycle_shakeout_or_decline") or c.get("share_instability_top25")
                       or c.get("key_person_no_succession"))
            if trig:
                score = min(score, 50.0)
        out.append({
            "S_dur": c["_S_dur"], "S_trend": c["_S_trend"], "S_mag": c["_S_mag"],
            "S_stab": stab[i], "S_price": price[i], "S_share": share[i],
            "avg_spread": c["_avg_spread"], "B_score": score,
            "B_cap50": bool(c.get("lifecycle_shakeout_or_decline") or c.get("share_instability_top25")
                           or c.get("key_person_no_succession")),
        })
    return out


# ---------------------------------------------------------------------------
# C. QMJ 품질 요소 (Expectation Gap은 기저율 DB가 없어 별도 보류, 여기 포함 안 함)
# ---------------------------------------------------------------------------

def qmj_component(companies: List[dict], fields: Dict[str, bool], group_key="industry",
                  fallback_key="sector") -> List[Optional[float]]:
    """Asness, Frazzini, Pedersen(2019) 방식: 변수별 그룹 백분위 -> 정규 z -> 평균 -> 재백분위.
    구성 변수의 절반 이상이 있어야 산출. fields: {필드명: higher_is_better}."""
    pct_by_field = {f: group_percentile(companies, f, group_key, fallback_key, hib)
                    for f, hib in fields.items()}
    comp = []
    for i in range(len(companies)):
        zs = []
        for f in fields:
            p = pct_by_field[f][i]
            if p is not None:
                zs.append(inv_normal_cdf(min(0.995, max(0.005, p))))
        comp.append(sum(zs) / len(zs) if len(zs) >= math.ceil(len(fields) / 2) else None)
    for i, c in enumerate(companies):
        c["_qmj_tmp"] = comp[i]
    return list(group_percentile(companies, "_qmj_tmp", group_key, fallback_key, True).values())


# ---------------------------------------------------------------------------
# D. 경영진 (자본배분, 주주환원, 지배구조, 경영자효율 근사, 정직성 가감)
# ---------------------------------------------------------------------------

def capital_allocation_subscore(companies: List[dict]) -> List[Optional[float]]:
    """roiic_5y, wacc, dollar_test_ratio, market_dollar_ratio, gw_impair_ratio_5y,
    netdebt_ebitda 를 쓴다. 0~40, roiic_pct 결측이면 None."""
    for c in companies:
        c["_roiic_ex"] = (c["roiic_5y"] - c["wacc"]) if c.get("roiic_5y") is not None and c.get("wacc") is not None else None
    roiic_pct = group_percentile(companies, "_roiic_ex", "industry", "sector", True)
    out = []
    for i, c in enumerate(companies):
        dollar = None
        if c.get("dollar_test_ratio") is not None and c.get("market_dollar_ratio"):
            dollar = max(0.0, min(1.0, c["dollar_test_ratio"] / c["market_dollar_ratio"]))
        impair = (1 - max(0.0, min(1.0, c["gw_impair_ratio_5y"]))) if c.get("gw_impair_ratio_5y") is not None else None
        lev = None
        if c.get("netdebt_ebitda") is not None:
            peers = [x["netdebt_ebitda"] for x in companies if x.get("industry") == c.get("industry")
                    and x.get("netdebt_ebitda") is not None]
            med = max(0.5, sorted(peers)[len(peers) // 2]) if peers else 1.5
            lev = max(0.0, min(1.0, 1 - (c["netdebt_ebitda"] / med - 1.5) / 1.5))
        parts = {"roiic": (roiic_pct[i], 15), "dollar": (dollar, 10), "impair": (impair, 10), "lev": (lev, 5)}
        if parts["roiic"][0] is None:
            out.append(None); continue
        wsum = sum(w for v, w in parts.values() if v is not None)
        out.append(sum(v * w for v, w in parts.values() if v is not None) / wsum * 40)
    return out


def managerial_efficiency_proxy(companies: List[dict]) -> List[Optional[float]]:
    """Demerjian, Lev, McVay(2012) 1단계 DEA의 대체 근사. DEA가 아니다(모듈 docstring 참조).
    log(sales) ~ log(cogs+sga+net_ppe+rou_asset+rnd+goodwill+other_intangibles 각각)의
    업종별 OLS 잔차를 구하고, 그 잔차를 규모/점유율/업력으로 2차 회귀한 잔차를 다시
    업종 내 백분위로 변환한다. 입력 중 하나라도 0 이하이면(log 불가) 해당 회사는 제외."""
    inputs = ["cogs", "sga", "net_ppe", "rou_asset", "rnd", "goodwill", "other_intangibles"]
    by_ind: Dict[object, List[int]] = {}
    for i, c in enumerate(companies):
        if c.get("sales", 0) and c["sales"] > 0 and all((c.get(k) or 0) > 0 for k in inputs) and all(
                c.get(k) is not None for k in ("log_assets", "mkt_share", "firm_age")):
            by_ind.setdefault(c.get("industry"), []).append(i)
    resid_all: Dict[int, float] = {}
    for _, idx in by_ind.items():
        if len(idx) < MIN_PEERS:
            continue
        X = [[1.0] + [math.log(companies[i][k]) for k in inputs] for i in idx]
        y = [math.log(companies[i]["sales"]) for i in idx]
        beta = ols(X, y)
        if beta is None:
            continue
        stage1 = {i: y[pos] - sum(beta[k] * X[pos][k] for k in range(len(beta))) for pos, i in enumerate(idx)}
        X2 = [[1.0, companies[i]["log_assets"], companies[i]["mkt_share"], companies[i]["firm_age"]] for i in idx]
        y2 = [stage1[i] for i in idx]
        beta2 = ols(X2, y2)
        if beta2 is None:
            continue
        for pos, i in enumerate(idx):
            resid_all[i] = y2[pos] - sum(beta2[k] * X2[pos][k] for k in range(len(beta2)))
    for i, c in enumerate(companies):
        c["_ma_resid"] = resid_all.get(i)
    return list(group_percentile(companies, "_ma_resid", "industry", "sector", True).values())


HONESTY_ITEMS = {"restated_down_3y": -4, "unfaithful_disclosure": -4, "guidance_miss_3y": -2,
                 "promise_kept_record": 3, "voluntary_bad_news": 2}


def honesty_adjustment(checklist: Optional[Dict[str, str]]) -> float:
    """증거 URL이 있는 항목만 반영. 범위 -10~+5."""
    if not checklist:
        return 0.0
    total = sum(v for k, v in HONESTY_ITEMS.items() if checklist.get(k))
    return max(-10.0, min(5.0, total))


def management_subscores(companies: List[dict]) -> List[dict]:
    """자본배분/주주환원/지배구조/경영자효율근사/정직성 가감을 모듈 내부에서만 합친다.
    이 D_score를 다른 모듈과 합쳐 하나의 순위로 만드는 로직은 이 파일에 없다."""
    cap = capital_allocation_subscore(companies)
    npy = group_percentile(companies, "net_payout_yield", "industry", "sector", True)
    bbt = [c.get("buyback_timing") for c in companies]
    divp = [c.get("div_predictable") for c in companies]
    ma = managerial_efficiency_proxy(companies)

    comp_by_bucket = group_percentile(companies, "kcg_compliance", "size_bucket", None, True)
    out = []
    for i, c in enumerate(companies):
        ret_parts = {"npy": (npy[i], 10), "divp": (float(divp[i]) if divp[i] is not None else None, 5),
                    "bbt": (bbt[i], 5)}
        if ret_parts["npy"][0] is None:
            ret = None
        else:
            wsum = sum(w for v, w in ret_parts.values() if v is not None)
            ret = sum(v * w for v, w in ret_parts.values() if v is not None) / wsum * 20

        comp = comp_by_bucket[i]
        gov = (comp if comp is not None else 0.5) * 10 + 15
        for key, pts in [("split_then_listing_5y", -10), ("related_party_top10", -5),
                        ("opp_insider_net_sell", -5), ("opp_insider_net_buy", 5),
                        ("chair_separated", 2.5), ("ceo_succession_policy", 2.5)]:
            if c.get(key):
                gov += pts
        gov = max(0.0, min(25.0, gov))

        honesty = honesty_adjustment(c.get("honesty_checklist"))
        d_ma = ma[i] * 15 if ma[i] is not None else None

        base_ok = cap[i] is not None and ret is not None
        d_score = None
        if base_ok:
            fallback_ma = (cap[i] + ret + gov) / 85 * 15
            d_score = max(0.0, min(100.0, cap[i] + ret + gov + (d_ma if d_ma is not None else fallback_ma) + honesty))
        out.append({
            "D_cap": cap[i], "D_ret": ret, "D_gov": gov, "D_gov_compliance_missing": comp is None,
            "D_ma_proxy": d_ma, "D_ma_is_fallback": d_ma is None, "D_honesty": honesty,
            "D_score": d_score,
            "D_status": "확정" if c.get("honesty_reviewed") else "잠정(정성 검토 전)",
        })
    return out
