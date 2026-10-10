"""
가이던스 원장 (v3.96) — 실제 보도자료에서 마주친 형식을 입력으로 고정한다.

각 케이스는 2026-10-07 수집 중 실제로 틀렸거나 놓칠 뻔한 형식이다:
  ADBE  표 머리 'FY2026 targets' + 같은 문서의 분기 표('first quarter FY2026 targets')
  DUOL  'Q4 2025 FY 2025' 나란한 표 머리 — 첫 범위는 **분기** 열이다
  DECK  'Outlook for the Twelve Month Period Ending …' 제목과 수치 사이에 긴 면책 문단, '약 $X' 점 추정
  NBIX  'INGREZZA® Net Sales Guidance' — 제품 매출을 총매출로 읽으면 안 된다
  PTC   'FY’26'(곡선 아포스트로피), '$ in millions' 표
"""

import ast
import os
import unittest

from engine import guidance_ledger as G

ADBE = ("Financial Targets The following table summarizes Adobe’s FY2026 targets 1 : Total revenue "
        "$25.90 billion to $26.10 billion Business Professionals & Consumers subscription revenue $7.35 billion "
        "to $7.40 billion The following table summarizes Adobe’s first quarter FY2026 targets 2 : Total revenue "
        "$6.25 billion to $6.30 billion")
ADBE_Q_FIRST = ("The following table summarizes Adobe’s fourth quarter fiscal year 2025 targets, which assumes "
                "current macroeconomic conditions 1 : Total revenue $6.075 billion to $6.125 billion")
DUOL = ("Duolingo is providing the following guidance for the fourth quarter ending December 31, 2025 and the "
        "full year ending December 31, 2025. (in millions) Q4 2025 FY 2025 Bookings $329.5 - $335.5 $1,151 - "
        "$1,157 YoY Bookings Growth 21.3% - 23.5% 32.2% - 32.9% Revenues $273 - $277 $1,028 - $1,032")
DUOL_POINT_FIRST = ("(in millions) Q1 2026 FY 2026 Bookings $301.5 $1,274 - $1,298 YoY Bookings Growth 11% "
                    "10% - 12% Revenues $288.5 $1,197 - $1,221")
DECK = ("Outlook for the Twelve Month Period Ending March 31, 2024 The Company’s outlook is forward-looking in "
        "nature, reflecting our expectations as of May 25, 2023, and is subject to significant risks and "
        "uncertainties that limit our ability to accurately forecast results. This outlook assumes no meaningful "
        "changes to the Company’s business prospects or risks and uncertainties identified by management that "
        "could impact future results, which include but are not limited to: changes in macroeconomic "
        "conditions, including consumer confidence, discretionary spending, inflationary pressures. • Net sales "
        "are expected to be approximately $3.950 billion. • Gross margin is expected to be approximately 52%.")
DECK_Q = ("Outlook for the Three Month Period Ending September 30, 2025 The Company’s outlook is "
          "forward-looking in nature. • Net sales are expected to be in the range of $1.38 billion to $1.42 billion.")
NBIX = ("Reaffirmed 2026 Full-Year INGREZZA ® (valbenazine) Net Sales Guidance of $2.7 - $2.8 Billion "
        "SAN DIEGO , May 5, 2026")
PTC = ("Guidance $ in millions, except per share amounts FY’25 Actual FY’26 Guidance FY’26 YoY Growth Guidance "
       "Q1’26 Guidance Free cash flow $857 ~$1,000 ~17% $265 to $270 Revenue $2,739 $2,650 to $2,915 3 (3%) to 6% "
       "3 $600 to $660")


def _one(text):
    out = G.extract_annual_revenue_guidance(text)
    return {g["fy"]: g for g in out}


class TestExtraction(unittest.TestCase):
    def test_adbe_annual_table_not_segment_not_quarter(self):
        g = _one(ADBE)
        self.assertEqual(set(g), {2026})
        self.assertEqual((g[2026]["low"], g[2026]["high"]), (25.90e9, 26.10e9))

    def test_quarter_attached_to_year_is_quarterly(self):
        self.assertEqual(_one(ADBE_Q_FIRST), {})

    def test_duol_side_by_side_header_takes_annual_column(self):
        g = _one(DUOL)
        self.assertEqual((g[2025]["low"], g[2025]["high"]), (1028e6, 1032e6))   # 분기 $273~277M가 아니다

    def test_duol_point_in_quarter_column(self):
        g = _one(DUOL_POINT_FIRST)
        self.assertEqual((g[2026]["low"], g[2026]["high"]), (1197e6, 1221e6))

    def test_deck_heading_fallback_and_point(self):
        g = _one(DECK)
        self.assertEqual(g[2024]["kind"], "point")
        self.assertEqual(g[2024]["low"], 3.95e9)

    def test_deck_three_month_heading_is_quarterly(self):
        self.assertEqual(_one(DECK_Q), {})

    def test_product_trademark_guidance_rejected(self):
        self.assertEqual(_one(NBIX), {})

    def test_ptc_curly_apostrophe_and_unit_header(self):
        g = _one(PTC)
        self.assertEqual((g[2026]["low"], g[2026]["high"]), (2650e6, 2915e6))

    def test_excerpt_is_verbatim_substring(self):
        for text in (ADBE, DUOL, DECK, PTC):
            for g in G.extract_annual_revenue_guidance(text):
                self.assertIn(g["excerpt"], text)


