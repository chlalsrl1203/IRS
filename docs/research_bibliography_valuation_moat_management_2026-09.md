# IRS(투자리서치V1) 재정립용 기초 자료 지도: 내재가치, 사업 본질, 펀더멘털, 해자, 경영자 자질 (주석 달린 참고문헌, 2026년 9월 기준)

> **이 문서의 성격**: 외부에서 조사된 1차 문헌·학술 참고문헌 목록이다. 저장만
> 목적으로 커밋됐고 아직 IRS 코드·판정 로직에는 어떤 영향도 주지 않는다.
> 향후 growth_quality/accounting_quality 배선 근거 검토, 해자(CAP) 진단축
> 신설, 한국 상법 개정 반영 여부 등을 논의할 때 참조할 것 — CLAUDE.md의
> Simplicity First·exit_rule 원칙(사전등록 실험 없이 이 문헌만으로 곧바로
> engine/에 새 축을 배선하지 않는다)이 그대로 적용된다.

IRS 확장에 가장 먼저 쓸 1차 자료 축은 다섯 가지로 정리된다: 버크셔 서한과 Owner's Manual, 린치의 『One Up on Wall Street』, Mauboussin & Rappaport의 『Expectations Investing』(2021 개정판)과 무료 튜토리얼, Morningstar의 공개 방법론 문서, 그리고 2025~2026년 한국 상법 3차 개정 자료다. 이 가운데 Expectation Gap 엔진과 바로 연결되는 것은 Expectations Investing과 Morningstar의 해자별 초과수익 소멸(fade) 기간 가정, 그리고 Mauboussin의 Competitive Advantage Period 보고서다.

## TL;DR

- **1차 원문과 공개 방법론만으로 뼈대를 세울 수 있다.** 버크셔 서한(1965~2025, 2026년 2월 28일 발표된 Greg Abel의 첫 CEO 서한 포함), expectationsinvesting.com의 무료 reverse DCF(PIE) 스프레드시트, Morningstar Equity Research Methodology(2012, 2020, 2022, 2023년판)와 Capital Allocation Rating(2020년 10월) 문서는 모두 무료로 받을 수 있다. 여기에 정의, 공식, 등급 기준이 원문 그대로 들어 있다.
- **한국 특화 제도 환경은 2025~2026년에 크게 바뀌었다.** 상법 1차 개정은 2025년 7월 22일 공포, 시행되어 이사의 충실의무 대상에 주주를 넣었다. 2차 개정은 2025년 9월 9일 공포되어 자산 2조원 이상 상장사에 집중투표를 의무화했다. 3차 개정은 2026년 3월 6일 공포, 시행되어 자사주를 원칙적으로 1년 안에 소각하도록 했다. 코리아 밸류업 지수는 2026년 6월 정기변경부터 기업가치 제고 계획을 공시한 기업만으로 구성된다. 한국 지배구조 체크리스트는 이 네 가지 변화를 기준으로 다시 짜야 한다.
- **반론 자료도 1급 입력이다.** value premium 약화 논쟁(Fama-French 2021, Lev-Srivastava 2019, Arnott 외 2021), 장기 수익이 극소수 종목에 쏠린다는 Bessembinder(2018), Good to Great의 후광효과 비판(Rosenzweig), LLM 재무분석 논문(Kim/Muhn/Nikolaev)이 arXiv에서 저자에 의해 철회된 사실(2025년 2월 v3)은 방법론과 AI 보조 범위를 정할 때 반드시 함께 봐야 한다.

## 읽는 법 (필드 정의)

- **Tier**: T1(시스템 구축 필수), T2(권장), T3(참고)
- **태그**: [내재가치] [본질] [펀더멘털] [해자] [경영자] [한국특화] [데이터] [프로세스]
- **EG**: Expectation Gap 엔진과 직결되는 자료
- **정량**: 체크리스트, 공식, 스코어가 있으면 "有", 없으면 "無"
- **신뢰도**: 1차 원문 / 동료심사 논문 / 실무 리서치 / 2차 해설 / 커뮤니티
- **서지 검증**: 이번 조사에서 웹으로 직접 확인한 항목에는 (확인)을 붙였다. 학계의 표준 인용으로 널리 쓰이지만 이번 조사에서 DOI를 개별 확인하지 못한 항목은 [DOI 미확인]으로 표시했다. 확인하지 못한 수치, 서지, 날짜는 [Data Missing]으로 적었다.

## Key Findings (사실 요약)

1. **버크셔 승계 이후 1차 원문의 연속성.** Greg Abel의 첫 연례 서한(2026년 2월 28일, WOWT 같은 날 보도 기준 20쪽)은 자사주 매입 기준을 "trade below our estimate of intrinsic value, conservatively determined"로 적었다. 배당 기준은 "more than one dollar of market value ... by each dollar of retained earnings" 로, 버핏의 유보이익 1달러 테스트 문구를 그대로 이어받았다(CNBC 2026년 3월 1일 보도). 현금과 국채는 3,733억 달러였고(Fortune), 주총은 2026년 5월 2일에 열렸다. CNBC 보도에 따르면 주총 Q&A는 두 세션으로, 오전은 Abel과 Ajit Jain, 오후는 Abel, BNSF의 Katie Farmer, Adam Johnson이 맡았고, 같은 기사는 자사주 매입이 2024년 5월 이후 없었다("no buybacks during the fourth quarter, extending a streak that goes back to May 2024")고 전했다. 버핏은 이사회 의장으로 남았다.
2. **Expectations Investing 2021 개정판**(Columbia Business School Publishing, ISBN 9780231203043, 초판 2001 HBS Press)은 주가에서 출발해 가격에 내재된 기대(PIE)를 읽고 기대 수정 가능성을 평가하는 "expectations infrastructure"를 제시한다(확인). 공식 사이트에는 무료 튜토리얼 10개(현재가치, 가치동인, PIE 분석, M&A, 실물옵션)와 스프레드시트, 사이트 전용 보너스 3개 장이 있다(확인).
3. **Morningstar 방법론은 해자를 DCF 입력값으로 쓴다.** 해자는 "ROIC가 WACC를 상회하는 초과수익을 장기간 유지하게 하는 구조적 특징"으로 정의된다. narrow는 10년 이상 초과수익이 "more likely than not", wide는 10년에 대해 "very high confidence"이고 20년까지도 가능성이 더 높은 경우다(2023년판, 확인). Stage II(RONIC이 WACC로 수렴하는 기간)는 2012년판에서 "0년(무해자)~25년(wide)"이었고 2020년판에서는 "1년~10~15년 이상"으로 표기가 바뀌었다(확인).
4. **Mauboussin의 Measuring the Moat**는 2002년 초판, 2016년 개정, Counterpoint Global 최신판(Mauboussin & Callahan)이 있다. 최신판은 Consilient Observer 2024년 10월 15일 발행이며(investingmotherlode.com 인용), Morgan Stanley PDF 본문은 "Of more than 1,600 companies evaluated in 2024, about 17 percent were deemed to have a wide moat"라고 적었다. 해자를 측정하는 체계적 틀(산업 분석, 기업 분석, 기업 간 상호작용)을 제시한다(확인).
5. **한국 코리아 디스카운트 실증.** 자본시장연구원 이슈보고서 23-05 「코리아 디스카운트 원인 분석」(김준석, 강소현, 2023년 2월 16일)은 45개국 상장사를 비교해 헬스케어를 뺀 전 업종에서 지속적인 할인이 있다고 보고했다. 가장 유력한 원인으로 낮은 주주환원과 낮은 수익성, 성장성을 꼽았고, 지배구조, 회계 불투명성, 기관 보유 비중의 효과는 상대적으로 작다고 봤다.
6. **한국 가치투자 1세대의 현재 소속(2026년 기준 검증).** 이채원은 라이프자산운용 이사회 의장이다(공동대표 강대권, 남두우). 허남권은 2024년 3월 신영자산운용 대표를 사임하고 고문으로 물러났다(후임 엄준흠). 강방천은 2022년 7월 에셋플러스 경영일선에서 물러났고 2023년 1월 금융위원회에서 직무정지 6개월 징계를 받았다. 2025년 4월에는 "전 회장" 자격으로 고객 서신을 냈다. VIP자산운용(최준철, 김민국 공동대표)은 2003년 설립, 2018년 운용사 전환이며, 운용자산은 11조 3,335억원(2026년 5월 31일 기준, 회사 홈페이지)이다.

