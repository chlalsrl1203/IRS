"""
SEC Document Index (P0-11, 2026-08-19) — 주장을 **인용 가능한 문서**에 묶는다.

# SOURCE:
https://github.com/dgunning/edgartools  (MIT)

# CAPABILITY:
20+ filing types / filing 접근 / typed filing abstraction

# IRS_TARGET:
engine/data/providers/sec_documents.py

# METHOD:
REIMPLEMENT (P0-03과 동일 근거 — 의존성 21개 vs IRS 0개)

# ⚠️ 범위를 의도적으로 좁혔다 — 본문 파싱을 하지 않는다

계획서의 P0-11은 "Financial Document Intelligence"지만, **10-K 본문 섹션 추출
(risk factors·MD&A)은 하지 않는다.** 근거:

1. **필요한 실증 사례가 없다.** IRS의 정성 조사는 지금까지 전부 WebSearch로
   했고, 본문 파싱이 없어서 막힌 분석이 하나도 없다. Simplicity First가
   겨냥하는 "나중에 필요할 것 같아서"에 정확히 해당한다.
2. **HTML/PDF 파싱은 의존성을 부른다.** lxml·beautifulsoup4가 필요하고, IRS는
   런타임 의존성이 0개다(P0-03에서 edgartools를 REIMPLEMENT로 돌린 것과 같은 벽).
3. **정작 지금 막혀 있는 것은 본문이 아니라 인용이다.** `thesis.build_evidence()`의
   `source`가 **자유 문자열**이라 §15가 요구하는 Document·Location·Verification이
   전혀 없다. 본문을 긁어와도 그걸 담을 계약이 없으면 또 자유 문자열이 된다.

그래서 이 모듈은 **문서 신원(identity)** 만 다룬다: 어떤 서식이 언제 제출됐고
그 원문이 어디 있는가. 그것만으로 `EvidenceCitation`(P0-12)이 성립한다.
본문 추출이 실제로 필요해지면 그때 구체적 요구사항을 갖고 배선한다.

# TEST:
tests/test_sec_documents.py
"""

from dataclasses import asdict, dataclass

from engine.data.providers.base import FinancialProvider
from engine.filing_dates import _http_json, ticker_to_cik

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{doc}"


@dataclass(frozen=True)
class FilingDocument:
    """
    공시 문서 하나의 **신원**. 본문을 담지 않는다 — 어디를 보라고 가리킬 뿐이다.

    `filing_date`(제출일)와 `report_date`(대상 기간 종료일)를 분리한다.
    `FinancialFact`의 `available_at` vs `period_end`와 같은 구분이며, 섞으면
    PIT가 무의미해진다.
    """

    entity: str
    cik: str
    form: str                 # "10-K" / "10-Q" / "8-K" / "20-F" ...
    filing_date: str          # 제출일
    report_date: str          # 대상 기간 종료일(없을 수 있다)
    accession_number: str
    primary_document: str
    url: str
    is_xbrl: bool
    description: str = ""

    def citation(self, location: str = "") -> str:
        """
        인용 문자열. `location`은 분석자가 적는다(예: "Item 7 MD&A", "F-12 주석 14").
        **자동 생성하지 않는다** — 본문을 파싱하지 않으므로 위치를 알 수 없고,
        모르는 것을 지어내면 그게 바로 조작된 인용이다.
        """
        base = f"{self.entity} {self.form} ({self.filing_date})"
        return f"{base}, {location}" if location else base


