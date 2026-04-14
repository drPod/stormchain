// StormChain - EPPS-AA Data Challenge Presentation
// Built with pptxgenjs for the 7-minute finalist slot

const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";  // 13.33 x 7.5 inches
pptx.title = "StormChain";
pptx.author = "drPod";

// ============================================================
// COLOR PALETTE — Ocean Gradient (aviation/weather appropriate)
// ============================================================
const COLORS = {
  midnight: "21295C",     // deep midnight — title backgrounds
  deepBlue: "065A82",     // primary accent — storm blue
  teal: "1C7293",         // secondary — calm ocean
  ice: "CADCFC",          // light support
  white: "FFFFFF",
  offWhite: "F5F7FA",
  charcoal: "2C3E50",     // body text on light bg
  coral: "FF6B6B",        // warning/high-risk accent
  gold: "F9B233",         // highlight/success
  slate: "64748B",        // muted
  lightGray: "E5E7EB",
};

const FONTS = {
  header: "Georgia",
  body: "Calibri",
};

// Helper for consistent footer on content slides
function addFooter(slide, slideNum) {
  slide.addText("StormChain  •  EPPS-AA Data Challenge  •  drPod", {
    x: 0.5, y: 7.1, w: 10, h: 0.3,
    fontFace: FONTS.body, fontSize: 9, color: COLORS.slate, italic: true,
  });
  slide.addText(`${slideNum}`, {
    x: 12.5, y: 7.1, w: 0.5, h: 0.3,
    fontFace: FONTS.body, fontSize: 9, color: COLORS.slate, align: "right",
  });
}

// ============================================================
// SLIDE 1 — Title (dark, dramatic)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.midnight };

  // Decorative storm-like gradient band
  slide.addShape("rect", {
    x: 0, y: 0, w: 13.33, h: 0.15,
    fill: { color: COLORS.coral },
    line: { type: "none" },
  });

  slide.addText("StormChain", {
    x: 0.8, y: 2.2, w: 11.7, h: 1.4,
    fontFace: FONTS.header, fontSize: 96, bold: true,
    color: COLORS.white, align: "left",
  });

  slide.addText("Airline Crew Sequences Meet Bad Weather", {
    x: 0.8, y: 3.8, w: 11.7, h: 0.6,
    fontFace: FONTS.header, fontSize: 28, italic: true,
    color: COLORS.ice, align: "left",
  });

  slide.addText("Identifying pilot flight pairings through DFW that should not share a sequence", {
    x: 0.8, y: 4.5, w: 11.7, h: 0.5,
    fontFace: FONTS.body, fontSize: 18, color: COLORS.ice,
  });

  // Bottom metadata
  slide.addShape("rect", {
    x: 0.8, y: 6.2, w: 4, h: 0.03,
    fill: { color: COLORS.coral }, line: { type: "none" },
  });
  slide.addText("EPPS-American Airlines Data Challenge  •  GROW 26.2", {
    x: 0.8, y: 6.3, w: 11.7, h: 0.4,
    fontFace: FONTS.body, fontSize: 14, color: COLORS.white,
  });
  slide.addText("github.com/drPod/stormchain   •   stormchain.streamlit.app", {
    x: 0.8, y: 6.75, w: 11.7, h: 0.4,
    fontFace: FONTS.body, fontSize: 12, color: COLORS.ice, italic: true,
  });
}

