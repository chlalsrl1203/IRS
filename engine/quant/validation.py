"""
Research Validation (Repo 03·04·17, 2026-08-19) — 연구가 스스로를 속이지 않는지 검사한다.

# SOURCE:
https://github.com/stefan-jansen/machine-learning-for-trading  (Repo 04)
https://github.com/CPZ-Lab/cpz-quant  (Repo 17, Apache-2.0)
https://github.com/microsoft/qlib  (Repo 03, PIT 아키텍처)

# CAPABILITY:
look-ahead bias / survivorship bias / data leakage / multiple testing /
overfitting detection / walk-forward / PBO / DSR

# IRS_TARGET:
engine/quant/validation.py

# METHOD:
**기능 단위로 갈렸다**(통합 프롬프트 §1: "Repository 전체에 하나의 판단을
내리지 말고 기능 단위로 판단한다").

| 기능 | 판정 | 근거 |
|---|---|---|
| look-ahead / PIT | **DUPLICATE** | `filing_dates.check_lookahead`·`GATE.LOOKAHEAD`·`FinancialFact.available_at`이 이미 담당 |
| data leakage(시계열 분할) | **DEFER** | 분할할 시계열이 없다 |
| **multiple testing** | **REIMPLEMENT** | 지금 계산 가능하고 실제로 필요하다 — 아래 |
| **survivorship bias** | **REIMPLEMENT** | 스크리닝 탈락 기록이 남아 있어 계산 가능 |
| Purged CV / Walk-Forward | **DEFER** | 시계열 부재 |
| PBO / DSR | **DEFER** | Sharpe를 계산할 수익률 시계열이 없다 |

## 왜 multiple testing이 지금 필요한가 — 실측

이 저장소는 **같은 34종목 표본에 반복해서** 분석을 돌려왔다(2026-08-19 실측:
`reports/` 28건 + `experiments/` 9건). gap_distribution · gap_range · model_choice ·
growth_scorecard · market_relative · n_sensitivity · R-001(유효 시나리오
**9,675개**) 전부 같은 표본이다.

R-001은 §26에서 다중검정을 **인지**하고 "단일 flip을 핵심 발견으로 과장하지
않는다"고 적었지만, **저장소 전체에 걸친 검정 횟수를 센 적은 없다.** 그 수를
세는 것 자체가 이 모듈의 목적이다.

## ⚠️ 이 모듈이 하지 않는 것 — 없는 데이터로 통계를 만들지 않는다

`sharpe_based_metrics_available()`이 PBO·DSR 계산 가능 여부를 **먼저 검사하고
불가능하면 그 사실을 반환한다.** 원본 라이브러리에는 이 함수가 있지만 IRS에는
입력이 없다 — 억지로 돌리면 "정밀해 보이는 허구"가 된다(§31 안티기능 등록부의
포트폴리오 최적화 REJECT와 같은 판단).

또한 **p값을 만들어내지 않는다.** IRS의 분석들은 대부분 가설검정이 아니라
감사·서술이라 nominal p값 자체가 없다. 이 모듈은 "몇 번 봤는가"와 "그 횟수면
우연한 발견이 얼마나 나오는가"만 계산한다.
"""

import glob
import json
import os
import re

VALIDATION_STATUS = {
    "multiple_testing": (
        "SOFTWARE_VALIDATED — 검정 횟수 집계와 FWER 계산은 표준 공식이고 "
        "테스트로 고정돼 있다. 다만 **IRS의 분석 대부분은 nominal p값이 없어** "
        "이 수치는 '보정된 유의수준'이 아니라 '우연한 발견의 기대 규모'다."
    ),
    "survivorship": (
        "SOFTWARE_VALIDATED — 스크리닝 기록에서 세는 것이라 정확하다. 다만 "
        "**기록되지 않은 탈락은 셀 수 없다**(WebSearch 단계에서 조용히 넘어간 "
        "후보). 따라서 아래 수치는 생존편향의 **하한**이다."
    ),
    "pbo_dsr": (
        "NOT_APPLICABLE — 수익률 시계열이 저장소에 없다. 계산하지 않는다."
    ),
}

# 분석 리포트로 인정할 파일 패턴. ledger·predictions는 분석이 아니라 기록이라 제외.
REPORT_GLOB = "reports/*.json"
EXPERIMENT_GLOB = "experiments/*.json"

