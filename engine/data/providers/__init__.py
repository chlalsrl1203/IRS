"""Provider 계층 - 외부 출처를 IRS 도메인 타입으로 들이는 관문.

외부 라이브러리 객체는 이 경계를 넘지 않는다(통합 원칙 §1.8).
"""
from engine.data.providers.base import (  # noqa: F401
    FinancialFact, FinancialProvider, METRIC_TO_INPUT_FIELD, METRICS,
    ProviderGovernanceError, ProviderResult,
)
