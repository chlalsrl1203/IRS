/* IRS 발전 방향 — 전략 발표자료
   모든 수치는 2026-08-27 저장소 실측값이다(추정치를 쓰지 않는다). */
const pptxgen = require("pptxgenjs");

const INK   = "0B2239";
const NAVY  = "12395C";
const BLUE  = "2E6FA3";
const TEAL  = "0E7C86";
const GREEN = "2F7D5D";
const RED   = "9B3A32";
const AMBER = "9A6B2F";
const SLATE = "55636F";
const MUTE  = "8A98A5";
const LINE  = "CBD5DF";
const PANEL = "F4F7FA";
const W     = "FFFFFF";
const PALE  = "DCE7F0";

const F = "Malgun Gothic";     // 한글 업무문서 표준. 한글에 이탤릭은 쓰지 않는다.

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "IRS";
pres.title = "IRS 발전 방향";

const M = 0.55;
const FULL = 13.33 - 2 * M;
const TOTAL = 13;
let page = 0;

/* ── 공통 ─────────────────────────────────────────────────────────────── */
function slide(title, sub, kicker) {
  const s = pres.addSlide();
  s.background = { color: W };
  page += 1;
  if (kicker) {
    s.addText(kicker, {
      x: M, y: 0.32, w: FULL, h: 0.20, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9, bold: true, color: TEAL, charSpacing: 1.2,
    });
  }
  s.addText(title, {
    x: M, y: kicker ? 0.56 : 0.34, w: FULL, h: 0.46, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 22, bold: true, color: INK,
  });
  if (sub) {
    s.addText(sub, {
      x: M, y: kicker ? 1.06 : 0.86, w: FULL, h: 0.26, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 11, color: SLATE,
    });
  }
  s.addText("IRS · 발전 방향", {
    x: M, y: 7.06, w: 5, h: 0.20, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 8, color: MUTE,
  });
  s.addText(`${page} / ${TOTAL}`, {
    x: 13.33 - M - 1.2, y: 7.06, w: 1.2, h: 0.20, isTextBox: true, margin: 0,
    align: "right", fontFace: F, fontSize: 8, color: MUTE,
  });
  return s;
}

function card(s, x, y, w, h, opt = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.05,
    fill: { color: opt.fill || W },
    line: { color: opt.border || LINE, width: 1,
            ...(opt.dash ? { dashType: "dash" } : {}) },
  });
}

function stat(s, x, y, w, value, label, note, color) {
  s.addText(value, {
    x, y, w, h: 0.52, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 30, bold: true, color: color || INK,
  });
  s.addText(label, {
    x, y: y + 0.54, w, h: 0.22, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, bold: true, color: INK,
  });
  if (note) s.addText(note, {
    x, y: y + 0.76, w, h: 0.36, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 8.5, color: SLATE, lineSpacing: 11,
  });
}

/* ════════ 1 표지 ════════ */
const c = pres.addSlide();
c.background = { color: INK };
c.addText("IRS 발전 방향", {
  x: 1.0, y: 2.35, w: 11, h: 0.9, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 40, bold: true, color: W,
});
c.addText("분석을 더 얹기 전에, 판단과 결과를 잇는 루프를 닫는다", {
  x: 1.0, y: 3.32, w: 11, h: 0.4, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 15, color: PALE,
});
c.addText("투자 리서치 운영체계 · 전략 방향 보고", {
  x: 1.0, y: 4.05, w: 11, h: 0.3, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, color: "8FA8BC",
});
[["엔진 버전", "v3.71"], ["분석 종목", "34"], ["회귀 테스트", "917"],
 ["기준일", "2026-08-27"]].forEach(([k, v], i) => {
  const x = 1.0 + i * 2.35;
  c.addText(k, { x, y: 5.55, w: 2.1, h: 0.20, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 8.5, color: "7E93A6" });
  c.addText(v, { x, y: 5.76, w: 2.1, h: 0.30, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 15, bold: true, color: W });
});
c.addNotes("이 보고의 결론은 하나다 — 지금 필요한 것은 더 정교한 분석이 아니라 검증 루프다.");
page = 1;

/* ════════ 2 핵심 요약 ════════ */
const s2 = slide("핵심 요약",
  "이 보고가 주장하는 것은 세 가지다", "EXECUTIVE SUMMARY");

const SUM = [
  ["01", "인프라는 완성 단계에 있다",
   "29일간 35개 모듈 · 917 회귀 테스트 · 34종목 분석. 계산 재현성은 34/34 완전 일치.",
   "계산이 자기 자신과 일치하는가 — 이 질문에는 충분히 답할 수 있다.", TEAL],
  ["02", "그러나 검증 루프가 열려 있다",
   "예측 34건을 동결했으나 해소 0건. 투자 논거 기록 0건. 실험 9건 중 5건이 데이터 부재로 차단.",
   "판단이 현실과 맞았는가 — 이 질문에는 아직 한 건도 답하지 못했다.", RED],
  ["03", "따라서 다음 투자는 분석이 아니라 기록·관측이다",
   "실측상 정밀화 여지가 큰 축은 이미 드러나 있고, 자본을 실제로 움직이는 것은 그 축이 아니었다.",
   "분석 심화는 루프를 닫은 뒤에 해도 늦지 않다.", NAVY],
];
SUM.forEach(([n, t, d, k, col], i) => {
  const y = 1.58 + i * 1.56;
  card(s2, M, y, FULL, 1.38);
  s2.addShape(pres.ShapeType.roundRect, {
    x: M + 0.30, y: y + 0.30, w: 0.52, h: 0.52, rectRadius: 0.06,
    fill: { color: col }, line: { color: col, width: 1 },
  });
  s2.addText(n, { x: M + 0.30, y: y + 0.30, w: 0.52, h: 0.52, isTextBox: true,
    margin: 0, align: "center", valign: "middle", fontFace: F, fontSize: 13,
    bold: true, color: W });
  s2.addText(t, { x: M + 1.02, y: y + 0.22, w: FULL - 1.35, h: 0.32,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 14.5, bold: true, color: INK });
  s2.addText(d, { x: M + 1.02, y: y + 0.58, w: FULL - 1.35, h: 0.26,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 10, color: SLATE });
  s2.addText(k, { x: M + 1.02, y: y + 0.88, w: FULL - 1.35, h: 0.26,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 10, bold: true, color: col });
});
s2.addShape(pres.ShapeType.roundRect, {
  x: M, y: 6.30, w: FULL, h: 0.58, rectRadius: 0.05,
  fill: { color: INK }, line: { color: INK, width: 1 } });
