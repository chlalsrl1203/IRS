"""
v3.96 — 외국 발행사(20-F) 경로와 국내 표지·자본배분 기계 규칙.

전부 2026-10-07 수집 중 실제 문서에서 마주친 형식이다(DLO·MNDY·PDD·SE 20-F, ADBE·NXT·TW·HLNE 10-K).
"""

import unittest

from engine import sec_events as E


class TestIcfr20F(unittest.TestCase):
    def test_dlo_maintained_effective_form(self):
        body = ("Item 15. Controls and Procedures. (b) Management’s annual report on internal control over "
                "financial reporting. Based on our assessment and those criteria, management concluded that the "
                "Company maintained effective internal control over financial reporting as of December 31, 2025 . "
                "Item 16. [Reserved]")
        r = E.icfr_from_20f(body)
        self.assertEqual(r["answer"], "effective")
        self.assertEqual(r["scope"], "Item 15")

    def test_did_not_maintain_is_ineffective(self):
        body = ("Item 15. Controls and Procedures. management concluded that the Company did not maintain effective "
                "internal control over financial reporting as of December 31, 2025. Item 16. x")
        self.assertEqual(E.icfr_from_20f(body)["answer"], "ineffective")

    def test_cross_reference_layout_falls_back_to_whole_document(self):
        # MNDY 20-F는 'Item 15' 머리 없이 교차참조표 형식이다.
        body = ("Part 4 ... our management concluded that, as of December 31, 2025, our internal control over "
                "financial reporting was effective. Attestation Report ...")
        r = E.icfr_from_20f(body)
        self.assertEqual(r["answer"], "effective")
        self.assertIn("문서 전체", r["scope"])


class TestItem16F(unittest.TestCase):
    def test_not_applicable_after_toc_line(self):
        # 목차 줄(짧은 절)이 아니라 본문(가장 긴 절)을 읽는다.
        body = ("Item 16F. Change in Registrant’s Certifying Accountant 138 Item 16G. Corporate Governance 138 "
                "... Item 16F. Change in Registrant’s Certifying Accountant. Not applicable. Item 16G. Corporate "
                "Governance. Foreign Private Issuer Status Nasdaq listing rules include certain accommodations")
        self.assertEqual(E.auditor_change_from_16f(body)["answer"], 0)

    def test_split_letters_and_cross_reference_na(self):
        self.assertEqual(E.auditor_change_from_16f(
            "I tem 16F. Change in Registrant’s Certifying Accountant. Not applicable. I tem 16G. Corporate")
            ["answer"], 0)
        self.assertEqual(E.auditor_change_from_16f(
            "16F Change in Registrant’s Certifying Accountant N/A 16G Corporate Governance 167-168")["answer"], 0)

    def test_pdd_dismissal_counts_one_event(self):
        body = ("Item 16F. Change in Registrant’s Certifying Accountant On July 23, 2025, with the approval of the "
                "audit committee of our board of directors, we appointed Ernst & Young, located in Hong Kong, as our "
                "independent registered public accounting firm. As a result of the appointment, our previous "
                "independent registered public accounting firm, Ernst & Young Hua Ming LLP, was dismissed as our "
                "independent registered public accounting firm on the same date. The reports of Ernst & Young Hua "
                "Ming LLP did not contain an adverse opinion. Item 16G. Corporate Governance")
        r = E.auditor_change_from_16f(body)
        self.assertEqual(r["answer"], 1)
        self.assertIn("was dismissed", r["excerpt"])


class TestLitigation20F(unittest.TestCase):
    def test_se_nor_aware_form_is_materiality_qualified(self):
        body = ("Legal and Administrative Proceedings We are not a party to, nor are we aware of, any legal proceeding, "
                "investigation or claim which, in the opinion of our management, is likely to have any material "
                "adverse effect on our business, financial condition or results of operations. Other text.")
        r = E.litigation_from_20f(body)
        self.assertEqual(r["answer"], "immaterial")

    def test_describing_proceedings_is_not_answered(self):
        body = ("Legal Proceedings We are involved in claims, proceedings, and litigation on an ongoing basis. The "
                "outcomes of the legal proceedings to which we are a party are inherently unpredictable.")
        self.assertIsNone(E.litigation_from_20f(body)["answer"])