---

## Details: 주제축별 주석 달린 참고문헌

### A. 내재가치 / 밸류에이션 / 기대(Expectations)

**A-1. 1차 원문 (버크셔, 그레이엄)**

| 자료 | 서지 | 한국어판 | 접근성 | 사실 요약 | 태그 / 정량 / 신뢰도 / Tier |
|---|---|---|---|---|---|
| Berkshire Hathaway Owner's Manual | Buffett, 1996년 작성, 이후 개정. 연차보고서에 수록 | 이건 편역 서한집 계열에 일부 수록 [Data Missing: 수록 여부] | 무료(berkshirehathaway.com) | 내재가치를 사업의 잔여 수명 동안 인출 가능한 현금의 할인가치로 정의. 장부가치와의 차이, 유보이익 테스트 서술 | [내재가치][경영자] / 無 / 1차 원문 / T1 / EG |
| 1983 서한 부록 "Goodwill and its Amortization" | Buffett, 1983 연례 서한 | 동상 | 무료 | 경제적 영업권과 회계상 영업권을 구분. See's Candies 사례 | [내재가치][해자] / 無 / 1차 / T1 |
| 1986 서한 부록(owner earnings) | Buffett, 1986 연례 서한 | 동상 | 무료 | owner earnings = 보고이익 + 감가상각 등 비현금비용 - 경쟁력 유지에 필요한 평균 자본적지출(± 운전자본). Scott Fetzer 인수 회계를 예로 설명 | [내재가치][펀더멘털] / 有(공식) / 1차 / T1 / EG |
| look-through earnings | Buffett, 1990년대 초 서한(1990, 1991 등) [Data Missing: 최초 도입 연도 정확 확인] | 동상 | 무료 | 피투자회사 유보이익 중 버크셔 지분 몫을 합산하는 이익 개념 | [내재가치] / 有 / 1차 / T2 |
| 유보이익 1달러 테스트 | Buffett, 1983~1984 서한 및 Owner's Manual. Abel 2026 서한에서 재천명(확인) | 동상 | 무료 | 유보한 1달러가 1달러 이상의 시장가치를 만드는지로 유보의 정당성을 판단 | [경영자][내재가치] / 有(테스트) / 1차 / T1 |
| "How Inflation Swindles the Equity Investor" | Buffett, Fortune, 1977년 5월 | [Data Missing] | Fortune 아카이브 무료 공개본 존재 [Data Missing: URL] | 주식의 자기자본이익률이 약 12% 부근에 고정되는 "equity coupon" 논리와 인플레이션 영향 | [내재가치][펀더멘털] / 無 / 1차 / T2 |
| "The Superinvestors of Graham-and-Doddsville" | Buffett, Hermes(Columbia Business School), 1984 가을 | 『현명한 투자자』 일부 판 부록 [Data Missing: 판차] | 무료 PDF 다수 | 가치투자자 집단의 성과는 운이 아니라는 논증 | [프로세스] / 無 / 1차 / T2 |
| Greg Abel 첫 연례 서한 | Abel, 2025 Annual Report, 2026년 2월 28일 발표(확인) | 미번역 | 무료 | 문화 유지, 요새형 재무구조, 내재가치 이하에서만 자사주 매입, 배당 불가 원칙 유지. 현금 3,733억 달러 | [경영자][내재가치] / 無 / 1차 / T1 |
| Security Analysis | Graham & Dodd, 1934 초판. 6판 2008(McGraw-Hill, Klarman 서문) | [Data Missing] | 유료 | 정상이익력, 자산가치, 안전마진의 원형 | [내재가치][펀더멘털] / 有(부분) / 1차 / T2 |
| The Intelligent Investor | Graham, 4판 1973. Zweig 해설판 2003(HarperBusiness) | 『현명한 투자자』(이건 역, 4판 번역 확인) [Data Missing: 출판사, 연도] | 유료 | 방어적 투자자 기준 7가지, 20장 안전마진 | [내재가치][펀더멘털] / 有(체크리스트) / 1차 / T1 |

**A-2. 도서 (밸류에이션 체계)**

| 자료 | 서지 | 한국어판 | 사실 요약 | 태그 / 정량 / 신뢰도 / Tier |
|---|---|---|---|---|
| **Expectations Investing (Revised and Updated)** | Mauboussin & Rappaport, 2021, Columbia Business School Publishing, ISBN 9780231203043(확인) | 초판 번역 여부 [Data Missing] | 주가에서 출발해 PIE를 추출하고 가치 트리거(매출, 비용, 투자)에서 가치동인으로 이어지는 기대 수정을 분석. 실물옵션, M&A, 자사주 장 포함. 2021판은 무형자산 확대와 계속가치 추정 부록을 갱신(확인) | [내재가치] **EG 최우선** / 有(reverse DCF, PIE) / 1차(저자 원전) / T1 |
| expectationsinvesting.com 튜토리얼 | 공식 사이트(확인) | 없음 | 무료 튜토리얼 10개와 스프레드시트(PV, 가치동인, PIE, M&A, 실물옵션), 보너스 3개 장 | [내재가치][데이터] **EG** / 有 / 1차 / T1 |
| Expectations Investing 서평 및 인터뷰 | CFA Institute Enterprising Investor 서평(2022, 확인). Motley Fool Q&A(2022년 1월 19일, 확인) | 없음 | 서평은 8장 실물옵션과 Shopify 사례를 스타트업 가치평가 자료로 강조. Q&A는 저자 추가 해설 | [내재가치] EG / 無 / 2차 해설 / T2 |
| Value Investing: From Graham to Buffett and Beyond, 2판 | Greenwald, Kahn, Bellissimo, Cooper, Santos, 2020(Wiley) | [Data Missing] | 자산가치, 이익력가치(EPV), 프랜차이즈(성장) 가치의 3단계 평가 | [내재가치][해자] / 有 / 2차(학술 실무) / T1 / EG(EPV 대비 시장가 비교) |
| Investment Valuation, 3판 | Damodaran, 2012(Wiley) | [Data Missing] | DCF, 상대가치, 옵션가치 전 영역 교재 | [내재가치] / 有 / 2차 교재 / T2 |
| Narrative and Numbers | Damodaran, 2017(Columbia Business School Publishing) | [Data Missing] | 스토리를 가치동인 수치로 옮기는 절차 | [내재가치][본질] / 有 / 2차 / T1 / EG |
| The Little Book of Valuation, The Dark Side of Valuation | Damodaran, 2011(개정 2024 [Data Missing]) / 3판 2018 | [Data Missing] | 입문서 / 적자, 초기, 경기순환, 신흥시장 기업 평가 | [내재가치] / 有 / 2차 / T2 |
| Valuation(McKinsey) | Koller, Goedhart, Wessels, 7판 2020(Wiley) [Data Missing: 8판 발간 여부] | [Data Missing] | ROIC와 성장이 가치의 핵심 동인이라는 체계 | [내재가치][펀더멘털] / 有 / 실무 리서치 / T1 |
| Financial Statement Analysis and Security Valuation / Accounting for Value | Penman, 5판 2013(McGraw-Hill) / 2011(Columbia) | [Data Missing] | 잔여이익, 회계 기반 가치평가. 성장에 값을 치르지 말라는 관점 | [내재가치][펀더멘털] / 有 / 학술 / T2 |
| CFROI(HOLT) | Madden, CFROI Valuation(1999, Butterworth-Heinemann) | [Data Missing] | CFROI와 경쟁적 소멸(fade) 개념 | [내재가치][해자] / 有 / 실무 / T2 / EG |

