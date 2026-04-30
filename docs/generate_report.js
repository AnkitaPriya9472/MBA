const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat,
} = require("docx");

// ── Shared config ──────────────────────────────────────────────
const PAGE = {
  size: { width: 12240, height: 15840 },
  margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
};
const CONTENT_WIDTH = 9360; // 12240 - 2*1440
const FONT = "Times New Roman";
const COLORS = { heading: "1B3A5C", accent: "2E75B6", light: "E8F0FE", white: "FFFFFF", black: "000000" };

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

// ── Helpers ────────────────────────────────────────────────────
function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, font: FONT, size: 32, bold: true, color: COLORS.heading })],
  });
}
function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: FONT, size: 28, bold: true, color: COLORS.accent })],
  });
}
function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160 },
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: FONT, size: 24, ...opts })],
  });
}
function paraRuns(runs) {
  return new Paragraph({
    spacing: { after: 160 },
    alignment: AlignmentType.JUSTIFIED,
    children: runs.map(r => typeof r === "string" ? new TextRun({ text: r, font: FONT, size: 24 }) : new TextRun({ font: FONT, size: 24, ...r })),
  });
}
function bulletItem(text, ref = "bullets") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 24 })],
  });
}
function numberItem(text, ref = "numbers") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 24 })],
  });
}
function emptyLine() {
  return new Paragraph({ spacing: { after: 120 }, children: [] });
}

function makeTable(headers, rows, colWidths) {
  const headerRow = new TableRow({
    children: headers.map((h, i) =>
      new TableCell({
        borders,
        width: { size: colWidths[i], type: WidthType.DXA },
        shading: { fill: COLORS.heading, type: ShadingType.CLEAR },
        margins: cellMargins,
        children: [new Paragraph({ children: [new TextRun({ text: h, font: FONT, size: 22, bold: true, color: COLORS.white })] })],
      })
    ),
  });
  const dataRows = rows.map(row =>
    new TableRow({
      children: row.map((cell, i) =>
        new TableCell({
          borders,
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { fill: COLORS.white, type: ShadingType.CLEAR },
          margins: cellMargins,
          children: [new Paragraph({ children: [new TextRun({ text: cell, font: FONT, size: 22 })] })],
        })
      ),
    })
  );
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows],
  });
}

// ── Numbering config ───────────────────────────────────────────
const numberingConfig = {
  config: [
    {
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "numbers",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets2",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets3",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets4",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets5",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets6",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "bullets7",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "numbers2",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
  ],
};

// ── Styles ─────────────────────────────────────────────────────
const styles = {
  default: { document: { run: { font: FONT, size: 24 } } },
  paragraphStyles: [
    {
      id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 32, bold: true, font: FONT, color: COLORS.heading },
      paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 },
    },
    {
      id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 28, bold: true, font: FONT, color: COLORS.accent },
      paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 },
    },
  ],
};

// ── Title page ─────────────────────────────────────────────────
function titlePage(title, subtitle, isEli5) {
  const children = [
    emptyLine(), emptyLine(), emptyLine(), emptyLine(), emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 100 },
      children: [new TextRun({ text: "IIT PATNA", font: FONT, size: 36, bold: true, color: COLORS.heading })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: "Department of Humanities and Social Sciences", font: FONT, size: 26, color: COLORS.accent })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [new TextRun({ text: "MBA Major Project Report", font: FONT, size: 28, bold: true })],
    }),
    isEli5 ? new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: "(Simplified / ELI5 Version)", font: FONT, size: 24, italics: true, color: COLORS.accent })],
    }) : emptyLine(),
    emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 60 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.accent, space: 8 } },
      children: [],
    }),
    emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 120 },
      children: [new TextRun({ text: title, font: FONT, size: 34, bold: true, color: COLORS.heading })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 300 },
      children: [new TextRun({ text: subtitle, font: FONT, size: 26, italics: true, color: COLORS.accent })],
    }),
    emptyLine(), emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [new TextRun({ text: "Submitted by", font: FONT, size: 22, color: "666666" })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: "Nitin", font: FONT, size: 28, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [new TextRun({ text: "MBA (Finance) \u2014 Semester 4", font: FONT, size: 24 })],
    }),
    emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [new TextRun({ text: "Under the Guidance of", font: FONT, size: 22, color: "666666" })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: "Prof. Nalin Bharti", font: FONT, size: 28, bold: true })],
    }),
    emptyLine(), emptyLine(),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "April 2026", font: FONT, size: 24, color: "666666" })],
    }),
  ];
  return children;
}

