"""
Research Experiment Registry (v3.48 신규, 2026-08-15) - 투자 가설을 실험으로
등록하고, **실패한 실험을 지우지 않는다.**

## 왜 필요한가

이 프로젝트는 Expectation Gap을 중심으로 34종목을 분석해왔지만, **Gap이 실제로
초과수익과 관계가 있는지는 한 번도 검증한 적이 없다.** 그런데 매수리스트는
이미 Gap 기반 등급(S/A)으로 만들어지고 있다 - 즉 미검증 가설이 이미 자본배분을
움직이고 있는 상태다.

이 모듈은 그 상태를 **정직하게 드러내는 장치**다. 가설을 등록하고, 검증 규칙을
미리 못박고, 결과가 나오면 좋든 나쁘든 남긴다.

## ⚠️ 이 모듈의 핵심 제약 - 실패를 지우면 등록부가 무의미하다

실패한 실험을 지우거나 덮어쓰면 남는 것은 **성공한 실험만 모아둔 목록**이고,
그건 연구 기록이 아니라 광고다. 그래서:

  - `results`는 **덧붙이기만** 가능하다(`record_result`). 기존 결과를 고치려는
    시도는 예외를 던진다.
  - 실험 코어(가설·유니버스·진입/청산 규칙·기간·벤치마크)는 등록 후 **변경
    불가**다. 규칙을 바꾸고 싶으면 새 실험을 등록한다 - 결과를 본 뒤 규칙을
    조정하는 것이 정확히 사후합리화이고, 백테스트를 무의미하게 만드는 주범이다.
  - `status="ABANDONED"`로 닫을 수는 있지만 **삭제 함수는 제공하지 않는다.**

`engine/prediction_ledger.py`와 같은 사고방식이되, 대상이 종목이 아니라
**방법론**이다.

## ⚠️ EXP-001의 결과를 미리 가정하지 않는다

첫 실험은 이 시스템의 근본 가설이다:

    "Valuation-Implied Requirement와 Evidence-Supported Forward Expectation
     사이의 괴리가 미래 위험조정수익률과 관계가 있는가?"

이 저장소에는 아직 그 답이 없다. 관계가 없다는 결과가 나오면 그것도 그대로
기록한다 - 이 프로젝트는 이미 가설이 실측으로 기각된 사례를 그대로 남겨둔
전례가 있다(v3.44 gap_distribution의 "P(저평가)=73% 형태" 가설 기각,
META capex 가설 기각).

**현재 이 실험은 실행 불가능하다** - 분석 이력이 3주뿐이고 `price_at_analysis`가
채워진 종목이 10건뿐이라 미래 수익률을 잴 구간 자체가 없다. 그 사실도
등록부에 `blocked_reason`으로 남긴다(계약서 5.1절 - 모르는 것을 아는 것처럼
쓰지 않는다).
"""

import glob
import json
import os
from dataclasses import asdict, dataclass, field

# 봉인용 해시는 prediction_ledger의 것을 그대로 쓴다 - 같은 목적의 로직을
# 두 벌 두면 두 구현이 미묘하게 어긋난다(Simplicity First가 반복 경고한 함정).
from engine.prediction_ledger import core_hash

EXPERIMENT_DIR = "experiments"

EXPERIMENT_STATUSES = (
    "REGISTERED",   # 등록만 됨
    "BLOCKED",      # 실행 전제(데이터 등)가 아직 없음
    "RUNNING",      # 실행 중
    "COMPLETED",    # 결과 확정
    "ABANDONED",    # 중단(삭제하지 않고 사유와 함께 남긴다)
)

# 실험 코어 = 결과를 보기 전에 확정돼야 하는 것. 등록 후 변경 불가.
_CORE_FIELDS = (
    "experiment_id", "hypothesis", "universe", "entry_rule", "exit_rule",
    "parameters", "test_period", "oos_period", "benchmark",
)


@dataclass
class Experiment:
    """§8의 실험 1건. 코어 필드는 등록 시점에 전부 확정돼야 한다."""

    experiment_id: str
    hypothesis: str
    universe: str
    entry_rule: str
    exit_rule: str
    test_period: str
    oos_period: str
    benchmark: str
    parameters: dict = field(default_factory=dict)
    registered_date: str = None
    note: str = ""

    def __post_init__(self):
        for f in ("experiment_id", "hypothesis", "universe", "entry_rule",
                  "exit_rule", "test_period", "oos_period", "benchmark"):
            v = str(getattr(self, f, "") or "").strip()
            if not v:
                raise ValueError(
                    f"{f}이(가) 비어 있다. 실험 규칙은 결과를 보기 **전에** 전부 "
                    f"확정돼야 한다 - 나중에 채우면 사후합리화와 구분할 수 없다."
                )
            setattr(self, f, v)
        self.parameters = dict(self.parameters or {})

    def core(self) -> dict:
        d = asdict(self)
        return {k: d[k] for k in _CORE_FIELDS}


