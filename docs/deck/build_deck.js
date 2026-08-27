const pptxgen = require("pptxgenjs");

/* ── Palette: navy-led, restrained. Blue → Teal → Navy → Green marks the
      four functional zones of the loop (input · research · decision · watch). */
const INK   = "0B2239";
const NAVY  = "12395C";
const BLUE  = "2E6FA3";
const TEAL  = "0E7C86";
const GREEN = "2F7D5D";
const SLATE = "5C6B7A";
const MUTE  = "8494A3";
const LINE  = "CBD5DF";
const PANEL = "F4F7FA";
const W     = "FFFFFF";

const HEAD = "Cambria";
const BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";              // 13.33 x 7.5 — set BEFORE addSlide
pres.author = "IRS";
pres.title = "IRS Investment Research OS";

const M = 0.45;
const FULL = 13.33 - 2 * M;

/* ── helpers ─────────────────────────────────────────────────────────── */
function title(s, t, sub) {
  s.addText(t, {
    x: M, y: 0.28, w: FULL, h: 0.54, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 25, bold: true, color: INK,
  });
  s.addText(sub, {
    x: M, y: 0.84, w: 11.4, h: 0.30, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: SLATE,
  });
}

function tag(s, x, y, w, txt, fill, fg) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.26, rectRadius: 0.05,
    fill: { color: fill }, line: { color: fill, width: 0.75 },
  });
  s.addText(txt, {
    x, y, w, h: 0.26, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: BODY, fontSize: 7.5, bold: true, color: fg,
    charSpacing: 0.4,
  });
}

/* ════════════════════════════════════════════════════════════════════════
   SLIDE 1 — the loop
   ════════════════════════════════════════════════════════════════════════ */
const s1 = pres.addSlide();
s1.background = { color: W };
title(s1, "IRS Investment Research OS",
  "Continuous Investment Research  →  Decision  →  Monitoring  →  Learning");

const STAGES = [
  { n: "01", t: "MARKET\n& DATA",        c: BLUE,  items: ["Market data", "SEC filings", "Company disclosures", "News / external evidence"] },
  { n: "02", t: "DISCOVERY",             c: BLUE,  items: ["Daily screening", "Universe filtering", "Candidate identification"] },
  { n: "03", t: "RESEARCH\nPRIORITY",    c: TEAL,  items: ["Expectation vs reality", "Research question", "Information gap", "Why now?"] },
  { n: "04", t: "DEEP\nRESEARCH",        c: TEAL,  items: ["Financial / accounting", "Moat / competition", "Industry", "Management", "Valuation"] },
  { n: "05", t: "INVESTMENT\nCASE",      c: TEAL,  items: ["Facts", "Interpretation", "Investment implication", "Key assumptions", "Contradictions"] },
  { n: "06", t: "HUMAN\nDECISION",       c: NAVY,  items: ["BUY", "WATCH", "PASS", "Research more"], solid: true },
  { n: "07", t: "WATCHLIST\n& MONITORING", c: GREEN, items: ["Thesis-linked monitoring", "Filings", "KPIs", "Valuation", "Business changes"] },
  { n: "08", t: "THESIS\nCHANGE",        c: GREEN, items: ["Strengthened", "Weakened", "Assumption changed", "Invalidation trigger"] },
];

const GAP = 0.18;
const CW = (FULL - GAP * 7) / 8;          // 1.396
const PITCH = CW + GAP;
const CY = 1.58, CH = 2.30;
const cx = (i) => M + i * PITCH;
const cmid = (i) => cx(i) + CW / 2;