**A-3. 실무 리서치 (EG 직결)**

- **Mauboussin & Callahan, "Competitive Advantage Period"**(Counterpoint Global, 파일명 "The Neglected Value Driver", 확인): Measuring the Moat의 분석 틀(Porter 5 forces 중 진입장벽과 경쟁강도, 가치사슬)을 경쟁우위 지속 기간(CAP) 추정에 연결한다. [내재가치][해자] **EG** / 有 / 실무 리서치 / T1. Consilient Observer 2026년 4월 14일 발행(morganstanley.com 페이지 메타데이터 기준)이며, 원형은 Mauboussin & Paul Johnson (1997) "Competitive Advantage Period: The Neglected Value Driver", Financial Management 26, 67~74다.
- **The Base Rate Book**(Mauboussin, Callahan, Majd, Credit Suisse, 2016): 매출 성장률, 이익률 변화의 기저율 분포를 제공한다. [펀더멘털][프로세스] **EG**(시장 내재 성장률이 기저율 분포에서 어디에 놓이는지 판정) / 有 / 실무 / T1.
- **Morningstar Equity Research Methodology**(2012, 2020년 10월 23일, 2022년 9월 29일, 2023년 6월 14일판, 확인): 3단계 DCF에서 Stage I은 5~10년 명시 예측, Stage II 기간은 해자 등급에 따라 달라지고, Stage III은 초과수익 0을 가정한다. [내재가치][해자] **EG**(해자 등급을 소멸 기간으로 환산하는 공개 사례) / 有 / 실무 / T1.

**A-4. 학술 논문 (기대와 수익률)**

| 논문 | 서지 | 사실 요약 | 신뢰도 / Tier |
|---|---|---|---|
| La Porta (1996) "Expectations and the Cross-Section of Stock Returns" | Journal of Finance 51(5) [DOI 미확인] | 애널리스트 장기성장 기대가 높은 종목의 수익률이 낮음 | 동료심사 / T1 / EG |
| La Porta, Lakonishok, Shleifer, Vishny (1997) "Good News for Value Stocks" | Journal of Finance 52(2) [DOI 미확인] | 이익 발표 시점 수익률로 기대 오류 가설 검증 | 동료심사 / T2 / EG |
| Lakonishok, Shleifer, Vishny (1994) "Contrarian Investment, Extrapolation, and Risk" | Journal of Finance 49(5) [DOI 미확인] | 가치 프리미엄을 과거 성장의 과도한 외삽으로 설명 | 동료심사 / T1 / EG |
| Chan, Karceski, Lakonishok (2003) "The Level and Persistence of Growth Rates" | Journal of Finance 58(2) [DOI 미확인] | 이익 성장률의 지속성이 우연 수준에 가까움 | 동료심사 / T1 / EG |
| Ohlson (1995) "Earnings, Book Values, and Dividends in Equity Valuation" | Contemporary Accounting Research 11(2) [DOI 미확인] | 잔여이익 모형 | 동료심사 / T2 |
| PEAD 계열: Ball & Brown (1968), Bernard & Thomas (1989) | Journal of Accounting Research 6(2) / JAR 27 Supplement [DOI 미확인] | 이익 발표 후 가격 표류 | 동료심사 / T2 / EG |

### B. 사업의 본질 / 비즈니스 모델 / 성장

**B-1. 피터 린치**

| 자료 | 서지 | 한국어판 | 사실 요약 | 태그 / 정량 / 신뢰도 / Tier |
|---|---|---|---|---|
| One Up on Wall Street | Lynch & Rothchild, 1989(Simon & Schuster), 2000년판 신서문 | 『전설로 떠나는 월가의 영웅』, 이건 역, 국일증권경제연구소. 2009년 2월 6일 개정판, 2017년 4월 17일 개정판, 2021년 7월 30일판(홍진채 감수, 464쪽, ISBN 9788957825945)(확인) | 6분류(7장), 완벽한 주식의 조건과 피해야 할 주식(8~9장), 2분 스토리, PER과 성장률 비교(PEG 원형), 재고, 부채, 순현금, 내부자 매수, 자사주. 챕터 번호는 [Data Missing: 2021 번역판 쪽수 대조] | [본질][펀더멘털] / 有(분류별 체크리스트) / 1차 / T1 |
| Beating the Street | Lynch & Rothchild, 1993 | 『피터 린치의 이기는 투자』 [Data Missing: 출판사, 역자] | 마젤란 운용 사례, 25 황금률, 업종별 사례 | [본질][프로세스] / 有 / 1차 / T1 |
| Learn to Earn | Lynch & Rothchild, 1995 | 『증권투자로 돈 버는 비결』 [Data Missing] | 기업과 자본주의 입문 | [본질] / 無 / 1차 / T3 |
| PBS Frontline 인터뷰 | 1997년 "Betting on the Market" [Data Missing: 방영일] | 없음 | 녹취록 공개 | [프로세스] / 無 / 1차 / T2 |
| Worth 칼럼, Barron's Roundtable, Magellan 보고서 | 1990년대 [Data Missing: 호수별 목록] | 없음 | 칼럼 아카이브 접근 경로 미확인 | [본질] / 無 / 1차 / T3 |

**B-2. 피셔, 멍거**

| 자료 | 서지 | 한국어판 | 사실 요약 | Tier |
|---|---|---|---|---|
| Common Stocks and Uncommon Profits | Fisher, 1958. 1996년 Wiley판(Ken Fisher 서문, Other Writings 합본) | 『위대한 기업에 투자하라』, 박정태 역, 굿모닝북스 "투자의 고전 1". 2005년판(절판), 2025년 7월 15일 개정판(확인) | 15 points(한국어판 58~104쪽 부근으로 독자가 인용, 2차 확인), scuttlebutt | T1 [본질][경영자] 有 1차 |
| Conservative Investors Sleep Well / Developing an Investment Philosophy | Fisher, 1975 / 1980 | 『보수적인 투자자는 마음이 편하다』, 굿모닝북스 "투자의 고전 2" 개정판(확인) [Data Missing: 연도] | 보수적 투자의 4차원, 투자철학 형성 과정(Motorola 등 사례 언급) | T2 |
| Poor Charlie's Almanack | Kaufman 편, 2005 초판. Stripe Press판 2023년 12월 5일(ISBN 9781953953230)(확인) | 『가난한 찰리의 연감』, 김태훈 역, 김영사, 2024년 11월 8일. 국내 최초 공식 출간, "인간적 오판의 심리학" 개정 최종판 기반(확인) | 1986~2007년 강연 11편. 1994 USC "A Lesson on Elementary, Worldly Wisdom", "The Psychology of Human Misjudgment"(1995 초연) | T1 [프로세스][본질] 無 1차 |
| Daily Journal 주총, Wesco 서한 | 1990년대~2023 | 없음 | 녹취는 커뮤니티 전사본 위주(신뢰도 주의) | T2 |

**B-3. 현대 퀄리티, 장기 투자자 1차 자료**