// ============================================================
// SLIDE 2 — The Problem in One Day (case study as hook)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("May 28, 2024", {
    x: 0.5, y: 0.4, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 36, bold: true, color: COLORS.midnight,
  });
  slide.addText("A single day at DFW — and the problem this model exists to solve", {
    x: 0.5, y: 1.05, w: 12, h: 0.4,
    fontFace: FONTS.body, fontSize: 16, italic: true, color: COLORS.slate,
  });

  // Big stat callouts
  const stats = [
    { label: "Weather-delayed inbound flights", value: "172", x: 0.5 },
    { label: "Outbound delays > 15 min", value: "471", x: 4.8 },
    { label: "Cascade cost (single day)", value: "$4.4M", x: 9.1 },
  ];
  stats.forEach((s) => {
    slide.addShape("rect", {
      x: s.x, y: 1.8, w: 3.8, h: 2.2,
      fill: { color: COLORS.white },
      line: { color: COLORS.lightGray, width: 1 },
    });
    slide.addText(s.value, {
      x: s.x, y: 1.95, w: 3.8, h: 1.3,
      fontFace: FONTS.header, fontSize: 64, bold: true,
      color: COLORS.deepBlue, align: "center", valign: "middle",
    });
    slide.addText(s.label, {
      x: s.x, y: 3.2, w: 3.8, h: 0.6,
      fontFace: FONTS.body, fontSize: 13, color: COLORS.charcoal,
      align: "center",
    });
  });

  // The mechanic explained
  slide.addShape("rect", {
    x: 0.5, y: 4.5, w: 12.4, h: 2.1,
    fill: { color: COLORS.midnight },
    line: { type: "none" },
  });
  slide.addText("THE CASCADE", {
    x: 0.8, y: 4.65, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 11, bold: true,
    color: COLORS.gold, charSpacing: 3,
  });
  slide.addText(
    "Thunderstorm at MCO delays inbound → pilot arrives DFW late → outbound to MIA departs late → " +
    "MIA has its own weather → delay compounds → ripple across the day.",
    {
      x: 0.8, y: 5.0, w: 11.8, h: 1.5,
      fontFace: FONTS.header, fontSize: 20, italic: true,
      color: COLORS.white, valign: "top",
    }
  );

  slide.addText("The question: which pairs of flights should NOT share a pilot sequence?", {
    x: 0.5, y: 6.75, w: 12.4, h: 0.4,
    fontFace: FONTS.body, fontSize: 14, bold: true,
    color: COLORS.deepBlue, align: "center",
  });

  addFooter(slide, 2);
}

// ============================================================
// SLIDE 3 — What We Built (4-quadrant grid)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("What We Built", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 36, bold: true, color: COLORS.midnight,
  });
  slide.addText("A working system — not a theoretical framework", {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 15, italic: true, color: COLORS.slate,
  });

  const items = [
    { title: "Data Pipeline", desc: "842K flights (BTS) + 3.5M weather obs (Open-Meteo) + 3.3M METAR obs (IEM)", x: 0.5, y: 1.7 },
    { title: "ML Model", desc: "XGBoost with AUC-ROC 0.81 on held-out 2024 data, 117 features, 1.5M training samples", x: 6.9, y: 1.7 },
    { title: "Risk Engine", desc: "37,920 pair-month risk scores + 1,220 avoid recommendations + 294 safe swaps", x: 0.5, y: 4.3 },
    { title: "Live Dashboard", desc: "7-tab Streamlit app deployed publicly — schedulers can use it tomorrow", x: 6.9, y: 4.3 },
  ];

  items.forEach((it, i) => {
    slide.addShape("rect", {
      x: it.x, y: it.y, w: 5.9, h: 2.4,
      fill: { color: COLORS.white },
      line: { color: COLORS.lightGray, width: 1 },
    });
    // Number accent
    slide.addShape("ellipse", {
      x: it.x + 0.3, y: it.y + 0.3, w: 0.6, h: 0.6,
      fill: { color: COLORS.deepBlue }, line: { type: "none" },
    });
    slide.addText(`${i + 1}`, {
      x: it.x + 0.3, y: it.y + 0.3, w: 0.6, h: 0.6,
      fontFace: FONTS.header, fontSize: 22, bold: true,
      color: COLORS.white, align: "center", valign: "middle",
    });
    slide.addText(it.title, {
      x: it.x + 1.1, y: it.y + 0.3, w: 4.5, h: 0.55,
      fontFace: FONTS.header, fontSize: 24, bold: true,
      color: COLORS.midnight, valign: "middle",
    });
    slide.addText(it.desc, {
      x: it.x + 0.4, y: it.y + 1.1, w: 5.1, h: 1.2,
      fontFace: FONTS.body, fontSize: 14, color: COLORS.charcoal,
    });
  });

  addFooter(slide, 3);
}

