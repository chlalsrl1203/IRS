"""
§4 기준선 동결 (2026-08-16) — Growth Quality 연구 시작 전 production 상태 고정.

이 연구가 끝날 때까지 기존 공식 결과는 변경하지 않는다. 그 약속을 문서가 아니라
**해시**로 강제한다: 연구 도중 어떤 이유로든 34종목의 공식 수치가 바뀌면
`verify_baseline()`이 즉시 실패한다.

⚠️ 이 스크립트는 ledger를 **읽기만** 한다. 기준선 파일은 ledger의 파생물이며
ledger 자체를 대체하지 않는다.
"""
import glob
import hashlib
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import ENGINE_VERSION  # noqa: E402

BASELINE_PATH = "reports/baseline_frozen_2026-08-16.json"

# §4가 열거한 9개 항목. 순서를 바꾸면 해시가 바뀌므로 고정한다.
FIELDS = (
    "engine_version", "realistic_growth", "implied_growth", "expectation_gap",
    "judgment", "model_used", "n", "drs_score", "confidence",
)


def extract(ledger: dict) -> dict:
    ig = ledger["implied_growth"]
    conf = ledger["confidence"]
    return {
        "engine_version": ledger["meta"].get("engine_version"),
        "realistic_growth": ledger["growth"]["realistic_growth"],
        "implied_growth": ig.get("value"),
        "expectation_gap": ledger["expectation_gap"],
        "judgment": ledger["judgment"],
        "model_used": ig["model_used"],
        "n": ledger["discount_rate"]["n"],
        "drs_score": ledger["drs"]["score"],
        "confidence": conf["final"] if isinstance(conf, dict) else conf,
    }


def collect() -> dict:
    out = {}
    for p in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(p, encoding="utf-8"))
        out[led["meta"]["ticker"]] = extract(led)
    return out


def fingerprint(rows: dict) -> str:
    """티커·필드 순서를 고정한 정규형에서 SHA-256. 부동소수는 repr 그대로 쓴다."""
    canon = [[t] + [repr(rows[t][f]) for f in FIELDS] for t in sorted(rows)]
    return hashlib.sha256(
        json.dumps(canon, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_baseline(path: str = BASELINE_PATH) -> dict:
    """현재 ledger가 동결 시점과 동일한지 확인한다."""
    with open(path, encoding="utf-8") as f:
        frozen = json.load(f)
    now = collect()
    changed = [t for t in sorted(set(frozen["rows"]) | set(now))
               if frozen["rows"].get(t) != now.get(t)]
    actual = fingerprint(now)
    return {
        "match": actual == frozen["fingerprint"] and not changed,
        "expected": frozen["fingerprint"],
        "actual": actual,
        "changed_tickers": changed,
    }


def main():
    rows = collect()
    fp = fingerprint(rows)
    payload = {
        "frozen_at": "2026-08-16",
        "purpose": (
            "Growth Quality 연구(§4) 동안 production 결과를 변경하지 않는다는 약속을 "
            "해시로 강제한다. 이 값이 바뀌면 연구가 공식 결과를 오염시킨 것이다."
        ),
        "engine_version_at_freeze": ENGINE_VERSION,
        "fields": list(FIELDS),
        "n_tickers": len(rows),
        "fingerprint": fp,
        "rows": rows,
    }
    os.makedirs("reports", exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"동결 완료: {len(rows)}종목")
    print(f"  ENGINE_VERSION(동결시점): {ENGINE_VERSION}")
    print(f"  fingerprint: {fp}")
    print(f"  저장: {BASELINE_PATH}")
    print(f"  ledger 스탬프 분포: {dict(Counter(r['engine_version'] for r in rows.values()))}")
    print("    (ledger는 계산 시점 버전을 유지한다 - 소급 갱신하지 않는다)")


if __name__ == "__main__":
    main()