| 자료 | 서지 / 접근 | 사실 요약 | 태그 / Tier |
|---|---|---|---|
| Nomad Investment Partnership 서한 | Sleep & Zakaria, 2001~2014, 공개 PDF 모음 | scale economies shared, 목적지 분석 | [해자][본질] T1 |
| Fundsmith 연례 서한 / Investing for Growth | Terry Smith, 2011년~, 무료 / Harriman House 2020 | "좋은 회사를 사고, 비싸게 사지 말고, 아무것도 하지 말라". ROCE, 매출총이익률 중시 | [펀더멘털][해자] T1 |
| Giverny Capital 연례 서한 | Rochon, 무료 | 보유기업 내재가치 증가율 공개 방식 | [내재가치] T2 |
| Constellation Software 주주서한 | Mark Leonard, 2006~, 무료 | ROIC + 유기성장 지표, 자본배분 원칙 | [경영자] T1 |
| Amazon 주주서한 | Bezos, 1997~2020, 무료 | 1997 서한의 장기 FCF 중시 | [경영자][본질] T1 |
| Margin of Safety | Klarman, 1991, 절판(고가 중고) | 안전마진, 가치평가 불확실성 | [내재가치] T2 |
| Howard Marks 메모 | Oaktree, 1990~, 무료 | 2차적 사고, 사이클 | [프로세스] T2 |
| 100 Baggers / 100 to 1 in the Stock Market | Mayer 2015 / Phelps 1972 | 장기 복리 종목의 공통 특성 | [본질] T2 |
| Quality Investing | Cunningham, Eide, Hargreaves, 2016(Harriman) | 퀄리티 기업의 속성 체계화 | [해자] T2 |
| Capital Returns / Capital Account | Marathon(Chancellor 편), 2015 / 2004 | capital cycle: 공급 측 분석 | [해자][본질] T1 |
| Li Lu, 段永平, 张磊 Value | 강연, 雪球 게시물, 2020 도서 | 雪球 게시물은 커뮤니티 등급(원 게시물 링크 확인 필요) | [본질] T3 |
| Pabrai, Spier, Greenblatt | The Dhandho Investor(2007) / The Education of a Value Investor(2014) / You Can Be a Stock Market Genius(1997), The Little Book That Beats the Market(2005) | 체크리스트, 특수상황, magic formula | [프로세스] T2 |

### C. 펀더멘털 / 재무제표 분석 / 이익의 질

**C-1. 교재와 실무서**: CFA Program Curriculum(Financial Statement Analysis, Equity Valuation, 연도별 개정), Schilit, Perler, Engelhart, Financial Shenanigans 4판(2018, McGraw-Hill), Mary Buffett & Clark, Warren Buffett and the Interpretation of Financial Statements(2008), Montier, Value Investing: Tools and Techniques(2009, Wiley), Lev & Gu, The End of Accounting(2016, Wiley). 한국어판은 모두 [Data Missing]. 태그는 [펀더멘털], 정량 有(Shenanigans 경고 신호 목록), T1~T2.

**C-2. 정량 스코어 원 논문**

| 스코어 | 원 논문 서지 | 정의 요약 | 정량 / Tier |
|---|---|---|---|
| Piotroski F-score | Piotroski (2000), Journal of Accounting Research 38 Supplement [DOI 미확인] | 수익성 4, 레버리지와 유동성 3, 효율성 2, 합계 9개 이진 신호. 고 B/M 종목 내 선별 | 有 / T1 |
| Mohanram G-score | Mohanram (2005), Review of Accounting Studies 10 [DOI 미확인] | 저 B/M(성장주)용 8개 신호 | 有 / T2 |
| Beneish M-score | Beneish (1999), Financial Analysts Journal 55(5) [DOI 미확인] | 8변수 이익조작 확률 모형 | 有 / T1 |
| Altman Z-score | Altman (1968), Journal of Finance 23(4) [DOI 미확인] | 5개 재무비율의 판별분석 부도예측 | 有 / T2 |
| Sloan 발생액 | Sloan (1996), The Accounting Review 71(3) [DOI 미확인] | 발생액 비중이 높을수록 이익 지속성이 낮음 | 有 / T1 |
| Richardson 외 (2005) | Journal of Accounting and Economics 39(3) [DOI 미확인] | 발생액 신뢰성과 이익 지속성 | 有 / T2 |
| Dechow, Ge, Larson, Sloan (2011) F-score | Contemporary Accounting Research 28(1) [DOI 미확인] | 회계 부정표시 예측 | 有 / T2 |
| Novy-Marx (2013) Gross Profitability | Journal of Financial Economics 108(1) [DOI 미확인] | 매출총이익/총자산의 수익률 예측력 | 有 / T1 |
| Fama-French 5-factor (2015) | Journal of Financial Economics 116(1) [DOI 미확인] | 수익성(RMW), 투자(CMA) 팩터 추가 | 有 / T2 |
| Asness, Frazzini, Pedersen (2019) QMJ | Review of Accounting Studies 24(1) [DOI 미확인] | 수익성, 성장, 안전성, 배당성향의 퀄리티 합성 | 有 / T1 |
| Frazzini, Kabiller, Pedersen (2018) Buffett's Alpha | Financial Analysts Journal 74(4), 35~55, DOI 10.2469/faj.v74.n4.3 | 버핏 수익을 저베타, 퀄리티, 레버리지로 분해. 레버리지는 NBER WP 19681(2013) 초록에서 "about 1.6-to-1 on average", FAJ 게재본에서 "about 1.7 to 1, on average"이며 Sharpe는 게재본 0.79(NBER판 0.76) | 有 / T1 |
| Magic Formula | Greenblatt (2005) 도서 | ROC와 이익수익률 순위 합산 | 有 / T2 |
| Graham 기준, Graham number | Intelligent Investor 14장 | 방어적 투자자 7기준. Graham number = sqrt(22.5 x EPS x BPS) | 有 / T2 |

**C-3. 반론, 한계**

- Fama & French (2021) "The Value Premium", Review of Asset Pricing Studies 11(1) [DOI 미확인]: 1991~2019 기간 가치 프리미엄 약화를 통계적으로 검토.
- Lev & Srivastava (2019) "Explaining the Recent Failure of Value Investing", SSRN 워킹페이퍼 [링크 미확인]: 무형자산 비용처리로 B/M이 왜곡된다는 주장.
- Arnott, Harvey, Kalesnik, Linnainmaa (2021) "Reports of Value's Death May Be Greatly Exaggerated", Financial Analysts Journal 77(1) [DOI 미확인].
- Bessembinder (2018) "Do Stocks Outperform Treasury Bills?", Journal of Financial Economics 129(3) [DOI 미확인]: 1926년 이후 미국 주식의 순부(net wealth) 창출이 극소수 종목에 집중.

### D. 경제적 해자 / 경쟁우위 지속성