s2.addText("한 문장으로 —  지금 필요한 것은 더 정교한 분석이 아니라, 판단이 맞았는지 알 수 있는 상태다.", {
  x: M + 0.36, y: 6.30, w: FULL - 0.72, h: 0.58, isTextBox: true, margin: 0,
  valign: "middle", fontFace: F, fontSize: 12, bold: true, color: W });
s2.addNotes("02가 이 보고의 핵심이다. 01은 자랑이 아니라 02를 말하기 위한 전제다.");

/* ════════ 3 현재 위치 ════════ */
const s3 = slide("현재 위치 — 29일간 무엇을 만들었는가",
  "2026-07-25 최초 분석 이후 누적 실측치", "현황");

const STATS = [
  ["35", "엔진 모듈", "밸류에이션 · 스크리닝 · 감시 · 검증"],
  ["917", "회귀 테스트", "모든 커밋에서 자동 실행"],
  ["34", "분석 종목", "재현용 원장 보관"],
  ["127", "커밋", "전 과정 감사 추적 가능"],
];
STATS.forEach(([v, l, n], i) => {
  const w = (FULL - 0.36 * 3) / 4;
  stat(s3, M + i * (w + 0.36), 1.66, w, v, l, n);
});

card(s3, M, 3.30, FULL, 1.62, { fill: PANEL, border: PANEL });
s3.addText("자동으로 매일 실행되는 것", {
  x: M + 0.32, y: 3.48, w: 4.2, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK });
const AUTO = ["평일 09:00 자동 기동", "후보 선별 파이프라인", "SEC 원자료 검증",
  "심층 스크리닝 스냅샷", "관심종목 감시"];
AUTO.forEach((t, i) => {
  const w = (FULL - 0.64 - 0.20 * 4) / 5;
  const x = M + 0.32 + i * (w + 0.20);
  card(s3, x, 3.86, w, 0.62);
  s3.addText(t, { x, y: 3.86, w, h: 0.62, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: F, fontSize: 9.5, color: NAVY });
});

card(s3, M, 5.14, FULL, 1.68, { border: LINE, dash: true });
s3.addText("아직 한 번도 운영되지 않은 것", {
  x: M + 0.32, y: 5.32, w: 5.0, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: RED });
const IDLE = [["투자 논거 기록", "0건"], ["예측 해소", "0건"],
  ["실현 수익률 관측", "0건"], ["시점 검증 완료 분석", "3 / 34"],
  ["진입가 기록", "9 / 34"]];
IDLE.forEach(([t, v], i) => {
  const w = (FULL - 0.64 - 0.20 * 4) / 5;
  const x = M + 0.32 + i * (w + 0.20);
  s3.addText(v, { x, y: 5.66, w, h: 0.36, isTextBox: true, margin: 0,
    align: "center", fontFace: F, fontSize: 19, bold: true, color: RED });
  s3.addText(t, { x, y: 6.06, w, h: 0.24, isTextBox: true, margin: 0,
    align: "center", fontFace: F, fontSize: 9.5, color: SLATE });
});
s3.addText("이 다섯 항목은 기능이 없어서가 아니라, 기능은 있는데 채워진 적이 없어서 0이다.", {
  x: M + 0.32, y: 6.42, w: FULL - 0.64, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 9, color: SLATE });
s3.addNotes("윗줄과 아랫줄의 대비가 이 보고 전체의 출발점이다.");

/* ════════ 4 신뢰도 분해 ════════ */
const s4 = slide("신뢰도는 하나의 숫자가 아니다",
  "축별로 나누면 강한 곳과 빈 곳이 분명히 갈린다", "진단");

const AXES = [
  ["계산 재현성", "34 / 34", 100, TEAL,
   "저장된 입력으로 재실행 시 8개 핵심지표 완전 일치", "검증됨"],
  ["입력 대 1차자료 일치", "84.0%", 84, TEAL,
   "34종목 1,256개 값을 SEC 원자료와 대조 · 불일치 원인 전수 분류", "검증됨"],
  ["가정 강건성", "13 / 34", 38, AMBER,
   "정당화 가능한 가정 격자에서 판정이 유지되는 종목 비율", "부분 검증"],
  ["투자 성과", "0 건", 0, RED,
   "실현 수익률 관측 자체가 없다 — 측정을 시작한 적이 없다", "미검증"],
];
AXES.forEach(([name, val, pct, col, desc, tagTxt], i) => {
  const y = 1.62 + i * 1.28;
  card(s4, M, y, FULL, 1.10);
  s4.addText(name, { x: M + 0.30, y: y + 0.18, w: 3.1, h: 0.28, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 12.5, bold: true, color: INK });
  s4.addText(desc, { x: M + 0.30, y: y + 0.52, w: 5.6, h: 0.40, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 9, color: SLATE, lineSpacing: 11 });

  const bx = M + 6.30, bw = 3.85;
  s4.addShape(pres.ShapeType.roundRect, {
    x: bx, y: y + 0.42, w: bw, h: 0.26, rectRadius: 0.03,
    fill: { color: "E8EDF2" }, line: { color: "E8EDF2", width: 0.5 } });
  if (pct > 0) {
    s4.addShape(pres.ShapeType.roundRect, {
      x: bx, y: y + 0.42, w: Math.max(bw * pct / 100, 0.12), h: 0.26,
      rectRadius: 0.03, fill: { color: col }, line: { color: col, width: 0.5 } });
  }
  s4.addText(val, { x: bx + bw + 0.22, y: y + 0.36, w: 1.35, h: 0.36,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: col });
  s4.addText(tagTxt, { x: M + FULL - 1.35, y: y + 0.42, w: 1.05, h: 0.26,
    isTextBox: true, margin: 0, align: "right", valign: "middle",
    fontFace: F, fontSize: 9, bold: true, color: col });
});
s4.addText("⚠  네 축은 곱해지지 않는다.  앞의 세 축이 아무리 높아도 마지막 축을 대신하지 못한다 — 서로 다른 질문에 답하기 때문이다.", {
  x: M, y: 6.62, w: FULL, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, bold: true, color: INK });
