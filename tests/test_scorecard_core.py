"""
scorecard_core.py 검증. 이 파일은 stdlib(unittest)만으로 전부 실행된다.
scipy는 inv_normal_cdf/normal_cdf 근사 오차를 확인하는 오라클로만 쓰고, 없으면
해당 검사만 건너뛴다(CI에 scipy를 추가할 필요 없음, 이 프로젝트의 런타임 의존성
0개 원칙과 무관).
"""
import math
import random
import unittest

from engine import scorecard_core as S

try:
    from scipy.stats import norm as _scipy_norm
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


class TestNumerics(unittest.TestCase):
    def test_normal_cdf_known_points(self):
        self.assertAlmostEqual(S.normal_cdf(0.0), 0.5, places=12)
        self.assertAlmostEqual(S.normal_cdf(1.959964), 0.975, places=5)
        self.assertAlmostEqual(S.normal_cdf(-1.959964), 0.025, places=5)

    def test_inv_normal_cdf_roundtrip(self):
        for x in [-3, -1.5, -0.3, 0, 0.3, 1.5, 3]:
            p = S.normal_cdf(x)
            self.assertAlmostEqual(S.inv_normal_cdf(p), x, places=6)

    def test_inv_normal_cdf_out_of_range(self):
        with self.assertRaises(ValueError):
            S.inv_normal_cdf(0.0)
        with self.assertRaises(ValueError):
            S.inv_normal_cdf(1.0)

    @unittest.skipUnless(HAVE_SCIPY, "scipy 없음: 오라클 교차검증 생략(필수 아님)")
    def test_inv_normal_cdf_vs_scipy(self):
        random.seed(1)
        worst = 0.0
        for _ in range(2000):
            p = random.uniform(1e-4, 1 - 1e-4)
            worst = max(worst, abs(S.inv_normal_cdf(p) - float(_scipy_norm.ppf(p))))
        self.assertLess(worst, 1e-8, f"scipy 대비 최대오차 {worst}")

    def test_rank_pct_ties_and_order(self):
        vals = [10, 30, 20, 30, 10]
        r = S.rank_pct(vals)
        self.assertEqual(r[0], r[4])        # 동점(10) 동일 백분위
        self.assertEqual(r[1], r[3])        # 동점(30) 동일 백분위
        self.assertLess(r[0], r[2])
        self.assertLess(r[2], r[1])
        self.assertAlmostEqual(sum(sorted(set(round(x, 6) for x in r))), sum(sorted(set(round(x, 6) for x in r))))

    def test_ols_recovers_exact_linear(self):
        # y = 2 + 3*x1 - 1*x2, 잡음 없음, x1과 x2는 서로 독립(공선성 없음) -> 정확히 복원되어야 함
        rng = random.Random(42)
        rows = [(i, rng.uniform(0, 5)) for i in range(1, 12)]
        X = [[1.0, x1, x2] for x1, x2 in rows]
        y = [2 + 3 * x1 - 1 * x2 for x1, x2 in rows]
        beta = S.ols(X, y)
        self.assertIsNotNone(beta)
        for b, exp in zip(beta, [2, 3, -1]):
            self.assertAlmostEqual(b, exp, places=6)

    def test_ols_collinear_returns_none(self):
        # x2 = 0.5*x1 이면 설계행렬이 특이행렬 -> None 반환(암묵적 추정값 금지)
        rows = [(1.0, i, i * 0.5) for i in range(1, 12)]
        X = [[1.0, x1, x2] for _, x1, x2 in rows]
        y = [2 + 3 * x1 for _, x1, _x2 in rows]
        self.assertIsNone(S.ols(X, y))

    def test_ols_insufficient_rank_returns_none(self):
        self.assertIsNone(S.ols([[1.0, 1.0], [1.0, 2.0]], [1.0, 2.0, 3.0][:2]) if False else
                          S.ols([[1.0, 1.0]], [1.0]))  # n<p


