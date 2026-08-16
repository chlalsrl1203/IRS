"""
ledger 디렉터리 자체의 무결성 테스트 (v3.32 신규, 2026-08-05)

왜 만들었나 - 2026-08-05 감사에서 실제로 터진 사고:
이 프로젝트는 "같은 종목의 구 ledger는 git rm하고 새 파일로 통합한다"는 관행을
2026-07-28 이후 매번 손으로 지켜왔다(CLAUDE.md에 GWRE/TYL/ROP/BRO 등 사례가
반복 기록돼 있다). 그런데 그 관행이 자리잡기 **전**에 정정된 WM/WCN/IDXX
3종목은 구 파일(2026-07-25)이 지워지지 않고 남아 있었다.

남은 결과가 조용한 오염이었다:
  - `ledger/*.json`을 그냥 glob하면 33종목인데 36건이 나온다
  - 그 3종목은 v3.19 sensitivity 근본수정 **이전** 값(judgment_flipped=True,
    Confidence 59/59/64)을 그대로 들고 있어, 같은 티커에 대해 서로 모순되는
    기록 2부가 저장소에 공존했다
  - 실제로 CLAUDE.md v3.26 항목의 "RAR<0인 13종목" 통계가 이 중복 때문에
    나온 값이다 - 나열된 티커는 10개뿐인데 개수만 13으로 적혀 있었고,
    거기서 산출한 순위상관(+0.291)도 3종목을 두 번씩 센 결과였다
    (중복 제거 시 +0.067로 사실상 소멸 - 2026-08-05 재계산)

`rank_portfolio`가 티커별 최신만 고르는 덕분에 최종 산출물은 무사했지만,
그건 그 스크립트 하나가 우연히 방어적으로 짜였기 때문이지 저장소가 건전해서가
아니었다. 관행을 문서로만 두면 지켜지지 않는다는 걸 이 프로젝트는 이미 세 번
겪었다(run_self_check·confidence_score·claim/lock) - 그래서 테스트로 고정한다.
"""

import collections
import glob
import json
import os
import re

LEDGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ledger")

FNAME_RE = re.compile(r"^(?P<ticker>[A-Z.]+)_(?P<date>\d{4}-\d{2}-\d{2})\.json$")


def _ledger_files():
    return sorted(glob.glob(os.path.join(LEDGER_DIR, "*.json")))


def test_one_ledger_file_per_ticker():
    """
    종목당 ledger는 정확히 1건이어야 한다. 정정·재실행으로 새 날짜 파일을
    만들었다면 구 파일은 git rm으로 지우고 통합할 것(CLAUDE.md 관행).

    2건 이상 남아 있으면 같은 종목에 대해 서로 다른 Gap/RAR/Confidence를
    주장하는 기록이 공존하게 되고, ledger를 단순 glob하는 모든 집계가
    그 종목을 중복 계상한다.
    """
    by_ticker = collections.defaultdict(list)
    for path in _ledger_files():
        m = FNAME_RE.match(os.path.basename(path))
        assert m, f"ledger 파일명 규약 위반(<TICKER>_<YYYY-MM-DD>.json): {path}"
        by_ticker[m.group("ticker")].append(os.path.basename(path))

    duplicated = {t: sorted(f) for t, f in by_ticker.items() if len(f) > 1}
    assert not duplicated, (
        "같은 종목의 ledger가 2건 이상 남아 있다 - 구 파일을 git rm하고 최신 "
        f"1건으로 통합할 것: {duplicated}"
    )


def test_ledger_filename_matches_content():
    """파일명의 티커·날짜가 내용의 meta와 일치해야 한다(수동 rename 사고 방지)."""
    mismatches = []
    for path in _ledger_files():
        m = FNAME_RE.match(os.path.basename(path))
        d = json.load(open(path, encoding="utf-8"))
        if d["meta"]["ticker"] != m.group("ticker"):
            mismatches.append(f"{os.path.basename(path)}: ticker={d['meta']['ticker']}")
        if d["meta"]["analyzed_at"][:10] != m.group("date"):
            mismatches.append(
                f"{os.path.basename(path)}: analyzed_at={d['meta']['analyzed_at'][:10]}"
            )
    assert not mismatches, f"파일명과 meta 불일치: {mismatches}"


