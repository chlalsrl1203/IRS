"""
PHASE 2 — 미검증 가정 자본 노출 감사: 사이징 구간 (2026-08-21)

## 왜 이 구간인가

자본 배분 경로는 다음과 같다.

    ledger(Gap) -> portfolio_ranking(등급) -> build_buylist(유니버스 S/A) -> **비중**

앞의 세 구간은 반복해서 감사됐다(ablation_analysis: DRS 3%·구조적할인 12%·
모델선택 32% / R-001 6축 / RQ-002·PHASE 1 SBC). 그런데 **마지막 구간
(유니버스 -> 비중)은 한 번도 감사된 적이 없다.**

그 구간을 결정하는 것은 `build_buylist_2026_08_03.py`의 상수 8개다:

| 상수 | 값 | 근거 |
|---|---|---|
| `NOMINAL_BUCKET_TARGET` | 40/30/20/10% | 없음 |
| `BUCKET` | 종목->버킷 수작업 매핑 | 분석자 판단 |
| `PER_STOCK_CAP` | 12% | 없음 |
| `MIN_BUCKET_TARGET_ACHIEVEMENT` | 90% | 사용자 지정 |
| `CONFIDENCE_ADJ` | 종목별 45~87 | 정성조사(주관) |
| `quality_score` 형태 | `Gap%p x Conf/100` | 없음 |
| 캡바인딩 패널티 | x0.85 | 없음 |
| `SEVERE_FLAG`/`THESIS_BROKEN_FLAG` | 각 x0.85 | 없음 |

**이 여덟 개가 비중 100%를 결정한다.** 어느 것도 실현 성과로 검증된 적이 없다.

## 이 스크립트가 하는 일 / 하지 않는 일

**한다**: 각 가정을 하나씩 절제(ablation)해 비중이 얼마나 움직이는지 잰다.
`build_buylist`의 `main()`을 그대로 호출하고 **상수만 바꿔치기**한다 —
사이징 로직을 재구현하면 두 계산이 어긋난다(Simplicity First).

**하지 않는다**: 어떤 사이징이 옳은지 판정하지 않는다. 공식 비중을 바꾸지
않는다(실행 후 원본 산출물을 복원하고 동일함을 확인한다). 새 스코어를
만들지 않는다.

## 지표

- `turnover` = Σ|Δw| / 2 — 이 가정 하나를 바꿨을 때 실제로 옮겨야 하는 자본 비율
- `max_shift` — 단일 종목 최대 변화
- `universe_changed` — 편입 종목 집합이 바뀌는가(사이징 절제는 보통 안 바뀐다)
"""
import contextlib
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.build_buylist_2026_08_03 as BL  # noqa: E402

OUTPUTS = ("reports/buylist_2026-08-03.json",
           "reports/buylist_boundary_review_2026-08-16.json")
BACKUP_SUFFIX = ".phase2bak"