s4.addNotes("단일 신뢰도 점수를 만들지 않는 이유 — 공백이 평균 뒤에 숨는다.");

/* ════════ 5 핵심 문제 ════════ */
const s5 = slide("핵심 문제 — 루프의 절반만 닫혀 있다",
  "발굴에서 판단까지는 돌아가지만, 판단에서 학습으로 돌아오지 않는다", "문제 정의");

const CLOSED = ["발굴", "조사", "판단"];
const OPEN = ["결과 관측", "오류 귀속", "체계 개선"];
// 6개 박스 + 그룹 간 분리 간격이 슬라이드 폭 안에 들어오도록 계산한다.
// 초판(bw2=1.72, bg=0.42)은 마지막 박스 우측이 13.52로 슬라이드(13.33)를 넘쳤다.
const bw2 = 1.67, bg = 0.34, SEP = 0.84;
const rowY = 2.20;
const g1End = M + 2 * (bw2 + bg) + bw2;          // 첫 그룹 우측 끝
const openX = g1End + SEP;                        // 둘째 그룹 시작

s5.addText("작동 중", { x: M, y: 1.72, w: 2.0, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10, bold: true, color: TEAL });
CLOSED.forEach((t, i) => {
  const x = M + i * (bw2 + bg);
  card(s5, x, rowY, bw2, 0.78, { border: TEAL });
  s5.addText(t, { x, y: rowY, w: bw2, h: 0.78, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: F, fontSize: 12.5, bold: true, color: NAVY });
  if (i < 2) s5.addShape(pres.ShapeType.line, {
    x: x + bw2 + 0.05, y: rowY + 0.39, w: bg - 0.10, h: 0,
    line: { color: TEAL, width: 1.5, endArrowType: "triangle" } });
});

s5.addText("멈춰 있음", { x: openX, y: 1.72, w: 2.0, h: 0.24, isTextBox: true,
  margin: 0, fontFace: F, fontSize: 10, bold: true, color: RED });
OPEN.forEach((t, i) => {
  const x = openX + i * (bw2 + bg);
  card(s5, x, rowY, bw2, 0.78, { border: LINE, dash: true, fill: PANEL });
  s5.addText(t, { x, y: rowY, w: bw2, h: 0.78, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: F, fontSize: 12.5, bold: true, color: MUTE });
  if (i < 2) s5.addShape(pres.ShapeType.line, {
    x: x + bw2 + 0.05, y: rowY + 0.39, w: bg - 0.10, h: 0,
    line: { color: LINE, width: 1.5, dashType: "dash", endArrowType: "triangle" } });
});
s5.addShape(pres.ShapeType.line, {
  x: g1End + 0.14, y: rowY + 0.39, w: SEP - 0.28, h: 0,
  line: { color: RED, width: 2, dashType: "dash", endArrowType: "triangle" } });
s5.addText("단절", { x: g1End + SEP / 2 - 0.50, y: rowY + 0.86, w: 1.0, h: 0.22,
  isTextBox: true, margin: 0, align: "center", fontFace: F, fontSize: 9,
  bold: true, color: RED });

card(s5, M, 3.42, FULL, 1.30, { fill: PANEL, border: PANEL });
s5.addText("이 단절이 만드는 실제 결과", {
  x: M + 0.32, y: 3.58, w: 5, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK });
s5.addText([
  { text: "· 판단이 맞았는지 틀렸는지 알 수 없으므로, 잘못된 가정이 교정되지 않고 계속 쓰인다", options: { breakLine: true } },
  { text: "· 무엇을 개선해야 성과가 좋아지는지 알 수 없으므로, 개선 우선순위가 직관에 의존한다", options: { breakLine: true } },
  { text: "· 시간이 지나도 축적되는 것이 코드뿐이고, 판단 능력은 축적되지 않는다", options: {} },
], { x: M + 0.32, y: 3.90, w: FULL - 0.64, h: 0.76, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, color: SLATE, lineSpacing: 15 });

card(s5, M, 4.94, FULL, 1.88, { border: INK });
s5.addText("루프를 닫는다는 것의 정확한 의미", {
  x: M + 0.32, y: 5.12, w: 6, h: 0.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11.5, bold: true, color: INK });
const MEAN = [
  ["판단 시점에", "무엇을 믿었는지 · 어떤 조건이면 틀린 것인지 기록한다"],
  ["기한이 오면", "그 조건이 실제로 발동했는지 확인하고 결과를 남긴다"],
  ["차이가 나면", "성장 · 마진 · 산업 · 경영진 · 밸류에이션 · 데이터 중 어디서 틀렸는지 귀속한다"],
];
MEAN.forEach(([k, v], i) => {
  const y = 5.48 + i * 0.42;
  s5.addText(k, { x: M + 0.32, y, w: 1.55, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, bold: true, color: NAVY });
  s5.addText(v, { x: M + 1.95, y, w: FULL - 2.30, h: 0.28, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10.5, color: SLATE });
});
s5.addNotes("루프를 닫는 것은 새 기능이 아니라 기록 습관의 문제다.");

