"""
Snapshot (P0-09, 2026-08-19) — 원자료를 그때 모습 그대로 얼려둔다.

# SOURCE:
https://github.com/chenditc/investment_data  (Apache-2.0) — `qlib_bin.manifest.json`
버저닝/재현 아카이브

# CAPABILITY:
versioned dataset / manifest / 재현 가능한 원자료 아카이브

# IRS_TARGET:
engine/data/snapshot.py  (저장 위치 `snapshots/`)

# METHOD:
REIMPLEMENT — 원본은 릴리스 tarball + manifest이고 배포가 목적이다. IRS가 필요한
것은 배포가 아니라 **"그때 무엇을 봤는가"의 증거**라, 값 단위 해시와 매니페스트만
가져오고 아카이브 포맷은 옮기지 않았다.

# WHY — 이것이 없어서 막혀 있던 것들

이 저장소가 반복해서 "이건 스냅샷이 있어야 답할 수 있다"고 미뤄둔 항목들:

| 미뤄둔 곳 | 답하지 못한 질문 |
|---|---|
| `filing_dates.py` docstring | "그때 숫자가 이거였는가"(재작성 여부) |
| v3.49 PIT 감사 | 34종목을 `PIT_VALID`로 못 올린 유일한 이유 |
| `docs/change_plan.md` C-09 | Provenance를 DEFERRED로 둔 사유 |
| P0-02 `FinancialFact` | `version`·`restated_at`을 안 넣은 이유 |

전부 같은 전제조건 하나에 걸려 있다: **원자료를 조회 시점 그대로 보관해야 한다.**
지금 SEC를 다시 조회하면 재작성된 최신값이 오므로, 과거를 재현할 수 없다.

# TEST:
tests/test_snapshot.py

---

## ⚠️ 이 모듈이 **하지 않는** 것 — 소급 스냅샷

기존 34종목의 스냅샷을 지금 만들지 않는다. 오늘 조회한 값을 그때 값인 양
저장하면 **허위 증거**가 되며, 그건 이 저장소가 provenance(v3.50)에서 이미
같은 이유로 거부한 일이다. 스냅샷은 **오늘 이후 조회분부터** 쌓인다.

## 재작성 탐지가 작동하는 방식

같은 (엔티티, 지표, 회계연도)에 대해 스냅샷이 2개 이상 쌓이면 값을 비교한다.
값이 달라졌다면 그 사이에 재작성이 있었다는 뜻이고, `detect_restatements()`가
그 이력을 돌려준다. **한 번의 조회로는 알 수 없다** — 시간이 지나야 증거가 된다.
"""

import hashlib
import json
import os
from datetime import date

SNAPSHOT_DIR = "snapshots"


def content_hash(payload) -> str:
    """
    내용 해시. 같은 내용이면 같은 해시가 나와야 하므로 키를 정렬해 직렬화한다
    (`experiment_registry.core_hash`와 같은 발상 — 결과를 보고 조용히 고칠 수
    없게 만드는 것이 목적이다).
    """
    canon = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _path(entity: str, source_key: str, retrieved_at: str, base_dir) -> str:
    return os.path.join(base_dir, source_key, f"{entity}_{retrieved_at}.json")


