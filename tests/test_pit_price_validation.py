"""
pit_price_validation.py / pit_scorecard.py 테스트 — 네트워크 없이.

고정하는 것:
  ① 조정종가(a)를 쓴다(단순 종가 c가 아니다 - 배당 재투자 총수익이어야 함)
  ② 확보 실패를 0%나 평균으로 채우지 않는다(생존편향을 유리하게 오독 금지)
  ③ T0 이전 상장이 아닌 종목은 조용히 통과시키지 않는다
  ④ 성적표가 표본을 고르지 않는다(입력 전부를 쓴다)
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts import pit_price_validation as V  # noqa: E402
from scripts import pit_scorecard as S  # noqa: E402


# ── ① 조정종가를 쓴다 ────────────────────────────────────────────────────
def test_uses_adjusted_close_not_raw_close(monkeypatch):
    """`a`(배당조정)와 `c`(단순종가)가 다를 때 반드시 `a`를 써야 한다."""
    payload = {"status": 200, "data": [
        {"t": "2021-06-01", "c": 136.96, "a": 133.386986},
        {"t": "2026-08-03", "c": 319.70, "a": 319.70},
    ]}

    class FakeResp:
        def __enter__(self_):
            return self_

        def __exit__(self_, *a):
            return False

        def read(self_):
            return json.dumps(payload).encode()

    monkeypatch.setattr(V.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    series, err = V.fetch_monthly_adjusted("AAPL")
    assert err is None
    assert series["2021-06"] == pytest.approx(133.386986)
    assert series["2026-08"] == pytest.approx(319.70)

    ret, p0, p1, err = V.holding_return(series, "2021-06")
    # 조정종가 기준: 319.70/133.386986 - 1 = +139.7%
    assert ret == pytest.approx(139.68, abs=0.1)


def test_holding_return_rejects_ticker_listed_after_t0():
    """T0 이전 가격이 없으면 수익률을 만들어내지 않는다."""
    ret, p0, p1, err = V.holding_return({"2023-01": 10.0, "2026-08": 20.0}, "2021-06")
    assert ret is None
    assert "T0" in err


def test_holding_return_rejects_series_ending_at_t0():
    ret, p0, p1, err = V.holding_return({"2021-06": 10.0}, "2021-06")
    assert ret is None


def test_empty_series_is_reported_not_zero_filled(monkeypatch):
    """상장폐지 등으로 시계열이 없으면 사유를 남긴다 - 0%로 채우지 않는다."""
    payload = {"status": 200, "data": []}

    class FakeResp:
        def __enter__(self_):
            return self_

        def __exit__(self_, *a):
            return False

        def read(self_):
            return json.dumps(payload).encode()

    monkeypatch.setattr(V.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    series, err = V.fetch_monthly_adjusted("DEAD")
    assert series is None
    assert "없음" in err


def test_symbol_overrides_cover_dotted_tickers():
    assert V.SYMBOL_OVERRIDES["BRK-B"] == "BRK.B"


# ── ② 성적표: 표본을 고르지 않는다 ───────────────────────────────────────
SAMPLE = {
    "as_of_t0": "2021-06-30",
    "validated_at": "2026-08-29",
    "price_source": "stockanalysis.com (배당·분할 조정 월봉 종가)",
    "return_definition": "a(최신월)/a(T0월)-1",
    "benchmark": {"ticker": "SPY", "return_pct": 100.0},
    "n_unavailable": 3,
    "flagged": [{"ticker": "A", "return_pct": 200.0},
                {"ticker": "B", "return_pct": 50.0}],
    "not_flagged": [{"ticker": "C", "return_pct": 10.0},
                    {"ticker": "D", "return_pct": -20.0},
                    {"ticker": "E", "return_pct": 130.0}],
}


def test_scorecard_counts_and_rates(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    summary, text = S.build(str(p))
    assert summary["flagged"]["n"] == 2
    assert summary["not_flagged"]["n"] == 3
    # 동일가중 = 단순평균
    assert summary["flagged"]["equal_weight_portfolio_pct"] == pytest.approx(125.0)
    assert summary["not_flagged"]["equal_weight_portfolio_pct"] == pytest.approx(40.0)
    # 벤치마크(100%) 초과: flagged는 A만 -> 50%, not_flagged는 E만 -> 33%
    assert summary["flagged"]["beat_benchmark_rate"] == pytest.approx(0.5)
    assert summary["not_flagged"]["beat_benchmark_rate"] == pytest.approx(1 / 3)


def test_scorecard_surfaces_unavailable_count(tmp_path):
    """생존편향 경고가 성적표에 반드시 남아야 한다."""
    p = tmp_path / "r.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    summary, text = S.build(str(p))
    assert summary["n_unavailable"] == 3
    assert "생존편향" in text


def test_scorecard_reports_benchmark(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    _, text = S.build(str(p))
    assert "SPY" in text and "+100.0%" in text


# ── 여러 T0 교차 요약 ────────────────────────────────────────────────────
from scripts import pit_multi_t0_summary as M  # noqa: E402


def _returns_file(tmp_path, name, flagged, not_flagged, bench):
    p = tmp_path / name
    p.write_text(json.dumps({
        "as_of_t0": name.replace("pit_returns_", "").replace(".json", ""),
        "validated_at": "2026-08-29",
        "price_source": "test", "return_definition": "test",
        "benchmark": {"ticker": "SPY", "return_pct": bench},
        "n_unavailable": 0,
        "flagged": [{"ticker": f"F{i}", "return_pct": v}
                    for i, v in enumerate(flagged)],
        "not_flagged": [{"ticker": f"N{i}", "return_pct": v}
                        for i, v in enumerate(not_flagged)],
    }), encoding="utf-8")
    return str(p)


def test_multi_t0_reports_per_metric_replication_counts(tmp_path):
    """
    T0 하나에서 이겨도 다른 T0에서 지면 그 사실이 드러나야 한다 - 단일 T0만
    보고 결론내는 함정(2026-08-29 실측에서 실제로 발생)을 막는 장치다.
    """
    a = _returns_file(tmp_path, "pit_returns_2021-06-30.json",
                      flagged=[100.0, 200.0], not_flagged=[10.0, 20.0], bench=50.0)
    b = _returns_file(tmp_path, "pit_returns_2023-06-30.json",
                      flagged=[10.0, 20.0], not_flagged=[100.0, 200.0], bench=50.0)
    rows = M.compare([a, b])
    assert len(rows) == 2
    text = M.render(rows)
    # 한 쪽은 이기고 한 쪽은 져야 재현 횟수가 1/2로 나온다
    assert "**1/2**" in text


def test_multi_t0_does_not_compare_absolute_returns_across_t0(tmp_path):
    """보유기간이 다르므로 T0끼리 절대 수익률을 비교하면 안 된다는 경고 고정."""
    a = _returns_file(tmp_path, "pit_returns_2018-06-30.json",
                      flagged=[10.0], not_flagged=[5.0], bench=1.0)
    text = M.render(M.compare([a]))
    assert "T0끼리 절대 수익률을 비교하지 말 것" in text


def test_scorecard_concentration_metrics_present(tmp_path):
    p = _returns_file(tmp_path, "pit_returns_2021-06-30.json",
                      flagged=[1000.0, 10.0, 20.0, 30.0, 40.0, 50.0],
                      not_flagged=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0], bench=50.0)
    summary, text = S.build(p)
    c = summary["flagged"]["concentration"]
    # 상위 1종목(1000%) 제외하면 평균이 급락해야 한다
    assert c["mean_excl_top1_pct"] == pytest.approx(30.0)
    assert "집중도" in text