/* ════════ 6 근거 ① ════════ */
const s6 = slide("근거 ① 무엇이 판정을 좌우하는가",
  "가정을 하나씩 흔들어 34종목의 판정이 뒤집히는 횟수를 측정했다", "실측 근거");

s6.addChart(pres.ChartType.bar, [{
  name: "판정이 뒤집힌 종목 수",
  labels: ["모델 선택", "할인율", "터미널 성장률", "위험점수(DRS) 전체"],
  values: [11, 6, 2, 1],
}], {
  x: M, y: 1.66, w: 7.30, h: 2.90,
  barDir: "bar", barGrouping: "clustered",
  chartColors: [NAVY],
  showTitle: true, title: "단독 가정 하나만 바꿨을 때 판정이 뒤집힌 종목 수 (n = 34)",
  titleFontSize: 11, titleColor: INK, titleFontFace: F,
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK,
  dataLabelFontSize: 11, dataLabelFontBold: true, dataLabelFontFace: F,
  catAxisLabelColor: SLATE, catAxisLabelFontSize: 10.5, catAxisLabelFontFace: F,
  valAxisLabelColor: MUTE, valAxisLabelFontSize: 9, valAxisLabelFontFace: F,
  valAxisMinVal: 0, valAxisMaxVal: 14, valGridLine: { color: "E8EDF2", size: 1 },
  catGridLine: { style: "none" }, showLegend: false,
});

const R1 = [
  ["32%", "모델 선택 하나로 판정이 뒤집히는 종목 비율", RED],
  ["3%", "위험점수를 정의역 전체로 흔들어도 뒤집히는 비율", TEAL],
  ["+0.850", "Gap과 현실적 성장률의 순위상관 — 순위를 지배하는 축", NAVY],
];
R1.forEach(([v, t, col], i) => {
  const y = 1.72 + i * 1.00;
  card(s6, M + 7.70, y, FULL - 7.70, 0.86);
  s6.addText(v, { x: M + 7.94, y: y + 0.10, w: 1.5, h: 0.36, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 17, bold: true, color: col });
  s6.addText(t, { x: M + 7.94, y: y + 0.48, w: FULL - 8.20, h: 0.32, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 9, color: SLATE, lineSpacing: 11 });
});

card(s6, M, 4.86, FULL, 1.86, { fill: PANEL, border: PANEL });
s6.addText("해석", { x: M + 0.32, y: 5.04, w: 3, h: 0.24, isTextBox: true,
  margin: 0, fontFace: F, fontSize: 11, bold: true, color: INK });
s6.addText([
  { text: "정밀화의 우선순위가 실제 영향력과 어긋나 있었다.", options: { bold: true, breakLine: true } },
  { text: "위험점수(DRS)는 다섯 개 구성요소와 여러 차례의 정성 조사가 투입된 축이지만, 정의역 전체를 흔들어도 판정은 34종목 중 1건만 바뀐다. 반대로 모델 선택은 분석자가 자유서술 근거만 남기고 고르는 항목인데 32%를 뒤집는다.", options: { breakLine: true } },
  { text: "→ 다음 개선은 지표를 더 얹는 쪽이 아니라, 가장 큰 축(성장률 가정과 모델 선택)이 현실과 맞았는지 확인하는 쪽이어야 한다.", options: { bold: true } },
], { x: M + 0.32, y: 5.34, w: FULL - 0.64, h: 1.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, color: SLATE, lineSpacing: 15 });
s6.addNotes("이 슬라이드는 '분석을 더 정교하게'라는 직관을 실측으로 반박한다.");

/* ════════ 7 근거 ② ════════ */
const s7 = slide("근거 ② 무엇이 자본을 좌우하는가",
  "매수 비중을 정하는 가정을 하나씩 제거해 옮겨야 하는 자본의 양을 측정했다", "실측 근거");

s7.addChart(pres.ChartType.bar, [{
  name: "자본 이동량",
  labels: ["버킷 분산 강제", "버킷 목표 비중", "버킷 달성률 바닥",
    "종목당 상한", "신뢰도 축", "정성 심층조사 반영", "리스크 플래그"],
  values: [17.92, 16.64, 6.00, 5.18, 2.78, 2.68, 1.06],
}], {
  x: M, y: 1.66, w: 7.30, h: 3.10,
  barDir: "bar", chartColors: [NAVY],
  showTitle: true, title: "그 가정 하나를 빼면 옮겨야 하는 자본 비중 (%)",
  titleFontSize: 11, titleColor: INK, titleFontFace: F,
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK,
  dataLabelFontSize: 10, dataLabelFontBold: true, dataLabelFontFace: F,
  dataLabelFormatCode: '0.0"%"',
  catAxisLabelColor: SLATE, catAxisLabelFontSize: 9.5, catAxisLabelFontFace: F,
  valAxisLabelColor: MUTE, valAxisLabelFontSize: 9, valAxisLabelFontFace: F,
  valAxisMinVal: 0, valAxisMaxVal: 22, valGridLine: { color: "E8EDF2", size: 1 },
  catGridLine: { style: "none" }, showLegend: false,
});

card(s7, M + 7.70, 1.72, FULL - 7.70, 3.00, { fill: PANEL, border: PANEL });
s7.addText("노력과 영향이 역비례한다", {
  x: M + 7.94, y: 1.94, w: FULL - 8.20, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12, bold: true, color: INK });