// ============================================================
// SLIDE 4 — The Model (two columns)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("Two Complementary Models", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 36, bold: true, color: COLORS.midnight,
  });
  slide.addText("Because one model couldn't serve both roles well", {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 15, italic: true, color: COLORS.slate,
  });

  // Left column — Risk Scoring
  slide.addShape("rect", {
    x: 0.5, y: 1.8, w: 6.1, h: 5.0,
    fill: { color: COLORS.white },
    line: { color: COLORS.deepBlue, width: 2 },
  });
  slide.addShape("rect", {
    x: 0.5, y: 1.8, w: 6.1, h: 0.7,
    fill: { color: COLORS.deepBlue }, line: { type: "none" },
  });
  slide.addText("Risk Scoring Model", {
    x: 0.5, y: 1.8, w: 6.1, h: 0.7,
    fontFace: FONTS.header, fontSize: 22, bold: true,
    color: COLORS.white, align: "center", valign: "middle",
  });
  slide.addText("PRODUCTION OUTPUT", {
    x: 0.5, y: 2.6, w: 6.1, h: 0.3,
    fontFace: FONTS.body, fontSize: 10, bold: true, charSpacing: 3,
    color: COLORS.gold, align: "center",
  });
  slide.addText(
    [
      { text: "• Weighted composite of pair-level features\n", options: {} },
      { text: "• Normalized to 0–100 scale\n", options: {} },
      { text: "• Per pair × per month → 37,920 scores\n", options: {} },
      { text: "• Weights cover all 4 PDF objectives:\n", options: {} },
      { text: "   − Delay propagation: 60%\n", options: { color: COLORS.slate } },
      { text: "   − Missed connections: 15%\n", options: { color: COLORS.slate } },
      { text: "   − Duty time: 10%\n", options: { color: COLORS.slate } },
      { text: "   − Fatigue: 10%\n", options: { color: COLORS.slate } },
    ],
    {
      x: 0.8, y: 3.0, w: 5.5, h: 3.6,
      fontFace: FONTS.body, fontSize: 14, color: COLORS.charcoal,
      valign: "top",
    }
  );

  // Right column — XGBoost
  slide.addShape("rect", {
    x: 6.8, y: 1.8, w: 6.0, h: 5.0,
    fill: { color: COLORS.white },
    line: { color: COLORS.teal, width: 2 },
  });
  slide.addShape("rect", {
    x: 6.8, y: 1.8, w: 6.0, h: 0.7,
    fill: { color: COLORS.teal }, line: { type: "none" },
  });
  slide.addText("XGBoost Classifier", {
    x: 6.8, y: 1.8, w: 6.0, h: 0.7,
    fontFace: FONTS.header, fontSize: 22, bold: true,
    color: COLORS.white, align: "center", valign: "middle",
  });
  slide.addText("VALIDATION + FEATURE DISCOVERY", {
    x: 6.8, y: 2.6, w: 6.0, h: 0.3,
    fontFace: FONTS.body, fontSize: 10, bold: true, charSpacing: 3,
    color: COLORS.gold, align: "center",
  });
  slide.addText(
    [
      { text: "• 117 features, 1.5M synthetic sequences\n", options: {} },
      { text: "• Temporal split: train 2019–2023, test 2024\n", options: {} },
      { text: "• Class imbalance handled (42.7:1)\n", options: {} },
      { text: "• AUC-ROC 0.81, AUC-PR 0.12\n", options: {} },
      { text: "• Drives feature weighting for risk scoring\n", options: {} },
      { text: "• Honest note: AUC-PR is low because", options: {} },
      { text: " cascading delays are 2.5% of sequences.\n", options: { italic: true, color: COLORS.slate } },
    ],
    {
      x: 7.1, y: 3.0, w: 5.4, h: 3.6,
      fontFace: FONTS.body, fontSize: 14, color: COLORS.charcoal,
      valign: "top",
    }
  );

  addFooter(slide, 4);
}