def register_experiment(experiment: Experiment, status: str = "REGISTERED",
                        blocked_reason: str = None,
                        experiment_dir: str = EXPERIMENT_DIR) -> str:
    """
    실험을 등록한다. 같은 ID가 이미 있으면 거부한다(덮어쓰기 금지).

    status="BLOCKED"이면 `blocked_reason`이 필수다 - "왜 지금 못 하는가"를
    적어두지 않으면 나중에 재개 조건을 알 수 없다.
    """
    if status not in EXPERIMENT_STATUSES:
        raise ValueError(f"알 수 없는 상태: {status} (허용: {EXPERIMENT_STATUSES})")
    if status == "BLOCKED" and not (blocked_reason or "").strip():
        raise ValueError(
            "status='BLOCKED'이면 blocked_reason이 필요하다 - 재개 조건을 "
            "적어두지 않으면 이 실험은 조용히 잊힌다."
        )

    os.makedirs(experiment_dir, exist_ok=True)
    path = os.path.join(experiment_dir, f"{experiment.experiment_id}.json")
    if os.path.exists(path):
        raise FileExistsError(
            f"{path}에 같은 ID의 실험이 이미 있다. 규칙을 바꾸려면 새 실험을 "
            f"등록할 것 - 결과를 본 뒤 규칙을 고치면 검증이 무의미해진다."
        )

    record = {
        "core": experiment.core(),
        # 등록 시점 규칙의 지문. `record_result()`가 매번 대조해 "결과를 본 뒤
        # 규칙을 고쳤는지"를 잡는다 - prediction_ledger의 봉인 방식을 그대로
        # 재사용한다(해시 로직을 복제하면 두 구현이 어긋날 수 있다).
        "core_hash": core_hash(experiment.core()),
        "registered_date": experiment.registered_date,
        "note": experiment.note,
        "status": status,
        "blocked_reason": blocked_reason,
        # 결과는 리스트다 - 덮어쓰지 않고 쌓는다(실패한 시도도 남는다)
        "results": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return path


def record_result(path: str, result: dict, status: str = None) -> dict:
    """
    결과를 **덧붙인다.** 기존 결과는 절대 수정되지 않는다.

    result에는 최소한 무엇을 측정했고 무엇이 나왔는지가 들어가야 한다.
    "결과가 나쁘다"는 이유로 이 함수를 건너뛰고 파일을 지우지 말 것 -
    실패한 실험이 남아 있어야 다음에 같은 실수를 반복하지 않는다.
    """
    if not isinstance(result, dict) or not result:
        raise ValueError("result는 비어 있지 않은 dict여야 한다.")
    if status is not None and status not in EXPERIMENT_STATUSES:
        raise ValueError(f"알 수 없는 상태: {status} (허용: {EXPERIMENT_STATUSES})")

    with open(path, encoding="utf-8") as f:
        record = json.load(f)

    # ⚠️ 등록 시점 규칙과 지금 파일의 규칙이 같은지 **먼저** 확인한다.
    # 결과를 본 뒤 진입/청산 규칙을 조정하는 것이 백테스트를 무의미하게 만드는
    # 주범이므로, 결과를 쓰기 전에 막는다.
    stored_hash = record.get("core_hash")
    if stored_hash is None:
        raise ValueError(
            "core_hash가 없는 실험 기록이다(v3.48 이전 형식이거나 손상). "
            "규칙 불변을 검증할 수 없으므로 결과를 기록하지 않는다."
        )
    if core_hash(record["core"]) != stored_hash:
        raise ValueError(
            f"실험 코어가 등록 이후 변경됐다.\n"
            f"  등록 시점 해시: {stored_hash}\n"
            f"  현재 코어 해시: {core_hash(record['core'])}\n"
            f"결과를 본 뒤 규칙을 고치면 검증이 무의미해진다. 규칙을 바꾸려면 "
            f"새 experiment_id로 등록할 것 - 이 실험은 그대로 두고."
        )

    before = json.dumps(record.get("results", []), ensure_ascii=False, sort_keys=True)
    record.setdefault("results", []).append(result)

    # append-only를 코드로 확인한다(기존 결과가 한 건이라도 바뀌면 거부)
    if json.dumps(record["results"][:-1], ensure_ascii=False, sort_keys=True) != before:
        raise ValueError("기존 결과가 변경됐다 - append-only 위반.")

    if status:
        record["status"] = status

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return record


def load_experiments(experiment_dir: str = EXPERIMENT_DIR) -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(experiment_dir, "*.json"))):
        with open(p, encoding="utf-8") as f:
            rec = json.load(f)
        rec["_path"] = p
        out.append(rec)
    return out