def _run_quiet():
    """main()을 조용히 실행하고 rows를 돌려준다."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return BL.main()


def _weights(rows):
    return {r["ticker"]: r["weight_final"] for r in rows}


def _compare(base, alt):
    # 정렬된 순서로 순회한다 - `set(base) | set(alt)`는 문자열 해시가
    # 프로세스마다 랜덤화(PYTHONHASHSEED)되어 순회 순서가 실행마다 달라지고,
    # 그 결과 아래 `sum()`의 덧셈 순서가 바뀌어 turnover가 말단자리에서
    # 매번 다른 값(1e-17 수준 ULP 노이즈)을 내고 있었다 - 실행마다 리포트가
    # 미세하게 달라 커밋 노이즈를 반복 유발한 원인.
    tickers = sorted(set(base) | set(alt))
    shifts = {t: alt.get(t, 0.0) - base.get(t, 0.0) for t in tickers}
    return {
        "turnover": sum(abs(v) for v in shifts.values()) / 2,
        "max_shift": max(shifts.values(), key=abs) if shifts else 0.0,
        "max_shift_ticker": max(shifts, key=lambda t: abs(shifts[t])) if shifts else None,
        "universe_changed": set(base) != set(alt),
        "shifts": {t: v for t, v in sorted(shifts.items(), key=lambda kv: -abs(kv[1]))
                   if abs(v) > 1e-9},
    }


# ── 절제 시나리오 ────────────────────────────────────────────────────────
# 각 항목: (id, 설명, 무엇이 미검증인가, 적용 함수)
def _ablations(base_rows):
    orig = {
        "NOMINAL_BUCKET_TARGET": dict(BL.NOMINAL_BUCKET_TARGET),
        "CONFIDENCE_ADJ": dict(BL.CONFIDENCE_ADJ),
        "PER_STOCK_CAP": BL.PER_STOCK_CAP,
        "MIN_BUCKET_TARGET_ACHIEVEMENT": BL.MIN_BUCKET_TARGET_ACHIEVEMENT,
        "SEVERE_FLAG": set(BL.SEVERE_FLAG),
        "THESIS_BROKEN_FLAG": set(BL.THESIS_BROKEN_FLAG),
        "BUCKET": dict(BL.BUCKET),
        "effective_bucket_targets": BL.effective_bucket_targets,
    }

    def restore():
        BL.NOMINAL_BUCKET_TARGET = dict(orig["NOMINAL_BUCKET_TARGET"])
        BL.CONFIDENCE_ADJ = dict(orig["CONFIDENCE_ADJ"])
        BL.PER_STOCK_CAP = orig["PER_STOCK_CAP"]
        BL.MIN_BUCKET_TARGET_ACHIEVEMENT = orig["MIN_BUCKET_TARGET_ACHIEVEMENT"]
        BL.SEVERE_FLAG = set(orig["SEVERE_FLAG"])
        BL.THESIS_BROKEN_FLAG = set(orig["THESIS_BROKEN_FLAG"])
        BL.BUCKET = dict(orig["BUCKET"])
        BL.effective_bucket_targets = orig["effective_bucket_targets"]

    def conf_to_engine():
        """CONFIDENCE_ADJ를 엔진 원값으로 -> 정성조사 반영을 통째로 제거."""
        eng = {r["ticker"]: r["confidence"] for r in json.load(
            open("reports/portfolio_ranking_2026-08-02.json", encoding="utf-8"))}
        BL.CONFIDENCE_ADJ = {
            t: (eng.get(t, v[0]), "엔진원값(절제)", "ablation")
            for t, v in orig["CONFIDENCE_ADJ"].items()}

    def conf_flat():
        """Confidence를 전부 동일값으로 -> quality_score에서 Confidence 축 제거."""
        BL.CONFIDENCE_ADJ = {t: (100, "균등(절제)", "ablation")
                             for t in orig["CONFIDENCE_ADJ"]}

    def buckets_neutral(base_rows=None):
        """
        버킷 분산 강제 제거 - 버킷 목표를 각 버킷의 quality_score 합 비율로 둔다.

        ⚠️ `BUCKET` 매핑 자체를 `{t: "all"}`로 바꾸는 방식은 쓸 수 없다 -
        `build_buylist`의 진단 출력이 `bucket_count['growth_platform']`을
        하드코딩 참조해 KeyError가 난다(실측 확인). 버킷 **이름은 유지**하고
        목표비중만 중립화하면 캡·바닥이 안 걸리는 한 전역 quality 비례와 같다.
        """
        qsum = {}
        for r in base_rows:
            qsum[r["bucket"]] = qsum.get(r["bucket"], 0.0) + r["quality_score"]
        total = sum(qsum.values())
        BL.NOMINAL_BUCKET_TARGET = {k: v / total for k, v in qsum.items()}

    def buckets_equal():
        """버킷 목표를 균등으로 -> 40/30/20/10이라는 특정 숫자의 영향만 분리."""
        n = len(orig["NOMINAL_BUCKET_TARGET"])
        BL.NOMINAL_BUCKET_TARGET = {k: 1.0 / n for k in orig["NOMINAL_BUCKET_TARGET"]}

    def no_cap():
        BL.PER_STOCK_CAP = 1.0

    def no_floor():
        """
        버킷 달성률 바닥 제거.

        ⚠️ **모듈 상수만 바꾸면 이 절제는 조용히 무력화된다** - 실측으로 확인했다.
        `effective_bucket_targets(min_achievement=MIN_BUCKET_TARGET_ACHIEVEMENT)`의
        기본 인자는 **함수 정의 시점**에 0.90으로 바인딩되므로, 나중에
        `BL.MIN_BUCKET_TARGET_ACHIEVEMENT = 0.0`을 대입해도 호출부는 여전히
        0.90을 쓴다. 초판이 정확히 이 함정에 걸려 turnover 0.00%를 냈고,
        그건 "바닥이 무해하다"가 아니라 "절제가 적용되지 않았다"는 뜻이었다
        (R-001에서 fcf0 축 키 오타로 한 축이 조용히 죽어 있던 것과 같은 유형).

        그래서 상수가 아니라 **함수 자체를 래핑**한다.
        """
        BL.MIN_BUCKET_TARGET_ACHIEVEMENT = 0.0
        base_fn = orig["effective_bucket_targets"]
        BL.effective_bucket_targets = (
            lambda counts, targets, cap, min_achievement=0.0:
            base_fn(counts, targets, cap, 0.0))

    def no_penalty():
        BL.SEVERE_FLAG = set()
        BL.THESIS_BROKEN_FLAG = set()

    return restore, [
        ("conf_qualitative_removed",
         "CONFIDENCE_ADJ를 엔진 원값으로 (정성조사 반영 제거)",
         "정성조사 Confidence 조정 - 주관적 입력, 실현결과로 보정된 적 없음",
         conf_to_engine),
        ("conf_axis_removed",
         "Confidence를 전부 100으로 (quality_score에서 Confidence 축 제거)",
         "quality_score = Gap x Conf 라는 곱셈 형태 자체가 임의",
         conf_flat),
        ("bucket_diversification_removed",
         "버킷 분산 강제 제거 (목표를 quality 비율로 중립화)",
         "BUCKET 매핑 + 목표비중 - 근거 없는 수작업 분류",
         buckets_neutral),
        ("bucket_targets_equalized",
         "버킷 목표를 균등으로 (40/30/20/10 -> 25/25/25/25)",
         "NOMINAL_BUCKET_TARGET 40/30/20/10 - 근거 없음",
         buckets_equal),
        ("per_stock_cap_removed",
         "종목당 상한 제거 (12% -> 무제한)",
         "PER_STOCK_CAP 12% - 근거 없음",
         no_cap),
        ("bucket_floor_removed",
         "버킷 달성률 바닥 제거 (90% -> 0%)",
         "MIN_BUCKET_TARGET_ACHIEVEMENT 90% - 사용자 지정값",
         no_floor),
        ("flag_penalties_removed",
         "SEVERE/THESIS_BROKEN 패널티 제거 (각 x0.85)",
         "0.85라는 배수에 근거 없음",
         no_penalty),
    ]


def main():
    for p in OUTPUTS:
        shutil.copyfile(p, p + BACKUP_SUFFIX)
    try:
        base_rows = _run_quiet()
        base = _weights(base_rows)
        restore, cases = _ablations(base_rows)

        results = []
        for cid, desc, why, apply in cases:
            restore()
            apply(base_rows) if cid == "bucket_diversification_removed" else apply()
            alt = _weights(_run_quiet())
            cmp = _compare(base, alt)
            results.append({"id": cid, "description": desc,
                            "unvalidated_assumption": why, **cmp})
        restore()
    finally:
        # 공식 산출물을 원복한다 - 절제 실행이 실제 매수리스트를 덮어쓰면 안 된다.
        for p in OUTPUTS:
            shutil.move(p + BACKUP_SUFFIX, p)

    results.sort(key=lambda r: -r["turnover"])
    print("사이징 구간 미검증 가정 — 절제 시 자본 이동량 (turnover = Σ|Δw|/2)\n")
    hdr = f"{'가정':34} {'turnover':>9} {'최대이동':>10} {'유니버스':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['id']:34} {r['turnover'] * 100:8.2f}% "
              f"{r['max_shift'] * 100:+8.2f}%p({r['max_shift_ticker']:4}) "
              f"{'변경' if r['universe_changed'] else '불변':>8}")

    print("\n상위 3건 종목별 이동:")
    for r in results[:3]:
        top = list(r["shifts"].items())[:5]
        print(f"  [{r['id']}]")
        for t, v in top:
            print(f"     {t:6} {v * 100:+6.2f}%p")

    out = {
        "generated_at": "2026-08-21",
        "phase": "PHASE 2 — unvalidated assumption capital exposure (sizing segment)",
        "affects_official_judgment": False,
        "scope": ("유니버스->비중 구간. Gap 이전 구간(DRS·구조적할인·모델선택·SBC)은 "
                  "기존 감사 결과를 재사용하며 여기서 재계산하지 않는다."),
        "not_a_proposal": "어떤 사이징이 옳은지 판정하지 않는다. 노출 측정일 뿐이다.",
        "base_weights": base,
        "results": results,
    }
    path = "reports/sizing_assumption_exposure_2026-08-21.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