def test_every_ledger_is_self_consistent_on_judgment():
    """
    한 ledger 안에서 최상위 judgment와 sensitivity_check의 판정 라벨이 같은
    어휘를 써야 한다(v3.32 judgment_from_gap 통일 이전에는 중립 구간이
    "적정가"(sensitivity) vs "적정가/경계선"(judgment)으로 갈려 있었다).

    과거에 저장된 ledger는 통일 이전 라벨을 그대로 갖고 있으므로 여기서는
    **어휘 집합**만 검사한다 - 두 라벨이 모두 알려진 판정 어휘여야 한다는
    최소 조건이고, 새로 저장되는 ledger는 자동으로 통일된 값이 들어간다.
    """
    from engine.expectation_gap_engine import (
        JUDGMENT_NEUTRAL,
        JUDGMENT_OVERVALUED,
        JUDGMENT_UNDERVALUED,
    )

    known = {JUDGMENT_UNDERVALUED, JUDGMENT_NEUTRAL, JUDGMENT_OVERVALUED, "적정가"}
    bad = []
    for path in _ledger_files():
        d = json.load(open(path, encoding="utf-8"))
        labels = [d["judgment"]] + [
            d["sensitivity_check"][k]
            for k in ("judgment_with_drs", "judgment_without_drs")
            if k in d["sensitivity_check"]
        ]
        for lab in labels:
            if lab not in known:
                bad.append(f"{os.path.basename(path)}: {lab!r}")
    assert not bad, f"알 수 없는 판정 라벨: {bad}"


# ----------------------------------------------------------------------
# ETF ledger (v3.35 추가)
# ----------------------------------------------------------------------
# 회사 ledger에서 겪은 "구 파일이 안 지워져 33종목이 36건으로 잡히고 그 중복이
# 통계를 오염시킨" 사고(v3.32)를 ETF 쪽에서 반복하지 않도록 같은 규칙을 건다.
# 실제로 v3.35 작업 중 UTC 날짜가 바뀌면서 같은 ETF의 파일이 두 날짜로 생길
# 뻔했다 - 규칙이 없으면 정확히 같은 일이 벌어진다.

ETF_LEDGER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ledger_etf")


def _etf_ledger_files():
    if not os.path.isdir(ETF_LEDGER_DIR):
        return []
    return sorted(glob.glob(os.path.join(ETF_LEDGER_DIR, "*.json")))


def test_one_etf_ledger_file_per_ticker():
    by_ticker = collections.defaultdict(list)
    for path in _etf_ledger_files():
        m = FNAME_RE.match(os.path.basename(path))
        assert m, f"ETF ledger 파일명 규약 위반: {path}"
        by_ticker[m.group("ticker")].append(os.path.basename(path))

    duplicated = {t: sorted(f) for t, f in by_ticker.items() if len(f) > 1}
    assert not duplicated, (
        "같은 ETF의 ledger가 2건 이상 남아 있다 - 구 파일을 git rm하고 최신 "
        f"1건으로 통합할 것: {duplicated}"
    )


def test_etf_ledger_filename_matches_content():
    mismatches = []
    for path in _etf_ledger_files():
        m = FNAME_RE.match(os.path.basename(path))
        d = json.load(open(path, encoding="utf-8"))
        if d["meta"]["ticker"] != m.group("ticker"):
            mismatches.append(f"{os.path.basename(path)}: {d['meta']['ticker']}")
        if d["meta"]["analyzed_at"][:10] != m.group("date"):
            mismatches.append(
                f"{os.path.basename(path)}: {d['meta']['analyzed_at'][:10]}")
    assert not mismatches, f"파일명과 meta 불일치: {mismatches}"


def test_etf_ledger_is_not_mixed_into_company_ledger_dir():
    """ETF 기록이 회사 ledger 디렉터리로 새어 들어가지 않았는지 확인."""
    for path in _ledger_files():
        d = json.load(open(path, encoding="utf-8"))
        assert d["meta"].get("analysis_type") != "etf", (
            f"ETF ledger가 회사 ledger 디렉터리에 있다: {path}")


# ----------------------------------------------------------------------
# KRX 래퍼 ETF ledger (v3.38 추가)
# ----------------------------------------------------------------------
# ETF ledger와 같은 이유로 같은 규칙을 건다 - 회사/미국ETF/국내래퍼 세 스키마가
# 서로 다르고 파일명 규약 사고(v3.32)가 이미 두 번(회사·ETF) 반복됐다.

KRX_LEDGER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ledger_krx")

# 회사/미국ETF 티커는 알파벳(+.)이지만 KRX 종목코드는 6자리 숫자다
# (예: "360750") - FNAME_RE로는 매칭이 안 돼 별도 정규식을 쓴다.
KRX_FNAME_RE = re.compile(r"^(?P<ticker>[0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})\.json$")


def _krx_ledger_files():
    if not os.path.isdir(KRX_LEDGER_DIR):
        return []
    return sorted(glob.glob(os.path.join(KRX_LEDGER_DIR, "*.json")))


def test_one_krx_ledger_file_per_ticker():
    by_ticker = collections.defaultdict(list)
    for path in _krx_ledger_files():
        m = KRX_FNAME_RE.match(os.path.basename(path))
        assert m, f"KRX ledger 파일명 규약 위반: {path}"
        by_ticker[m.group("ticker")].append(os.path.basename(path))

    duplicated = {t: sorted(f) for t, f in by_ticker.items() if len(f) > 1}
    assert not duplicated, (
        "같은 종목의 KRX ledger가 2건 이상 남아 있다 - 구 파일을 git rm하고 최신 "
        f"1건으로 통합할 것: {duplicated}"
    )