# 스크리닝 스크립트에서 후보 목록을 담는 상수 이름들.
SCREEN_BUCKETS = (
    "CANDIDATES",              # 실제 screen() 호출까지 간 후보
    "PREFILTERED_OUT",         # 4분류 체크리스트에서 사전 제외
    "FRAMEWORK_MISMATCH",      # 프레임워크 부적합(5y CAGR 불가 등)
    "PASSED_INITIAL_SCREEN",   # 1차 통과, 재무데이터 미확보
)


def count_tests_on_sample(reports_glob: str = REPORT_GLOB,
                          experiments_glob: str = EXPERIMENT_GLOB) -> dict:
    """
    같은 표본에 몇 번의 분석·검정이 돌았는지 센다.

    ⚠️ **리포트 1건 = 검정 1회가 아니다.** R-001 하나가 9,675개 시나리오를
    검사했다. 그래서 리포트가 시나리오 수를 스스로 밝히면 그것도 함께 센다 —
    안 밝히면 1로 세되 그 사실을 `unknown_scenario_counts`에 남긴다(모르는 것을
    1로 확정하지 않는다).
    """
    reports, scenario_total, unknown = [], 0, []
    for p in sorted(glob.glob(reports_glob)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = os.path.basename(p)
        # 리포트가 스스로 밝힌 시나리오/검정 수를 찾는다.
        n = None
        for key in ("total_valid_scenarios_examined", "n_valid_scenarios",
                    "n_simulations", "n_scenarios"):
            if isinstance(d, dict) and isinstance(d.get(key), int):
                n = d[key]
                break
        if n is None:
            unknown.append(name)
            n = 1
        reports.append({"report": name, "counted_tests": n,
                        "self_reported": name not in unknown})
        scenario_total += n

    experiments = []
    for p in sorted(glob.glob(experiments_glob)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        core = d.get("core") if isinstance(d.get("core"), dict) else d
        experiments.append({
            "file": os.path.basename(p),
            "experiment_id": core.get("experiment_id") or d.get("experiment_id"),
            "status": d.get("status") or core.get("status"),
        })

    return {
        "n_reports": len(reports),
        "n_experiments": len(experiments),
        "counted_tests": scenario_total,
        "unknown_scenario_counts": unknown,
        "reports": reports,
        "experiments": experiments,
        "note": (
            "리포트 1건 = 검정 1회가 아니다. 시나리오 수를 스스로 밝힌 리포트는 "
            "그 수를, 안 밝힌 리포트는 1로 세되 그 사실을 남긴다."
        ),
    }


def familywise_error(n_tests: int, alpha: float = 0.05) -> dict:
    """
    독립 검정 n회에서 **적어도 하나가 우연히 유의하게 나올 확률**:
    `1 - (1-alpha)^n`. Bonferroni 보정 임계값도 함께 준다.

    ⚠️ **독립 가정은 IRS에서 성립하지 않는다.** 같은 34종목·같은 엔진에 돌린
    분석들은 서로 강하게 상관돼 있어, 실제 FWER은 이 값보다 **낮다**. 즉 이
    숫자는 상한이며, "이만큼 나쁘다"가 아니라 "무보정으로 두면 이 정도까지
    나빠질 수 있다"로 읽어야 한다.
    """
    if n_tests < 1:
        raise ValueError(f"검정 횟수는 1 이상이어야 한다: {n_tests}")
    if not 0 < alpha < 1:
        raise ValueError(f"alpha는 (0,1) 구간이어야 한다: {alpha}")
    fwer = 1.0 - (1.0 - alpha) ** n_tests
    # ⚠️ n이 수백만 넘어도 FWER은 1.0으로 **포화**한다. 1.0이 나왔다고 계산이
    # 틀린 게 아니라, 그 지점에서 FWER이라는 지표 자체가 정보를 잃는 것이다.
    # 그때 읽어야 할 값은 `expected_false_positives`다.
    saturated = fwer > 0.9999
    return {
        "n_tests": n_tests,
        "alpha_nominal": alpha,
        "fwer_upper_bound": fwer,
        "fwer_saturated": saturated,
        "bonferroni_alpha": alpha / n_tests,
        "expected_false_positives": n_tests * alpha,
        "independence_assumed": True,
        "note": (
            "독립 가정은 IRS에서 성립하지 않는다(같은 표본·같은 엔진). 실제 "
            "FWER은 이보다 낮으므로 이 값은 **상한**이다."
            + (" ⚠️ FWER이 1.0으로 포화됐다 — 계산 오류가 아니라 이 검정 "
               "횟수에서는 FWER이 정보를 잃는다는 뜻이다. expected_false_positives를 "
               "볼 것." if saturated else "")
        ),
    }


def sharpe_based_metrics_available(ledger_glob: str = "ledger/*.json") -> dict:
    """
    PBO·DSR을 계산할 입력이 있는지 **먼저 검사한다.**

    없으면 계산을 시도하지 않고 그 사실을 돌려준다 — 없는 데이터로 통계를
    만들면 "정밀해 보이는 허구"가 된다(§31 등록부의 포트폴리오 최적화 REJECT와
    같은 판단).
    """
    total = with_price = 0
    for p in sorted(glob.glob(ledger_glob)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        total += 1
        if (d.get("inputs") or {}).get("price_at_analysis"):
            with_price += 1
    return {
        "available": False,          # 현재 상태에서는 항상 False다
        "n_tickers": total,
        "n_with_entry_price": with_price,
        "has_return_series": False,
        "blocking_inputs": ["종목별 수익률 시계열", "백테스트 Sharpe 분포"],
        "validation_status": VALIDATION_STATUS["pbo_dsr"],
        "reason": (
            f"PBO·DSR은 백테스트 Sharpe 분포를 요구한다. IRS에는 수익률 시계열이 "
            f"없고 진입가조차 {with_price}/{total}종목뿐이다. **계산하지 않는다.**"
        ),
    }


def _parse_screen_buckets(path: str) -> dict:
    """
    스크리닝 스크립트에서 버킷별 티커를 뽑는다.

    ⚠️ AST 실행이 아니라 **정규식 파싱**이다. 스크립트를 import하면 네트워크
    호출·분석이 실행되므로 그럴 수 없다. 파싱에 실패하면 그 버킷을 **0이 아니라
    None**으로 남긴다(파싱 실패와 실제 0건은 다르다).
    """
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return {}
    out = {}
    # ⚠️ `CANDIDATES`는 특수하다 — 스크립트가 `CANDIDATES = []`로 시작한 뒤
    # `CANDIDATES.append(Candidate(ticker="META", ...))`로 채운다(2026-08-19
    # 실측). 리터럴 블록만 파싱하면 **항상 0건**이 나온다(초판이 그랬다).
    # 그래서 이 버킷만 파일 전체에서 `Candidate(... ticker="X" ...)`를 찾는다.
    if re.search(r"^CANDIDATES\s*=", src, re.M):
        out["CANDIDATES"] = sorted(set(re.findall(
            r'Candidate\(\s*(?:#[^\n]*\n\s*)*ticker\s*=\s*"([A-Z][A-Z.]{0,5})"',
            src)))

    for bucket in SCREEN_BUCKETS:
        if bucket == "CANDIDATES":
            continue
        m = re.search(rf"^{bucket}\s*=\s*[\[\{{]", src, re.M)
        if not m:
            continue
        # 대괄호/중괄호 균형을 맞춰 블록 끝을 찾는다.
        start = m.end() - 1
        depth, end = 0, None
        for i in range(start, len(src)):
            if src[i] in "[{":
                depth += 1
            elif src[i] in "]}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            out[bucket] = None          # 파싱 실패 — 0으로 만들지 않는다
            continue
        block = src[start:end]
        # ⚠️ 버킷마다 자료구조가 다르다(2026-08-19 실측으로 확인):
        #   CANDIDATES = [Candidate(ticker="AMD", ...), ...]        -> ticker= 인자
        #   PREFILTERED_OUT = {"KR(Kroger)": "사유...", ...}        -> 딕셔너리 키
        # 하나의 정규식으로 뭉뚱그리면 설명 문자열 안의 대문자까지 티커로
        # 잡히거나(과대) 딕셔너리 키를 통째로 놓친다(과소 — 초판이 그랬다).
        tickers = set(re.findall(r'ticker\s*=\s*"([A-Z][A-Z.]{0,5})"', block))
        # 딕셔너리 키는 줄 시작에 오고 뒤에 `(회사명)` 또는 바로 `":`가 붙는다.
        tickers |= set(re.findall(r'^\s*"([A-Z][A-Z.]{0,5})(?:\([^"]*\))?"\s*:',
                                  block, re.M))
        out[bucket] = sorted(tickers)
    return out


def survivorship_report(screen_glob: str = "scripts/screen_*.py",
                        ledger_glob: str = "ledger/*.json") -> dict:
    """
    스크리닝을 통과해 ledger에 남은 종목 vs 탈락한 종목.

    ⚠️ **이 수치는 생존편향의 하한이다.** 기록되지 않은 탈락(WebSearch 단계에서
    조용히 넘어간 후보)은 셀 수 없다. "탈락이 이만큼뿐"이 아니라 "최소한 이만큼은
    있었다"로 읽어야 한다.

    ⚠️ 또한 **ledger에 있다고 '성공'한 것이 아니다.** ledger는 분석을 마친
    기록이지 수익을 낸 기록이 아니다 — 성과 검증은 STOP CONDITION 상태다.
    """
    ledger_tickers = set()
    for p in sorted(glob.glob(ledger_glob)):
        try:
            ledger_tickers.add(json.load(open(p, encoding="utf-8"))["meta"]["ticker"])
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    by_script, buckets = {}, {b: set() for b in SCREEN_BUCKETS}
    parse_failures = []
    for p in sorted(glob.glob(screen_glob)):
        parsed = _parse_screen_buckets(p)
        name = os.path.basename(p)
        by_script[name] = {}
        for bucket, tickers in parsed.items():
            if tickers is None:
                parse_failures.append(f"{name}:{bucket}")
                by_script[name][bucket] = None
                continue
            by_script[name][bucket] = tickers
            buckets[bucket].update(tickers)

    considered = set().union(*buckets.values()) if buckets else set()
    rejected = considered - ledger_tickers
    from_screening = considered & ledger_tickers
    return {
        "n_ledger_tickers": len(ledger_tickers),
        "n_considered_in_screening": len(considered),
        # ⚠️ ledger 종목이 전부 스크리닝을 거친 것이 아니다. 상당수는 스크리닝
        # 스크립트가 생기기 전(v3.13~v3.19 큐 기반 분석) 경로로 들어왔다.
        # 이 구분 없이 생존율을 읽으면 ledger 전체에 적용되는 것으로 오독된다.
        "n_ledger_from_screening": len(from_screening),
        "ledger_from_screening": sorted(from_screening),
        "n_ledger_not_from_screening": len(ledger_tickers - considered),
        "n_rejected": len(rejected),
        "rejected_tickers": sorted(rejected),
        "by_bucket": {b: sorted(t) for b, t in buckets.items()},
        "by_script": by_script,
        "parse_failures": parse_failures,
        "survival_rate_lower_bound": (
            len(from_screening) / len(considered) if considered else None
        ),
        "validation_status": VALIDATION_STATUS["survivorship"],
        "note": (
            "기록되지 않은 탈락은 셀 수 없으므로 이 수치는 생존편향의 **하한**이다. "
            "또한 ledger에 있다는 것은 분석을 마쳤다는 뜻이지 수익을 냈다는 뜻이 "
            "아니다 — 성과 검증은 STOP CONDITION 상태다. "
            "survival_rate_lower_bound는 **스크리닝을 거친 부분집합에만** 적용된다 "
            "(n_ledger_not_from_screening 참조)."
        ),
    }


def multiple_testing_report(alpha: float = 0.05) -> dict:
    """저장소 전체의 다중검정 상태. **보정을 적용하지 않고 사실만 보고한다.**"""
    counts = count_tests_on_sample()
    n = max(counts["counted_tests"], 1)
    return {
        "generated_for_alpha": alpha,
        "counts": counts,
        "familywise": familywise_error(n, alpha),
        "correction_applied": False,
        "validation_status": VALIDATION_STATUS["multiple_testing"],
        "note": (
            "IRS의 분석 대부분은 가설검정이 아니라 감사·서술이라 nominal p값이 "
            "없다. 따라서 이 리포트는 보정된 유의수준이 아니라 **'같은 표본을 "
            "몇 번 봤는가'**를 드러내는 것이 목적이다. 보정을 자동 적용하지 "
            "않는다 — 적용할 p값이 없기 때문이다."
        ),
    }
