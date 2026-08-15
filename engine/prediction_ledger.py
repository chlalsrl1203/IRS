"""
Prediction Ledger (v3.48 신규, 2026-08-15) - 판단 당시의 예측을 봉인하고,
나중에 실제 결과를 붙여 비교한다.

## 왜 필요한가 - 이 프로젝트에 이미 있던 것과 없던 것

`falsification_conditions`(v3.24)는 **자유 텍스트**다. "2026-08-05 Q2 실적에서
유료구독자 순증이 재차 감소하면 재검토"처럼 잘 적힌 것도 있지만, 구조가 없어
기계적으로 채점할 수 없고 **얼마나 틀렸는지**를 잴 수 없다(맞았다/틀렸다만 가능).

`growth_scorecard`(v3.43)는 성장률 한 축만 본다.

이 모듈은 **임의의 지표**에 대해 "언제까지, 어느 범위일 것이다"를 사전등록하고,
실제값이 나오면 오차와 함께 봉인한다. 시간이 쌓이면 "나는 어떤 종류의 예측을
반복적으로 틀리는가"에 답할 수 있게 된다 - 이 시스템의 최종 목표다.

## ⚠️ 이 모듈의 존재 이유이자 유일한 핵심 불변조건

    **결과를 알고 난 뒤에는 예측을 고칠 수 없다.**

이게 없으면 예측 기록은 무의미하다 - 결과를 보고 예측을 슬쩍 넓히면 적중률이
100%가 되기 때문이다. 이 프로젝트는 그런 유형의 사고를 이미 여러 번 경계해왔다
(반증조건 소급 작성 금지, ledger 덮어쓰기 금지, 구 ledger가 통계를 오염시킨 사고).

강제 방식은 **코어 해시**다:
  - 예측을 기록할 때 코어(지표·기한·범위·가정)의 SHA-256을 함께 저장한다.
  - 결과를 붙일 때 코어를 다시 해싱해 대조한다. 한 글자라도 바뀌었으면 거부한다.
  - 이미 해소(resolve)된 예측을 다시 해소하려 해도 거부한다.

파일을 직접 손으로 고치는 것까지 막지는 못하지만(git이 그걸 잡는다), **코드
경로로는 불가능**하게 만든다.

## 채점 규칙 - 발명이 아니라 사전등록 범위의 정의 그대로

  status = HIT   : 실제값이 expected_range 안
           MISS  : 밖
           UNRESOLVABLE : 데이터를 구할 수 없음(추측으로 채우지 않는다)

  forecast_error = 범위 안이면 0.0, 밖이면 가장 가까운 경계까지의 거리

"범위를 벗어난 만큼이 오차"는 사전등록 범위의 의미 그대로이며 새로 만든
가중치가 아니다. 부호를 유지해(위로 벗어나면 +, 아래로 -) 편향(bias)을
나중에 볼 수 있게 한다 - "나는 늘 낙관적인가"에 답하려면 부호가 필요하다.
"""

import glob
import hashlib
import json
import os
from dataclasses import asdict, dataclass

PREDICTION_DIR = "predictions"

PREDICTION_STATUSES = ("OPEN", "HIT", "MISS", "UNRESOLVABLE")

# 코어 = 결과를 알기 전에 확정돼야 하는 것 전부. 이 필드들이 해시 대상이다.
_CORE_FIELDS = (
    "thesis_id", "ticker", "prediction_date", "horizon",
    "metric", "expected_low", "expected_high", "assumption", "unit",
)


