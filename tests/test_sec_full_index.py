"""
sec_full_index.py 테스트 (2026-08-30).

고정하는 것:
  ① 고정폭 파싱이 공백 많은 회사명에서도 CIK를 정확히 뽑는다
  ② ANNUAL_FORMS를 **재사용**한다(집합을 복제하면 유니버스와 스크리너가 어긋난다)
  ③ as_of 이후 제출분을 배제한다(미래정보가 유니버스 정의에 들어오면 안 된다)
  ④ 분기 역산이 연도 경계를 넘어간다
  ⑤ 한 분기 조회 실패가 전체를 막지 않는다
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.data.providers import sec_full_index as F  # noqa: E402
from engine.filing_dates import ANNUAL_FORMS  # noqa: E402

# company.idx 고정폭: 회사명 62칸 + 서식 12칸 + CIK + 날짜 + 경로
HEADER = (
    "Company Name                                                  Form Type   "
    "CIK         Date Filed  File Name\n"
    "-" * 140 + "\n"
)


def _row(name, form, cik, filed):
    return f"{name:<62}{form:<12}{cik:<12}{filed}  edgar/data/{cik}/x.txt"


def test_parses_cik_from_fixed_width_even_with_spaces_in_name():
    text = HEADER + "\n".join([
        _row("ALPHABET INC CLASS C CAPITAL STOCK", "10-K", "1652044", "2018-02-06"),
        _row("A & B CO OF DELAWARE, THE", "10-K", "9999999", "2018-03-01"),
    ])
    out = F.parse_company_idx(text)
    assert out["0001652044"][0] == "ALPHABET INC CLASS C CAPITAL STOCK"
    assert "0009999999" in out, "회사명에 공백·쉼표가 있어도 CIK를 놓치면 안 된다"


def test_only_annual_forms_are_kept():
    text = HEADER + "\n".join([
        _row("ANNUAL CO", "10-K", "111", "2018-03-01"),
        _row("QUARTERLY CO", "10-Q", "222", "2018-03-01"),
        _row("CURRENT CO", "8-K", "333", "2018-03-01"),
        _row("FOREIGN CO", "20-F", "444", "2018-03-01"),
    ])
    out = F.parse_company_idx(text)
    assert set(out) == {"0000000111", "0000000444"}


def test_reuses_annual_forms_constant_not_a_copy():
    """
    서식 집합을 복제하면 유니버스 정의와 스크리너가 읽는 데이터가 어긋난다
    (sec_daily_index와 동일한 이유). 기본 인자가 그 상수 자체여야 한다.
    """
    import inspect
    assert inspect.signature(F.parse_company_idx).parameters["forms"].default \
        is ANNUAL_FORMS


def test_10ka_amendment_is_included():
    text = HEADER + _row("RESTATED CO", "10-K/A", "555", "2018-05-01")
    assert "0000000555" in F.parse_company_idx(text)


def test_keeps_latest_filing_per_cik():
    text = HEADER + "\n".join([
        _row("SAME CO", "10-K", "777", "2017-03-01"),
        _row("SAME CO", "10-K", "777", "2018-03-01"),
    ])
    assert F.parse_company_idx(text)["0000000777"][1] == "2018-03-01"


# ── ③ 미래정보 배제 ──────────────────────────────────────────────────────
def test_universe_excludes_filings_after_as_of():
    text = HEADER + "\n".join([
        _row("BEFORE CO", "10-K", "111", "2018-05-01"),
        _row("AFTER CO", "10-K", "222", "2018-08-15"),   # as_of 이후
    ])
    uni = F.universe_at("2018-06-30", fetch_text=lambda u: text, quarters=1)
    assert "0000000111" in uni
    assert "0000000222" not in uni, "as_of 이후 제출분이 유니버스에 들어왔다"


def test_universe_includes_company_that_later_delisted():
    """생존편향 해소의 핵심 성질 - 오늘 없어진 회사도 그 시점 유니버스에 있다."""
    text = HEADER + _row("AKORN INC", "10-K", "3116", "2018-02-28")
    uni = F.universe_at("2018-06-30", fetch_text=lambda u: text, quarters=1)
    assert uni["0000003116"]["name"] == "AKORN INC"


# ── ④ 분기 역산 ──────────────────────────────────────────────────────────
def test_quarters_back_crosses_year_boundary():
    assert F._quarters_back("2018-06-30", 4) == [
        (2017, 3), (2017, 4), (2018, 1), (2018, 2)]


def test_quarters_back_from_q1():
    assert F._quarters_back("2020-02-15", 2) == [(2019, 4), (2020, 1)]


# ── ⑤ 부분 실패 내성 ─────────────────────────────────────────────────────
def test_one_failing_quarter_does_not_abort_the_rest():
    good = HEADER + _row("GOOD CO", "10-K", "111", "2018-05-01")

    def flaky(url):
        if "QTR1" in url:
            raise RuntimeError("SEC 조회 실패")
        return good

    uni = F.universe_at("2018-06-30", fetch_text=flaky, quarters=4)
    assert "0000000111" in uni


# ── T0 이전 폐지 기업 배제 (2026-08-30 파일럿에서 실제로 잡힌 결함) ────────
def test_universe_excludes_companies_already_delisted_at_t0():
    """
    WESTMORELAND COAL(폐지 2018-04-24)·MICROSEMI(2018-05-29)이 T0=2018-06-30
    유니버스에 들어왔던 실제 사고의 회귀 테스트. 직전 12개월에 10-K를 냈어도
    T0 시점에 이미 폐지됐으면 **살 수 없는 종목**이라 유니버스가 아니다.
    """
    text = HEADER + "\n".join([
        _row("WESTMORELAND COAL Co", "10-K", "106455", "2018-03-01"),
        _row("ALIVE CO", "10-K", "111", "2018-03-01"),
    ])
    uni = F.universe_at("2018-06-30", fetch_text=lambda u: text, quarters=1,
                        delisted_before={"0000106455"})
    assert "0000106455" not in uni, "T0 이전 폐지 기업이 유니버스에 남았다"
    assert "0000000111" in uni


def test_delisted_before_defaults_to_no_exclusion():
    """기본값은 기존 동작 유지 - 폐지 정보가 없다고 조용히 다르게 굴면 안 된다."""
    text = HEADER + _row("ANY CO", "10-K", "111", "2018-03-01")
    assert "0000000111" in F.universe_at(
        "2018-06-30", fetch_text=lambda u: text, quarters=1)


def test_delisted_before_takes_ciks_not_tickers():
    """
    폐지 정보 출처(LISTING_STATUS)는 CIK를 주지 않는다 - 매핑 책임을 호출부에
    두어 이 모듈이 특정 데이터 출처에 의존하지 않게 한다.
    """
    text = HEADER + _row("ANY CO", "10-K", "111", "2018-03-01")
    uni = F.universe_at("2018-06-30", fetch_text=lambda u: text, quarters=1,
                        delisted_before={"ANYCO"})   # 티커를 넣으면 안 걸린다
    assert "0000000111" in uni