// ============================================================
// SLIDE 5 — The Proof (baseline comparison chart)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("The Proof — Beating a Naive Baseline", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 32, bold: true, color: COLORS.midnight,
  });
  slide.addText('Naive baseline: "just avoid pairs where both airports have above-median delay rates"', {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 14, italic: true, color: COLORS.slate,
  });

  // Bar chart
  slide.addChart(pptx.ChartType.bar, [
    {
      name: "Our Model",
      labels: ["K=50", "K=100", "K=200", "K=500"],
      values: [295, 563, 1090, 2600],
    },
    {
      name: "Naive Baseline",
      labels: ["K=50", "K=100", "K=200", "K=500"],
      values: [195, 335, 610, 1620],
    },
  ], {
    x: 0.5, y: 1.6, w: 8.0, h: 4.8,
    barDir: "col", barGrouping: "clustered",
    chartColors: [COLORS.deepBlue, COLORS.slate],
    catAxisLabelFontFace: FONTS.body,
    catAxisLabelFontSize: 12,
    valAxisLabelFontFace: FONTS.body,
    valAxisLabelFontSize: 10,
    showLegend: true,
    legendPos: "b",
    legendFontFace: FONTS.body,
    legendFontSize: 12,
    showValue: false,
    title: "Cascade Delay Minutes Caught (thousands)",
    showTitle: true,
    titleFontFace: FONTS.header,
    titleFontSize: 14,
    titleColor: COLORS.charcoal,
  });

  // Big callout on right
  slide.addShape("rect", {
    x: 8.8, y: 1.6, w: 4.2, h: 4.8,
    fill: { color: COLORS.deepBlue }, line: { type: "none" },
  });
  slide.addText("+78%", {
    x: 8.8, y: 2.2, w: 4.2, h: 1.4,
    fontFace: FONTS.header, fontSize: 88, bold: true,
    color: COLORS.white, align: "center",
  });
  slide.addText("more cascade minutes\ncaught at K=200", {
    x: 8.8, y: 3.8, w: 4.2, h: 0.8,
    fontFace: FONTS.body, fontSize: 14,
    color: COLORS.ice, align: "center",
  });
  slide.addShape("rect", {
    x: 9.6, y: 4.8, w: 2.6, h: 0.03,
    fill: { color: COLORS.gold }, line: { type: "none" },
  });
  slide.addText("176 pairs\nour model catches\nthe naive misses", {
    x: 8.8, y: 5.0, w: 4.2, h: 1.2,
    fontFace: FONTS.body, fontSize: 14, italic: true,
    color: COLORS.ice, align: "center",
  });

  // Key insight
  slide.addText(
    "This proves the model captures correlated weather, cascade mechanics, and turnaround " +
    "sensitivity — beyond what common-sense airport-level thinking catches.",
    {
      x: 0.5, y: 6.5, w: 12.4, h: 0.5,
      fontFace: FONTS.body, fontSize: 13, italic: true,
      color: COLORS.charcoal, align: "center",
    }
  );

  addFooter(slide, 5);
}