@dataclass
class Prediction:
    """
    §6의 예측 1건.

    expected_range를 (low, high) 두 필드로 나눈 이유: 튜플/리스트로 두면 JSON
    왕복 시 타입이 흔들려 해시가 달라진다(list vs tuple). 봉인이 목적인
    구조에서 그런 불안정성은 치명적이라 스칼라 두 개로 고정했다.
    """

    thesis_id: str
    ticker: str
    prediction_date: str      # ISO 날짜 - 예측을 **한** 날
    horizon: str              # 언제까지의 예측인가 (예: "FY2026 Q3 실적")
    metric: str               # 무엇을 예측하는가 (예: "매출 YoY 성장률")
    expected_low: float
    expected_high: float
    assumption: str           # 이 예측이 성립하는 전제
    unit: str = "decimal"     # decimal(0.12=12%) / percent / usd / count 등
    source: str = ""          # 예측 근거 출처

    def __post_init__(self):
        self.ticker = str(self.ticker).strip().upper()
        for f in ("thesis_id", "prediction_date", "horizon", "metric", "assumption"):
            v = str(getattr(self, f, "") or "").strip()
            if not v:
                raise ValueError(
                    f"{f}이(가) 비어 있다. 사전등록 예측은 나중에 채울 수 없으므로 "
                    f"기록 시점에 전부 확정돼야 한다."
                )
            setattr(self, f, v)

        self.expected_low = float(self.expected_low)
        self.expected_high = float(self.expected_high)
        if self.expected_low > self.expected_high:
            raise ValueError(
                f"expected_low({self.expected_low}) > expected_high({self.expected_high}). "
                f"범위가 뒤집혀 있다."
            )

    def core(self) -> dict:
        d = asdict(self)
        return {k: d[k] for k in _CORE_FIELDS}

    def core_hash(self) -> str:
        return core_hash(self.core())

    @property
    def prediction_id(self) -> str:
        """결정적 ID - 같은 내용이면 같은 ID(중복 기록을 파일명 단계에서 잡는다)."""
        return f"{self.ticker}-{self.prediction_date}-{self.core_hash()[:8]}"


