"""
Provider Interface (P0-02, 2026-08-19) — 외부 데이터 출처를 IRS 도메인으로 들이는 관문.

# SOURCE:
https://github.com/dgunning/edgartools        (typed filing abstraction, adapter 경계)
https://github.com/eddmpython/dartlab         (SEC/DART 통합 Company 추상화)
https://github.com/simonlin1212/global-stock-data  (source governance 연결)

# CAPABILITY:
provider abstraction / typed domain object / adapter 경계 / 시장 중립 인터페이스

# IRS_TARGET:
engine/data/providers/base.py

# METHOD:
REIMPLEMENT — 어느 라이브러리의 클래스도 상속하거나 재노출하지 않는다.
가져온 것은 **경계 설계**뿐이다: 외부 라이브러리 객체가 도메인 안으로 새지
않도록 provider가 IRS 자체 타입만 돌려주게 하는 구조(통합 원칙 §1.8), 그리고
SEC/DART처럼 서로 다른 시장을 **같은 인터페이스**로 다루는 발상(DartLab).

# WHY:
지금까지 원자료는 **분석 스크립트 안 dict 리터럴**로만 존재했다
(`docs/change_plan.md` C-09가 Provenance를 DEFERRED로 둔 사유가 정확히 이것).
그래서 다음을 구조적으로 답할 수 없었다:
  - 이 숫자가 어느 provider에서 왔는가 (`data_sources` 자유문자열뿐)
  - 그 provider를 이 용도로 써도 되는가 (P0-01 등록부가 만들어졌지만 미배선)
  - **회계기간과 공시일이 구분되는가** (§14: period ≠ available_at)

# TEST:
tests/test_provider_base.py

---

## 이 계층이 정한 것 — P0-01이 남긴 "어디서 차단할 것인가"

`check_use()`는 판정만 돌려주고 차단하지 않는다. 그 강제 지점을 여기로 정했다:

| 판정 | provider 동작 |
|---|---|
| `PROHIBITED` | **거부**(예외). 약관을 확인했고 그 용도가 아니라고 확인된 경우다 |
| `UNVERIFIED` | **진행하되 결과에 경고를 싣는다.** 차단하지 않는다 |
| `ALLOWED` | 진행 |

`UNVERIFIED`에서 차단하지 않는 이유: 현재 등록된 6건 중 4건이 미확인이고
(Alpha Vantage·FMP·stockanalysis·web_research), 여기서 막으면 실제로 돌아가던
스크리닝이 전부 멈춘다. **그러나 조용히 통과시키지도 않는다** — 모든
`ProviderResult`가 `governance` 판정을 들고 다니므로 ledger·리포트까지 따라간다.
"미확인이니 일단 진행"과 "미확인인 줄 모르고 진행"은 다르다.

## 이 계층이 하지 않는 것

- **정규화·대조를 하지 않는다**(P0-06/07의 몫). provider는 출처가 준 값을
  IRS 타입으로 옮기기만 한다. 여기서 값을 고치면 "출처가 뭐라고 했는가"를
  잃는다.
- **캐시하지 않는다.** 필요해지면 실증 사례를 갖고 넣는다(Simplicity First).
- **AnalysisInputs를 만들지 않는다.** `to_series()`로 분석자가 조립할 재료만
  준다 — provider가 분석 입력을 직접 조립하면 주관 입력(경쟁강도 등)이
  자동 생성된 것처럼 보인다.
"""

import abc
from dataclasses import asdict, dataclass, field

from engine.data.governance.source_registry import UNVERIFIED, check_use, get_source

# IRS 도메인이 쓰는 지표 어휘. `AnalysisInputs`의 `*_by_year` 필드와 1:1이며,
# 새 지표를 늘리기 전에 그 지표를 실제로 쓰는 분석이 있는지부터 확인할 것.
METRICS = (
    "revenue",
    "operating_income",
    "operating_cashflow",
    "capex",
    "net_income",
    "shareholders_equity",
    "dividends_paid",
    "sbc",
)

# `AnalysisInputs` 필드명으로의 매핑. 조립은 분석자가 하되, 이름이 어긋나
# 조용히 빈 딕셔너리가 들어가는 일은 없게 한다.
METRIC_TO_INPUT_FIELD = {m: f"{m}_by_year" for m in METRICS}