// ============================================================
// SLIDE 6 — The Product (avoid list + swap)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("The Product — Actionable Recommendations", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 32, bold: true, color: COLORS.midnight,
  });
  slide.addText("Not a risk score. A specific avoid list with swaps.", {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 15, italic: true, color: COLORS.slate,
  });

  // Avoid list table (left 2/3)
  slide.addText("AVOID LIST — SUMMER (JUN–AUG)", {
    x: 0.5, y: 1.7, w: 8.2, h: 0.35,
    fontFace: FONTS.body, fontSize: 11, bold: true, charSpacing: 2,
    color: COLORS.coral,
  });

  const tableRows = [
    [
      { text: "Pair", options: { bold: true, color: COLORS.white, fill: { color: COLORS.midnight }, fontSize: 13 } },
      { text: "Risk", options: { bold: true, color: COLORS.white, fill: { color: COLORS.midnight }, fontSize: 13, align: "center" } },
      { text: "Why", options: { bold: true, color: COLORS.white, fill: { color: COLORS.midnight }, fontSize: 13 } },
    ],
    [
      { text: "MCO → DFW → MIA", options: { fontFace: FONTS.body, fontSize: 14, bold: true } },
      { text: "96", options: { color: COLORS.coral, bold: true, align: "center", fontSize: 16 } },
      { text: "Correlated Florida thunderstorms, tight turnaround", options: { fontSize: 13 } },
    ],
    [
      { text: "ATL → DFW → MCO", options: { fontFace: FONTS.body, fontSize: 14, bold: true } },
      { text: "93", options: { color: COLORS.coral, bold: true, align: "center", fontSize: 16 } },
      { text: "Southeast storm system hits both", options: { fontSize: 13 } },
    ],
    [
      { text: "LAS → DFW → MCO", options: { fontFace: FONTS.body, fontSize: 14, bold: true } },
      { text: "94", options: { color: COLORS.coral, bold: true, align: "center", fontSize: 16 } },
      { text: "Afternoon convection + long flights", options: { fontSize: 13 } },
    ],
    [
      { text: "IAH → DFW → SAT", options: { fontFace: FONTS.body, fontSize: 14, bold: true } },
      { text: "77", options: { color: COLORS.coral, bold: true, align: "center", fontSize: 16 } },
      { text: "Texas storm corridor, shared weather cell", options: { fontSize: 13 } },
    ],
  ];

  slide.addTable(tableRows, {
    x: 0.5, y: 2.1, w: 8.2, h: 3.2,
    fontFace: FONTS.body,
    border: { pt: 0.5, color: COLORS.lightGray },
    rowH: [0.5, 0.65, 0.65, 0.65, 0.65],
    colW: [2.6, 0.9, 4.7],
  });

  // Swap recommendation callout (right 1/3)
  slide.addShape("rect", {
    x: 9.0, y: 1.7, w: 4.0, h: 3.6,
    fill: { color: COLORS.midnight }, line: { type: "none" },
  });
  slide.addText("SAFE SWAP", {
    x: 9.0, y: 1.85, w: 4.0, h: 0.3,
    fontFace: FONTS.body, fontSize: 11, bold: true, charSpacing: 2,
    color: COLORS.gold, align: "center",
  });
  slide.addText("Instead of", {
    x: 9.0, y: 2.25, w: 4.0, h: 0.35,
    fontFace: FONTS.body, fontSize: 12, italic: true,
    color: COLORS.ice, align: "center",
  });
  slide.addText("MCO → DFW → MIA", {
    x: 9.0, y: 2.6, w: 4.0, h: 0.5,
    fontFace: FONTS.header, fontSize: 18, bold: true,
    color: COLORS.white, align: "center",
  });
  slide.addText("risk 96", {
    x: 9.0, y: 3.1, w: 4.0, h: 0.3,
    fontFace: FONTS.body, fontSize: 12,
    color: COLORS.coral, align: "center", bold: true,
  });
  slide.addText("▼", {
    x: 9.0, y: 3.5, w: 4.0, h: 0.4,
    fontFace: FONTS.body, fontSize: 28,
    color: COLORS.gold, align: "center",
  });
  slide.addText("Assign", {
    x: 9.0, y: 3.95, w: 4.0, h: 0.35,
    fontFace: FONTS.body, fontSize: 12, italic: true,
    color: COLORS.ice, align: "center",
  });
  slide.addText("MCO → DFW → HRL", {
    x: 9.0, y: 4.3, w: 4.0, h: 0.5,
    fontFace: FONTS.header, fontSize: 18, bold: true,
    color: COLORS.white, align: "center",
  });
  slide.addText("risk 30", {
    x: 9.0, y: 4.8, w: 4.0, h: 0.3,
    fontFace: FONTS.body, fontSize: 12,
    color: COLORS.gold, align: "center", bold: true,
  });

  // Totals footer
  slide.addShape("rect", {
    x: 0.5, y: 5.7, w: 12.4, h: 1.2,
    fill: { color: COLORS.white },
    line: { color: COLORS.lightGray, width: 1 },
  });
  const totals = [
    { num: "1,220", label: "avoid recommendations", x: 0.8 },
    { num: "294", label: "safe swap alternatives", x: 5.0 },
    { num: "4", label: "seasonal views", x: 9.2 },
  ];
  totals.forEach((t) => {
    slide.addText(t.num, {
      x: t.x, y: 5.8, w: 3.8, h: 0.6,
      fontFace: FONTS.header, fontSize: 32, bold: true,
      color: COLORS.deepBlue, align: "center",
    });
    slide.addText(t.label, {
      x: t.x, y: 6.4, w: 3.8, h: 0.35,
      fontFace: FONTS.body, fontSize: 13, color: COLORS.charcoal,
      align: "center",
    });
  });

  addFooter(slide, 6);
}

