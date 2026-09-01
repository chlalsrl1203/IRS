"""
broad_screen_post.py (2026-08-29) — broad_screen.py의 결과를 GitHub Issue로.

일일 스크리닝(daily_screen_ci.py)과 **별도 제목**을 쓴다 - 주 1회 전체 유니버스
결과를 매일 도는 이슈에 섞으면 알림 피로가 생기고, "오늘 급락한 종목"과 "전체
유니버스 구조적 저평가 후보"는 성격이 다른 정보라 분리해야 나중에 훑어보기도
쉽다. 2026-09-01부터 일일과 마찬가지로 **실행일마다 새 이슈**를 만들고 제목에
날짜와 긴급도를 박는다(scripts/issue_reporting.py).
"""
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports", "broad_screen")


def log(msg):
    print(msg, flush=True)


def latest_report():
    paths = sorted(glob.glob(os.path.join(REPORTS_DIR, "broad_screen_*.json")))
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def format_body(d):
    lines = [
        f"## {d['retrieved_at']} 대규모 스크리닝(Stage 1, SEC 전용)",
        "",
        f"원본 유니버스 **{d['universe_total']}종목** -> 이름 사전필터 후 "
        f"**{d['attempted']}종목** 시도 -> SEC 재무계산 성공 **{d['sec_ok']}종목** "
        f"-> 채점 **{d['scored']}종목** -> 통과 **{d['passed']}종목**",
        "",
        "⚠️ **1차 추정치일 뿐 정식 판정이 아니다.** 시가총액은 SEC "
        "`EntityPublicFloat`(10-K 표지, 계열주주 제외·최대 2년까지 낡을 수 "
        "있음) 근사치이고, 경쟁강도·마진변동성 등은 corpus 중앙값 가정이다 - "
        "`engine.deep_screen`/`run_analysis()`로 정밀 재확인 전에는 매수 "
        "판단에 쓰지 말 것.",
        "",
    ]
    passed = d.get("passed_tickers") or []
    in_scope = [r for r in passed if not r.get("out_of_validated_scope")]
    out_scope = [r for r in passed if r.get("out_of_validated_scope")]
    if passed:
        # ⚠️ 범위 밖을 같은 표에 섞지 않는다. 검증 코퍼스(34종목) 관측범위를
        # 벗어난 종목은 "틀렸다"가 아니라 **이 스크리너가 그 구간에서 맞는지
        # 확인된 적이 없다**는 뜻이라, 같이 정렬하면 Gap이 큰 초소형주가 늘
        # 맨 위에 온다(첫 실행에서 실제로 VATE +93%p/$0.03B가 1위였다).
        lines.append(f"### 검증범위 안 통과 후보 ({len(in_scope)}종목)")
        if in_scope:
            lines.append("| 종목 | 등급 | Gap(추정) | 시총(근사) | 비고 |")
            lines.append("|---|:--:|---:|---:|---|")
            for r in sorted(in_scope, key=lambda x: -x["expectation_gap_est"]):
                lines.append(
                    f"| **{r['ticker']}** | {r['tier']} "
                    f"| {r['expectation_gap_est'] * 100:+.2f}%p "
                    f"| ${r['market_cap'] / 1e9:.1f}B | {r.get('note', '')} |")
        else:
            lines.append("없음 - 통과 후보가 전부 검증범위 밖이다.")
        if out_scope:
            lines.append("")
            lines.append(
                f"<details><summary>검증범위 밖 통과 {len(out_scope)}종목 "
                f"(엔진이 이 구간에서 맞는지 **확인된 적이 없다** - "
                f"틀렸다는 뜻은 아니다)</summary>\n")
            for r in sorted(out_scope, key=lambda x: -x["expectation_gap_est"]):
                why = "; ".join(r["out_of_validated_scope"])
                lines.append(
                    f"- {r['ticker']} [{r['tier']}] "
                    f"{r['expectation_gap_est'] * 100:+.2f}%p · "
                    f"${r['market_cap'] / 1e9:.2f}B — {why}")
            lines.append("\n</details>")
    else:
        lines.append("**통과 후보 없음.**")

    lines.append("")
    lines.append("<details><summary>제외 사유 분포</summary>\n")
    for g in d.get("skip_breakdown", []):
        mark = "🔧 " if g.get("infra_failure") else ""
        shown = ", ".join(g["sample"])
        more = f" 외 {g['count'] - len(g['sample'])}종목" if g["count"] > len(g["sample"]) else ""
        lines.append(f"- {mark}{g['label']} — **{g['count']}종목**: {shown}{more}")
    lines.append("\n</details>")
    return "\n".join(lines)


def post(d):
    """
    실행일자 이슈에 결과를 올린다. 제목의 후보 수는 **검증범위 안**만 센다 -
    첫 전체 실행(2026-08-30)에서 통과 259종목 중 173종목이 코퍼스 관측범위
    밖이었고, 259를 제목에 적으면 알림만 보고는 실제로 볼 게 얼마인지 알 수 없다.
    """
    import issue_reporting as IR

    urgency, detail = IR.broad_urgency(d)
    return IR.report("broad", d["retrieved_at"], format_body(d),
                     urgency_key=urgency, detail=detail, log=log) is not None


def main():
    d = latest_report()
    if d is None:
        log("[broad_screen_post] reports/broad_screen/*.json이 없다 - 게시 건너뜀"
            "(broad_screen.py가 먼저 실행돼야 한다)")
        return
    post(d)


if __name__ == "__main__":
    main()
