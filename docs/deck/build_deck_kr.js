const pptxgen = require("pptxgenjs");

/* ── 팔레트: 네이비 중심. 블루 → 틸 → 네이비 → 그린이 루프의 네 구역
      (입력 · 조사 · 판단 · 감시)을 구분한다. */
const INK   = "0B2239";
const NAVY  = "12395C";
const BLUE  = "2E6FA3";
const TEAL  = "0E7C86";
const GREEN = "2F7D5D";
const AMBER = "9A6B2F";
const SLATE = "55636F";
const MUTE  = "8A98A5";
const LINE  = "CBD5DF";
const PANEL = "F4F7FA";
const W     = "FFFFFF";

/* 맑은 고딕 = 한글 업무문서 표준(Windows Office 기본 탑재).
   ⚠️ 한글에는 이탤릭을 쓰지 않는다 — 합성 기울임이라 인쇄·발표에서 품질이 떨어진다. */
const F = "Malgun Gothic";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";               // 13.33 x 7.5 — 슬라이드 추가 전에 지정
pres.author = "IRS";
pres.title = "IRS 투자 리서치 운영체계";

const M = 0.45;
const FULL = 13.33 - 2 * M;

/* ── 공통 요소 ───────────────────────────────────────────────────────── */
function head(s, t, sub) {
  s.addText(t, {
    x: M, y: 0.30, w: FULL, h: 0.50, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 24, bold: true, color: INK,
  });
  s.addText(sub, {
    x: M, y: 0.86, w: FULL, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11.5, color: SLATE,
  });
}

function foot(s, page) {
  s.addText("IRS · 투자 리서치 운영체계", {
    x: M, y: 7.05, w: 5.0, h: 0.22, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 8, color: MUTE,
  });
  s.addText(`${page} / 3`, {
    x: 13.33 - M - 1.2, y: 7.05, w: 1.2, h: 0.22, isTextBox: true, margin: 0,
    align: "right", fontFace: F, fontSize: 8, color: MUTE,
  });
}

function chip(s, x, y, w, txt, fill, fg) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.27, rectRadius: 0.05,
    fill: { color: fill }, line: { color: fill, width: 0.75 },
  });
  s.addText(txt, {
    x, y, w, h: 0.27, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: F, fontSize: 8, bold: true, color: fg,
  });
}

/* ════════════════════════════════════════════════════════════════════════
   1 — 전체 운영 루프
   ════════════════════════════════════════════════════════════════════════ */
const s1 = pres.addSlide();
s1.background = { color: W };
head(s1, "IRS 투자 리서치 운영체계",
  "지속적 리서치 → 판단 → 감시 → 학습으로 닫히는 폐쇄 루프");

const STAGES = [
  { n: "01", k: "시장 · 데이터", e: "Market & Data", c: BLUE,
    items: ["시장 데이터", "SEC 공시", "기업 공시", "뉴스 · 외부 근거"] },
  { n: "02", k: "발굴", e: "Discovery", c: BLUE,
    items: ["일일 스크리닝", "유니버스 필터링", "후보 식별"] },
  { n: "03", k: "조사 우선순위", e: "Research Priority", c: TEAL,
    items: ["기대와 현실의 격차", "리서치 질문", "정보 격차", "지금 봐야 할 이유"] },
  { n: "04", k: "심층 조사", e: "Deep Research", c: TEAL,
    items: ["재무 · 회계", "해자 · 경쟁", "산업", "경영진", "밸류에이션"] },
  { n: "05", k: "투자 논거", e: "Investment Case", c: TEAL,
    items: ["사실", "해석", "투자 함의", "핵심 가정", "상충 근거"] },
  { n: "06", k: "사람의 판단", e: "Human Decision", c: NAVY, solid: true,
    items: ["매수", "관찰", "제외", "추가 조사"] },
  { n: "07", k: "관찰 · 감시", e: "Monitoring", c: GREEN,
    items: ["논거 연동 감시", "공시", "핵심 지표", "밸류에이션", "사업 변화"] },
  { n: "08", k: "논거 변화", e: "Thesis Change", c: GREEN,
    items: ["논거 강화", "논거 약화", "가정 변경", "반증조건 발동"] },
];

const GAP = 0.18;
const CW = (FULL - GAP * 7) / 8;
const PITCH = CW + GAP;
const CY = 1.52, CH = 2.42;
const cx = (i) => M + i * PITCH;
const cmid = (i) => cx(i) + CW / 2;