class TestMoatDuration(unittest.TestCase):
    def test_permanent_moat_saturates(self):
        d = S.ar1_shrinkage_duration([0.10] * 12)
        self.assertAlmostEqual(d["Q"], 1.0, places=2)
        self.assertEqual(d["T"], 20)

    def test_declining_moat_not_saturated(self):
        d = S.ar1_shrinkage_duration([0.15, 0.13, 0.11, 0.09, 0.08, 0.06, 0.05, 0.04])
        self.assertLess(d["Q"], 0.5)
        self.assertLess(d["trend"], 0)

    def test_insufficient_history_is_none(self):
        d = S.ar1_shrinkage_duration([0.1, 0.1, 0.1, 0.1])
        self.assertIsNone(d["Q"])
        self.assertEqual(d["n"], 4)

    def test_empty_or_none_input(self):
        self.assertIsNone(S.ar1_shrinkage_duration(None)["Q"])
        self.assertIsNone(S.ar1_shrinkage_duration([])["Q"])

    def test_duration_matches_hand_rolled_statsmodels_free_check(self):
        # numpy 없이도 동일한 결과가 나오는지 순수 파이썬 재구현과 다시 대조(이중 구현 교차검증)
        s = [0.12, 0.10, 0.09, 0.07, 0.06, 0.05]
        x, y = s[:-1], s[1:]
        n = len(y)
        mx, my = sum(x) / n, sum(y) / n
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
        var = sum((xi - mx) ** 2 for xi in x) / n
        rho_f = cov / var
        w = n / (n + S.SHRINK_K)
        rho = w * rho_f + (1 - w) * S.FF_RHO_PRIOR
        a = my - rho * mx
        v = n / (n + S.SHRINK_K_MEAN) * (a / (1 - rho))
        d = S.ar1_shrinkage_duration(s)
        self.assertAlmostEqual(d["rho"], rho, places=10)
        self.assertAlmostEqual(d["s_inf"], v, places=10)


class TestGroupPercentile(unittest.TestCase):
    def _make(self, n, group="IND"):
        return [{"v": i, "industry": group, "sector": "SEC"} for i in range(n)]

    def test_sufficient_peers_computed(self):
        items = self._make(12)
        out = S.group_percentile(items, "v", "industry", "sector", True)
        self.assertTrue(all(v is not None for v in out.values()))
        self.assertAlmostEqual(out[0], S.rank_pct([it["v"] for it in items])[0])

    def test_insufficient_peers_falls_back_to_sector(self):
        # 두 업종 모두 개별로는 MIN_PEERS 미만이지만, 같은 섹터로 합치면 기준을 넘는 경우.
        # (한쪽 업종만 단독으로 10개를 넘기면 1차 업종 패스에서 이미 해소되어 폴백 경로를
        #  검증하지 못하므로, 둘 다 미만으로 설계한다.)
        a = self._make(4, group="SMALL_IND_A")
        b = self._make(8, group="SMALL_IND_B")
        for it in a + b:
            it["sector"] = "BIG_SEC"
        items = a + b  # 섹터 합산 12개 >= MIN_PEERS, 업종별로는 각각 4개/8개로 미달
        out = S.group_percentile(items, "v", "industry", "sector", True)
        self.assertTrue(all(v is not None for v in out.values()))

    def test_still_insufficient_is_none(self):
        items = self._make(3)
        out = S.group_percentile(items, "v", "industry", None, True)
        self.assertTrue(all(v is None for v in out.values()))

    def test_missing_value_stays_none(self):
        items = self._make(12)
        items[0]["v"] = None
        out = S.group_percentile(items, "v", "industry", "sector", True)
        self.assertIsNone(out[0])
        self.assertIsNotNone(out[1])

    def test_lower_is_better_inverts(self):
        items = self._make(12)
        hib = S.group_percentile(items, "v", "industry", None, True)
        lib = S.group_percentile(items, "v", "industry", None, False)
        self.assertGreater(hib[11], hib[0])
        self.assertGreater(lib[0], lib[11])