// ============================================================
// SLIDE 7 — Case Study: May 28, 2024 (timeline)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("Case Study — May 28, 2024", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 32, bold: true, color: COLORS.midnight,
  });
  slide.addText('METAR at 05:53 UTC: "+TSRA FG SQ" — heavy thunderstorm, fog, squall, zero visibility', {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 14, italic: true, color: COLORS.slate,
  });

  // Timeline chart — delays by hour
  slide.addChart(pptx.ChartType.bar, [
    {
      name: "Cascade Delay (minutes)",
      labels: ["06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"],
      values: [2276, 11365, 4295, 9326, 4097, 4558, 1916, 3679, 970, 3200, 978, 4203, 2211, 3814, 1819, 464],
    },
  ], {
    x: 0.5, y: 1.6, w: 8.2, h: 4.6,
    barDir: "col",
    chartColors: [COLORS.coral],
    catAxisLabelFontFace: FONTS.body,
    catAxisLabelFontSize: 10,
    valAxisLabelFontFace: FONTS.body,
    valAxisLabelFontSize: 10,
    showLegend: false,
    title: "Cascade delay minutes by hour of inbound arrival",
    showTitle: true,
    titleFontFace: FONTS.header,
    titleFontSize: 14,
    titleColor: COLORS.charcoal,
    showCatAxisTitle: true,
    catAxisTitle: "Hour of Day (local time)",
    catAxisTitleFontSize: 11,
  });

  // Right side — key numbers and honest note
  const facts = [
    { label: "Realistic pilot sequences", value: "170" },
    { label: "With propagated delay", value: "149" },
    { label: "Total cascade cost", value: "$4.4M" },
  ];
  facts.forEach((f, i) => {
    const y = 1.6 + i * 1.0;
    slide.addShape("rect", {
      x: 9.0, y: y, w: 4.0, h: 0.9,
      fill: { color: COLORS.white },
      line: { color: COLORS.lightGray, width: 1 },
    });
    slide.addText(f.value, {
      x: 9.0, y: y, w: 1.6, h: 0.9,
      fontFace: FONTS.header, fontSize: 28, bold: true,
      color: COLORS.deepBlue, align: "center", valign: "middle",
    });
    slide.addText(f.label, {
      x: 10.6, y: y, w: 2.3, h: 0.9,
      fontFace: FONTS.body, fontSize: 12, color: COLORS.charcoal,
      valign: "middle",
    });
  });

  // Honest finding box
  slide.addShape("rect", {
    x: 9.0, y: 4.8, w: 4.0, h: 1.4,
    fill: { color: COLORS.midnight }, line: { type: "none" },
  });
  slide.addText("HONEST FINDING", {
    x: 9.0, y: 4.9, w: 4.0, h: 0.3,
    fontFace: FONTS.body, fontSize: 10, bold: true, charSpacing: 2,
    color: COLORS.gold, align: "center",
  });
  slide.addText(
    "Our model flagged only 9 of 170 sequences. Extreme days produce cascades on unusual routes. " +
    "Our strength: predictable seasonal patterns, not black swans.",
    {
      x: 9.15, y: 5.25, w: 3.8, h: 1.1,
      fontFace: FONTS.body, fontSize: 10, italic: true,
      color: COLORS.ice, valign: "top",
    }
  );

  addFooter(slide, 7);
}

