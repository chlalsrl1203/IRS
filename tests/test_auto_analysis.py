import glob, json, os, re, unittest

from engine import auto_analysis as A
from engine.auto_analysis import AutoAnalysisRefused, auto_analyze, check_gates


def _series(rev_growth=0.08, n=11, op=True, fcf_last=100.0):
    rev = {2015 + i: 1000 * (1 + rev_growth) ** i for i in range(n)}
    s = {"revenue_by_year": rev,
         "operating_cashflow_by_year": {y: v * 0.2 for y, v in rev.items()},
         "capex_by_year": {y: v * 0.05 for y, v in rev.items()}}
    s["operating_income_by_year"] = {y: v * 0.15 for y, v in rev.items()} if op else {}
    return s


class GateTests(unittest.TestCase):
    def test_clean_series_passes(self):
        years, fcf, override, _ = check_gates(_series())
        self.assertIsNone(override)

    def test_no_operating_income_refused_as_framework_mismatch(self):
        with self.assertRaises(AutoAnalysisRefused) as c:
            check_gates(_series(op=False))
        self.assertEqual(c.exception.category, "FRAMEWORK_MISMATCH")

    def test_step_up_inside_3y_window_refused(self):
        s = _series()
        y = max(s["revenue_by_year"]) - 1
        s["revenue_by_year"][y] *= 1.6
        s["revenue_by_year"][y + 1] = s["revenue_by_year"][y] * 1.05
        with self.assertRaises(AutoAnalysisRefused):
            check_gates(s)

    def test_covid_style_base_year_gets_override(self):
        s = _series()
        base = sorted(s["revenue_by_year"])[-6]
        s["revenue_by_year"][base] *= 0.8
        _, _, override, _ = check_gates(s)
        self.assertEqual(override[0], base - 1)

    def test_negative_fcf_refused(self):
        s = _series()
        last = max(s["revenue_by_year"])
        s["operating_cashflow_by_year"][last] = 0.0
        with self.assertRaises(AutoAnalysisRefused):
            check_gates(s)

    def test_too_few_years_refused(self):
        with self.assertRaises(AutoAnalysisRefused):
            check_gates(_series(n=4))


class PipelineTests(unittest.TestCase):
    def test_result_is_marked_unofficial_with_both_models_recorded(self):
        r = auto_analyze("TST", "Test", _series(), 4_000.0, "2026-10-10")
        a = r["auto_analysis"]
        self.assertFalse(a["official"])
        self.assertFalse(a["qualitative_research"])
        self.assertIn(a["model_rule"]["chosen"], ("single_stage", "two_stage"))
        self.assertTrue(r["meta"]["engine_version"].startswith("v"))
        self.assertIn("AUTO", r["inputs"]["model_choice_reason"])

    def test_model_rule_follows_preregistered_margin(self):
        r = auto_analyze("TST", "Test", _series(), 4_000.0, "2026-10-10")
        m = r["auto_analysis"]["model_rule"]
        expect = "two_stage" if m["rg"] - m["g_terminal"] >= A.TWO_STAGE_MARGIN else "single_stage"
        self.assertEqual(m["chosen"], expect)

    def test_thresholds_are_the_preregistered_values(self):
        self.assertEqual((A.STEP_UP_REFUSE, A.BASE_DROP, A.TWO_STAGE_MARGIN), (0.30, -0.08, 0.05))


class IsolationTests(unittest.TestCase):
    """자동 결과가 공식 경로로 새어 들어가지 않는다."""

    def test_official_paths_never_read_ledger_auto(self):
        for p in glob.glob("engine/*.py") + glob.glob("scripts/*.py"):
            if os.path.basename(p) in ("auto_analysis.py", "auto_analysis_ci.py", "auto_vs_official_2026_10_10.py"):
                continue
            self.assertNotIn("ledger_auto", open(p, encoding="utf-8").read(), p)

    def test_auto_ledgers_live_outside_official_dir_and_are_marked(self):
        for p in glob.glob("ledger_auto/*.json"):
            d = json.load(open(p, encoding="utf-8"))
            self.assertFalse(d["auto_analysis"]["official"], p)
            self.assertFalse(os.path.exists(os.path.join("ledger", os.path.basename(p))), p)

    def test_no_llm_or_network_dependency_in_engine_module(self):
        src = open("engine/auto_analysis.py", encoding="utf-8").read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+(anthropic|openai|requests)", src, re.M))


if __name__ == "__main__":
    unittest.main()