| 자료 | 서지 | 한국어판 | 사실 요약 | 정량 / 신뢰도 / Tier |
|---|---|---|---|---|
| Buffett 해자 발언 | 1995 주총 [Data Missing: 연도 확인], "Mr. Buffett on the Stock Market"(Fortune, 1999년 11월 22일), 2007 서한(great, good, gruesome) | 서한 번역서 | 해자는 넓고 깊어야 하며 늘 넓어지거나 좁아진다는 취지(Mauboussin이 인용, 확인) | 無 / 1차 / T1 |
| Morningstar Economic Moat Rating | 2012 소개 문서(VanEck 게재, 확인), 방법론 2023년판(확인) | 없음 | 원천 5가지: 전환비용, 네트워크 효과, 무형자산, 원가우위, 효율적 규모(홈페이지 확인). Moat Trend와 Uncertainty Rating은 방법론 문서의 구성요소 | 有(등급 기준) / 실무 / T1 / EG |
| Morningstar Capital Allocation Rating | 2020년 10월 문서(확인) | 없음 | Stewardship Rating을 대체. 재무구조, 투자, 주주환원 3축. Exemplary, Standard, Poor. 약 10년 경기순환 기준의 전망형 평가 | 有 / 실무 / T1 |
| The Little Book That Builds Wealth / The Five Rules | Dorsey, 2008 / 2004(Wiley) | 『경제적 해자』(북스토리, 확인) [Data Missing: 역자, 연도] | 해자 원천 4가지(무형자산, 전환비용, 네트워크, 원가우위). 우수 제품, 점유율, 실행력, 경영진은 해자가 아니라고 봄(한국어판 32, 49쪽, 독자 인용 2차 확인) | 有 / 2차(실무) / T1 |
| Why Moats Matter | Brilliant & Collins 외, 2014(Wiley) | [Data Missing] | Morningstar 해자 방법론 해설 | 有 / 실무 / T2 |
| Measuring the Moat | Mauboussin, 2002 초판, 2016 개정, Counterpoint Global 최신판(Mauboussin & Callahan, Consilient Observer 2024년 10월 15일)(확인) | 없음 | 산업 분석(5 forces, 진입장벽), 기업 분석(가치사슬), 상호작용(게임이론) 체크리스트 | 有 / 실무 / T1 / EG |
| 7 Powers | Helmer, 2016(Deep Strategy) | 『세븐 파워』, 유지연 역, 한빛비즈, 2022년 9월(전자책 2022년 9월 2일, 확인) | Power = 지속적 차별 수익의 잠재력을 만드는 조건. benefit과 barrier. 7가지 힘과 Power Progression(Origination, Take-off, Stability) | 有(프레임) / 2차(실무) / T1 |
| Porter | Competitive Strategy(1980), Competitive Advantage(1985), HBR 2008년 1월 "The Five Competitive Forces That Shape Strategy" | 번역본 다수 [Data Missing] | 5 forces, 가치사슬 | 有 / 1차(학술) / T1 |
| Competition Demystified | Greenwald & Kahn, 2005 | [Data Missing] | 진입장벽 중심. 고객 포획, 규모의 경제, 정부 보호 | 有 / T1 |
| Rumelt, Christensen, McGrath, Thompson | Good Strategy Bad Strategy(2011), The Innovator's Dilemma(1997), The End of Competitive Advantage(2013), Aggregation Theory(Stratechery, 2015~) | 일부 번역 [Data Missing] | 전략 핵심, 파괴적 혁신, 일시적 우위, 플랫폼 집적 | 無 / T2 |
| 학술: 이익 지속성 | Mueller(1977, RES; 1986, Profitability and the Public Interest), Rumelt(1991, SMJ 12(3)), McGahan & Porter(1997, SMJ 18), Wiggins & Ruefli(2002, Organization Science 13(1); 2005, SMJ 26(10)), Barney(1991, Journal of Management 17(1)) [모두 DOI 미확인] | 없음 | 초과이익의 평균회귀, 산업효과 대 기업효과, 지속적 우위의 희소성, RBV(VRIN) | 동료심사 / T1~T2 / EG(소멸 속도 기저율) |

### E. 경영자 자질 / 자본배분 / 지배구조

**E-1. 1차 원문과 도서**

| 자료 | 서지 | 한국어판 | 사실 요약 | Tier |
|---|---|---|---|---|
| Buffett 4 filters | 1977 연례 서한(이해 가능한 사업, 양호한 장기 전망, 정직하고 유능한 경영진, 매력적 가격) | 서한 번역서 | 투자 필터 원형. 인수 기준은 매년 서한 말미 "Acquisition Criteria" 목록 | T1 |
| The Essays of Warren Buffett | Cunningham 편, 1997~(최신판 [Data Missing: 판차]) | 이건 역 『워런 버핏 바이블』은 별개의 편역서임에 유의 [Data Missing: 출판사, 연도] | 주제별 서한 발췌 | T1 |
| Margin of Trust / The Warren Buffett CEO | Cunningham & Cuba, 2020 / Robert Miles, 2002 | [Data Missing] | 신뢰 기반 문화, 자회사 CEO 사례 | T2 |
| The Outsiders | Thorndike, 2012(HBR Press) | 『현금의 재발견』, 이혜경 역, 마인드빌딩, 2019년 3월 30일(확인) | 잭 웰치보다 성과가 좋았던 CEO 8인(버핏 포함)의 자본배분 | T1 |
| The Warren Buffett Way | Hagstrom, 1994 초판, 3판 2013 [Data Missing: 30주년판 여부] | [Data Missing] | 12 tenets(사업, 경영, 재무, 시장) | T1 |
| The Investment Checklist | Shearn, 2011(Wiley) | [Data Missing] | 경영진 평가 질문 목록 | T1 |
| Investing Between the Lines | Rittenhouse, 2013(McGraw-Hill) | [Data Missing] | CEO 서한의 솔직성 채점 | T2 |
| Mauboussin "Capital Allocation" | Mauboussin & Callahan, "Capital Allocation: Results, Analysis, and Assessment", Consilient Observer, 2022년 12월 15일. 이전판은 "Capital Allocation: Evidence, Analytical Methods, and Assessment Guidance", Journal of Applied Corporate Finance 26(2014), 48~74, DOI 10.1111/jacf.12090 | 없음 | 자본배분 5 선택지와 평가 기준 | T1 |
| Founders 팟캐스트, "Founder Mode" | Senra(2016~) / Paul Graham, 2024년 9월 | 없음 | 창업자 사례, 창업자 경영론 | T3 |
| Good to Great / The Halo Effect | Collins, 2001 / Rosenzweig, 2007 | 번역 있음 [Data Missing] | 후자는 성과를 보고 역으로 속성을 부여하는 후광효과와 생존편향을 비판 | T2(반론 병기) |

**E-2. 학술 논문** (모두 동료심사, [DOI 미확인])

- 대리인, 잉여현금: Jensen & Meckling(1976, JFE 3(4)), Jensen(1986, AER 76(2)).
- 자만, 과신: Roll(1986, Journal of Business 59(2)), Malmendier & Tate(2005, JF 60(6); 2008, JFE 89(1)), Chatterjee & Hambrick(2007, ASQ 52(3)).
- 경영자 효과: Hambrick & Mason(1984, AMR 9(2)), Bertrand & Schoar(2003, QJE 118(4)), Demerjian, Lev, McVay(2012, Management Science 58(7), DEA 기반 경영자 능력 점수, 정량 有), Bloom & Van Reenen(2007, QJE 122(4)), Bandiera 외(2020, JPE 128(4)).
- 소유구조: Anderson & Reeb(2003, JF 58(3)), Fahlenbrach(2009, JFQA 44(2)), Morck, Shleifer, Vishny(1988, JFE 20).
- 내부자, 자사주, M&A: Lakonishok & Lee(2001, RFS 14(1)), Cohen, Malloy, Pomorski(2012, JF 67(3), routine 대 opportunistic 내부자 구분, 정량 有), Ikenberry, Lakonishok, Vermaelen(1995, JFE 39), Moeller, Schlingemann, Stulz(2005, JF 60(2)).
- 경영자 행태, 텍스트: Graham, Harvey, Rajgopal(2005, JAE 40), Loughran & McDonald(2011, JF 66(1), DOI 10.1111/j.1540-6261.2010.01625.x, 확인), Larcker & Zakolyukina(2012, JAR 50(2)).

### F. 한국 시장 특화 (최우선)

**F-1. 제도 1차 자료 (2025~2026)**