// ════════════════════════════════════════════════════════════════
//  NORMAL VERSION
// ════════════════════════════════════════════════════════════════
function buildNormalDoc() {
  const children = [
    ...titlePage(
      "Multi-Agent AI Simulation for Strategic Foresight",
      "Modelling Business Ecosystem Responses to External Shocks in the Indian Manufacturing Sector",
      false
    ),
    new Paragraph({ children: [new PageBreak()] }),

    // ── Section 1 ──
    heading1("1. Executive Summary"),
    para("This project builds a simulation tool that models how real-world business ecosystems respond to sudden disruptions \u2014 trade wars, supply chain crises, geopolitical conflicts, and regulatory changes. Instead of analysing one company in isolation (as traditional frameworks like SWOT or scenario planning do), this simulation places multiple actors \u2014 companies, governments, consumers, suppliers, and regulators \u2014 into the same virtual environment and lets them interact with each other over multiple rounds."),
    para("Each actor in the simulation is powered by artificial intelligence, grounded in real financial data from listed Indian companies, and programmed with realistic objectives and constraints drawn from annual reports and public filings. When an external shock is introduced (for example, \u201Cthe US imposes a 50% tariff on Indian steel\u201D), every actor responds \u2014 not just to the shock itself, but to what the other actors are doing. This creates a dynamic chain of reactions that mirrors how real economies behave."),
    para("The result is a strategic foresight tool: inject a disruption, observe how the ecosystem responds across multiple rounds, and extract actionable insights \u2014 before the disruption ever happens in the real world."),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 2 ──
    heading1("2. The Problem \u2014 Why Traditional Tools Fall Short"),
    para("Strategic planning in business schools and boardrooms typically relies on frameworks that are static and single-actor:"),
    bulletItem("SWOT Analysis examines one organisation at a time, without modelling how competitors or regulators will respond."),
    bulletItem("Scenario Planning creates \u201Cwhat-if\u201D narratives, but these are written by humans who cannot easily account for multi-actor feedback loops."),
    bulletItem("War-Gaming exercises are expensive, time-consuming, and limited by the imagination and biases of participants."),
    emptyLine(),
    para("The fundamental limitation: real economies are ecosystems, not isolated entities. When one actor makes a decision, it changes the landscape for everyone else \u2014 triggering a cascade of responses that reshape the entire system. A government retaliatory tariff changes the supplier\u2019s pricing calculus, which changes the consumer\u2019s options, which changes the company\u2019s strategy \u2014 and the cycle repeats."),
    para("No traditional framework can simulate these multi-actor, multi-round feedback dynamics. This project addresses that gap."),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 3 ──
    heading1("3. What We Built"),
    para("We developed a multi-agent simulation where AI-powered actors \u2014 each representing a real participant in a business ecosystem \u2014 respond to external shocks and to each other\u2019s decisions across multiple rounds."),
    heading2("Key Design Principles"),
    paraRuns([
      { text: "Real-World Grounding: ", bold: true },
      "Each agent is built using actual financial data from listed Indian companies. Tata Steel\u2019s agent, for example, knows its revenue (\u20B92.28 lakh crore), EBITDA margin (14.2%), iron ore self-sufficiency (65%), coking coal import dependency (85%), domestic market share (12%), and key strategic risks \u2014 all sourced from FY2024-25 annual reports.",
    ]),
    paraRuns([
      { text: "Multi-Actor Ecosystem: ", bold: true },
      "The simulation includes not just the company, but the full ecosystem \u2014 the Indian Government (Ministry of Steel & Commerce), steel consumers (automotive and construction sectors), iron ore suppliers, and regulators. Each has its own objectives, constraints, and decision-making logic.",
    ]),
    paraRuns([
      { text: "Dynamic Interaction: ", bold: true },
      "Agents don\u2019t just react to the shock \u2014 they react to each other. In Round 1, each actor sees the shock and makes an initial decision. In Round 2, every actor can see what the others decided in Round 1, and adjusts its strategy accordingly. This continues for multiple rounds, producing emergent dynamics that mirror real ecosystem behaviour.",
    ]),
    paraRuns([
      { text: "Memory and Adaptation: ", bold: true },
      "Each agent remembers its own past decisions and the decisions of others. Strategies evolve over time \u2014 an initial aggressive move may soften as the agent sees collaborative signals from others, or harden if the environment becomes more hostile.",
    ]),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 4 ──
    heading1("4. Scenarios Tested"),
    para("We designed and tested four distinct shock scenarios, each representing a different category of external disruption:"),
    emptyLine(),
    heading2("Scenario 1: US 50% Tariff on Indian Steel (Trade War)"),
    para("The United States imposes a 50% tariff on all Indian steel imports under Section 232, disrupting $1.8 billion in annual trade flows. This forces Indian producers to divert 2+ million tons of steel to already-competitive Asian and European markets, compressing margins industry-wide."),
    makeTable(["Parameter", "Detail"], [
      ["Severity", "High (0.85 / 1.0)"],
      ["Affected Sectors", "Steel, Manufacturing, Automotive"],
      ["Agents Involved", "Tata Steel, Indian Government, Steel Consumer, Iron Ore Supplier"],
    ], [3000, 6360]),
    emptyLine(),
    heading2("Scenario 2: Strait of Hormuz Closure (Geopolitical / Energy Crisis)"),
    para("An Iran-US military conflict leads to the blockade of the Strait of Hormuz \u2014 the chokepoint through which 20% of global oil supply transits. India, which imports 88% of its crude oil with 40% sourced from Gulf nations, faces an acute energy crisis. Brent crude surges past $150/barrel."),
    makeTable(["Parameter", "Detail"], [
      ["Severity", "Extreme (0.95 / 1.0)"],
      ["Affected Sectors", "Oil & Gas, Refining, Aviation, Manufacturing, Agriculture, Forex Markets"],
      ["Agents Involved", "Indian Oil Corporation, Indian Government (Energy), Indian Airlines, Farmers (Fertiliser), RBI"],
    ], [3000, 6360]),
    emptyLine(),
    heading2("Scenario 3: Australian Iron Ore Supply Disruption (Supply Chain Shock)"),
    para("Severe cyclone activity disrupts iron ore exports from Western Australia, reducing supply by 25 million tons. Indian producers, who import 40% of iron ore from Australia, face a 28% spot price spike during peak construction season."),
    makeTable(["Parameter", "Detail"], [
      ["Severity", "Moderate (0.6 / 1.0)"],
      ["Affected Sectors", "Steel, Mining"],
      ["Agents Involved", "Tata Steel, Indian Government, Steel Consumer, Iron Ore Supplier"],
    ], [3000, 6360]),
    emptyLine(),
    heading2("Scenario 4: Anti-Dumping Petition Against Chinese Steel (Regulatory)"),
    para("Indian steel industry files an anti-dumping petition against Chinese producers, alleging below-market pricing that has increased imports 35% year-over-year and depressed domestic prices by 12%."),
    makeTable(["Parameter", "Detail"], [
      ["Severity", "Low-Moderate (0.4 / 1.0)"],
      ["Affected Sectors", "Steel, Construction"],
      ["Agents Involved", "Tata Steel, Indian Government, Steel Consumer, Iron Ore Supplier"],
    ], [3000, 6360]),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 5 ──
    heading1("5. How the Simulation Works"),
    para("Think of it as a structured war-game played by AI actors instead of human participants:"),
    emptyLine(),
    paraRuns([{ text: "Step 1 \u2014 Setting the Stage: ", bold: true }, "We define the external shock (e.g., \u201CUS imposes a 50% tariff on Indian steel\u201D) and the participants (Tata Steel, Government, Consumers, Suppliers). Each participant is loaded with real-world data from annual reports and public filings."]),
    paraRuns([{ text: "Step 2 \u2014 Round 1 Reactions: ", bold: true }, "Every participant reads the shock description and makes its initial strategic decision. Tata Steel might decide to \u201Credirect exports to Southeast Asia.\u201D The Government might consider \u201Cretaliatory tariffs on US goods.\u201D The Consumer might plan to \u201Cseek alternative domestic suppliers.\u201D The Supplier might decide to \u201Creduce iron ore prices to support domestic steelmakers.\u201D"]),
    paraRuns([{ text: "Step 3 \u2014 Feedback Loop: ", bold: true }, "In Round 2, every participant can see what the others decided in Round 1. Now Tata Steel sees the Government is considering retaliatory tariffs (which could escalate tensions) and the Consumer is shifting to domestic sourcing (which could increase domestic demand). It adjusts its strategy accordingly."]),
    paraRuns([{ text: "Step 4 \u2014 Emergence: ", bold: true }, "Over 3\u20135 rounds, the ecosystem settles into a pattern \u2014 or doesn\u2019t. Some scenarios produce convergence (everyone finds a stable equilibrium). Others produce escalation spirals. The simulation captures these dynamics automatically."]),
    paraRuns([{ text: "Step 5 \u2014 Analysis: ", bold: true }, "We examine the trajectory of decisions, the evolution of confidence levels, which actors influenced others the most, and what second-order effects emerged that would be invisible in a static analysis."]),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 6 ──
    heading1("6. Theoretical Grounding"),
    para("This project is not purely a technology exercise \u2014 it is firmly grounded in established academic frameworks:"),
    emptyLine(),
    makeTable(
      ["Framework", "Application in This Project"],
      [
        ["PESTLE Analysis", "External shocks are mapped to Political, Economic, Social, Technological, Legal, and Environmental dimensions. Each scenario activates different PESTLE factors."],
        ["Porter\u2019s Five Forces", "The agent ecosystem is structured around competitive dynamics \u2014 rivalry, supplier power, buyer power, threat of substitutes, and regulatory barriers."],
        ["Game Theory (Prisoner\u2019s Dilemma)", "Multi-round interaction between agents models cooperative vs. competitive dynamics. Agents must decide whether to act in self-interest or signal cooperation."],
        ["Principal-Agent Theory", "Information asymmetry between actors (what one agent knows vs. what others can see) is built into the simulation through a visibility system."],
        ["Antitrust Economics", "Regulator agents monitor for anti-competitive behaviour and can intervene \u2014 modelling how regulatory oversight shapes market dynamics."],
      ],
      [3000, 6360]
    ),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 7 ──
    heading1("7. What Makes This Project Original"),
    numberItem("Beyond Static Analysis: Traditional MBA projects apply SWOT or Porter\u2019s to a single company. This project simulates the entire ecosystem dynamically.", "numbers"),
    numberItem("Real Data, Not Hypotheticals: Agents are grounded in actual financial data from Tata Steel, Indian Oil Corporation, and other listed companies \u2014 not made-up numbers.", "numbers"),
    numberItem("Multi-Actor Feedback Loops: The simulation captures second-order and third-order effects that single-actor analysis cannot \u2014 e.g., how a government retaliatory tariff changes not just the target, but the supplier\u2019s and consumer\u2019s behaviour too.", "numbers"),
    numberItem("Cross-Disciplinary Bridge: The project brings together strategic management theory (PESTLE, Porter\u2019s, Game Theory), agent-based modelling methodology (from computational economics), and modern AI capabilities.", "numbers"),
    numberItem("Practical Applicability: The tool can be used by companies, regulators, and strategists to test ecosystem reactions before disruptions happen.", "numbers"),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 8 ──
    heading1("8. Practical Applications and Relevance"),
    heading2("For Companies"),
    bulletItem("Test how your ecosystem will react to disruptions before they happen", "bullets2"),
    bulletItem("Identify second-order effects (e.g., \u201Cif we redirect exports, will domestic prices drop enough that consumers switch suppliers?\u201D)", "bullets2"),
    bulletItem("Stress-test strategies against different ecosystem responses", "bullets2"),
    emptyLine(),
    heading2("For Regulators and Policymakers"),
    bulletItem("Simulate policy interventions and see how the market actually responds", "bullets3"),
    bulletItem("Anticipate workarounds, unintended consequences, and feedback loops", "bullets3"),
    bulletItem("Model the impact of trade policies on employment, prices, and industry competitiveness", "bullets3"),
    emptyLine(),
    heading2("For Strategy Consultants and Risk Analysts"),
    bulletItem("Move from \u201Cwhat should the client do?\u201D to \u201Cwhat will the entire system do?\u201D", "bullets4"),
    bulletItem("Provide clients with simulation-backed scenario analysis", "bullets4"),
    bulletItem("Quantify ecosystem-level risks that qualitative frameworks cannot capture", "bullets4"),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 9 ──
    heading1("9. Limitations and Future Scope"),
    heading2("Current Limitations"),
    bulletItem("The simulation is a conceptual prototype \u2014 it demonstrates the methodology and produces meaningful insights, but is not a production-grade forecasting tool", "bullets5"),
    bulletItem("Agent behaviour is only as good as the data and constraints provided; real-world decision-making involves political, emotional, and information factors that are difficult to fully capture", "bullets5"),
    bulletItem("The number of agents and scenarios is limited to the Indian manufacturing sector in this phase", "bullets5"),
    emptyLine(),
    heading2("Future Research Directions"),
    bulletItem("Expand to additional sectors (automotive with Maruti Suzuki/EV disruption, banking, pharmaceuticals)", "bullets6"),
    bulletItem("Incorporate real-time data feeds from financial markets and news sources", "bullets6"),
    bulletItem("Back-test simulation outputs against known historical events for validation", "bullets6"),
    bulletItem("Develop into a web-based configurable tool for strategy consultants and risk analysts", "bullets6"),
    bulletItem("Add more sophisticated agent types (media, investors, labour unions, international bodies)", "bullets6"),

    new Paragraph({ children: [new PageBreak()] }),
    // ── Section 10 ──
    heading1("10. Conclusion"),
    para("This project demonstrates that AI-powered multi-agent simulation can serve as a powerful strategic foresight tool \u2014 one that goes beyond the static, single-actor limitations of traditional strategic planning frameworks. By grounding AI agents in real financial data from listed Indian companies and letting them interact dynamically across multiple rounds, the simulation produces emergent ecosystem-level insights that are practically impossible to generate through conventional analysis."),
    para("The key contribution is methodological: we show that agent-based modelling, combined with modern AI capabilities and real-world data, can bridge the gap between academic strategic frameworks (PESTLE, Porter\u2019s, Game Theory) and the dynamic, multi-actor reality of business ecosystems. This has direct implications for how companies, regulators, and strategists approach disruption planning and risk management."),
  ];

  return new Document({
    styles,
    numbering: numberingConfig,
    sections: [{
      properties: {
        page: PAGE,
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Multi-Agent AI Simulation for Strategic Foresight", font: FONT, size: 18, italics: true, color: "999999" })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Page ", font: FONT, size: 18, color: "999999" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "999999" })],
          })],
        }),
      },
      children,
    }],
  });
}