// ⚠️ 크기가 다른 줄을 한 상자에 넣고 lineSpacing을 걸면 큰 글자가 윗줄을 덮는다.
//    (초판에서 실제로 22pt 숫자가 9pt 설명을 가렸다) — 줄마다 상자를 분리한다.
[["가장 많은 노력을 들인 축", "정성 심층조사 33종목 · 5개 관점", "2.68%", AMBER, 2.40],
 ["근거 없이 정한 상수", "버킷 목표 비중 40 / 30 / 20 / 10", "16.64%", RED, 3.40],
].forEach(([lab, sub, val, col, y]) => {
  s7.addText(lab, { x: M + 7.94, y, w: FULL - 8.20, h: 0.22, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10, color: SLATE });
  s7.addText(sub, { x: M + 7.94, y: y + 0.22, w: FULL - 8.20, h: 0.20,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 8.5, color: MUTE });
  s7.addText(val, { x: M + 7.94, y: y + 0.44, w: FULL - 8.20, h: 0.44,
    isTextBox: true, margin: 0, fontFace: F, fontSize: 22, bold: true, color: col });
});
s7.addText("약 6배 차이", {
  x: M + 7.94, y: 4.34, w: FULL - 8.20, h: 0.30, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 13, bold: true, color: INK });

card(s7, M, 4.94, FULL, 1.78, { border: INK });
s7.addText("해석", { x: M + 0.32, y: 5.12, w: 3, h: 0.24, isTextBox: true,
  margin: 0, fontFace: F, fontSize: 11, bold: true, color: INK });
s7.addText([
  { text: "분석 품질을 높여도 자본 배분은 거의 움직이지 않는다.", options: { bold: true, breakLine: true } },
  { text: "실제로 비중을 결정하는 것은 종목 분석이 아니라 포트폴리오 규칙이고, 그 규칙의 상위 두 항목은 근거가 기록된 바 없다. 이 사실을 모른 채 분석만 정교화하면, 투입 대비 성과가 나오지 않는 이유를 영영 알 수 없다.", options: { breakLine: true } },
  { text: "→ 이 상수들을 임의로 바꾸지 않는다. 대신 성과 관측이 쌓인 뒤 근거를 갖고 조정한다.", options: { bold: true } },
], { x: M + 0.32, y: 5.42, w: FULL - 0.64, h: 1.18, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, color: SLATE, lineSpacing: 15 });
s7.addNotes("근거 없는 상수를 근거 없는 다른 숫자로 바꾸는 것은 개선이 아니다 — 그래서 지금은 드러내기만 한다.");

/* ════════ 8 근거 ③ ════════ */
const s8 = slide("근거 ③ 왜 아직 검증할 수 없는가",
  "검증은 의지의 문제가 아니라 전제조건의 문제다", "실측 근거");

const GATES = [
  ["시간", "29일", "전체 분석 이력", "12개월 보유수익률 구간이 존재하지 않는다", RED],
  ["진입가", "9 / 34", "분석 시점 주가 기록", "나머지 25종목은 수익률 계산 자체가 불가능하다", RED],
  ["시점 고정", "3 / 34", "미래정보 미사용 검증", "과거 시점 재현 시 최신 판본이 섞여 들어간다", AMBER],
];
GATES.forEach(([k, v, l, d, col], i) => {
  const w = (FULL - 0.36 * 2) / 3;
  const x = M + i * (w + 0.36);
  card(s8, x, 1.66, w, 1.90);
  s8.addText(k, { x: x + 0.28, y: 1.86, w: w - 0.56, h: 0.24, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10.5, bold: true, color: col });
  s8.addText(v, { x: x + 0.28, y: 2.14, w: w - 0.56, h: 0.52, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 27, bold: true, color: INK });
  s8.addText(l, { x: x + 0.28, y: 2.68, w: w - 0.56, h: 0.22, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 9, color: MUTE });
  s8.addText(d, { x: x + 0.28, y: 2.96, w: w - 0.56, h: 0.46, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 9.5, color: SLATE, lineSpacing: 12 });
});

s8.addShape(pres.ShapeType.roundRect, {
  x: M, y: 3.82, w: FULL, h: 0.86, rectRadius: 0.05,
  fill: { color: INK }, line: { color: INK, width: 1 } });
s8.addText("세 관문 중 하나라도 비면 성과 검증은 시작되지 않는다.  현재 세 관문이 모두 비어 있고, 그 결과 실현 수익률 관측은 0건이다.", {
  x: M + 0.36, y: 3.82, w: FULL - 0.72, h: 0.86, isTextBox: true, margin: 0,
  valign: "middle", fontFace: F, fontSize: 12, bold: true, color: W });

card(s8, M, 4.92, FULL, 1.82, { fill: PANEL, border: PANEL });
s8.addText("이미 확인된 비용 — 같은 실수가 두 번 반복됐다", {
  x: M + 0.32, y: 5.10, w: 7, h: 0.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK });
s8.addText([
  { text: "진입가 필드는 백테스트 전제조건이라며 도입됐지만 아무도 채우지 않았고, 12일 뒤 감시 기능을 만들 때 «34종목 중 24종목은 계산 자체가 불가능»이라는 형태로 비용이 드러났다.", options: { breakLine: true } },
  { text: "시점 고정 필드도 같은 경로를 밟고 있다 — 도입은 됐고, 채워진 것은 3건이다.", options: { breakLine: true } },
  { text: "→ 새로 만들 기능은 없다. 새 분석에서 세 필드를 채우는 것이 전부이며, 그것이 유일한 병목이다.", options: { bold: true } },
], { x: M + 0.32, y: 5.42, w: FULL - 0.64, h: 1.22, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, color: SLATE, lineSpacing: 15 });
s8.addNotes("여기서 강조할 점 — 이건 개발 과제가 아니라 운영 규율 과제다.");

/* ════════ 9 방향성 ════════ */
const s9 = slide("발전 방향 — 세 개의 축",
  "모두 «분석을 더 얹지 않는다»는 하나의 원칙에서 나온다", "방향성");