| 자료 | 서지 / 날짜 | 사실 요약 | 태그 / Tier |
|---|---|---|---|
| 1차 상법 개정 | 2025년 7월 3일 본회의, 7월 22일 공포, 시행(법률 제20991호)(확인) | 제382조의3: 이사 충실의무 대상에 주주 추가, "총주주의 이익 보호" 및 공평 대우. 독립이사와 감사위원 3% 룰은 2026년 7월 23일 시행, 전자주총 의무는 2027년 1월 1일 시행 | [한국특화][경영자] T1 |
| 2차 상법 개정 | 2025년 8월 25일 본회의, 9월 9일 공포(법률 제21044호)(확인) | 자산총액 2조원 이상 상장사는 정관으로 집중투표를 배제할 수 없음. 분리선출 감사위원 1명에서 2명으로 확대 | T1 |
| 3차 상법 개정 | 2026년 2월 25일 본회의(법사위 대안, 의안번호 2216966), 3월 6일 공포, 시행(확인) | 자기주식 원칙적 취득 후 1년 내 소각(시행 전 보유분은 1년 6개월). 예외 보유, 처분은 자기주식보유처분계획서를 매년 주총에서 승인받아야 함. 외국인 지분 제한 업종 3년 특례 | T1 |
| 법무부 「자기주식 소각 의무화 관련 개정 상법 길라잡이」 | 2026년 3월 11일, moj.go.kr(확인) | Q&A 형식 해석 지침. 전체 회사(비상장, 벤처 포함)에 적용 | [한국특화][데이터] T1 |
| 로펌 해설 | 김앤장, 율촌, 세종, 삼일PwC 뉴스레터(2025~2026, 확인) | 시행일, 경과조치, 실무 쟁점 | 실무 / T2 |
| 코리아 밸류업 지수 | KRX, 2024년 9월 발표. 2026년 5월 21일 주가지수운영위 심의, 6월 12일 반영(확인) | 공시기업 비중 7%(2024.9) -> 25%(2024.12) -> 61%(2025.6) -> 100%(2026.6). 20종목 편입, 19종목 편출, 100종목. 전체 시총 대비 약 54.6% | [한국특화][데이터] T1 |
| KRX 기업 밸류업 프로그램 백서 | kind.krx.co.kr(확인, 발행일 [Data Missing]) | 제도 설계 문서 | T2 |
| 자본시장연구원 「코리아 디스카운트 원인 분석」 | 이슈보고서 23-05, 김준석, 강소현, 2023년 2월 16일, 26쪽, kcmi.re.kr(서브에이전트 확인) | 45개국 비교. 낮은 주주환원, 수익성, 성장성이 주원인. 금융위 보도자료는 한국 PBR이 선진시장의 52%, 신흥시장의 58%, 아태 지역의 69%라고 인용 | T1 |
| 기업지배구조보고서 공시, KCGS 평가 | 거래소 공시제도 / 한국ESG기준원 | 핵심지표 준수율 공시 [Data Missing: 2026 기준 대상 범위] | T2 |

**F-2. 한국 지배구조 학술 (국제 저널)**

- Bae, Kang, Kim (2002) "Tunneling or Value Added? Evidence from Mergers by Korean Business Groups", Journal of Finance 57(6), 2695~2740, DOI 10.1111/1540-6261.00510(확인): 재벌 계열사가 인수를 하면 주가는 평균적으로 하락하지만 지배주주는 다른 계열사 가치 상승으로 이득을 본다. 터널링 가설과 부합. T1.
- Baek, Kang, Lee (2006) "Business Groups and Tunneling: Evidence from Private Securities Offerings by Korean Chaebols", Journal of Finance 61(5), 2415~2449(인용 목록으로 확인). T1.
- Baek, Kang, Park (2004), Journal of Financial Economics 71(2), 265~313(인용 목록으로 확인): 외환위기 당시 지배구조와 기업가치. T2.
- Bae, Cheon, Kang (2008) "Intragroup Propping", Review of Financial Studies 21, 2015~2060(인용 목록으로 확인). T2.
- Black, Jang, Kim (2006), Journal of Law, Economics, and Organization 22(2) [DOI 미확인]: 한국 지배구조 지수와 기업가치. T1.
- Cho (2018) "Tunneling by Related-party Transactions: Evidence from Korean Conglomerates", Asian Economic Journal, DOI 10.1111/asej.12146(확인): 특수관계자 거래와 지배주주 현금흐름권의 관계. T2.

**F-3. 한국 학술지 (KCI) 실증** (서브에이전트 검증)

| 주제 | 서지 | 사실 요약 | 검증 상태 |
|---|---|---|---|
| F-score | 권세원, 이수정 (2025) "Fundamental analysis and stock returns: Korean evidence", Korean Accounting Review 50(6), 253~271, DOI 10.24056/KAR.2025.12.008 | 2000~2022년 KRX 비금융 기업. F-score 5분위 상하위 초과수익 차 약 18%. 영업현금흐름과 주식발행 여부가 예측력의 주원천 | 확인 |
| 수익성 프리미엄 | 김민기, 정진수, 김동석 (2018) 「한국 주식시장에서의 수익성 프리미엄 발생 요인 분석」, 재무관리연구 35(4), 69~108, DOI 10.22510/kjofm.2018.35.4.004 | 2001~2017년. 위험보상이 아니라 정보 불확실성과 차익거래 제약이 클수록 강해짐(과소반응 해석) | 확인 |
| 발생액 이상현상 | 고봉찬, 김진우 (2009) 「발생액 이상현상과 차익거래기회에 관한 연구」, 한국증권학회지 38(1), 77~105 | 차익거래 위험이 높은 종목에 이상현상이 집중된다는 2차 요약 | 쪽수, 요약은 2차 확인. DOI [Data Missing] |
| 발생액, 투자 이상현상 | 이경준, 김현식, 조훈 (2017), 한국증권학회지 46(5), 1121~1155, DOI 10.26845/KJFS.2017.12.46.5.1121 | 1992~2016년. 수익률 횡단면 변동성 위험 노출로 두 이상현상을 설명 | 확인 |
| 자사주, 내부자 | 박정지, 신정순 (2022) 「자사주 취득 공시와 내부자거래 관계 분석」, 한국증권학회지 51(3), 335~358, DOI 10.26845/KJFS.2022.06.51.3.335 | 2005~2014년. 공시 전 내부자거래가 저평가 정도에 따라 달라지고 공시 반응은 양(+) | 확인 |
| 자사주 취득, 처분 | 설원식, 김수정 (2005), 재무관리연구 22(1), 37~69 | 취득, 처분 목적별 주주부 효과 | 초록 [Data Missing] |
| 경영자 능력(DEA) | 고창열, 박준호, 정훈 외 1인 (2013) 「DEA를 이용한 경영자 능력이 기업성과에 미치는 영향에 관한 연구」, 관리회계연구 13(1), 165~200 | Demerjian 방식의 국내 표준 적용 사례로 많이 인용됨 | 4번째 저자, 초록 [Data Missing] |
| 경영자 능력과 기업가치 | 김진산, 이명기 (2021), 국제회계연구 98호, 67~91 | DEA 경영자 능력은 영업성과에 유의하지 않고 기업가치에는 음(-)의 영향. CEO 연령은 역U자 | 확인 |
| 오너경영 | 최우석, 이우백 (2005) 「오너경영과 기업성과에 관한 실증연구」, 재무연구 18(1), 121~155 | 비금융 상장사 1,616개. 오너경영 기업의 성과가 유의하게 높음 | 확인 |
| 가족경영과 기업가치 | 김동욱, 김병곤 (2016), 金融工學硏究 15(2), 91~120, DOI 10.35527/kfedoi.2016.15.2.004 | 2004~2014년 KOSPI 5,760 기업연도. 가족경영이 기업가치를 낮추며 비재벌 가족기업에 집중 | 확인. 위 최우석, 이우백(2005)과 결론이 반대(성과 지표 대 가치 지표 차이) |

**F-4. 한국 가치투자자, 운용사 1차 자료와 언론**