// ════════════════════════════════════════════════════════════════
//  ELI5 VERSION
// ════════════════════════════════════════════════════════════════
function buildEli5Doc() {
  const children = [
    ...titlePage(
      "Multi-Agent AI Simulation for Strategic Foresight",
      "Modelling Business Ecosystem Responses to External Shocks in the Indian Manufacturing Sector",
      true
    ),
    new Paragraph({ children: [new PageBreak()] }),

    heading1("1. What Is This Project About?"),
    para("Imagine a board game where each player represents a real company, a government, a customer group, or a raw material supplier. Now imagine that instead of humans rolling dice and making moves, each player is an AI that has memorised the actual financial reports, market data, and constraints of the real-world organisation it represents."),
    para("When something big happens in the world \u2014 say, the US suddenly slaps a massive tax on Indian steel \u2014 each AI player reacts. But here\u2019s the key: they don\u2019t just react to the event. They react to what the other players are doing. And then they react to those reactions. Round after round, the \u201Cgame\u201D plays out, and we get to watch what the entire business ecosystem does \u2014 not just one company."),
    para("That\u2019s this project in a nutshell: a simulation that lets us see how entire business ecosystems respond to big disruptions, before those disruptions actually happen."),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("2. Why Did We Build This?"),
    heading2("The Problem with How We Usually Plan"),
    para("In business schools and corporate boardrooms, when people want to figure out \u201Cwhat would happen if X occurred?\u201D, they typically use tools like:"),
    bulletItem("SWOT Analysis \u2014 looks at one company\u2019s strengths, weaknesses, opportunities, and threats. But it ignores what everyone else in the market will do.", "bullets"),
    bulletItem("Scenario Planning \u2014 humans write \u201Cwhat-if\u201D stories. But humans can\u2019t easily think through what happens when 5 different actors all react to each other simultaneously.", "bullets"),
    bulletItem("War Games \u2014 people role-play as different companies or governments. But this is expensive, slow, and limited by the players\u2019 imagination.", "bullets"),
    emptyLine(),
    heading2("The Core Insight"),
    para("The economy is not a chess game between two players. It\u2019s more like a football match with dozens of players, a referee, fans, and weather \u2014 all happening at once. When one player makes a move, it changes what every other player does next. Traditional tools can\u2019t capture this complexity. Our simulation can."),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("3. How Does It Work? (The Simple Version)"),
    para("Here\u2019s the process, step by step:"),
    emptyLine(),
    paraRuns([{ text: "Step 1: We create the players. ", bold: true }, "Each player is an AI loaded with real data. For example, the \u201CTata Steel\u201D player knows Tata Steel\u2019s actual revenue (\u20B92.28 lakh crore), how much iron ore it mines itself (65%), how much it depends on imported coal (85%), and what its biggest risks are. All from real annual reports."]),
    paraRuns([{ text: "Step 2: We drop a bomb. ", bold: true }, "Not literally! We introduce a \u201Cshock\u201D \u2014 a sudden event that disrupts the market. For example: \u201CThe US government imposes a 50% tax on all Indian steel imports.\u201D"]),
    paraRuns([{ text: "Step 3: Everyone reacts (Round 1). ", bold: true }, "Tata Steel might say: \u201CWe\u2019ll redirect our exports to Southeast Asia.\u201D The Indian Government might say: \u201CWe\u2019ll impose counter-tariffs on American goods.\u201D Steel consumers might say: \u201CWe\u2019ll push for more domestic supply.\u201D The iron ore supplier might say: \u201CWe\u2019ll lower prices to help Indian steelmakers.\u201D"]),
    paraRuns([{ text: "Step 4: Everyone reacts to the reactions (Round 2). ", bold: true }, "Now Tata Steel can see that the government is getting aggressive with counter-tariffs AND consumers want more domestic steel. This changes its calculation entirely. Maybe it now decides to invest more in domestic capacity instead of finding new export markets."]),
    paraRuns([{ text: "Step 5: Repeat for 3\u20135 rounds. ", bold: true }, "By the end, we can see whether the ecosystem found a stable balance or spiralled into escalation. We can see which player influenced the others most, what surprising knock-on effects emerged, and what strategies worked best."]),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("4. What Scenarios Did We Test?"),
    para("We tested four different types of disruptions to show the simulation works across different kinds of crises:"),
    emptyLine(),
    heading2("1. Trade War: US Tariff on Indian Steel"),
    para("The US slaps a 50% tax on Indian steel. $1.8 billion in trade is disrupted overnight. Indian steelmakers need to find new markets for 2+ million tons of steel that can no longer go to America."),
    para("Players: Tata Steel, Indian Government, Steel Consumers, Iron Ore Suppliers"),
    emptyLine(),
    heading2("2. Energy Crisis: Strait of Hormuz Blockade"),
    para("A military conflict between Iran and the US blocks the Strait of Hormuz \u2014 through which 20% of the world\u2019s oil flows. India, which imports 88% of its oil, suddenly can\u2019t get 40% of its supply. Oil prices double. The rupee crashes. Airlines, farmers, and factories all face a crisis at the same time."),
    para("Players: Indian Oil Corporation, Government (Energy Ministry), Airlines, Farmers, Reserve Bank of India"),
    emptyLine(),
    heading2("3. Supply Chain Shock: Australian Cyclone"),
    para("A massive cyclone in Western Australia disrupts iron ore mining \u2014 the main raw material for steel. India imports 40% of its iron ore from Australia. Prices spike 28% right when construction season demand is highest."),
    para("Players: Tata Steel, Indian Government, Steel Consumers, Iron Ore Suppliers"),
    emptyLine(),
    heading2("4. Regulatory Action: Anti-Dumping Case"),
    para("Indian steel companies file a legal complaint that Chinese steelmakers are selling steel in India below cost (dumping), hurting domestic producers. This triggers a government investigation that could result in extra tariffs on Chinese steel."),
    para("Players: Tata Steel, Indian Government, Steel Consumers, Iron Ore Suppliers"),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("5. What Theory Backs This Up?"),
    para("This isn\u2019t just a cool tech demo \u2014 it\u2019s built on serious academic frameworks that business students study:"),
    emptyLine(),
    makeTable(
      ["Framework", "How We Used It"],
      [
        ["PESTLE Analysis", "We classify each shock by whether it\u2019s Political, Economic, Social, Technological, Legal, or Environmental. This helps agents think about the right dimensions."],
        ["Porter\u2019s Five Forces", "Our simulation includes all five forces: competing companies, supplier power, buyer power, substitutes, and regulators. They all interact dynamically."],
        ["Game Theory", "Each round is like a move in a game. Agents must decide: cooperate or compete? Act aggressively or wait? Classic Prisoner\u2019s Dilemma dynamics emerge naturally."],
        ["Principal-Agent Theory", "Not everyone sees everything. Some agents have more information than others \u2014 just like in real markets where information asymmetry shapes decisions."],
        ["Antitrust Economics", "Regulator agents watch for anti-competitive behaviour and can step in, just as real regulators do."],
      ],
      [3000, 6360]
    ),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("6. Why Is This Original?"),
    para("Here\u2019s what makes this project different from a typical MBA project:"),
    emptyLine(),
    numberItem("Most MBA projects analyse one company. We simulate an entire ecosystem of interacting actors.", "numbers2"),
    numberItem("We use real data from actual listed companies (Tata Steel, Indian Oil Corporation, etc.) \u2014 not hypothetical case studies.", "numbers2"),
    numberItem("We capture ripple effects. When the government retaliates with tariffs, that doesn\u2019t just affect the US \u2014 it changes what the supplier does, what the consumer does, and eventually what the company itself does. Traditional analysis misses these feedback loops.", "numbers2"),
    numberItem("We bridge strategy theory with AI. This isn\u2019t just a tech project or just a strategy analysis \u2014 it\u2019s both, working together.", "numbers2"),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("7. Who Can Use This?"),
    heading2("Company Executives"),
    para("Before a crisis hits, run a simulation. See how your suppliers, customers, competitors, and regulators are likely to react. Plan for the second-order effects, not just the obvious first-order ones."),
    heading2("Government Policymakers"),
    para("Before imposing a new tariff or regulation, simulate how the market will actually respond. Anticipate workarounds, unintended consequences, and who really gets hurt."),
    heading2("Strategy Consultants"),
    para("Instead of telling a client \u201Chere\u2019s what you should do,\u201D show them: \u201Chere\u2019s what the entire system will do in response to different strategies.\u201D"),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("8. What Are the Limitations?"),
    para("Let\u2019s be honest about what this can and can\u2019t do:"),
    bulletItem("This is a prototype, not a crystal ball. It shows plausible ecosystem dynamics, not guaranteed predictions.", "bullets7"),
    bulletItem("AI agents are smart, but they can\u2019t capture everything a real human decision-maker considers \u2014 emotions, personal relationships, behind-the-scenes politics.", "bullets7"),
    bulletItem("We focused on the Indian manufacturing sector. Expanding to other industries and countries is future work.", "bullets7"),

    emptyLine(),
    heading2("Where Could This Go Next?"),
    bulletItem("Add more industries: automotive (EV disruption), banking, pharmaceuticals", "bullets7"),
    bulletItem("Connect to live market data so simulations use today\u2019s numbers, not last year\u2019s annual report", "bullets7"),
    bulletItem("Test the simulation against past real events (e.g., 2018 US steel tariffs) to validate accuracy", "bullets7"),
    bulletItem("Build it into a tool that anyone can use through a web browser", "bullets7"),

    new Paragraph({ children: [new PageBreak()] }),
    heading1("9. The Bottom Line"),
    para("Traditional strategic planning asks: \u201CWhat should our company do?\u201D"),
    para("This project asks a much more powerful question: \u201CWhat will the entire system do?\u201D"),
    para("By simulating the full business ecosystem \u2014 with real data, real constraints, and real interaction dynamics \u2014 we can generate insights that are impossible to reach through conventional analysis. The simulation shows not just first-order effects (\u201Cour exports will drop\u201D) but second-order and third-order effects (\u201C...which will cause domestic oversupply, which will depress prices, which will trigger government intervention, which will...\u201D)."),
    para("That\u2019s the power of multi-agent simulation: it lets us see the whole picture, not just our corner of it."),
  ];

  return new Document({
    styles,
    numbering: numberingConfig,
    sections: [{
      properties: { page: PAGE },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Multi-Agent AI Simulation \u2014 ELI5 Version", font: FONT, size: 18, italics: true, color: "999999" })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Page ", font: FONT, size: 18, color: "999999" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "999999" })],
          })],
        }),
      },
      children,
    }],
  });
}

// ── Generate both ──────────────────────────────────────────────
async function main() {
  const normalDoc = buildNormalDoc();
  const eli5Doc = buildEli5Doc();

  const [normalBuf, eli5Buf] = await Promise.all([
    Packer.toBuffer(normalDoc),
    Packer.toBuffer(eli5Doc),
  ]);

  fs.writeFileSync("docs/Project_Report_Supervisor.docx", normalBuf);
  fs.writeFileSync("docs/Project_Report_Supervisor_ELI5.docx", eli5Buf);

  console.log("Created: docs/Project_Report_Supervisor.docx");
  console.log("Created: docs/Project_Report_Supervisor_ELI5.docx");
}

main().catch(err => { console.error(err); process.exit(1); });