const PILLARS = [
  ["축 1", "판단을 기록한다", NAVY,
   ["투자 논거를 종목별로 남긴다", "핵심 가정과 반증조건을 함께 적는다",
    "매수 · 관찰 · 제외 판단과 근거를 원장에 넣는다"],
   "지금은 판단이 대화와 커밋 메시지에만 남는다"],
  ["축 2", "결과를 관측한다", TEAL,
   ["새 분석마다 진입가 · 시점 · 출처를 채운다", "기한이 온 반증조건을 확인하고 닫는다",
    "예측과 실제의 차이를 부호까지 보존한다"],
   "지금은 예측 34건이 동결된 채 열리지 않는다"],
  ["축 3", "학습으로 되돌린다", GREEN,
   ["차이를 여섯 개 오류 유형으로 귀속한다", "귀속 결과로 가정과 상수를 조정한다",
    "조정 근거를 사전등록하고 사후에 바꾸지 않는다"],
   "지금은 개선 우선순위가 직관에 의존한다"],
];
PILLARS.forEach(([n, t, col, items, gapTxt], i) => {
  const w = (FULL - 0.32 * 2) / 3;
  const x = M + i * (w + 0.32);
  card(s9, x, 1.62, w, 4.02);
  s9.addShape(pres.ShapeType.roundRect, {
    x: x + 0.28, y: 1.86, w: 0.76, h: 0.30, rectRadius: 0.05,
    fill: { color: col }, line: { color: col, width: 1 } });
  s9.addText(n, { x: x + 0.28, y: 1.86, w: 0.76, h: 0.30, isTextBox: true,
    margin: 0, align: "center", valign: "middle", fontFace: F, fontSize: 10,
    bold: true, color: W });
  s9.addText(t, { x: x + 0.28, y: 2.28, w: w - 0.56, h: 0.34, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 15, bold: true, color: INK });
  items.forEach((it, k) => {
    const iy = 2.82 + k * 0.62;
    s9.addShape(pres.ShapeType.ellipse, {
      x: x + 0.30, y: iy + 0.09, w: 0.09, h: 0.09,
      fill: { color: col }, line: { color: col, width: 0.5 } });
    s9.addText(it, { x: x + 0.52, y: iy, w: w - 0.82, h: 0.56, isTextBox: true,
      margin: 0, fontFace: F, fontSize: 10, color: SLATE, lineSpacing: 13 });
  });
  card(s9, x + 0.28, 4.86, w - 0.56, 0.60, { fill: PANEL, border: PANEL });
  s9.addText(gapTxt, { x: x + 0.44, y: 4.86, w: w - 0.88, h: 0.60, isTextBox: true,
    margin: 0, valign: "middle", fontFace: F, fontSize: 8.5, color: AMBER });
});

s9.addShape(pres.ShapeType.roundRect, {
  x: M, y: 5.88, w: FULL, h: 0.84, rectRadius: 0.05,
  fill: { color: PANEL }, line: { color: PANEL, width: 1 } });
s9.addText("세 축 모두 새 밸류에이션 기능을 요구하지 않는다.  필요한 코드는 이미 있고, 필요한 것은 그 코드를 실제로 쓰는 운영 규율이다.", {
  x: M + 0.36, y: 5.88, w: FULL - 0.72, h: 0.84, isTextBox: true, margin: 0,
  valign: "middle", fontFace: F, fontSize: 11.5, bold: true, color: INK });
s9.addNotes("세 축의 순서가 중요하다 — 기록 없이는 관측이 불가능하고, 관측 없이는 학습이 불가능하다.");

/* ════════ 10 로드맵 ════════ */
const s10 = slide("실행 로드맵", "선행 조건이 충족되어야 다음 단계로 넘어간다", "실행");

const PH = [
  ["P0", "즉시 ~ 90일", "기록을 시작한다", NAVY,
   ["새 분석에 진입가 · 시점 · 출처 필수화", "투자 논거 스키마를 실제로 채운다",
    "판단 기록을 매수리스트와 연결한다", "반증조건 기한 감시를 일일 실행에 배선"],
   "완료 판정 — 신규 분석 100%가 세 필드를 갖춘다"],
  ["P1", "3 ~ 12개월", "결과를 측정한다", TEAL,
   ["동결된 예측 34건을 기한 도래 순으로 해소", "실현 성장률 대비 오차를 부호까지 기록",
    "사전등록 실험 H-006 검정 실행", "오류를 여섯 유형으로 귀속"],
   "완료 판정 — 예측 해소율 70% 이상, 귀속 리포트 발행"],
  ["P2", "12개월 이후", "분석을 심화한다", GREEN,
   ["회계 품질 지표를 판정 경로에 승격", "해자 · 투하자본 정의 확립",
    "산업 국면 신호 도입", "포트폴리오 규칙 상수 재검토"],
   "착수 조건 — P1의 귀속 결과가 개선 방향을 지목할 때"],
];
PH.forEach(([k, when, t, col, items, done], i) => {
  const w = (FULL - 0.32 * 2) / 3;
  const x = M + i * (w + 0.32);
  card(s10, x, 1.62, w, 4.22);
  s10.addShape(pres.ShapeType.roundRect, {
    x: x + 0.28, y: 1.86, w: 0.56, h: 0.32, rectRadius: 0.05,
    fill: { color: col }, line: { color: col, width: 1 } });
  s10.addText(k, { x: x + 0.28, y: 1.86, w: 0.56, h: 0.32, isTextBox: true,
    margin: 0, align: "center", valign: "middle", fontFace: F, fontSize: 11,
    bold: true, color: W });
  s10.addText(when, { x: x + 0.94, y: 1.90, w: w - 1.22, h: 0.26, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10, bold: true, color: col });
  s10.addText(t, { x: x + 0.28, y: 2.30, w: w - 0.56, h: 0.32, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 14.5, bold: true, color: INK });
  items.forEach((it, m) => {
    const iy = 2.80 + m * 0.60;
    s10.addText(`${m + 1}`, { x: x + 0.28, y: iy, w: 0.24, h: 0.24, isTextBox: true,
      margin: 0, fontFace: F, fontSize: 9, bold: true, color: MUTE });
    s10.addText(it, { x: x + 0.56, y: iy, w: w - 0.86, h: 0.54, isTextBox: true,
      margin: 0, fontFace: F, fontSize: 10, color: INK, lineSpacing: 13 });
  });
  card(s10, x + 0.28, 5.20, w - 0.56, 0.44, { fill: PANEL, border: PANEL });
  s10.addText(done, { x: x + 0.44, y: 5.20, w: w - 0.88, h: 0.44, isTextBox: true,
    margin: 0, valign: "middle", fontFace: F, fontSize: 8.5, bold: true, color: NAVY });
  if (i < 2) s10.addShape(pres.ShapeType.line, {
    x: x + w + 0.06, y: 3.70, w: 0.20, h: 0,
    line: { color: MUTE, width: 1.5, endArrowType: "triangle" } });
});