STAGES.forEach((st, i) => {
  const x = cx(i);
  const solid = !!st.solid;

  s1.addShape(pres.ShapeType.roundRect, {
    x, y: CY, w: CW, h: CH, rectRadius: 0.06,
    fill: { color: solid ? NAVY : W },
    line: { color: solid ? NAVY : LINE, width: solid ? 1 : 1 },
  });

  // stage number
  s1.addText(st.n, {
    x: x + 0.10, y: CY + 0.12, w: 0.5, h: 0.22, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9, bold: true,
    color: solid ? "9FC3E0" : st.c, charSpacing: 0.8,
  });

  s1.addText(st.t, {
    x: x + 0.10, y: CY + 0.40, w: CW - 0.20, h: 0.56, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, lineSpacing: 12,
    color: solid ? W : INK,
  });

  s1.addText(
    st.items.map((v, k) => ({
      text: v,
      options: { breakLine: k !== st.items.length - 1 },
    })),
    {
      x: x + 0.10, y: CY + 1.02, w: CW - 0.18, h: 1.16, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 7.5, lineSpacing: 10.5,
      color: solid ? "C9DCEC" : SLATE,
    });

  if (i < 7) {
    s1.addShape(pres.ShapeType.line, {
      x: x + CW + 0.015, y: CY + CH / 2, w: GAP - 0.03, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

// human-decision emphasis
s1.addText("HUMAN APPROVAL REQUIRED", {
  x: cx(5) - 0.02, y: CY + CH + 0.06, w: CW + 0.04, h: 0.20, isTextBox: true,
  margin: 0, align: "center", fontFace: BODY, fontSize: 7, bold: true,
  color: NAVY, charSpacing: 0.4,
});

/* feedback: 08 → 04 */
const FY = 4.42;
s1.addShape(pres.ShapeType.line, {
  x: cmid(7), y: CY + CH, w: 0, h: FY - (CY + CH),
  line: { color: GREEN, width: 1.5 },
});
s1.addShape(pres.ShapeType.line, {
  x: cmid(3), y: FY, w: cmid(7) - cmid(3), h: 0,
  line: { color: GREEN, width: 1.5 },
});
s1.addShape(pres.ShapeType.line, {
  x: cmid(3), y: CY + CH, w: 0, h: FY - (CY + CH),
  line: { color: GREEN, width: 1.5, beginArrowType: "triangle" },
});
s1.addText("THESIS CHANGE  →  RESEARCH AGAIN", {
  x: cmid(3) + 1.15, y: FY - 0.14, w: cmid(7) - cmid(3) - 2.30, h: 0.28,
  isTextBox: true, margin: 0, align: "center", fill: { color: W },
  fontFace: BODY, fontSize: 9, bold: true, color: GREEN, charSpacing: 0.3,
});

/* learning layer */
const LY = 4.86;
s1.addShape(pres.ShapeType.roundRect, {
  x: M, y: LY, w: FULL, h: 1.60, rectRadius: 0.06,
  fill: { color: PANEL }, line: { color: LINE, width: 1 },
});
s1.addText("LEARNING LAYER", {
  x: M + 0.28, y: LY + 0.14, w: 3.0, h: 0.24, isTextBox: true, margin: 0,
  fontFace: BODY, fontSize: 9, bold: true, color: INK, charSpacing: 1.0,
});
s1.addText("실제 결과로 판단 체계 자체를 교정한다", {
  x: M + 2.30, y: LY + 0.14, w: 4.6, h: 0.24, isTextBox: true, margin: 0,
  fontFace: BODY, fontSize: 9, color: SLATE,
});

const LEARN = ["POST-MORTEM", "PREDICTION\nvs OUTCOME", "ERROR\nATTRIBUTION",
  "PROCESS\nIMPROVEMENT", "IRS\nIMPROVEMENT"];
const LX = M + 0.28, LW = FULL - 0.56, LGAP = 0.30;
const CHW = (LW - LGAP * 4) / 5;
LEARN.forEach((t, i) => {
  const x = LX + i * (CHW + LGAP);
  s1.addShape(pres.ShapeType.roundRect, {
    x, y: LY + 0.50, w: CHW, h: 0.74, rectRadius: 0.05,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s1.addText(t, {
    x, y: LY + 0.50, w: CHW, h: 0.74, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: BODY, fontSize: 9, bold: true, color: NAVY,
    lineSpacing: 11,
  });
  if (i < 4) {
    s1.addShape(pres.ShapeType.line, {
      x: x + CHW + 0.04, y: LY + 0.87, w: LGAP - 0.08, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

// learning → research loop
s1.addShape(pres.ShapeType.line, {
  x: cmid(2), y: CY + CH, w: 0, h: LY - (CY + CH),
  line: { color: BLUE, width: 1.5, dashType: "dash", beginArrowType: "triangle" },
});

s1.addText(
  "IRS는 주가를 예측하거나 자동매매하는 시스템이 아니다 — 시장 변화에서 조사 가치가 높은 문제를 발견하고, 검증된 근거로 연구하고, Thesis를 기록·감시하며, 실제 결과로 다시 학습하는 연구 인프라다.",
  { x: M, y: 6.62, w: FULL, h: 0.34, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9.5, italic: true, color: SLATE });

s1.addNotes("핵심: 발견 → 조사 → 판단 → 감시 → 재평가 → 학습의 폐쇄형 루프. 06 HUMAN DECISION은 자동화되지 않는다.");

/* ════════════════════════════════════════════════════════════════════════
   SLIDE 2 — current vs target
   ════════════════════════════════════════════════════════════════════════ */
const s2 = pres.addSlide();
s2.background = { color: W };
title(s2, "From Analytical Engine to Investment Research OS",
  "무엇이 이미 돌아가고 있고, 무엇이 아직 운영 계층으로 남아 있는가");

const COLW = 6.02, LX2 = M, RX2 = M + COLW + 0.39;

s2.addText("CURRENT IRS FOUNDATION", {
  x: LX2, y: 1.22, w: 3.75, h: 0.26, isTextBox: true, margin: 0,
  fontFace: BODY, fontSize: 12, bold: true, color: INK, charSpacing: 0.6,
});
tag(s2, LX2 + COLW - 2.15, 1.22, 2.15, "IMPLEMENTED & RUNNING", TEAL, W);

s2.addText("TARGET INVESTMENT RESEARCH OS", {
  x: RX2, y: 1.22, w: 4.6, h: 0.26, isTextBox: true, margin: 0,
  fontFace: BODY, fontSize: 12, bold: true, color: INK, charSpacing: 0.6,
});
tag(s2, RX2 + COLW - 1.30, 1.22, 1.30, "TO BE BUILT", MUTE, W);

const CUR = [
  ["GitHub Actions", "평일 09:00 KST 스케줄 · 무인 실행"],
  ["Screening Funnel", "Market universe → SEC validation → candidate filtering"],
  ["Deep-screen Snapshot", "일별 스냅샷 영속화 · 전일 대비 변화 비교"],
  ["Watchlist Tracking", "독립 감시 경로 — 스크리닝이 실패해도 감시는 유지"],
  ["Validation Infrastructure", "골든 재현 · 데이터 무결성 · ledger 보호 · 회귀 테스트 917건"],
  ["GitHub Issues", "자동 실행 기록 · 실패/결과 로깅"],
];
const CH2 = 0.58, G2 = 0.08, Y2 = 1.60;
CUR.forEach(([t, d], i) => {
  const y = Y2 + i * (CH2 + G2);
  s2.addShape(pres.ShapeType.roundRect, {
    x: LX2, y, w: COLW, h: CH2, rectRadius: 0.05,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s2.addShape(pres.ShapeType.ellipse, {
    x: LX2 + 0.18, y: y + CH2 / 2 - 0.055, w: 0.11, h: 0.11,
    fill: { color: TEAL }, line: { color: TEAL, width: 0.5 },
  });
  s2.addText(t, {
    x: LX2 + 0.42, y: y + 0.09, w: COLW - 0.60, h: 0.22, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 10.5, bold: true, color: INK,
  });
  s2.addText(d, {
    x: LX2 + 0.42, y: y + 0.31, w: COLW - 0.60, h: 0.22, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 8.5, color: SLATE,
  });
});

const TGT = [
  ["RESEARCH PACK", "기업별 분석 결과를 하나의 auditable investment case로 통합",
    "미구축"],
  ["THESIS DATABASE", "Thesis · 가정 · 촉매 · 반증조건 · 감시변수 · 재검토일",
    "스키마는 코드에 존재 · 운영 기록 0건"],
  ["THESIS CHANGE DETECTION", "주가 변화가 아니라 Thesis를 바꿀 수 있는 변화를 탐지",
    "반증조건 스캔만 존재 · 판정은 사람이"],
  ["DECISION RECORD", "BUY / WATCH / PASS + 근거 · 가정 · 리스크 · 사람의 승인",
    "스키마는 코드에 존재 · 운영 기록 0건"],
  ["POST-MORTEM & LEARNING", "성장 · 마진 · 산업 · 경영진 · 밸류에이션 · 데이터 오류로 분해",
    "예측 34건 동결 · 해소 0건"],
];
const CH3 = 0.72, G3 = 0.08;
TGT.forEach(([t, d, st], i) => {
  const y = Y2 + i * (CH3 + G3);
  s2.addShape(pres.ShapeType.roundRect, {
    x: RX2, y, w: COLW, h: CH3, rectRadius: 0.05,
    fill: { color: PANEL }, line: { color: LINE, width: 1, dashType: "dash" },
  });
  s2.addText(`${i + 1}`, {
    x: RX2 + 0.16, y: y + 0.10, w: 0.30, h: 0.22, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, bold: true, color: MUTE,
  });
  s2.addText(t, {
    x: RX2 + 0.48, y: y + 0.09, w: COLW - 0.66, h: 0.22, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 10.5, bold: true, color: NAVY,
  });
  s2.addText(d, {
    x: RX2 + 0.48, y: y + 0.31, w: COLW - 0.66, h: 0.22, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 8.5, color: SLATE,
  });
  s2.addText(st, {
    x: RX2 + 0.48, y: y + 0.51, w: COLW - 0.66, h: 0.19, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 7.5, bold: true, color: "A5713C",
  });
});

/* chain */
const CHAIN = ["CURRENT FOUNDATION", "RESEARCH OS LAYER", "CONTINUOUS INVESTMENT LOOP"];
const CHW2 = 2.75, CHGAP = 0.55;
const chainW = CHW2 * 3 + CHGAP * 2;
const chainX = (13.33 - chainW) / 2;
CHAIN.forEach((t, i) => {
  const x = chainX + i * (CHW2 + CHGAP);
  s2.addShape(pres.ShapeType.roundRect, {
    x, y: 5.80, w: CHW2, h: 0.38, rectRadius: 0.05,
    fill: { color: i === 2 ? NAVY : W },
    line: { color: i === 2 ? NAVY : LINE, width: 1 },
  });
  s2.addText(t, {
    x, y: 5.80, w: CHW2, h: 0.38, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: BODY, fontSize: 9.5, bold: true,
    color: i === 2 ? W : INK, charSpacing: 0.4,
  });
  if (i < 2) {
    s2.addShape(pres.ShapeType.line, {
      x: x + CHW2 + 0.06, y: 5.99, w: CHGAP - 0.12, h: 0,
      line: { color: MUTE, width: 1.25, endArrowType: "triangle" },
    });
  }
});

s2.addShape(pres.ShapeType.roundRect, {
  x: M, y: 6.40, w: FULL, h: 0.60, rectRadius: 0.05,
  fill: { color: PANEL }, line: { color: PANEL, width: 1 },
});
s2.addText(
  "현재 IRS는 강한 Analytical & Validation Foundation을 갖추고 있다.  다음 단계는 더 많은 지표를 추가하는 것이 아니라 Research → Decision → Monitoring → Learning Loop를 완성하는 것이다.",
  { x: M + 0.30, y: 6.40, w: FULL - 0.60, h: 0.60, isTextBox: true, margin: 0,
    valign: "middle", fontFace: BODY, fontSize: 11.5, bold: true, color: INK });

s2.addNotes("좌측은 실제로 매일 실행되는 것만. 우측의 상태 태그는 '코드는 있으나 운영 기록 0건'을 숨기지 않기 위한 것이다.");

/* ════════════════════════════════════════════════════════════════════════
   SLIDE 3 — roadmap
   ════════════════════════════════════════════════════════════════════════ */
const s3 = pres.addSlide();
s3.background = { color: W };
title(s3, "IRS Realization Roadmap",
  "Close the Investment Loop Before Adding Analytical Complexity");

const PHASES = [
  { k: "P0", c: NAVY, name: "CLOSE THE LOOP", pri: "최우선",
    items: ["Research Pack", "Thesis Schema / Database", "Watchlist ↔ Thesis 연결",
      "Thesis Change Detection", "Human Decision Record"],
    goal: "IRS가 실제 투자 workflow에서 매일 사용되도록 만든다." },
  { k: "P1", c: TEAL, name: "VALIDATE THROUGH TIME", pri: "그 다음",
    items: ["Point-in-Time Backtesting", "Decision Ledger", "Prediction vs Outcome",
      "Attribution", "Post-Mortem"],
    goal: "과거에 무엇을 판단했고 실제로 어떻게 되었는지를 측정한다." },
  { k: "P2", c: GREEN, name: "DEEPEN ANALYTICS", pri: "P0 / P1 이후",
    items: ["Accounting Quality L2 / L3", "Moat Definition & Measurement",
      "Industry Regime Signals", "Management Evidence Layer",
      "Academic / Quantitative Research"],
    goal: "이미 만들어진 Research OS의 분석 품질을 지속 개선한다." },
];

const PW = (FULL - 0.24) / 3, PY = 1.42, PH = 3.42;
PHASES.forEach((p, i) => {
  const x = M + i * (PW + 0.12);
  s3.addShape(pres.ShapeType.roundRect, {
    x, y: PY, w: PW, h: PH, rectRadius: 0.06,
    fill: { color: W }, line: { color: LINE, width: 1 },
  });
  s3.addShape(pres.ShapeType.roundRect, {
    x: x + 0.22, y: PY + 0.22, w: 0.52, h: 0.30, rectRadius: 0.05,
    fill: { color: p.c }, line: { color: p.c, width: 1 },
  });
  s3.addText(p.k, {
    x: x + 0.22, y: PY + 0.22, w: 0.52, h: 0.30, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: BODY, fontSize: 12,
    bold: true, color: W,
  });
  s3.addText(p.name, {
    x: x + 0.86, y: PY + 0.24, w: PW - 1.08, h: 0.26, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, bold: true, color: INK,
  });
  s3.addText(p.pri, {
    x: x + 0.86, y: PY + 0.50, w: PW - 1.08, h: 0.20, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 8.5, color: p.c, bold: true,
  });

  p.items.forEach((it, k) => {
    const iy = PY + 0.92 + k * 0.335;
    s3.addText(`${k + 1}`, {
      x: x + 0.24, y: iy, w: 0.22, h: 0.24, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 9, bold: true, color: MUTE,
    });
    s3.addText(it, {
      x: x + 0.52, y: iy, w: PW - 0.76, h: 0.24, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 10, color: INK,
    });
  });

  s3.addShape(pres.ShapeType.roundRect, {
    x: x + 0.22, y: PY + PH - 0.72, w: PW - 0.44, h: 0.52, rectRadius: 0.05,
    fill: { color: PANEL }, line: { color: PANEL, width: 1 },
  });
  s3.addText(p.goal, {
    x: x + 0.34, y: PY + PH - 0.72, w: PW - 0.68, h: 0.52, isTextBox: true,
    margin: 0, valign: "middle", fontFace: BODY, fontSize: 8.5, color: SLATE,
  });

});

/* non-negotiable */
const NY = 5.06;
s3.addText("NON-NEGOTIABLE", {
  x: M, y: NY, w: 3.0, h: 0.24, isTextBox: true, margin: 0,
  fontFace: BODY, fontSize: 10, bold: true, color: INK, charSpacing: 1.0,
});
const NN = [
  ["DATA", "No fabrication\nMissing data = missing data"],
  ["EVIDENCE", "Primary sources first\nEvidence traceability"],
  ["VALIDATION", "Measure before wiring\nNo post-hoc threshold adjustment"],
  ["GOVERNANCE", "Human approval\nNo silent BUY"],
  ["REPRODUCIBILITY", "Golden tests · immutable ledger\nAudit trail"],
];
const NW = (FULL - 0.4 * 4) / 5;
NN.forEach(([h, d], i) => {
  const x = M + i * (NW + 0.4);
  s3.addText(h, {
    x, y: NY + 0.34, w: NW, h: 0.20, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 9, bold: true, color: NAVY, charSpacing: 0.5,
  });
  s3.addText(d, {
    x, y: NY + 0.56, w: NW, h: 0.46, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 8, color: SLATE, lineSpacing: 10,
  });
});

s3.addShape(pres.ShapeType.roundRect, {
  x: M, y: 6.28, w: FULL, h: 0.82, rectRadius: 0.06,
  fill: { color: INK }, line: { color: INK, width: 1 },
});
s3.addText(
  "IRS의 최종 목표는 더 많은 분석 기능을 갖는 것이 아니다.  시장 변화를 지속적으로 관찰하고, 조사 가치가 높은 문제를 발견하고, 검증된 근거로 투자 판단을 지원하고, Investment Thesis를 지속적으로 감시하며, 실제 결과를 통해 스스로의 판단 체계를 개선하는 Continuous Investment Research OS를 만드는 것이다.",
  { x: M + 0.34, y: 6.28, w: FULL - 0.68, h: 0.82, isTextBox: true, margin: 0,
    valign: "middle", fontFace: BODY, fontSize: 10, color: "DCE7F0" });

s3.addNotes("P2를 먼저 하지 않는다 — 루프를 닫기 전에 분석 복잡도를 늘리면 쓰이지 않는 지표만 쌓인다.");

pres.writeFile({ fileName: "IRS_Investment_Research_OS.pptx" })
  .then(f => console.log("wrote", f));