- **이채원(라이프자산운용 의장)**: 매경플러스 "한국의 위대한 투자자" 시리즈(2026년 6월 22일), 한경 머니 "가치투자 2.0" 기획(2025년 12월), 주간한국 인터뷰, 이로운넷 인터뷰(스스로 "피터 린치와 스타일이 비슷"하다고 언급), 회사 홈페이지 인터뷰(상법 개정 후 가치투자 시대 발언). 신뢰도: 언론 인터뷰(1차 발언, 2차 매체). T2.
- **허남권(신영자산운용 고문)**: 한국경제, 머니투데이, 이데일리 2024년 3월 6일 사임 보도. 신영마라톤, 신영밸류고배당 운용보고서(회사 공시). T2.
- **강방천(에셋플러스 전 회장)**: 2022년 7월 퇴진 보도(이데일리, 딜사이트), 2025년 4월 10일 고객 특별서신(뉴스프리존 보도). 에셋플러스 대표는 자료마다 다르게 나온다: 뉴스톱 보도는 양인찬, 회사 홈페이지 하단은 이성수. [Data Missing: 2026년 현재 대표 확정]. T3.
- **최준철, 김민국(VIP자산운용)**: 한국경제 "투자 고수를 찾아" 인터뷰(2024년 8월 18일, 화장품, 방산 투자 논리), 머니투데이 유튜브 인터뷰(2020), PUBLY 실패사례 콘텐츠(유료), 회사 홈페이지 공시정보(의결권 행사 내역). T2.
- **홍진채(라쿤자산운용)**: 『거인의 어깨』 [Data Missing: 출판사, 연도]. 『전설로 떠나는 월가의 영웅』 2021년판 감수(확인). T2.
- 박영옥, 숙향, 서준식, 이민주 저서, 얼라인파트너스, 머스트자산운용, KCGI 공개 서한: 이번 조사에서 서지 [Data Missing]. 얼라인파트너스의 코웨이 독립이사 의장 정관 변경 제안은 2차 보도로만 확인했다.

**F-5. 한국어 번역본 서지 요약** (확인분만 확정, 나머지 [Data Missing])

| 원서 | 한국어판 | 출판사 / 역자 / 연도 | 상태 |
|---|---|---|---|
| One Up on Wall Street | 전설로 떠나는 월가의 영웅 | 국일증권경제연구소 / 이건 / 2009, 2017, 2021(홍진채 감수) | 유통 |
| Common Stocks and Uncommon Profits | 위대한 기업에 투자하라 | 굿모닝북스 / 박정태 / 2005, 개정 2025년 7월 15일 | 2005판 절판, 개정판 유통 |
| Conservative Investors Sleep Well | 보수적인 투자자는 마음이 편하다 | 굿모닝북스 / [Data Missing] | 개정판 |
| Poor Charlie's Almanack | 가난한 찰리의 연감 | 김영사 / 김태훈 / 2024년 11월 8일 | 유통 |
| 7 Powers | 세븐 파워 | 한빛비즈 / 유지연 / 2022 | 유통 |
| The Outsiders | 현금의 재발견 | 마인드빌딩 / 이혜경 / 2019년 3월 30일 | 유통 |
| The Little Book That Builds Wealth | 경제적 해자 | 북스토리 / [Data Missing] | [Data Missing] |
| The Intelligent Investor 4판 | 현명한 투자자 | [Data Missing] / 이건 | [Data Missing] |
| 버핏 서한 편역 | 워런 버핏 바이블 | [Data Missing] / 이건 | [Data Missing] |
| Expectations Investing, Damodaran 저서, Greenwald, Hagstrom, Mauboussin 기타 | [Data Missing] | [Data Missing] | 미확인 |

**F-6. 한국 공시, 데이터 기본 자료**: DART 사업보고서(사업의 내용, 이사의 경영진단 및 분석의견, 임원 보수, 최대주주, 특수관계자 거래), OpenDART API(재무제표 전체 계정, 지분공시), KRX 정보데이터시스템, KIND(밸류업 공시, 확인). K-IFRS 연결 기준 지배주주순이익과 영업이익 표시 문제는 [Data Missing: 1차 기준서 문단 확인].

### G. 데이터 / 도구

- SEC EDGAR 전문검색과 XBRL API(data.sec.gov companyfacts, frames): 무료. [데이터] T1.
- OpenDART API, KRX 정보데이터시스템, KIND: 무료. [데이터][한국특화] T1.
- Damodaran Online 데이터셋(NYU Stern, 업종별 ROIC, WACC, 마진, 재투자율, 연 1회 갱신): 무료. **EG**(기저율, 재투자율 입력값). T1.
- 13F 추적: Dataroma(무료), WhaleWisdom(부분 무료). 신뢰도는 커뮤니티와 집계 사이트 수준이므로 원 13F 대조가 필요. T2.
- 공개 스코어링 방법론: Morningstar(A-3, D), expectationsinvesting.com 스프레드시트, Piotroski 원 논문 변수 정의. T1.
- 어닝콜 트랜스크립트: 기업 IR, Seeking Alpha(유료) 등. [Data Missing: 무료 한국 컨퍼런스콜 전사 소스].

### H. 의사결정 프로세스 / 행동재무 / 체크리스트 / 실패 사례

- 도서: Kahneman, Thinking, Fast and Slow(2011). Tetlock & Gardner, Superforecasting(2015). Duke, Thinking in Bets(2018). Bevelin, Seeking Wisdom 3판(2007). Gawande, The Checklist Manifesto(2009). 한국어판 [Data Missing]. [프로세스] T1~T2.
- Pabrai 체크리스트: 강연과 The Dhandho Investor 관련 자료(1차 체크리스트 원문 공개 범위 [Data Missing]).
- Counterpoint Global 관련: 스킬과 기회(dispersion), 노이즈 감소와 superforecaster 분석 보고서(Consilient Observer 시리즈, 확인). T2.
- 대가 실패 원문: Dexter Shoe(2007, 2014 서한), 섬유 사업(1985 서한), IBM 매도(2018 주총 [Data Missing]), Kraft Heinz 상각(2018, 2019 서한), 2020 항공주 매도(2020 주총), Tesco(2014 서한). 린치의 실수는 One Up 서문과 Beating the Street. 최준철의 실패 고백(PUBLY). T1(시스템 검증 케이스).

### I. AI 보조 펀더멘털 분석

- Kim, Muhn, Nikolaev, "Financial Statement Analysis with Large Language Models", arXiv 2407.17866(2024년 7월 25일 제출, 확인). GPT-4가 익명화된 재무제표만으로 이익 변화 방향을 애널리스트보다 잘 예측했다고 보고했다. **2025년 2월 20일 v3에서 저자(Nikolaev)가 철회했다(확인).** 인용하거나 방법론을 차용할 때는 철회 사실을 병기해야 한다. 신뢰도: 워킹페이퍼(철회). T2.
- Lopez-Lira & Tang (2023) "Can ChatGPT Forecast Stock Price Movements?", SSRN, arXiv 2304.07619 [링크 미확인]. T2.
- FinanceBench(Islam 외, 2023, arXiv 2311.11944 [링크 미확인]): 공시 기반 질의응답 벤치마크. T2.
- 금융 LLM 환각에 관한 실증(Kang & Liu 2023, NeurIPS 워크숍, 확인된 인용 목록). look-ahead bias 문헌은 [Data Missing: 대표 논문 서지]. T2.

---

## 핵심 개념 원문 정의 대조표