def save_snapshot(result, base_dir: str = SNAPSHOT_DIR,
                  overwrite: bool = False) -> str:
    """
    `ProviderResult`를 스냅샷으로 저장한다.

    ⚠️ **같은 날짜에 내용이 다른 스냅샷을 조용히 덮어쓰지 않는다.** v3.46이
    `save_ledger()`에서 정확히 이 사고(같은 날 재실행이 1차 결과를 흔적 없이
    지움)를 잡아 고쳤고, 같은 규칙을 여기에도 건다. 내용이 같으면 통과시킨다 —
    "같은 입력으로 재실행해 값이 같은지 확인"이 이 저장소의 표준 검증 관행이다.
    """
    payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    entity = payload["entity"]
    source_key = payload["source_key"]
    retrieved_at = payload["retrieved_at"]

    body = {k: v for k, v in payload.items() if k != "retrieved_at"}
    record = {
        "snapshot_version": 1,
        "entity": entity, "source_key": source_key,
        "retrieved_at": retrieved_at,
        "content_hash": content_hash(body),
        "payload": payload,
    }

    path = _path(entity, source_key, retrieved_at, base_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not overwrite:
        old = json.load(open(path, encoding="utf-8"))
        if old.get("content_hash") != record["content_hash"]:
            raise FileExistsError(
                f"{path}에 내용이 다른 스냅샷이 이미 있다"
                f"(기존 {old.get('content_hash','')[:12]} vs 새 "
                f"{record['content_hash'][:12]}). 조용히 덮어쓰면 그날 무엇을 "
                f"봤는지가 흔적 없이 사라진다 — 의도한 갱신이면 overwrite=True를 "
                f"명시할 것."
            )
        return path                      # 동일 내용이면 그대로 통과

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return path


def load_snapshots(entity: str, source_key: str = None,
                   base_dir: str = SNAPSHOT_DIR) -> list:
    """해당 엔티티의 스냅샷을 조회일 오름차순으로."""
    import glob

    pattern = os.path.join(base_dir, source_key or "*", f"{entity}_*.json")
    out = []
    for p in sorted(glob.glob(pattern)):
        try:
            out.append(json.load(open(p, encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            # 깨진 스냅샷 하나가 전체 조회를 막지 않는다 — 다만 조용히 무시하지
            # 않도록 호출부가 개수를 비교할 수 있게 예외를 삼키기만 한다.
            continue
    return sorted(out, key=lambda r: r.get("retrieved_at", ""))


def detect_restatements(entity: str, source_key: str = None,
                        base_dir: str = SNAPSHOT_DIR) -> dict:
    """
    같은 (지표, 회계연도)의 값이 스냅샷 사이에 **바뀌었는지** 본다.

    ⚠️ 스냅샷이 1개뿐이면 **아무것도 말할 수 없다.** "재작성 없음"이 아니라
    "비교할 대상이 없음"이며, 둘을 구분하지 않으면 데이터 부재가 안전 신호로
    오독된다(이 저장소가 겹침 측정에서 이미 겪은 함정 — v3.37).
    """
    snaps = load_snapshots(entity, source_key, base_dir)
    if len(snaps) < 2:
        return {
            "entity": entity, "comparable": False, "n_snapshots": len(snaps),
            "restatements": [],
            "note": (
                "스냅샷이 2개 미만이라 **비교 자체가 불가능하다.** "
                "'재작성 없음'이 아니라 '알 수 없음'이다."
            ),
        }

    seen, changes = {}, []
    for snap in snaps:
        when = snap["retrieved_at"]
        for f in snap["payload"]["facts"]:
            key = (f["metric"], f["fiscal_year"])
            prev = seen.get(key)
            if prev is not None and prev["value"] != f["value"]:
                changes.append({
                    "metric": f["metric"], "fiscal_year": f["fiscal_year"],
                    "from_value": prev["value"], "from_retrieved_at": prev["when"],
                    "to_value": f["value"], "to_retrieved_at": when,
                    "rel_change": (
                        None if not prev["value"]
                        else (f["value"] - prev["value"]) / abs(prev["value"])
                    ),
                    "source": f["source"],
                })
            seen[key] = {"value": f["value"], "when": when}

    return {
        "entity": entity, "comparable": True, "n_snapshots": len(snaps),
        "window": [snaps[0]["retrieved_at"], snaps[-1]["retrieved_at"]],
        "restatements": changes,
        "note": (
            "값이 바뀌었다는 것은 재작성 또는 출처의 태그·정의 변경을 뜻한다. "
            "어느 쪽인지는 이 함수가 판정하지 않는다 — 공시 원문을 확인할 것."
        ),
    }


def write_manifest(base_dir: str = SNAPSHOT_DIR, today: str = None) -> str:
    """
    스냅샷 전체 목록 + 해시 매니페스트. 아카이브가 나중에 손상·변조됐는지
    확인할 수 있게 한다(원본 저장소의 `qlib_bin.manifest.json`과 같은 목적).
    """
    import glob

    rows = []
    for p in sorted(glob.glob(os.path.join(base_dir, "*", "*.json"))):
        if os.path.basename(p) == "manifest.json":
            continue
        r = json.load(open(p, encoding="utf-8"))
        rows.append({
            "path": os.path.relpath(p, base_dir),
            "entity": r["entity"], "source_key": r["source_key"],
            "retrieved_at": r["retrieved_at"], "content_hash": r["content_hash"],
            "n_facts": len(r["payload"].get("facts", [])),
        })
    manifest = {
        "generated_at": today or date.today().isoformat(),
        "n_snapshots": len(rows),
        "entities": sorted({r["entity"] for r in rows}),
        "snapshots": rows,
        "note": (
            "⚠️ 기존 34종목에는 스냅샷이 없다. 소급 생성하지 않는다 — 오늘 조회한 "
            "값을 그때 값인 양 저장하면 허위 증거가 된다(provenance v3.50과 동일 판단). "
            "스냅샷은 오늘 이후 조회분부터 쌓인다."
        ),
    }
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return path