# ────────────────────────────────────────────────────────────────────────
# EXP-001 - 이 시스템의 근본 가설
# ────────────────────────────────────────────────────────────────────────

def core_hypothesis_experiment(registered_date: str) -> Experiment:
    """
    §8이 지정한 첫 실험을 만든다(등록은 호출부가 한다).

    ⚠️ 규칙을 구체적으로 못박아 둔 이유: "Gap이 높으면 수익이 좋은가"처럼
    모호하게 적어두면 나중에 결과를 보고 유리한 정의를 고르게 된다. 진입·청산·
    기간·벤치마크를 미리 확정해야 검증이 성립한다.

    ⚠️ 결과를 미리 가정하지 않는다 - 관계가 없다고 나와도 그대로 기록한다.
    """
    return Experiment(
        experiment_id="EXP-001",
        hypothesis=(
            "Valuation-Implied Requirement(현재 가격이 요구하는 성장률)와 "
            "Evidence-Supported Forward Expectation(재무 실적에 근거한 현실적 "
            "성장률) 사이의 괴리(Expectation Gap)가 미래 위험조정수익률과 "
            "관계가 있는가? **방향과 존재 여부 모두 미지이며 가정하지 않는다.**"
        ),
        universe=(
            "ledger/에 공식 분석이 존재하는 미국 상장 개별주식. 2026-08-15 기준 "
            "34종목. ETF·KRX 래퍼는 제외(밸류에이션 산식이 다르다)."
        ),
        entry_rule=(
            "분석일(meta.analyzed_at) 종가 기준 진입. Gap 오름차순 5분위로 나눠 "
            "최상위 분위(Gap 큼)와 최하위 분위(Gap 작음)를 비교한다. "
            "임계값을 별도로 만들지 않고 분위로 나누는 이유: ±5%p 판정밴드는 "
            "33종목 관측 기반 시작점일 뿐 검증된 경계가 아니기 때문이다."
        ),
        exit_rule=(
            "진입 후 12개월 보유 후 청산(단일 고정 보유기간). 중도 청산·재조정 "
            "없음 - 규칙이 늘어날수록 자유도가 커져 우연한 성공이 쉬워진다."
        ),
        parameters={
            "gap_source": "ledger[].expectation_gap",
            "return_measure": "총수익률(배당 포함), 위험조정은 실현 변동성 대비",
            "min_sample_per_quintile": 5,
            "price_source_required": "inputs.price_at_analysis (v3.24 필드)",
        },
        test_period="미정 - 데이터 확보 후 확정(임의 선택 방지를 위해 사전 고정 예정)",
        oos_period="미정 - test_period 확정과 동시에 분리 고정",
        benchmark=(
            "VOO(S&P500) 동일기간 총수익률. engine/market_relative.py가 이미 "
            "VOO를 기준선으로 쓰고 있어 같은 벤치마크를 유지한다."
        ),
        registered_date=registered_date,
        note=(
            "이 가설이 검증되기 전까지 Expectation Gap은 RESEARCH_HYPOTHESIS다"
            "(engine/gap_analysis.GAP_SIGNAL_STATUS). 매수리스트가 이미 Gap 기반 "
            "등급으로 만들어지고 있다는 사실 자체가 이 실험이 필요한 이유다."
        ),
    )


BLOCKED_REASON_EXP001 = (
    "실행 전제가 아직 없다(2026-08-15 실측). (1) 분석일이 2026-07-25~08-13에 "
    "몰려 있어 12개월 보유수익률을 잴 구간이 아예 존재하지 않는다. "
    "(2) price_at_analysis가 채워진 종목이 34건 중 **9건**뿐이라"
    "(ACGL·BSX·DUOL·MNDY·ROP·SE·TCOM·UBER·WDAY - v3.24 이후 분석만 해당) "
    "나머지 25종목은 진입가를 알 수 없다. (3) 9건을 5분위로 나누면 분위당 "
    "최소 표본(5건)을 채울 수 없다. "
    "재개 조건: 분석일로부터 12개월이 지난 종목이 분위당 5건 이상 확보될 것. "
    "그 전에 실행하면 표본 몇 건으로 alpha를 주장하게 된다(계약서 138절)."
)