s10.addText("⚠  P2를 먼저 시작하지 않는다.  루프를 닫기 전에 분석을 심화하면, 쓰이지 않는 지표만 늘고 어느 개선이 효과가 있었는지 끝내 알 수 없게 된다.", {
  x: M, y: 6.06, w: FULL, h: 0.30, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, bold: true, color: INK });
s10.addNotes("P0는 개발이 아니라 규율이다. 90일 안에 끝나지 않으면 그건 자원 문제가 아니라 습관 문제다.");

/* ════════ 11 성패 판정 ════════ */
const s11 = slide("성공과 실패를 무엇으로 판정하는가",
  "판정 기준을 결과가 나오기 전에 고정한다", "검증 설계");

const L = (FULL - 0.36) / 2;
card(s11, M, 1.62, L, 2.44, { border: TEAL });
s11.addText("성공으로 판정하는 조건", {
  x: M + 0.30, y: 1.84, w: L - 0.60, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12.5, bold: true, color: TEAL });
[["예측 해소율", "12개월 내 70% 이상"],
 ["성장률 예측 오차", "순진한 과거 CAGR 연장 대비 축소"],
 ["오류 귀속", "여섯 유형 중 특정 유형에 집중이 나타남"],
 ["판단 기록", "신규 분석 100%가 논거·반증조건 보유"]].forEach(([k, v], i) => {
  const y = 2.24 + i * 0.44;
  s11.addText(k, { x: M + 0.30, y, w: 2.15, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: INK });
  s11.addText(v, { x: M + 2.52, y, w: L - 2.82, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: SLATE });
});

card(s11, M + L + 0.36, 1.62, L, 2.44, { border: RED });
s11.addText("실패로 판정하는 조건", {
  x: M + L + 0.66, y: 1.84, w: L - 0.60, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12.5, bold: true, color: RED });
[["예측 해소", "12개월 뒤에도 해소율 30% 미만"],
 ["예측 정확도", "무정보 상수 추정보다 나쁨"],
 ["오류 귀속", "유형이 무작위로 흩어져 개선 지점을 못 지목"],
 ["운영", "P0 필드가 신규 분석에서 다시 비기 시작"]].forEach(([k, v], i) => {
  const y = 2.24 + i * 0.44;
  s11.addText(k, { x: M + L + 0.66, y, w: 2.15, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: INK });
  s11.addText(v, { x: M + L + 2.88, y, w: L - 2.82, h: 0.28, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10, color: SLATE });
});

card(s11, M, 4.28, FULL, 1.32, { fill: PANEL, border: PANEL });
s11.addText("판정 기준을 미리 고정하는 이유", {
  x: M + 0.32, y: 4.46, w: 6, h: 0.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK });
s11.addText([
  { text: "결과를 본 뒤에 기준을 조정하면 어떤 결과도 «성공»으로 서술할 수 있다. 그래서 예측은 해시로 봉인하고, 실험은 결과가 존재하기 전에 등록하며, 실패한 실험은 삭제 경로 자체를 만들지 않았다.", options: { breakLine: true } },
  { text: "현재 등록된 실험 9건 중 5건이 «데이터 부재로 차단» 상태다 — 이 상태를 숨기지 않는 것이 설계의 일부다.", options: {} },
], { x: M + 0.32, y: 4.76, w: FULL - 0.64, h: 0.76, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, color: SLATE, lineSpacing: 15 });

card(s11, M, 5.80, FULL, 0.92, { border: INK });
s11.addText([
  { text: "⚠  이 보고는 IRS가 시장을 이긴다고 주장하지 않는다.  ", options: { bold: true, color: INK } },
  { text: "현재까지 측정된 것은 내부 일관성뿐이며, 초과수익에 대한 근거는 한 건도 없다. 그것을 측정할 수 있는 상태로 만드는 것이 이번 방향성의 전부다.", options: { color: SLATE } },
], { x: M + 0.36, y: 5.80, w: FULL - 0.72, h: 0.92, isTextBox: true, margin: 0,
  valign: "middle", fontFace: F, fontSize: 10.5, lineSpacing: 14 });
s11.addNotes("과장하지 않는 것이 이 시스템의 유일한 자산이다.");

/* ════════ 12 원칙 / 안 하는 것 ════════ */
const s12 = slide("지키는 원칙과 의도적으로 하지 않는 것",
  "무엇을 만들지 않을지 정하는 것도 방향성이다", "원칙");

s12.addText("타협하지 않는 원칙", {
  x: M, y: 1.58, w: 5, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12.5, bold: true, color: INK });