@dataclass(frozen=True)
class FinancialFact:
    """
    수치 하나. §14 CORE DATA CONTRACT를 이 계층이 실제로 보장할 수 있는 만큼 담는다.

    ⚠️ **`period`와 `available_at`은 다른 것이다**(§14의 핵심 요구).
    `period`는 "무엇에 대한 수치인가"(FY2023 매출), `available_at`은 "언제부터
    알 수 있었는가"(그 10-K 제출일). 둘을 섞으면 PIT 검증이 통째로 무의미해진다 —
    이 저장소는 v3.47~v3.49에서 이미 그 대가를 치렀다.

    `version`·`restated_at`은 **의도적으로 넣지 않았다.** 재작성 이력을
    추적하려면 같은 사실의 여러 판본을 저장해야 하는데, 그건 스냅샷 계층
    (P0-09)이 생겨야 의미가 있다. 지금 필드만 만들면 항상 None인 칸이 된다.
    """

    entity: str            # 티커 또는 CIK
    metric: str            # METRICS 중 하나
    fiscal_year: int
    value: float
    unit: str              # "currency_amount" / "shares" / "ratio"
    currency: str          # 비통화 단위면 None
    period_start: str      # YYYY-MM-DD
    period_end: str
    available_at: str      # 공시일 — period와 다르다
    source: str            # 구체적 식별자 (예: "SEC XBRL us-gaap:Revenues")
    source_key: str        # SOURCE_REGISTRY 키
    retrieved_at: str

    def __post_init__(self):
        if self.metric not in METRICS:
            raise ValueError(
                f"알 수 없는 지표: {self.metric} (허용: {METRICS}). "
                f"새 지표는 그것을 실제로 쓰는 분석이 생겼을 때 추가할 것."
            )
        get_source(self.source_key)      # 미등록 출처면 여기서 KeyError
        for f in ("entity", "period_start", "period_end", "available_at",
                  "source", "retrieved_at"):
            if not str(getattr(self, f) or "").strip():
                raise ValueError(
                    f"{f}이(가) 비어 있다. **추측으로 채우지 않는다** — 특히 "
                    f"available_at을 오늘 날짜로 채우면 PIT 검증이 거짓이 된다."
                )
        if self.available_at < self.period_end:
            raise ValueError(
                f"{self.entity} {self.metric} FY{self.fiscal_year}: 공시일"
                f"({self.available_at})이 회계기간 종료일({self.period_end})보다 "
                f"앞선다 — 기간이 끝나기 전에 그 기간 실적이 공시될 수는 없다. "
                f"출처 파싱이 잘못됐거나 두 날짜가 뒤바뀌었다."
            )


@dataclass
class ProviderResult:
    """
    provider 한 번 호출의 산출물. **외부 라이브러리 객체를 담지 않는다**(§1.8).

    `limitations`를 비워두지 말 것 — 못 가져온 것을 적지 않으면 커버리지가
    실제보다 높아 보인다(provenance·ETF 엔진과 동일 원칙).
    """

    source_key: str
    entity: str
    facts: list                       # list[FinancialFact]
    governance: dict                  # check_use() 판정 — 결과를 따라다닌다
    retrieved_at: str
    limitations: list = field(default_factory=list)
    raw_ref: str = ""                 # 원본 위치(URL 등). 원본 객체가 아니라 참조만

    def to_series(self, metric: str) -> dict:
        """
        `{회계연도: 값}`. `AnalysisInputs.*_by_year`에 그대로 넣을 수 있는 형태다.

        같은 연도가 두 번 오면 **예외를 던진다** — 조용히 덮어쓰면 어느 값이
        살아남았는지 알 수 없다(대조는 P0-07의 몫이지 여기서 임의로 고를 일이 아니다).
        """
        if metric not in METRICS:
            raise ValueError(f"알 수 없는 지표: {metric}")
        out = {}
        for f in self.facts:
            if f.metric != metric:
                continue
            if f.fiscal_year in out and out[f.fiscal_year] != f.value:
                raise ValueError(
                    f"{self.entity} {metric} FY{f.fiscal_year}에 서로 다른 값이 "
                    f"둘 있다({out[f.fiscal_year]} vs {f.value}). provider가 임의로 "
                    f"고르지 않는다 — 대조·선택은 reconcile 계층(P0-07)의 몫이다."
                )
            out[f.fiscal_year] = f.value
        return out

    def available_at_by_year(self, metric: str = "revenue") -> dict:
        """`AnalysisInputs.filing_dates_by_year`에 바로 넣을 수 있는 형태."""
        return {f.fiscal_year: f.available_at
                for f in self.facts if f.metric == metric}

    def coverage(self) -> dict:
        metrics = sorted({f.metric for f in self.facts})
        years = sorted({f.fiscal_year for f in self.facts})
        return {
            "source_key": self.source_key, "entity": self.entity,
            "n_facts": len(self.facts), "metrics": metrics,
            "fiscal_years": years,
            "governance_decision": self.governance.get("decision"),
            "limitations": list(self.limitations),
        }

    def as_dict(self) -> dict:
        return {
            "source_key": self.source_key, "entity": self.entity,
            "retrieved_at": self.retrieved_at, "governance": self.governance,
            "limitations": list(self.limitations), "raw_ref": self.raw_ref,
            "facts": [asdict(f) for f in self.facts],
        }