def test_krx_ledger_filename_matches_content():
    mismatches = []
    for path in _krx_ledger_files():
        m = KRX_FNAME_RE.match(os.path.basename(path))
        d = json.load(open(path, encoding="utf-8"))
        if d["meta"]["ticker"] != m.group("ticker"):
            mismatches.append(f"{os.path.basename(path)}: {d['meta']['ticker']}")
        if d["meta"]["analyzed_at"][:10] != m.group("date"):
            mismatches.append(
                f"{os.path.basename(path)}: {d['meta']['analyzed_at'][:10]}")
    assert not mismatches, f"파일명과 meta 불일치: {mismatches}"


def test_krx_ledger_is_not_mixed_into_other_ledger_dirs():
    """KRX 래퍼 기록이 회사/미국ETF ledger 디렉터리로 새어 들어가지 않았는지 확인."""
    for path in _ledger_files() + _etf_ledger_files():
        d = json.load(open(path, encoding="utf-8"))
        assert d["meta"].get("analysis_type") != "krx_wrapper", (
            f"KRX 래퍼 ledger가 다른 ledger 디렉터리에 있다: {path}")


def test_krx_ledger_requires_wrapper_of_provenance():
    """모든 KRX ledger는 어느 미국 원본을 재사용했는지 근거를 남겨야 한다."""
    for path in _krx_ledger_files():
        d = json.load(open(path, encoding="utf-8"))
        wrapper_of = d["meta"].get("wrapper_of")
        assert wrapper_of and wrapper_of.get("us_reference_ticker"), (
            f"{os.path.basename(path)}: wrapper_of.us_reference_ticker 누락")
        assert wrapper_of.get("tracks_same_index_as"), (
            f"{os.path.basename(path)}: tracks_same_index_as 근거 누락")


# ----------------------------------------------------------------------
# 투자판단 기록 디렉터리 (v3.48 추가) - thesis / predictions / experiments
# ----------------------------------------------------------------------
# 세 기록은 ledger와 스키마가 전혀 다르다(judgment/drs 같은 키가 없다).
# 한 디렉터리에 섞이면 위 무결성 테스트들이 회사 스키마를 가정하고 전수
# 파싱하다 깨진다 - ETF(v3.35)·KRX(v3.38)에서 이미 두 번 확인한 규칙을
# 세 번째로 적용한다.

_RECORD_DIRS = ("thesis", "predictions", "experiments")
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_decision_records_are_not_mixed_into_any_ledger_dir():
    """thesis/prediction/experiment 기록이 ledger 디렉터리로 새지 않았는지."""
    ledger_dirs = [LEDGER_DIR, ETF_LEDGER_DIR, KRX_LEDGER_DIR]
    for d in ledger_dirs:
        if not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            rec = json.load(open(path, encoding="utf-8"))
            for key in ("thesis", "core_hash", "invalidation_conditions"):
                assert key not in rec, (
                    f"투자판단 기록('{key}' 키 보유)이 ledger 디렉터리에 있다: {path}"
                )


def test_experiment_records_keep_their_integrity_hash():
    """
    등록된 실험은 전부 core_hash를 갖고 있어야 하고, 그 해시가 현재 코어와
    일치해야 한다 - 규칙이 사후 변경되지 않았음을 저장소 차원에서 확인한다.
    """
    from engine.experiment_registry import core_hash

    d = os.path.join(_ROOT, "experiments")
    if not os.path.isdir(d):
        return
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        rec = json.load(open(path, encoding="utf-8"))
        assert rec.get("core_hash"), f"{path}에 core_hash가 없다"
        assert core_hash(rec["core"]) == rec["core_hash"], (
            f"{path}의 실험 규칙이 등록 이후 변경됐다 - 결과를 본 뒤 규칙을 "
            f"고치면 검증이 무의미해진다"
        )


def test_predictions_are_never_silently_edited_after_resolution():
    """
    저장된 예측 전부에 대해 코어 해시를 재계산해 봉인이 유지되는지 확인한다.
    resolve_prediction()이 막는 것은 코드 경로뿐이라, 손으로 파일을 고친
    경우는 이 테스트가 잡는다.
    """
    from engine.prediction_ledger import core_hash

    d = os.path.join(_ROOT, "predictions")
    if not os.path.isdir(d):
        return
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        rec = json.load(open(path, encoding="utf-8"))
        assert core_hash(rec["core"]) == rec["core_hash"], (
            f"{path}의 예측 코어가 변조됐다 - 결과를 알고 난 뒤 예측을 "
            f"수정할 수 없다는 것이 이 원장의 유일한 존재 이유다"
        )
