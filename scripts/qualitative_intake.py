"""
정성평가 표준입력 CLI (v3.93)

  python -m scripts.qualitative_intake checklist <lens_set>   # 조사 체크리스트 출력
  python -m scripts.qualitative_intake submit <payload.json>  # 검증 + 봉인 저장
  python -m scripts.qualitative_intake coverage               # 커버리지 리포트 갱신

조사는 이 스크립트 밖에서 한다(사람 또는 세션 안의 Claude). 여기서는 **형식과 근거
계약만 검증**하고 통과하면 `qualitative/`에 봉인 저장한다. 판정·비중은 건드리지 않는다.

`coverage`는 `reports/qualitative_coverage.json`을 만든다:
  - 봉인된 정성 평가(QSI)가 있는 종목과 축별 답한/모르는 질문 수
  - **레거시(자유서술)만 있는 종목** — `portfolio/qualitative_overrides.json`에 있으나
    QSI가 없는 종목. 소급해서 새 스키마로 다시 쓰지 않는다(사후합리화 방지).
"""

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402

OVERRIDES = os.path.join(ROOT, "portfolio", "qualitative_overrides.json")
REPORT = os.path.join(ROOT, "reports", "qualitative_coverage.json")
SPARSE_QSI = 0.5   # 답한 질문 비율이 이보다 낮으면 '희박' — 사전 고정, 결과를 보고 조정하지 않는다


def cmd_checklist(lens_set: str) -> int:
    print(f"# 정성 조사 체크리스트 — lens_set={lens_set}")
    print("# 모르면 status='unknown' + note(사유). ★=1차 확인(VERIFIED_PRIMARY) 필수")
    cur = None
    for q in Q.bank_for(lens_set):
        if q.lens != cur:
            cur = q.lens
            print(f"\n[{cur}]")
        extra = f" {list(q.allowed)}" if q.allowed else ""
        star = "★" if q.requires_primary else " "
        print(f"  {star} {q.qid:<34} ({q.answer_type}){extra}\n      {q.question}")
    return 0


def cmd_submit(path: str, directory: str = None) -> int:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    rec = Q.build_record(payload)
    out = Q.save_record(rec, directory)
    c = rec["coverage"]
    print(f"봉인 저장: {os.path.relpath(out, ROOT)}")
    print(f"  해시 {rec['sealed_core_hash'][:12]}…  답한 {c['n_answered']}/{c['n_questions']}"
          f"  미조사 축: {c['unexamined_lenses']}")
    if c["material_without_primary"]:
        print(f"  ⚠️ 중요도 HIGH인데 1차 확인 없는 주장: {c['material_without_primary']}")
    if not c["inversion_complete"]:
        print("  ⚠️ inversion(무엇이 이 회사를 죽이는가)이 비어 있다 — 미완료")
    return 0


def build_coverage(directory: str = None) -> dict:
    directory = directory or Q.QUALITATIVE_DIR
    sealed, tickers = [], set()
    latest = {}
    n_files = 0
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        Q.verify_record(rec)             # 과거 개정본도 전부 무결성 검증한다
        n_files += 1
        m = Q.FNAME_RE.match(os.path.basename(path))
        key = (rec["as_of"], int(m["rev"] or 1))
        if rec["entity"] not in latest or key > latest[rec["entity"]][0]:
            latest[rec["entity"]] = (key, rec)
    # 종목당 **최신본만** 현재 상태로 센다 — 개정본·과거 날짜를 모두 세면 같은 종목이 중복된다.
    for _, rec in sorted(latest.values(), key=lambda kr: kr[1]["entity"]):
        tickers.add(rec["entity"])
        c = rec["coverage"]
        n_na = sum(v.get("not_applicable", 0) for v in c["per_lens"].values())
        sealed.append({
            "n_not_applicable": n_na,
            "resolved_fraction": round((c["n_answered"] + n_na) / c["n_questions"], 4) if c["n_questions"] else None,
            "entity": rec["entity"], "as_of": rec["as_of"], "lens_set": rec["lens_set"],
            "sealed_core_hash": rec["sealed_core_hash"],
            "n_answered": c["n_answered"], "n_questions": c["n_questions"],
            "answered_fraction": c["answered_fraction"],
            "unexamined_lenses": c["unexamined_lenses"],
            "inversion_complete": c["inversion_complete"],
            "price_at_analysis_recorded": rec["price_at_analysis"] is not None,
            "per_lens": c["per_lens"],
        })
    legacy, with_legacy = [], set()
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding="utf-8") as f:
            with_legacy = set(json.load(f).get("overrides", {}))
        legacy = sorted(with_legacy - tickers)
    # 레거시 자유서술이 있는 종목의 QSI 답한 비율이 낮으면, QSI 봉인이 있다는 사실이
    # "정성조사가 표준화됐다"는 뜻이 아니다 — 풍부한 내용은 아직 자유서술에만 있다.
    sparse = sorted(r["entity"] for r in sealed
                    if r["entity"] in with_legacy and r["answered_fraction"] < SPARSE_QSI)
    slots = sum(r["n_questions"] for r in sealed)
    ans = sum(r["n_answered"] for r in sealed)
    na = sum(r["n_not_applicable"] for r in sealed)
    totals = {"slots": slots, "answered": ans, "not_applicable": na,
              "answered_fraction": round(ans / slots, 4) if slots else None,
              "resolved_fraction": round((ans + na) / slots, 4) if slots else None,
              "note": ("answered와 not_applicable을 따로 센다. 해당 없음은 규칙(무배당 직접 진술, 외국 발행사의 "
                       "보수 승인 투표 부재 등)으로만 주며 '모름'을 대신하지 않는다.")}
    return {
        "totals": totals,
        "n_sealed_records": len(sealed), "n_record_files": n_files, "sealed": sealed,
        "legacy_freeform_only": legacy,
        "legacy_with_sparse_qsi": sparse,
        "sparse_qsi_threshold": SPARSE_QSI,
        "legacy_note": ("자유서술 정성조사만 있고 QSI 봉인이 없는 종목. 소급 재작성하지 "
                        "않는다 — 새 조사부터 표준 입력으로 쌓는다."),
        "validation_status": Q.VALIDATION_STATUS,
    }


def cmd_coverage() -> int:
    rep = build_coverage()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    t = rep["totals"]
    print(f"전체 {t['slots']}칸: 답함 {t['answered']} ({t['answered_fraction']:.1%}), 해당없음 {t['not_applicable']}, "
          f"해결 {t['resolved_fraction']:.1%}")
    print(f"봉인 {rep['n_sealed_records']}건, 레거시 전용 {len(rep['legacy_freeform_only'])}종목"
          f" -> {os.path.relpath(REPORT, ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("checklist"); c.add_argument("lens_set")
    s = sub.add_parser("submit"); s.add_argument("payload")
    sub.add_parser("coverage")
    a = ap.parse_args(argv)
    if a.cmd == "checklist":
        return cmd_checklist(a.lens_set)
    if a.cmd == "submit":
        return cmd_submit(a.payload)
    return cmd_coverage()


if __name__ == "__main__":
    sys.exit(main())