class TestNoDividend(unittest.TestCase):
    def test_forms(self):
        self.assertIsNotNone(E.no_dividend_statement(
            "Dividend Policy We have never declared or paid any dividends on our ordinary shares."))
        self.assertIsNotNone(E.no_dividend_statement(
            "Dividends We do not anticipate paying any cash dividends in the foreseeable future."))
        self.assertIsNone(E.no_dividend_statement("We paid quarterly cash dividends of $0.25 per share."))


class TestCover(unittest.TestCase):
    ANCHOR = ("Indicate by check mark whether the registrant is a shell company (as defined in Rule 12b-2 of the "
              "Act). Yes ☐ No ☒ ")

    def test_single_class_adbe_decimal_par_value(self):
        body = self.ANCHOR + ("The aggregate market value of the registrant’s common stock held by non-affiliates "
                              "was $200 billion. As of January 9, 2026, 410.5 million shares of the registrant’s "
                              "common stock, $0.0001 par value per share, were issued and outstanding. "
                              "DOCUMENTS INCORPORATED BY REFERENCE")
        self.assertIs(E.single_class_from_cover(body)["answer"], False)

    def test_tw_class_table_not_mistaken_for_single_class(self):
        body = self.ANCHOR + ("Class of Stock Shares Outstanding as of January 29, 2026 Class A Common Stock, par "
                              "value $0.00001 per share 115,657,833 Class B Common Stock, par value $0.00001 per share "
                              "96,933,192 Class C Common Stock 18,000,000 Class D Common Stock 5,056,868")
        self.assertIsNone(E.single_class_from_cover(body)["answer"])

    def test_nxt_zero_class_b_is_single_class(self):
        body = self.ANCHOR + ("As of May 11, 2026, there were 150,274,472 shares of the registrant’s Class A common "
                              "stock outstanding and no shares of the registrant’s Class B common stock outstanding.")
        self.assertIs(E.single_class_from_cover(body)["answer"], False)


class TestCapitalRules(unittest.TestCase):
    def test_debt_balance_rule(self):
        buy = {2024: 0.0, 2025: 300.0}
        self.assertIs(E.debt_funded_buyback_balance(buy, {2024: 1000.0, 2025: 900.0}, 2024)["answer"], False)
        self.assertIs(E.debt_funded_buyback_balance(buy, {2024: 1000.0, 2025: 1200.0}, 2024)["answer"], True)
        self.assertIsNone(E.debt_funded_buyback_balance(buy, {2025: 1200.0}, 2024)["answer"])

    def test_ma_intensity(self):
        ocf = {y: 100.0 for y in range(2021, 2026)}
        self.assertEqual(E.ma_intensity({y: 5.0 for y in range(2021, 2026)}, ocf, 2025)["answer"], "no_material_ma")
        r = E.ma_intensity({2021: 0.0, 2022: 0.0, 2023: 300.0, 2024: 0.0, 2025: 0.0}, ocf, 2025)
        self.assertIsNone(r["answer"])
        self.assertAlmostEqual(r["ratio"], 0.6)
        self.assertIsNone(E.ma_intensity({}, ocf, 2025)["answer"])     # 태그 부재는 '인수 없음'이 아니다

    def test_fpi_listing_flags(self):
        listing = {"covers_window": True, "rows": [
            {"form": "NT 20-F", "filingDate": "2025-05-01"}, {"form": "20-F/A", "filingDate": "2022-01-01"},
            {"form": "20-F", "filingDate": "2026-04-01"}]}
        r = E.fpi_listing_flags(listing, "2026-10-07")
        self.assertEqual((r["n_nt"], r["n_20f_amendments"]), (1, 0))


if __name__ == "__main__":
    unittest.main()