def core_hash(core: dict) -> str:
    """
    코어의 SHA-256. `sort_keys=True`로 키 순서에 무관하게 만들고, 숫자는 JSON
    표준 표기를 쓴다 - 저장/로드를 왕복해도 같은 값이 나와야 봉인이 성립한다.
    """
    payload = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_prediction(prediction: Prediction,
                      prediction_dir: str = PREDICTION_DIR) -> str:
    """
    예측을 봉인해 기록한다. 같은 ID(=같은 내용) 파일이 있으면 거부한다.

    저장 시점에 `status="OPEN"`이며 결과 필드는 전부 None이다 - 결과를 미리
    채워 넣을 경로 자체를 만들지 않는다.
    """
    os.makedirs(prediction_dir, exist_ok=True)
    path = os.path.join(prediction_dir, f"{prediction.prediction_id}.json")
    if os.path.exists(path):
        raise FileExistsError(
            f"{path}에 같은 내용의 예측이 이미 있다(ID는 코어 해시에서 나온다). "
            f"다른 예측이라면 지표나 범위가 실제로 달라야 한다."
        )

    record = {
        "prediction_id": prediction.prediction_id,
        "core": prediction.core(),
        "core_hash": prediction.core_hash(),
        "source": prediction.source,
        "status": "OPEN",
        "actual_value": None,
        "actual_date": None,
        "forecast_error": None,
        "resolution_note": None,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return path


def forecast_error(actual: float, low: float, high: float) -> float:
    """
    사전등록 범위 대비 오차. 범위 안이면 0, 밖이면 가장 가까운 경계까지의
    **부호 있는** 거리(위로 벗어나면 +, 아래로 -).

    부호를 남기는 이유: 나중에 "내 예측이 체계적으로 낙관적인가"를 보려면
    절댓값만으로는 알 수 없다.
    """
    if low <= actual <= high:
        return 0.0
    return actual - high if actual > high else actual - low


def resolve_prediction(path: str, actual_value, actual_date: str,
                       note: str = "", unresolvable: bool = False) -> dict:
    """
    실제 결과를 붙인다. **여기가 이 모듈의 심장이다.**

    세 가지를 검사한다:
      1. 파일의 코어를 다시 해싱해 저장된 해시와 대조 - 다르면 거부.
         (결과를 본 뒤 예측을 고쳤다는 뜻이다)
      2. 이미 해소된 예측이면 거부 - 결과를 두 번 쓰지 않는다.
      3. `unresolvable=True`면 실제값 없이 UNRESOLVABLE로 닫는다 - 데이터를
         못 구했을 때 추측으로 채우지 않기 위한 정직한 출구다(계약서 155절).
    """
    with open(path, encoding="utf-8") as f:
        record = json.load(f)

    if record["status"] != "OPEN":
        raise ValueError(
            f"이미 해소된 예측이다(status={record['status']}). 결과는 한 번만 "
            f"기록한다 - 다시 쓰면 사후 조정과 구분할 수 없다."
        )

    recomputed = core_hash(record["core"])
    if recomputed != record["core_hash"]:
        raise ValueError(
            f"예측 코어가 변조됐다.\n"
            f"  기록 시점 해시: {record['core_hash']}\n"
            f"  현재 코어 해시: {recomputed}\n"
            f"결과를 알고 난 뒤 예측을 수정할 수 없다(이 모듈의 핵심 불변조건). "
            f"예측이 잘못 기록됐다면 이 건을 UNRESOLVABLE로 닫고 새 예측을 "
            f"기록할 것 - 과거 기록을 고치지 않는다."
        )

    if unresolvable:
        record.update({
            "status": "UNRESOLVABLE",
            "actual_date": actual_date,
            "resolution_note": note or "실제값을 확보하지 못함(추측으로 채우지 않음)",
        })
    else:
        actual = float(actual_value)
        low, high = record["core"]["expected_low"], record["core"]["expected_high"]
        err = forecast_error(actual, low, high)
        record.update({
            "status": "HIT" if err == 0.0 else "MISS",
            "actual_value": actual,
            "actual_date": actual_date,
            "forecast_error": err,
            "resolution_note": note,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return record


def load_predictions(prediction_dir: str = PREDICTION_DIR,
                     thesis_id: str = None, ticker: str = None) -> list:
    """저장된 예측을 읽는다(선택적으로 thesis/티커로 필터)."""
    out = []
    for p in sorted(glob.glob(os.path.join(prediction_dir, "*.json"))):
        with open(p, encoding="utf-8") as f:
            rec = json.load(f)
        if thesis_id and rec["core"]["thesis_id"] != thesis_id:
            continue
        if ticker and rec["core"]["ticker"] != ticker.upper():
            continue
        rec["_path"] = p
        out.append(rec)
    return out


def prediction_summary(prediction_dir: str = PREDICTION_DIR) -> dict:
    """
    적중률과 **편향**을 함께 낸다.

    ⚠️ 적중률을 확률로 해석하지 말 것 - 표본이 몇 건인지 반드시 함께 볼 것.
    이 프로젝트는 표본 5건으로 확률을 주장하는 것을 금지해왔다(계약서 138절,
    Confidence Calibration을 보류한 이유와 같다). 그래서 분자·분모를 그대로
    노출하고 비율은 표본이 있을 때만 계산한다.
    """
    records = load_predictions(prediction_dir)
    resolved = [r for r in records if r["status"] in ("HIT", "MISS")]
    hits = [r for r in resolved if r["status"] == "HIT"]
    errors = [r["forecast_error"] for r in resolved if r["forecast_error"] is not None]

    return {
        "n_total": len(records),
        "n_open": sum(1 for r in records if r["status"] == "OPEN"),
        "n_resolved": len(resolved),
        "n_unresolvable": sum(1 for r in records if r["status"] == "UNRESOLVABLE"),
        "n_hit": len(hits),
        "n_miss": len(resolved) - len(hits),
        "hit_rate": (len(hits) / len(resolved)) if resolved else None,
        # 부호 있는 평균 오차 = 편향. 양수면 실제가 예측 상단을 계속 넘었다는 뜻
        # (= 내가 체계적으로 보수적이었다), 음수면 반대(= 낙관적이었다).
        "mean_signed_error": (sum(errors) / len(errors)) if errors else None,
        "calibration_status": (
            "UNCALIBRATED - 표본이 적으면 적중률은 확률이 아니다. "
            "n_resolved를 반드시 함께 볼 것."
        ),
    }