def _rel(filed, fy, low, high, kind="range"):
    return {"filed": filed, "url": "u", "guidance": [{"fy": fy, "low": low, "high": high, "kind": kind,
                                                       "excerpt": "x"}]}


class TestLedger(unittest.TestCase):
    ACT = {2024: (100.0e6, "2024-12-31", "2025-02-20", "Revenues"),
           2025: (95.0e6, "2025-12-31", "2026-02-20", "Revenues")}

    def test_met_and_miss(self):
        led = G.build_ledger([_rel("2024-02-01", 2024, 98e6, 102e6), _rel("2025-02-01", 2025, 96e6, 99e6)],
                             self.ACT)
        st = {r["fy"]: r["status"] for r in led}
        self.assertEqual(st, {2024: "MET", 2025: "MISS"})

    def test_late_initial_not_evaluated(self):
        led = G.build_ledger([_rel("2024-10-01", 2024, 98e6, 102e6)], self.ACT)
        self.assertEqual(led[0]["status"], "LATE_INITIAL")

    def test_misread_quarter_dropped_individually(self):
        # 분기 가이던스가 연간으로 잘못 읽힌 항목(실제의 1/4)은 개별로 버려진다.
        led = G.build_ledger([_rel("2024-01-15", 2024, 24e6, 26e6), _rel("2024-02-01", 2024, 99e6, 101e6)],
                             self.ACT)
        self.assertEqual(led[0]["n_dropped"], 1)
        self.assertEqual(led[0]["initial"]["low"], 99e6)

    def test_point_tolerance(self):
        led = G.build_ledger([_rel("2025-02-01", 2025, 95.5e6, 95.5e6, "point")], self.ACT)
        self.assertEqual(led[0]["status"], "MET")      # 0.5% 하회는 '약' 범위 안
        led = G.build_ledger([_rel("2025-02-01", 2025, 97e6, 97e6, "point")], self.ACT)
        self.assertEqual(led[0]["status"], "MISS")

    def test_label_ambiguous_early_january_year_end(self):
        self.assertTrue(G.label_ambiguous({2025: (1.0, "2025-01-03", "2025-03-01", "R")}))
        self.assertFalse(G.label_ambiguous({2025: (1.0, "2025-11-28", "2026-01-20", "R")}))


class TestJudge(unittest.TestCase):
    def _row(self, fy, status):
        return {"fy": fy, "status": status, "actual": {"filed": f"{fy + 1}-02-01"}}

    def test_rules(self):
        J = lambda rows: G.judge(rows, "2026-10-07")
        j = J([self._row(2023, "MET"), self._row(2024, "MET"), self._row(2025, "MET")])
        self.assertEqual((j["guidance_miss_3y"], j["promise_kept_record"]), (False, True))
        j = J([self._row(2023, "MISS"), self._row(2024, "MET"), self._row(2025, "MET")])
        self.assertEqual((j["guidance_miss_3y"], j["promise_kept_record"]), (False, None))
        j = J([self._row(2023, "MISS"), self._row(2024, "MISS"), self._row(2025, "MET")])
        self.assertEqual((j["guidance_miss_3y"], j["promise_kept_record"]), (True, False))
        j = J([self._row(2025, "MET")])
        self.assertIsNone(j["guidance_miss_3y"])

    def test_late_and_pending_rows_not_counted(self):
        j = G.judge([self._row(2024, "LATE_INITIAL"), self._row(2025, "MET"),
                     {"fy": 2026, "status": "PENDING", "actual": None}], "2026-10-07")
        self.assertEqual(j["n_evaluated"], 1)


class TestExhibitIndex(unittest.TestCase):
    def test_ex99_rows_only(self):
        html = ('<tr><td>1</td><td>8-K</td><td><a href="/ix?doc=/Archives/edgar/data/1/2/a.htm">a.htm</a></td>'
                '<td>8-K</td></tr><tr><td>2</td><td>PR</td><td><a href="/Archives/edgar/data/1/2/ex991.htm">'
                'ex991.htm</a></td><td>EX-99.1</td></tr><tr><td>3</td><td>Letter</td><td>'
                '<a href="/Archives/edgar/data/1/2/ex992.htm">x</a></td><td>EX-99.2</td></tr>')
        self.assertEqual(G.exhibit99_urls(html), ["https://www.sec.gov/Archives/edgar/data/1/2/ex991.htm",
                                                  "https://www.sec.gov/Archives/edgar/data/1/2/ex992.htm"])


class TestBoundaries(unittest.TestCase):
    def test_no_verdict_or_score_functions(self):
        src = open(os.path.join(os.path.dirname(G.__file__), "guidance_ledger.py"), encoding="utf-8").read()
        names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)}
        self.assertFalse({n for n in names if any(w in n for w in ("score", "verdict", "weight", "buy"))})

    def test_not_wired_into_valuation(self):
        root = os.path.dirname(G.__file__)
        for f in ("pipeline.py", "expectation_gap_engine.py", "portfolio_pipeline.py"):
            self.assertNotIn("guidance_ledger", open(os.path.join(root, f), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