// ============================================================
// SLIDE 8 — Methodology Evolution (list with numbers)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("Methodology Evolution", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 32, bold: true, color: COLORS.midnight,
  });
  slide.addText("We built it, critiqued our own work, and fixed 12 gaps", {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 15, italic: true, color: COLORS.slate,
  });

  // Two columns of fixes
  const fixes = [
    "Duty time violations → added FAA Part 117 features",
    "Fatigue risk → added WOCL exposure scoring",
    "Missed connections → added buffer adequacy",
    "Binary weather co-occurrence → cascade physics",
    "General weather proxies → integrated real METAR",
    "Inflated impact: $614M → recounted → $4.4M",
    "Inflated annual: $25M → adjusted to $438K",
    "DFW weather dominance → reframed as conditioning",
    "Airport-level → time-of-day patterns identified",
    "No actionable output → avoid list + swaps",
    "No case study → May 28, 2024 analyzed",
    "Low AUC-PR → reframed as rare-event expected",
  ];

  const col1 = fixes.slice(0, 6);
  const col2 = fixes.slice(6);

  col1.forEach((f, i) => {
    const y = 1.75 + i * 0.72;
    slide.addShape("ellipse", {
      x: 0.5, y: y, w: 0.45, h: 0.45,
      fill: { color: COLORS.deepBlue }, line: { type: "none" },
    });
    slide.addText(`${i + 1}`, {
      x: 0.5, y: y, w: 0.45, h: 0.45,
      fontFace: FONTS.header, fontSize: 14, bold: true,
      color: COLORS.white, align: "center", valign: "middle",
    });
    slide.addText(f, {
      x: 1.1, y: y - 0.05, w: 5.5, h: 0.5,
      fontFace: FONTS.body, fontSize: 13, color: COLORS.charcoal,
      valign: "middle",
    });
  });

  col2.forEach((f, i) => {
    const y = 1.75 + i * 0.72;
    slide.addShape("ellipse", {
      x: 7.0, y: y, w: 0.45, h: 0.45,
      fill: { color: COLORS.teal }, line: { type: "none" },
    });
    slide.addText(`${i + 7}`, {
      x: 7.0, y: y, w: 0.45, h: 0.45,
      fontFace: FONTS.header, fontSize: 14, bold: true,
      color: COLORS.white, align: "center", valign: "middle",
    });
    slide.addText(f, {
      x: 7.6, y: y - 0.05, w: 5.4, h: 0.5,
      fontFace: FONTS.body, fontSize: 13, color: COLORS.charcoal,
      valign: "middle",
    });
  });

  // Bottom — outcome box
  slide.addShape("rect", {
    x: 0.5, y: 6.3, w: 12.4, h: 0.7,
    fill: { color: COLORS.midnight }, line: { type: "none" },
  });
  slide.addText(
    "Outcome: AUC-ROC improved 0.75 → 0.81  •  Impact estimates became defensible  •  Tool became actionable",
    {
      x: 0.5, y: 6.3, w: 12.4, h: 0.7,
      fontFace: FONTS.body, fontSize: 14, bold: true, italic: true,
      color: COLORS.white, align: "center", valign: "middle",
    }
  );

  addFooter(slide, 8);
}