class SecDocumentIndex(FinancialProvider):
    """
    SEC submissions API -> `FilingDocument` 목록.

    `FinancialProvider`를 상속해 거버넌스·레이트리밋을 그대로 물려받는다.
    다만 이 클래스는 재무수치를 다루지 않으므로 `fetch_annual_financials()`는
    **명시적으로 거부**한다 — 억지로 빈 결과를 돌려주면 호출부가 "데이터가
    없다"로 오해한다.
    """

    source_key = "sec_edgar"

    def __init__(self, purpose=None, today=None, user_agent=None, fetch_json=None,
                 resolve_cik=None):
        super().__init__(purpose=purpose, today=today)
        self.user_agent = user_agent
        self._fetch_json = fetch_json or (lambda url: _http_json(url, self.user_agent))
        self._resolve_cik = resolve_cik or ticker_to_cik

    def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None):
        raise NotImplementedError(
            "SecDocumentIndex는 문서 신원만 다룬다. 재무수치는 "
            "SecCompanyFactsProvider를 쓸 것 — 빈 결과를 돌려주면 호출부가 "
            "'데이터가 없다'로 오해한다."
        )

    def fetch_filings(self, entity: str, forms=None, since: str = None,
                      limit: int = None) -> list:
        """
        `entity`의 공시 목록. **최근분(`filings.recent`)만 본다.**

        ⚠️ SEC는 오래된 공시를 별도 파일(`filings.files`)로 분리하며, 이 모듈은
        그걸 따라가지 않는다. 따라서 결과는 **완전한 이력이 아니다.** 필요한
        문서를 못 찾았을 때 "없다"로 단정하지 말 것 — `truncated` 표시를 함께
        돌려주는 `fetch_filing_index()`를 쓰면 그 사실이 드러난다.
        """
        return self.fetch_filing_index(entity, forms, since, limit)["documents"]

    def fetch_filing_index(self, entity: str, forms=None, since: str = None,
                           limit: int = None) -> dict:
        cik = self._resolve_cik(entity, self.user_agent)
        if not cik:
            return {"entity": entity, "cik": None, "documents": [],
                    "truncated": False,
                    "limitations": [f"[티커 미해결] '{entity}'를 SEC 티커 목록에서 "
                                    f"찾지 못했다."]}

        data = self._fetch_json(SEC_SUBMISSIONS_URL.format(cik=str(cik).zfill(10)))
        recent = (data.get("filings") or {}).get("recent") or {}
        older = (data.get("filings") or {}).get("files") or []

        want = set(forms) if forms else None
        cik_int = str(int(cik))
        out = []
        n = len(recent.get("accessionNumber", []))
        for i in range(n):
            form = recent["form"][i]
            if want and form not in want:
                continue
            filed = recent["filingDate"][i]
            if since and filed < since:
                continue
            acc = recent["accessionNumber"][i]
            doc = recent.get("primaryDocument", [""] * n)[i]
            out.append(FilingDocument(
                entity=entity, cik=cik, form=form, filing_date=filed,
                report_date=recent.get("reportDate", [""] * n)[i] or "",
                accession_number=acc, primary_document=doc,
                url=SEC_ARCHIVE_URL.format(cik_int=cik_int,
                                           accession_nodash=acc.replace("-", ""),
                                           doc=doc) if doc else "",
                is_xbrl=bool(recent.get("isXBRL", [0] * n)[i]),
                description=recent.get("primaryDocDescription", [""] * n)[i] or "",
            ))
        out.sort(key=lambda d: d.filing_date, reverse=True)
        if limit:
            out = out[:limit]

        limitations = []
        if older:
            limitations.append(
                f"[이력 불완전] SEC가 오래된 공시를 별도 파일 {len(older)}개로 "
                f"분리해 두었고 이 모듈은 따라가지 않는다"
                f"({', '.join(f.get('filingFrom','?') + '~' + f.get('filingTo','?') for f in older[:3])}). "
                f"여기 없다고 '공시가 없다'로 단정하지 말 것."
            )
        return {"entity": entity, "cik": cik, "documents": out,
                "truncated": bool(older), "limitations": limitations,
                "governance": self.governance}

    def find_filing_for_fiscal_year(self, entity: str, fiscal_year: int,
                                    forms=("10-K", "10-K/A", "20-F", "40-F")):
        """
        특정 회계연도의 연차보고서를 찾는다. **`report_date`로 매칭한다** —
        `filing_date`로 하면 이듬해 초에 제출된 보고서를 놓친다.

        못 찾으면 `None`을 돌려준다(추측하지 않는다).
        """
        idx = self.fetch_filing_index(entity, forms=forms)
        for d in idx["documents"]:
            if d.report_date[:4] == str(fiscal_year):
                return d
        return None


def documents_as_dicts(documents) -> list:
    return [asdict(d) for d in documents]