class ProviderGovernanceError(PermissionError):
    """약관상 허용되지 않는 것이 **확인된** 사용. 미확인은 여기 해당하지 않는다."""


class FinancialProvider(abc.ABC):
    """
    모든 데이터 출처가 구현하는 인터페이스.

    SEC(미국)·DART(한국)를 같은 타입으로 다루는 것이 목적이다(DartLab의 통합
    Company 추상화에서 가져온 발상) — 시장별 분기가 도메인 코드로 새면 시장을
    하나 늘릴 때마다 분석 코드를 고쳐야 한다.
    """

    #: SOURCE_REGISTRY 키. 하위 클래스가 반드시 지정한다.
    source_key: str = None

    #: 이 provider의 기본 사용 목적. 등록부 판정에 쓰인다.
    default_purpose: str = "internal_research"

    def __init__(self, purpose: str = None, today: str = None):
        if not self.source_key:
            raise ValueError(
                f"{type(self).__name__}가 source_key를 지정하지 않았다 — 등록부에 "
                f"없는 출처는 그 사용이 어디에도 기록되지 않는다."
            )
        self.purpose = purpose or self.default_purpose
        self.governance = check_use(self.source_key, self.purpose, today=today)
        if self.governance["decision"] == "PROHIBITED":
            raise ProviderGovernanceError(
                f"[PROHIBITED] {self.governance['reason']}"
            )

    def governance_limitations(self) -> list:
        """
        미확인 출처를 **조용히 통과시키지 않는다.** 이 문자열이 ProviderResult를
        타고 ledger·리포트까지 따라간다.
        """
        g = self.governance
        out = []
        if g["decision"] == UNVERIFIED:
            out.append(
                f"[출처 거버넌스 미확인] {g['provider']}를 '{self.purpose}' 목적으로 "
                f"쓰고 있으나 약관을 확인하지 못했다 — {g['reason']}"
            )
        if g.get("stale"):
            out.append(
                f"[출처 확인 낡음] {g['provider']}의 마지막 약관 확인일이 "
                f"{g['last_verified']}다. 재확인 대상."
            )
        if get_source(self.source_key).authority in ("VENDOR", "AGGREGATOR_WEB"):
            out.append(
                f"[2차 출처] {g['provider']}는 1차 공시가 아니다. 판정에 영향을 줄 수 "
                f"있는 수치는 SEC 원자료로 대조할 것(TYL SBC 3배 오류의 교훈)."
            )
        return out

    def _result(self, entity: str, facts: list, retrieved_at: str,
                limitations: list = None, raw_ref: str = "") -> ProviderResult:
        """하위 클래스가 결과를 만들 때 쓰는 헬퍼 — 거버넌스 경고를 자동으로 얹는다."""
        return ProviderResult(
            source_key=self.source_key, entity=entity, facts=list(facts),
            governance=self.governance, retrieved_at=retrieved_at,
            limitations=self.governance_limitations() + list(limitations or []),
            raw_ref=raw_ref,
        )

    @abc.abstractmethod
    def fetch_annual_financials(self, entity: str, metrics=None,
                                fiscal_years=None) -> ProviderResult:
        """
        연간 재무수치를 IRS 타입으로 돌려준다.

        ⚠️ 요청한 지표·연도를 못 가져오면 **빈 값으로 채우지 말고**
        `limitations`에 적을 것. 0으로 채우면 CAGR이 조용히 틀린다.
        """