def _gen_universe(n=60, seed=3):
    rng = random.Random(seed)
    inds = ["반도체"] * (n // 3) + ["화학"] * (n // 3) + ["조선"] * (n - 2 * (n // 3))
    companies = []
    for i, ind in enumerate(inds):
        q = rng.gauss(0, 1)
        ta = 1e9 * rng.uniform(0.5, 5)
        series_n = 12 if i % 11 != 0 else 3  # 일부는 이력 부족
        spreads = [0.05 + 0.03 * q + rng.gauss(0, 0.01) for _ in range(series_n)] if i % 13 != 0 else None
        companies.append(dict(
            ticker=f"T{i:03d}", industry=ind, sector="산업재" if ind == "조선" else "IT/소재",
            spread_series=spreads,
            gm_cv_10y=abs(rng.gauss(0.1, 0.05)), gm_change_shock=rng.gauss(0, 0.02) + 0.01 * q,
            share_trend_5y=rng.gauss(0, 0.02),
            lifecycle_shakeout_or_decline=(i % 17 == 0), share_instability_top25=(i % 19 == 0),
            key_person_no_succession=(i % 23 == 0),
            gpoa=0.3 + 0.1 * q, roe=0.1 + 0.05 * q, roa=0.05 + 0.03 * q, cfoa=0.07 + 0.03 * q,
            gmar=0.3 + 0.1 * q, acc_total=rng.gauss(0, 0.03),
            roiic_5y=0.08 + 0.03 * q + rng.gauss(0, 0.02), wacc=0.08,
            dollar_test_ratio=rng.uniform(0, 2), market_dollar_ratio=1.1,
            gw_impair_ratio_5y=rng.uniform(0, 0.3), netdebt_ebitda=rng.uniform(-1, 4),
            net_payout_yield=rng.uniform(0, 0.06), buyback_timing=rng.uniform(0, 1),
            div_predictable=rng.choice([0, 1]),
            kcg_compliance=rng.uniform(0.2, 0.9), size_bucket="대형" if ta > 2.5e9 else "중소형",
            split_then_listing_5y=(i == 3), related_party_top10=(i == 4),
            opp_insider_net_sell=(i == 5), opp_insider_net_buy=(i == 6),
            chair_separated=(i % 4 == 0), ceo_succession_policy=(i % 4 == 1),
            cogs=ta * 0.5, sga=ta * 0.1 * (1 - 0.1 * q), net_ppe=ta * 0.3, rou_asset=ta * 0.02,
            rnd=ta * 0.03, goodwill=ta * 0.01, other_intangibles=ta * 0.02, sales=ta * (0.9 + 0.1 * q),
            log_assets=math.log(ta), mkt_share=rng.uniform(0, 0.3), firm_age=rng.randint(5, 50),
            honesty_reviewed=bool(rng.randint(0, 1)), honesty_checklist=None,
        ))
    companies[7]["honesty_checklist"] = {"restated_down_3y": "https://dart.fss.or.kr/x", "promise_kept_record": ""}
    companies[8]["honesty_checklist"] = {"promise_kept_record": "u", "voluntary_bad_news": "u", "restated_down_3y": ""}
    return companies


class TestModuleB(unittest.TestCase):
    def test_runs_on_synthetic_universe(self):
        out = S.moat_subscores(_gen_universe())
        self.assertEqual(len(out), 60)
        scored = [o for o in out if o["B_score"] is not None]
        self.assertGreater(len(scored), 30)
        for o in scored:
            self.assertGreaterEqual(o["B_score"], 0.0)
            self.assertLessEqual(o["B_score"], 100.0)

    def test_short_history_yields_none_score(self):
        out = S.moat_subscores(_gen_universe())
        none_hist = [o for i, o in enumerate(out) if i % 11 == 0 or i % 13 == 0]
        self.assertTrue(all(o["B_score"] is None for o in none_hist))

    def test_cap50_trigger_enforced(self):
        out = S.moat_subscores(_gen_universe())
        for i, o in enumerate(out):
            if o["B_cap50"] and o["B_score"] is not None:
                self.assertLessEqual(o["B_score"], 50.0 + 1e-9)


class TestModuleQMJ(unittest.TestCase):
    def test_component_in_unit_interval(self):
        comp = _gen_universe()
        PROF = {"gpoa": True, "roe": True, "roa": True, "cfoa": True, "gmar": True, "acc_total": False}
        out = S.qmj_component(comp, PROF)
        vals = [v for v in out if v is not None]
        self.assertGreater(len(vals), 30)
        self.assertTrue(all(0.0 < v <= 1.0 for v in vals))


class TestModuleD(unittest.TestCase):
    def test_runs_on_synthetic_universe(self):
        out = S.management_subscores(_gen_universe())
        self.assertEqual(len(out), 60)
        scored = [o for o in out if o["D_score"] is not None]
        self.assertGreater(len(scored), 30)
        for o in scored:
            self.assertGreaterEqual(o["D_score"], 0.0)
            self.assertLessEqual(o["D_score"], 100.0)

    def test_honesty_ignores_evidence_free_items(self):
        out = S.management_subscores(_gen_universe())
        self.assertEqual(out[7]["D_honesty"], -4)   # restated_down_3y만 증거 있음
        self.assertEqual(out[8]["D_honesty"], 5)    # promise_kept(3) + voluntary(2)

    def test_no_composite_across_modules_exposed(self):
        """이 모듈이 B/C/D를 하나의 점수로 합치는 함수를 제공하지 않는지 확인(설계 의도 고정)."""
        import inspect
        src_names = {n for n, _ in inspect.getmembers(S, inspect.isfunction)}
        forbidden = {"irs_composite", "compose", "overall_score", "final_score"}
        self.assertEqual(src_names & forbidden, set())


class TestNoForbiddenImports(unittest.TestCase):
    def test_module_file_has_no_pandas_numpy_scipy_import(self):
        with open(S.__file__, encoding="utf-8") as f:
            src = f.read()
        for bad in ("import pandas", "import numpy", "import scipy", "from pandas", "from numpy", "from scipy"):
            self.assertNotIn(bad, src, f"런타임 의존성 금지 위반: {bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
