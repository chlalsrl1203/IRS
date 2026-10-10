"""
경쟁 대리지표 (v3.97) — 2026-10-07 실데이터에서 틀렸던 형식을 입력으로 고정한다.
"""

import ast
import os
import unittest

from engine import competition_signals as C
from engine import sec_events as E


class TestPricingPower(unittest.TestCase):
    def test_rules(self):
        rev = {2022: 100.0, 2025: 130.0}
        P = lambda gm: C.pricing_power_from_margins(rev, gm)["answer"]
        self.assertEqual(P({2022: 50.0, 2025: 57.7}), "evidenced")       # DECK형 상승
        self.assertEqual(P({2022: 87.7, 2025: 89.3}), "evidenced")       # ADBE형 고수준 유지
        self.assertEqual(P({2022: 75.9, 2025: 56.3}), "eroding")         # PDD형 하락
        self.assertEqual(P({2022: 40.0, 2025: 40.2}), "unevidenced")

    def test_shrinking_revenue_never_evidenced(self):
        r = C.pricing_power_from_margins({2022: 100.0, 2025: 90.0}, {2022: 80.0, 2025: 85.0})
        self.assertEqual(r["answer"], "unevidenced")

    def test_no_cost_data_is_unknown(self):
        self.assertIsNone(C.pricing_power_from_margins({2025: 1.0}, {})["answer"])

    def test_gross_margin_from_cost(self):
        self.assertAlmostEqual(C.gross_margins({2025: 200.0}, None, {2025: 50.0})[2025], 75.0)


class TestRelativeGrowth(unittest.TestCase):
    def test_align_by_year_end_not_label(self):
        # NXT(3월 결산) vs ARRY(12월 결산): 라벨 2026 ↔ 결산 2025-12-31이 맞는 짝이다.
        company = {2026: (100.0, "2026-03-31"), 2023: (50.0, "2023-03-31")}
        peer = {2025: (80.0, "2025-12-31"), 2022: (60.0, "2022-12-31")}
        self.assertEqual(C.align_to(company, peer), {2026: 80.0, 2023: 60.0})

    def test_far_year_end_is_not_matched(self):
        self.assertEqual(C.align_to({2026: (1.0, "2026-03-31")}, {2024: (1.0, "2024-12-31")}), {})

    def test_gaining_losing_and_lifecycle(self):
        co = {2022: 100.0, 2025: 172.8}                     # CAGR 20%
        peers = {"A": {2022: 100.0, 2025: 133.1}}            # CAGR 10%
        r = C.relative_growth(co, peers)
        self.assertEqual((r["answer"], r["lifecycle_decline"]), ("gaining", False))
        r = C.relative_growth({2022: 100.0, 2025: 90.0}, {"A": {2022: 100.0, 2025: 80.0}})
        self.assertIs(r["lifecycle_decline"], True)

    def test_peer_missing_years_dropped(self):
        r = C.relative_growth({2022: 1.0, 2025: 2.0}, {"A": {2025: 5.0}})
        self.assertIsNone(r["answer"])


class TestRiskFactorDiff(unittest.TestCase):
    def test_section_pairs_end_with_nearest_start(self):
        # 본문 중간 상호참조('see Item 1A. Risk Factors')에서 시작하면 사업 설명을 삼킨다(실측: NBIX).
        body = ("Item 1. Business. Human capital: we offer competitive base salaries. See Item 1A. Risk Factors for "
                "details. ... Item 1A. Risk Factors We face competition from new entrants offering AI tools. "
                "Item 1B. Unresolved Staff Comments None.")
        sec = C.risk_factor_section(body, "10-K")
        self.assertNotIn("salaries", sec)
        self.assertIn("new entrants", sec)

    def test_no_end_marker_returns_empty(self):
        self.assertEqual(C.risk_factor_section("Item 1A. Risk Factors " + "x " * 50, "10-K"), "")

    def test_new_competition_sentences(self):
        old = ("Item 1A. Risk Factors We operate in a highly regulated industry and our results may fluctuate. "
               "Our competent authorities may change rules at any time without notice to us.")
        new = old + (" Our competitors may develop agentic AI solutions more rapidly and successfully than we do. "
                     "We provide competitive base salaries and bonuses to retain top talent across our teams. "
                     "Our competent authorities in Vietnam approved our ownership of the payment business.")
        r = C.new_competition_sentences(new, old)
        self.assertEqual(r["n_new_competition"], 1)      # 인재 경쟁·'competent'는 제외
        self.assertIn("agentic AI", r["sentences"][0])

    def test_missing_sections_unknown(self):
        self.assertIsNone(C.new_competition_sentences("", "x")["answer"])


class TestEnforcement(unittest.TestCase):
    def test_definitive_statements_only(self):
        self.assertTrue(E.enforcement_statements(
            "Additionally, in July 2022, we entered into a non-prosecution agreement with the DOJ concerning its "
            "investigation into our handling of the 2016 Breach."))
        self.assertFalse(E.enforcement_statements(
            "Such examinations can result in fines, censure, the issuance of cease-and-desist orders or other "
            "sanctions."))


class TestBoundaries(unittest.TestCase):
    def test_no_verdict_functions_and_not_wired(self):
        root = os.path.dirname(C.__file__)
        src = open(os.path.join(root, "competition_signals.py"), encoding="utf-8").read()
        names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
        self.assertFalse({n for n in names if any(w in n for w in ("score", "verdict", "weight", "buy"))})
        for f in ("pipeline.py", "expectation_gap_engine.py", "portfolio_pipeline.py"):
            self.assertNotIn("competition_signals", open(os.path.join(root, f), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