const NN = [
  ["데이터", "날조 금지 · 없는 데이터는 없는 것으로 기록"],
  ["근거", "1차 출처 우선 · 인용의 위치까지 추적 가능"],
  ["검증", "판정에 반영하기 전에 측정 · 사후 임계값 조정 금지"],
  ["거버넌스", "사람의 승인 필수 · 자동 매수 금지"],
  ["재현성", "기준값 재현 · 불변 기록 · 감사 추적"],
];
NN.forEach(([k, v], i) => {
  const y = 1.98 + i * 0.50;
  s12.addText(k, { x: M, y, w: 1.35, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, bold: true, color: NAVY });
  s12.addText(v, { x: M + 1.42, y, w: 4.95, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: SLATE });
});

const RX = M + 6.70;
s12.addText("의도적으로 만들지 않는 것", {
  x: RX, y: 1.58, w: 5, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12.5, bold: true, color: INK });
const ANTI = [
  ["단일 종합 점수", "중요도가 다른 축이 같은 무게가 되고 공백이 점수 뒤에 숨는다"],
  ["자동 매매 · 자동 매수", "판단은 사람이 한다"],
  ["주가 예측", "이 체계는 기대와 현실의 격차를 다루지 예측을 하지 않는다"],
  ["상관행렬 최적화", "수익률 시계열 자체가 없다"],
  ["다중 에이전트 구조", "병목은 조율이 아니라 입력 근거의 부재다"],
];
ANTI.forEach(([k, v], i) => {
  const y = 1.98 + i * 0.50;
  s12.addText(k, { x: RX, y, w: 2.0, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, bold: true, color: RED });
  s12.addText(v, { x: RX + 2.08, y, w: FULL - 6.70 - 2.08, h: 0.28, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 9.5, color: SLATE });
});

card(s12, M, 4.72, FULL, 1.98, { fill: PANEL, border: PANEL });
s12.addText("이 원칙들이 실제로 작동한 사례", {
  x: M + 0.32, y: 4.90, w: 6, h: 0.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK });
const CASES = [
  ["측정이 가설을 기각했다", "회계 품질 지표 후보가 실은 주식보상 강도를 재고 있었음이 상관 측정에서 드러나 폐기됐다"],
  ["단위 오류를 구조로 막았다", "같은 값을 두 통화로 보고하는 기업을 «재작성»으로 오탐한 사고를 계기로, 단위 혼재 경고를 배선했다"],
  ["근거 없는 수정을 거부했다", "임계값이 결과와 어긋나 보여도, 근거 없이 유지하던 값을 근거 없는 다른 값으로 바꾸지 않았다"],
];
CASES.forEach(([k, v], i) => {
  const y = 5.24 + i * 0.44;
  s12.addText(k, { x: M + 0.32, y, w: 3.2, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: TEAL });
  s12.addText(v, { x: M + 3.62, y, w: FULL - 3.94, h: 0.28, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10, color: SLATE });
});
s12.addNotes("원칙은 선언이 아니라 실제로 무언가를 거부했을 때만 원칙이다.");

/* ════════ 13 결론 ════════ */
const s13 = pres.addSlide();
s13.background = { color: INK };
page += 1;
s13.addText("결론", {
  x: M + 0.45, y: 1.05, w: FULL, h: 0.36, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: TEAL, charSpacing: 1.2 });
s13.addText("지금 필요한 것은 더 정교한 분석이 아니라,\n판단이 맞았는지 알 수 있는 상태다.", {
  x: M + 0.45, y: 1.52, w: 11.4, h: 1.30, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 27, bold: true, color: W, lineSpacing: 40 });

const FIN = [
  ["기록한다", "판단 시점에 무엇을 믿었고 어떤 조건이면 틀린 것인지 남긴다"],
  ["관측한다", "기한이 오면 실제 결과를 확인하고 예측과의 차이를 보존한다"],
  ["되돌린다", "차이가 난 이유를 귀속해 가정과 규칙을 근거 있게 고친다"],
];
FIN.forEach(([k, v], i) => {
  const w = (11.4 - 0.44 * 2) / 3;
  const x = M + 0.45 + i * (w + 0.44);
  s13.addShape(pres.ShapeType.roundRect, {
    x, y: 3.32, w, h: 1.42, rectRadius: 0.06,
    fill: { color: "16334F" }, line: { color: "2B4E6E", width: 1 } });
  s13.addText(k, { x: x + 0.28, y: 3.56, w: w - 0.56, h: 0.32, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 15, bold: true, color: W });
  s13.addText(v, { x: x + 0.28, y: 3.94, w: w - 0.56, h: 0.62, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 10, color: PALE, lineSpacing: 13 });
});

s13.addText("P0 착수 시점의 판단 기준은 단 하나다 — 다음 분석부터 진입가 · 시점 · 논거를 채우는가.", {
  x: M + 0.45, y: 5.22, w: 11.4, h: 0.32, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 12, bold: true, color: "9FC3E0" });
s13.addText("모든 수치는 2026-08-27 저장소 실측값이며, 추정치를 포함하지 않는다.", {
  x: M + 0.45, y: 5.68, w: 11.4, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 9, color: "6E859B" });
s13.addText("IRS · 발전 방향", {
  x: M, y: 7.06, w: 5, h: 0.20, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 8, color: "5C7690" });
s13.addText(`${TOTAL} / ${TOTAL}`, {
  x: 13.33 - M - 1.2, y: 7.06, w: 1.2, h: 0.20, isTextBox: true, margin: 0,
  align: "right", fontFace: F, fontSize: 8, color: "5C7690" });
s13.addNotes("이 한 문장으로 끝낸다 — 판단이 맞았는지 알 수 있는 상태를 만든다.");

pres.writeFile({ fileName: "IRS_발전방향.pptx" }).then(f => console.log("wrote", f));