| 용어 | 대가 / 원문 정의(짧은 인용 또는 요지) | 출처 위치 | 대조 자료 |
|---|---|---|---|
| 내재가치 | Buffett: 사업이 남은 수명 동안 창출할 현금의 할인가치 | Owner's Manual(원칙 11 부근 [Data Missing: 항목 번호]) | Morningstar: 미래 현금흐름에서 나오는 내재가치 = fair value estimate(2023 방법론) |
| owner earnings | 보고이익 + 감가상각 등 - 평균 유지 자본적지출(± 운전자본) | 1986 서한 부록 | Mauboussin/Rappaport: 가치동인 기반 FCF |
| 유보 테스트 | "more than one dollar of market value ... by each dollar of retained earnings" | 1983~84 서한. Abel 2026 서한(CNBC 인용) | Thorndike: 자본배분 5선택지 |
| 경제적 해자 | Buffett: 넓고 깊어야 하며 늘 넓어지거나 좁아짐 | 주총과 서한(Mauboussin, Measuring the Moat 각주 17 인용) | Morningstar: ROIC > WACC를 장기간 유지하게 하는 구조적 특징. Helmer: 지속적 차별 수익의 잠재력을 만드는 조건 |
| 해자 원천 | Dorsey: 4가지 / Morningstar: 5가지(효율적 규모 추가) / Helmer: 7 Powers | 각 도서, 웹 | 분류 체계 불일치 병기 |
| 능력범위 | Buffett: 범위의 크기보다 경계를 아는 것이 중요 | 1996 서한 [Data Missing: 원문 대조] | Munger 강연 |
| 안전마진 | Graham: 건전한 투자의 핵심 개념 | Intelligent Investor 20장 | Klarman, Margin of Safety |
| 4 filters | 이해 가능한 사업, 양호한 장기 전망, 정직하고 유능한 경영진, 매력적 가격 | 1977 서한 | Hagstrom 12 tenets |
| PEG | Lynch: 적정가 기업의 PER은 성장률과 같다는 취지. 배당수익률을 더한 변형 | One Up 13장 부근 [Data Missing: 장 번호 대조] | 비판: 성장률의 지속성 부족(Chan 외 2003), 성장의 질(ROIC)을 무시 |
| 린치 6분류 | slow grower, stalwart, fast grower, cyclical, turnaround, asset play | One Up 7장 | Morningstar 해자와 불확실성 등급(분류축이 다름) |
| Power | Helmer: benefit + barrier | 7 Powers 서론 | Porter 진입장벽 |
| PIE | 현재 주가를 정당화하는 매출 성장률, 이익률, 기간 | Expectations Investing 5장 부근 [Data Missing] | Morningstar Stage II 기간, CAP 보고서 |

## 충돌하는 관점과 반론 (병기 목록)

- **PEG 비판**: 이익 성장률의 지속성은 낮다(Chan, Karceski, Lakonishok 2003). 성장의 가치는 ROIC가 자본비용을 넘을 때만 생긴다(Koller 외, Mauboussin).
- **해자 지속성 회의론**: 초과이익은 평균회귀한다(Mueller, Wiggins & Ruefli). McGrath는 일시적 우위를 주장했다. Morningstar는 무해자 기업의 Stage II 기간을 2012년판 0년에서 2020년판 1년으로 바꿔 표기했다.
- **해자 원천 분류 불일치**: Dorsey 4개, Morningstar 5개, Helmer 7개. Dorsey는 우수 경영진을 해자로 보지 않는다.
- **value premium 논쟁**: Fama-French 2021, Lev-Srivastava 2019(무형자산 왜곡), Arnott 외 2021(가치 사망론 반박).
- **장기 수익 집중**: Bessembinder 2018. 분산과 집중 논쟁의 근거.
- **Good to Great 비판**: Rosenzweig, The Halo Effect.
- **오너경영 효과(한국)**: 최우석, 이우백(2005)은 성과가 양(+), 김동욱, 김병곤(2016)은 가치가 음(-), 김진산, 이명기(2021)는 경영자 능력이 가치에 음(-)이다.
- **코리아 디스카운트 원인**: KCMI(2023)는 지배구조보다 주주환원, 수익성이 주원인이라고 봤다. 반면 입법(2025~2026)은 지배구조를 개혁 대상으로 삼았다. 원인 진단과 정책 초점이 다르다.
- **AI 분석**: Kim/Muhn/Nikolaev의 긍정적 결과는 철회 상태다.

## 출처 불명, 와전 가능 어록 경고 목록

- "Rule No. 1: Never lose money. Rule No. 2: Never forget rule No. 1.": 버핏 발언으로 널리 인용되지만 최초 출처(매체, 연도) [Data Missing].
- "Price is what you pay; value is what you get.": 2008 서한에 나온다. 버핏은 이를 그레이엄의 가르침으로 소개한다. 원 발화자 귀속에 주의.
- 멍거 어록의 상당수는 주총 녹취의 커뮤니티 전사본에서 나왔다. Poor Charlie's Almanack 수록 여부로 1차 확인해야 한다.
- 段永平 어록은 雪球 원 게시물 링크가 없는 한국어 2차 인용이 많다. 커뮤니티 등급으로 분류한다.
- 린치 어록("Know what you own" 등)은 책 쪽수 대조 전까지 [Data Missing: 쪽수].

## 커뮤니티, 뉴스레터 신뢰도 등급

| 채널 | 성격 | 신뢰도 |
|---|---|---|
| Value Investors Club | 심사제 아이디어 게시 | 커뮤니티(상) |
| Corner of Berkshire & Fairfax | 버크셔 계열 포럼 | 커뮤니티(중상) |
| Reddit r/ValueInvesting, r/SecurityAnalysis | 개방형 | 커뮤니티(중하) |
| The Rational Walk, A Letter a Day(Substack) | 서한 해설, 전사 | 2차 해설(Abel 서한 전사 등, 원문 대조 필요) |
| Manual of Ideas / MOI Global, Value Investor Insight | 인터뷰 | 2차 해설(상) |
| 雪球, 네이버 카페 가치투자연구소, 아이투자 | 한중 커뮤니티 | 커뮤니티(중) |
| Seeking Alpha | 기고형 | 커뮤니티(편차 큼) |

## Recommendations (자료 수집 순서만 제시)

1. T1 1차 원문 묶음을 먼저 확보한다: 버크셔 서한 전 연도와 Owner's Manual, Abel 2026 서한, One Up on Wall Street 원서와 2021 번역판, Expectations Investing 2021과 사이트 스프레드시트, Morningstar 방법론 2012, 2020, 2023판과 Capital Allocation 2020, Measuring the Moat 최신판.
2. EG 엔진 관련 문서(A-3, D의 CAP, Base Rate Book, Damodaran 데이터셋)는 별도 폴더로 분리한다.
3. 한국 제도 자료(법률 제20991호, 제21044호, 3차 개정 공포문, 법무부 길라잡이, KRX 밸류업 백서, KCMI 23-05)를 날짜순으로 정리한다.
4. [DOI 미확인] 학술 항목은 DOI와 피인용 수를 일괄 조회한다(Crossref, Google Scholar). 피인용 수는 이번 조사에서 모두 [Data Missing].

## Caveats

- 해외 고전 논문의 권호는 표준 인용 기준이다. DOI와 피인용 수는 이번 조사에서 개별 확인하지 못했다.
- 한국어 번역본 중 확인되지 않은 항목(Expectations Investing, Damodaran, Greenwald, Hagstrom 등)은 번역 여부 자체가 [Data Missing]이다.
- 에셋플러스 대표이사는 자료마다 다르다(양인찬 보도, 홈페이지 이성수).
- 린치, 그레이엄 도서의 챕터와 쪽수는 판마다 다르므로 대조가 필요하다.
- Morningstar 방법론은 연도판마다 수치 표현이 바뀌었다. 인용할 때는 판 날짜를 함께 적어야 한다.
- 이 문서는 자료조사이며 평가, 투자 추천을 담지 않는다.