// ============================================================
// SLIDE 9 — Limitations (honesty)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.offWhite };

  slide.addText("What We Don't Know", {
    x: 0.5, y: 0.3, w: 12, h: 0.6,
    fontFace: FONTS.header, fontSize: 32, bold: true, color: COLORS.midnight,
  });
  slide.addText("Intellectual honesty — the limitations we've identified", {
    x: 0.5, y: 0.95, w: 12, h: 0.35,
    fontFace: FONTS.body, fontSize: 15, italic: true, color: COLORS.slate,
  });

  const limits = [
    {
      title: "DFW weather dominates XGBoost features",
      detail: "Expected — affects every sequence. Mitigated by risk-scoring model using pair-level features. Production should condition on DFW weather state.",
    },
    {
      title: "Rare route combinations slip through",
      detail: "Monthly aggregation can't score routes with sparse history. The May 28 case study showed extreme cascades on unusual pairs. Real-time monitoring complements the model.",
    },
    {
      title: "No access to actual crew schedules",
      detail: "We use synthetic sequences from matching inbound/outbound flights. AA's real crew assignments may differ. Internal data would refine this significantly.",
    },
    {
      title: "Single hub, 80 airports",
      detail: "Analysis covers DFW only. Extending to CLT, MIA, ORD, PHX, PHL — and full US airport universe — would multiply impact 5-6×.",
    },
  ];

  limits.forEach((l, i) => {
    const y = 1.7 + i * 1.3;
    slide.addShape("rect", {
      x: 0.5, y: y, w: 0.08, h: 1.1,
      fill: { color: COLORS.coral }, line: { type: "none" },
    });
    slide.addText(l.title, {
      x: 0.8, y: y, w: 12.0, h: 0.45,
      fontFace: FONTS.header, fontSize: 18, bold: true,
      color: COLORS.midnight,
    });
    slide.addText(l.detail, {
      x: 0.8, y: y + 0.45, w: 12.0, h: 0.7,
      fontFace: FONTS.body, fontSize: 13, color: COLORS.charcoal,
    });
  });

  addFooter(slide, 9);
}

// ============================================================
// SLIDE 10 — Closing (dark, match opening)
// ============================================================
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.midnight };

  slide.addShape("rect", {
    x: 0, y: 0, w: 13.33, h: 0.15,
    fill: { color: COLORS.coral }, line: { type: "none" },
  });

  slide.addText("What We're Delivering", {
    x: 0.8, y: 0.7, w: 11.7, h: 0.8,
    fontFace: FONTS.header, fontSize: 48, bold: true,
    color: COLORS.white,
  });

  const deliverables = [
    "A working, inspectable pipeline — full source on GitHub",
    "A live interactive dashboard — schedulers could use it tomorrow",
    "A concrete avoid list with swap recommendations",
    "A model that outperforms the naive baseline by 78%",
    "Honest documentation of what we know — and what we don't",
  ];

  deliverables.forEach((d, i) => {
    const y = 2.0 + i * 0.65;
    slide.addShape("ellipse", {
      x: 0.8, y: y + 0.1, w: 0.3, h: 0.3,
      fill: { color: COLORS.gold }, line: { type: "none" },
    });
    slide.addText(d, {
      x: 1.3, y: y, w: 11.5, h: 0.5,
      fontFace: FONTS.body, fontSize: 18,
      color: COLORS.white, valign: "middle",
    });
  });

  slide.addShape("rect", {
    x: 0.8, y: 5.5, w: 11.7, h: 0.03,
    fill: { color: COLORS.gold }, line: { type: "none" },
  });

  slide.addText(
    "$438K / year at DFW today. Across AA's full hub network — materially more.",
    {
      x: 0.8, y: 5.7, w: 11.7, h: 0.5,
      fontFace: FONTS.header, fontSize: 22, italic: true,
      color: COLORS.ice,
    }
  );

  slide.addText("Thank you.", {
    x: 0.8, y: 6.3, w: 11.7, h: 0.5,
    fontFace: FONTS.header, fontSize: 24, bold: true,
    color: COLORS.gold,
  });

  slide.addText("github.com/drPod/stormchain   •   stormchain.streamlit.app", {
    x: 0.8, y: 6.9, w: 11.7, h: 0.3,
    fontFace: FONTS.body, fontSize: 12, italic: true,
    color: COLORS.ice,
  });
}

// ============================================================
// Save
// ============================================================
pptx.writeFile({ fileName: "report/presentation.pptx" }).then((fileName) => {
  console.log(`Saved: ${fileName}`);
});