STAGES.forEach((st, i) => {
  const x = cx(i);
  const on = !!st.solid;

  s1.addShape(pres.ShapeType.roundRect, {
    x, y: CY, w: CW, h: CH, rectRadius: 0.06,
    fill: { color: on ? NAVY : W }, line: { color: on ? NAVY : LINE, width: 1 },
  });
  s1.addText(st.n, {
    x: x + 0.11, y: CY + 0.13, w: 0.5, h: 0.20, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9, bold: true, color: on ? "9FC3E0" : st.c,
    charSpacing: 0.8,
  });
  s1.addText(st.k, {
    x: x + 0.11, y: CY + 0.40, w: CW - 0.20, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, color: on ? W : INK,
  });
  s1.addText(st.e, {
    x: x + 0.11, y: CY + 0.69, w: CW - 0.20, h: 0.18, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 6.5, color: on ? "7FA6C6" : MUTE,
  });
  s1.addText(
    st.items.map((v, k) => ({ text: v, options: { breakLine: k !== st.items.length - 1 } })),
    { x: x + 0.11, y: CY + 0.88, w: CW - 0.20, h: 1.42, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 8, lineSpacing: 12.5, color: on ? "C9DCEC" : SLATE });

  if (i < 7) {
    s1.addShape(pres.ShapeType.line, {
      x: x + CW + 0.015, y: CY + CH / 2, w: GAP - 0.03, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

s1.addText("사람의 승인 필수", {
  x: cx(5) - 0.05, y: CY + CH + 0.07, w: CW + 0.10, h: 0.22, isTextBox: true,
  margin: 0, align: "center", fontFace: F, fontSize: 8.5, bold: true, color: NAVY,
});

/* 되먹임: 08 논거 변화 → 04 심층 조사 */
const FY = 4.48;
[[cmid(7), 0], [cmid(3), 1]].forEach(([px, arrow]) => {
  s1.addShape(pres.ShapeType.line, {
    x: px, y: CY + CH, w: 0, h: FY - (CY + CH),
    line: arrow
      ? { color: GREEN, width: 1.5, beginArrowType: "triangle" }
      : { color: GREEN, width: 1.5 },
  });
});
s1.addShape(pres.ShapeType.line, {
  x: cmid(3), y: FY, w: cmid(7) - cmid(3), h: 0,
  line: { color: GREEN, width: 1.5 },
});
s1.addText("논거가 바뀌면 다시 조사한다", {
  x: (cmid(3) + cmid(7)) / 2 - 1.25, y: FY - 0.15, w: 2.50, h: 0.30,
  isTextBox: true, margin: 0, align: "center", fill: { color: W },
  fontFace: F, fontSize: 9.5, bold: true, color: GREEN,
});

/* 학습 계층 */
const LY = 4.92;
s1.addShape(pres.ShapeType.roundRect, {
  x: M, y: LY, w: FULL, h: 1.56, rectRadius: 0.06,
  fill: { color: PANEL }, line: { color: LINE, width: 1 },
});
s1.addText("학습 계층", {
  x: M + 0.28, y: LY + 0.15, w: 1.6, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 10.5, bold: true, color: INK,
});
s1.addText("실제 결과로 판단 체계 자체를 교정한다", {
  x: M + 1.75, y: LY + 0.17, w: 5.0, h: 0.24, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 9.5, color: SLATE,
});

const LEARN = ["사후 검증", "예측 대 실제", "오류 귀속", "프로세스 개선", "체계 개선"];
const LX = M + 0.28, LW = FULL - 0.56, LGAP = 0.30;
const LCW = (LW - LGAP * 4) / 5;
LEARN.forEach((t, i) => {
  const x = LX + i * (LCW + LGAP);
  s1.addShape(pres.ShapeType.roundRect, {
    x, y: LY + 0.52, w: LCW, h: 0.72, rectRadius: 0.05,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s1.addText(t, {
    x, y: LY + 0.52, w: LCW, h: 0.72, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: F, fontSize: 10, bold: true, color: NAVY,
  });
  if (i < 4) {
    s1.addShape(pres.ShapeType.line, {
      x: x + LCW + 0.04, y: LY + 0.88, w: LGAP - 0.08, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

// 학습 → 조사 우선순위
s1.addShape(pres.ShapeType.line, {
  x: cmid(2), y: CY + CH, w: 0, h: LY - (CY + CH),
  line: { color: BLUE, width: 1.5, dashType: "dash", beginArrowType: "triangle" },
});

s1.addText(
  "IRS는 주가를 예측하거나 자동으로 매매하는 시스템이 아니다.  시장 변화에서 조사 가치가 높은 문제를 발견하고, 검증된 근거로 연구하며, 투자 논거를 기록하고 감시하다가, 실제 결과로 다시 학습하는 리서치 인프라다.",
  { x: M, y: 6.62, w: FULL, h: 0.30, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9.5, color: SLATE });

foot(s1, 1);
s1.addNotes("핵심 구조: 발굴 → 조사 → 판단 → 감시 → 재평가 → 학습의 폐쇄 루프. 06 사람의 판단은 자동화하지 않는다.");

/* ════════════════════════════════════════════════════════════════════════
   2 — 현재와 목표
   ════════════════════════════════════════════════════════════════════════ */
const s2 = pres.addSlide();
s2.background = { color: W };
head(s2, "분석 엔진에서 투자 리서치 운영체계로",
  "무엇이 이미 운영되고 있고, 무엇이 아직 남아 있는가");

const COLW = 6.02, LX2 = M, RX2 = M + COLW + 0.39;

s2.addText("현재 IRS 기반", {
  x: LX2, y: 1.22, w: 3.6, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 13, bold: true, color: INK,
});
chip(s2, LX2 + COLW - 1.75, 1.22, 1.75, "구현 · 운영 중", TEAL, W);

s2.addText("목표 운영 계층", {
  x: RX2, y: 1.22, w: 3.6, h: 0.28, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 13, bold: true, color: INK,
});
chip(s2, RX2 + COLW - 1.35, 1.22, 1.35, "구축 대상", MUTE, W);

const CUR = [
  ["자동 실행 체계", "평일 09:00 자동 기동 · 사람 개입 없이 완료"],
  ["후보 선별 파이프라인", "시장 유니버스 → SEC 원자료 검증 → 후보 선별"],
  ["심층 스크리닝 스냅샷", "일별 스냅샷 영속화 · 전일 대비 변화 비교"],
  ["관심종목 감시", "스크리닝이 실패해도 감시는 독립적으로 유지"],
  ["검증 인프라", "기준값 재현 · 데이터 무결성 · 기록 보호 · 회귀 테스트 917건"],
  ["실행 기록", "결과와 실패 사유를 이슈로 자동 게시"],
];
const H2 = 0.58, G2 = 0.08, Y2 = 1.62;
CUR.forEach(([t, d], i) => {
  const y = Y2 + i * (H2 + G2);
  s2.addShape(pres.ShapeType.roundRect, {
    x: LX2, y, w: COLW, h: H2, rectRadius: 0.05,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s2.addShape(pres.ShapeType.ellipse, {
    x: LX2 + 0.20, y: y + H2 / 2 - 0.055, w: 0.11, h: 0.11,
    fill: { color: TEAL }, line: { color: TEAL, width: 0.5 },
  });
  s2.addText(t, {
    x: LX2 + 0.44, y: y + 0.07, w: COLW - 0.62, h: 0.24, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 11, bold: true, color: INK,
  });
  s2.addText(d, {
    x: LX2 + 0.44, y: y + 0.31, w: COLW - 0.62, h: 0.22, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 8.5, color: SLATE,
  });
});

const TGT = [
  ["리서치 팩", "기업별 분석 결과를 하나의 감사 가능한 투자 논거로 통합", "미구축"],
  ["논거 데이터베이스", "논거 · 가정 · 촉매 · 반증조건 · 감시변수 · 재검토일",
    "스키마는 코드에 존재 · 운영 기록 0건"],
  ["논거 변화 탐지", "주가가 아니라 논거를 바꿀 수 있는 변화를 탐지",
    "반증조건 스캔만 존재 · 판정은 사람이"],
  ["판단 기록", "매수 / 관찰 / 제외 판단과 그 근거 · 가정 · 리스크 · 승인자",
    "스키마는 코드에 존재 · 운영 기록 0건"],
  ["사후 검증과 학습", "성장 · 마진 · 산업 · 경영진 · 밸류에이션 · 데이터 오류로 분해",
    "예측 34건 동결 · 해소 0건"],
];
const H3 = 0.72, G3 = 0.08;
TGT.forEach(([t, d, st], i) => {
  const y = Y2 + i * (H3 + G3);
  s2.addShape(pres.ShapeType.roundRect, {
    x: RX2, y, w: COLW, h: H3, rectRadius: 0.05,
    fill: { color: PANEL }, line: { color: LINE, width: 1, dashType: "dash" },
  });
  s2.addText(`${i + 1}`, {
    x: RX2 + 0.18, y: y + 0.08, w: 0.30, h: 0.22, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: MUTE,
  });
  s2.addText(t, {
    x: RX2 + 0.50, y: y + 0.07, w: COLW - 0.68, h: 0.24, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 11, bold: true, color: NAVY,
  });
  s2.addText(d, {
    x: RX2 + 0.50, y: y + 0.30, w: COLW - 0.68, h: 0.22, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 8.5, color: SLATE,
  });
  s2.addText(st, {
    x: RX2 + 0.50, y: y + 0.51, w: COLW - 0.68, h: 0.19, isTextBox: true,
    margin: 0, fontFace: F, fontSize: 8, bold: true, color: AMBER,
  });
});

const CHAIN = ["현재 기반", "운영 계층", "지속 투자 루프"];
const CCW = 2.60, CGAP = 0.60;
const chainX = (13.33 - (CCW * 3 + CGAP * 2)) / 2;
CHAIN.forEach((t, i) => {
  const x = chainX + i * (CCW + CGAP);
  const last = i === 2;
  s2.addShape(pres.ShapeType.roundRect, {
    x, y: 5.80, w: CCW, h: 0.40, rectRadius: 0.05,
    fill: { color: last ? NAVY : W }, line: { color: last ? NAVY : LINE, width: 1 },
  });
  s2.addText(t, {
    x, y: 5.80, w: CCW, h: 0.40, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: F, fontSize: 11, bold: true, color: last ? W : INK,
  });
  if (i < 2) {
    s2.addShape(pres.ShapeType.line, {
      x: x + CCW + 0.06, y: 6.00, w: CGAP - 0.12, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

s2.addShape(pres.ShapeType.roundRect, {
  x: M, y: 6.42, w: FULL, h: 0.56, rectRadius: 0.05,
  fill: { color: PANEL }, line: { color: PANEL, width: 1 },
});
s2.addText(
  "현재 IRS는 견고한 분석 · 검증 기반을 갖추고 있다.  다음 단계는 지표를 더 늘리는 것이 아니라, 리서치 → 판단 → 감시 → 학습의 루프를 닫는 것이다.",
  { x: M + 0.32, y: 6.42, w: FULL - 0.64, h: 0.56, isTextBox: true, margin: 0,
    valign: "middle", fontFace: F, fontSize: 11.5, bold: true, color: INK });

foot(s2, 2);
s2.addNotes("좌측은 실제로 매일 실행되는 것만 담았다. 우측의 상태 표기는 '코드는 있으나 운영 기록 0건'을 숨기지 않기 위한 것이다.");

/* ════════════════════════════════════════════════════════════════════════
   3 — 실행 로드맵
   ════════════════════════════════════════════════════════════════════════ */
const s3 = pres.addSlide();
s3.background = { color: W };
head(s3, "IRS 실행 로드맵", "분석을 더 얹기 전에 투자 루프를 먼저 닫는다");

const PHASES = [
  { k: "P0", c: NAVY, name: "루프를 닫는다", when: "최우선",
    items: ["리서치 팩", "논거 스키마 · 데이터베이스", "관심종목과 논거 연결",
      "논거 변화 탐지", "사람의 판단 기록"],
    goal: "IRS를 실제 투자 업무에서 매일 쓰이게 만든다." },
  { k: "P1", c: TEAL, name: "시간으로 검증한다", when: "그 다음",
    items: ["시점 고정 백테스트", "판단 원장", "예측 대 실제", "오류 귀속", "사후 검증"],
    goal: "과거에 무엇을 판단했고 실제로 어떻게 되었는지 측정한다." },
  { k: "P2", c: GREEN, name: "분석을 심화한다", when: "P0 · P1 이후",
    items: ["회계 품질 L2 · L3", "해자 정의와 측정", "산업 국면 신호",
      "경영진 근거 계층", "학술 · 계량 연구 반영"],
    goal: "이미 만들어진 운영체계의 분석 품질을 지속적으로 높인다." },
];

const PW = (FULL - 0.24) / 3, PY = 1.38, PH = 3.40;
PHASES.forEach((p, i) => {
  const x = M + i * (PW + 0.12);
  s3.addShape(pres.ShapeType.roundRect, {
    x, y: PY, w: PW, h: PH, rectRadius: 0.06,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s3.addShape(pres.ShapeType.roundRect, {
    x: x + 0.24, y: PY + 0.24, w: 0.54, h: 0.32, rectRadius: 0.05,
    fill: { color: p.c }, line: { color: p.c, width: 1 },
  });
  s3.addText(p.k, {
    x: x + 0.24, y: PY + 0.24, w: 0.54, h: 0.32, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: F, fontSize: 12, bold: true, color: W,
  });
  s3.addText(p.name, {
    x: x + 0.90, y: PY + 0.25, w: PW - 1.14, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13.5, bold: true, color: INK,
  });
  s3.addText(p.when, {
    x: x + 0.90, y: PY + 0.54, w: PW - 1.14, h: 0.20, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9, bold: true, color: p.c,
  });

  p.items.forEach((it, k) => {
    const iy = PY + 0.94 + k * 0.320;
    s3.addText(`${k + 1}`, {
      x: x + 0.26, y: iy, w: 0.24, h: 0.24, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9, bold: true, color: MUTE,
    });
    s3.addText(it, {
      x: x + 0.56, y: iy, w: PW - 0.82, h: 0.24, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 10.5, color: INK,
    });
  });

  s3.addShape(pres.ShapeType.roundRect, {
    x: x + 0.24, y: PY + PH - 0.70, w: PW - 0.48, h: 0.52, rectRadius: 0.05,
    fill: { color: PANEL }, line: { color: PANEL, width: 1 },
  });
  s3.addText(p.goal, {
    x: x + 0.38, y: PY + PH - 0.70, w: PW - 0.76, h: 0.52, isTextBox: true,
    margin: 0, valign: "middle", fontFace: F, fontSize: 9, color: SLATE,
  });
});

const NY = 5.02;
s3.addText("타협하지 않는 원칙", {
  x: M, y: NY, w: 3.0, h: 0.26, isTextBox: true, margin: 0,
  fontFace: F, fontSize: 11, bold: true, color: INK,
});
const NN = [
  ["데이터", "날조 금지\n없는 데이터는 없는 것으로 기록"],
  ["근거", "1차 출처 우선\n근거 추적 가능성 확보"],
  ["검증", "판정에 반영하기 전에 측정\n결과를 본 뒤 임계값 조정 금지"],
  ["거버넌스", "사람의 승인 필수\n자동 매수 금지"],
  ["재현성", "기준값 재현 테스트 · 불변 기록\n감사 추적"],
];
const NW = (FULL - 0.40 * 4) / 5;
NN.forEach(([h, d], i) => {
  const x = M + i * (NW + 0.40);
  s3.addText(h, {
    x, y: NY + 0.36, w: NW, h: 0.22, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: NAVY,
  });
  s3.addText(d, {
    x, y: NY + 0.60, w: NW, h: 0.46, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 8.5, color: SLATE, lineSpacing: 11.5,
  });
});

s3.addShape(pres.ShapeType.roundRect, {
  x: M, y: 6.24, w: FULL, h: 0.70, rectRadius: 0.06,
  fill: { color: INK }, line: { color: INK, width: 1 },
});
s3.addText(
  "IRS의 최종 목표는 분석 기능을 더 많이 갖는 것이 아니다.  시장 변화를 지속적으로 관찰하고, 조사 가치가 높은 문제를 발견하고, 검증된 근거로 투자 판단을 지원하며, 투자 논거를 계속 감시하다가, 실제 결과를 통해 스스로의 판단 체계를 개선하는 지속적 투자 리서치 운영체계를 만드는 것이다.",
  { x: M + 0.36, y: 6.24, w: FULL - 0.72, h: 0.70, isTextBox: true, margin: 0,
    valign: "middle", fontFace: F, fontSize: 9.5, color: "DCE7F0" });

foot(s3, 3);
s3.addNotes("P2를 먼저 하지 않는다. 루프를 닫기 전에 분석 복잡도를 늘리면 쓰이지 않는 지표만 쌓인다.");

pres.writeFile({ fileName: "IRS_투자리서치_운영체계.pptx" })
  .then(f => console.log("wrote", f));
