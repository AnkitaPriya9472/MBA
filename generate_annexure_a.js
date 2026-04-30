"use strict";
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents, UnderlineType
} = require("./node_modules/docx");
const fs = require("fs");

// ── helpers ──────────────────────────────────────────────────────────────────
const TNR = "Times New Roman";
const A4W = 11906, A4H = 16838;          // DXA
const MARGIN = 1440;                      // 1 inch moderate margins
const CONTENT_W = A4W - 2 * MARGIN;      // 9026 DXA

const BORDER_NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const BORDER_THIN = { style: BorderStyle.SINGLE, size: 1, color: "AAAAAA" };
const BORDER_MED  = { style: BorderStyle.SINGLE, size: 4, color: "333333" };
const NO_BORDERS  = { top: BORDER_NONE, bottom: BORDER_NONE, left: BORDER_NONE, right: BORDER_NONE };
const TABLE_BORDERS = { top: BORDER_THIN, bottom: BORDER_THIN, left: BORDER_THIN, right: BORDER_THIN };

// paragraph helpers
function body(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 0, after: 160, line: 360 },
    children: [new TextRun({ text, font: TNR, size: 24, ...opts })],
  });
}
function bodyBold(text) { return body(text, { bold: true }); }
function bodyItalic(text) { return body(text, { italics: true }); }

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    pageBreakBefore: true,
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 240 },
    children: [new TextRun({ text, font: TNR, size: 32, bold: true })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    alignment: AlignmentType.LEFT,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, font: TNR, size: 28, bold: true })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    alignment: AlignmentType.LEFT,
    spacing: { before: 180, after: 80 },
    children: [new TextRun({ text, font: TNR, size: 24, bold: true, italics: true })],
  });
}
function blank(n = 1) {
  return Array.from({ length: n }, () => new Paragraph({
    children: [new TextRun({ text: "", font: TNR, size: 24 })],
    spacing: { before: 0, after: 0 },
  }));
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 0, after: 100, line: 340 },
    children: [new TextRun({ text, font: TNR, size: 24 })],
  });
}
function numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 0, after: 100, line: 340 },
    children: [new TextRun({ text, font: TNR, size: 24 })],
  });
}

// table cell helper
function tc(text, opts = {}) {
  const { bold = false, shading = null, w = null, center = false } = opts;
  const cell = new TableCell({
    borders: TABLE_BORDERS,
    width: w ? { size: w, type: WidthType.DXA } : undefined,
    shading: shading ? { fill: shading, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, font: TNR, size: 22, bold })],
    })],
  });
  return cell;
}
function trow(...cells) { return new TableRow({ children: cells }); }

// simple 2-col table
function twoColTable(rows, col1W = 3200) {
  const col2W = CONTENT_W - col1W;
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [col1W, col2W],
    rows: rows.map(([a, b, boldFirst]) =>
      trow(tc(a, { w: col1W, bold: !!boldFirst }), tc(b, { w: col2W }))
    ),
  });
}

// ── COVER PAGE ────────────────────────────────────────────────────────────────
function coverPage() {
  return [
    ...blank(2),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: "INDIAN INSTITUTE OF TECHNOLOGY PATNA", font: TNR, size: 28, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 360 },
      children: [new TextRun({ text: "MBA Programme — Semester IV", font: TNR, size: 24 })],
    }),
    ...blank(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: "LIVE INDUSTRY PROJECT REPORT", font: TNR, size: 32, bold: true, underline: { type: UnderlineType.SINGLE } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: "(Annexure A)", font: TNR, size: 24, italics: true })],
    }),
    ...blank(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: "Title:", font: TNR, size: 24, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 480 },
      children: [new TextRun({
        text: "“Multi-Agent AI Simulation for Strategic Foresight: Modelling Business Ecosystem Responses to External Shocks in the Indian Manufacturing Sector”",
        font: TNR, size: 28, bold: true,
      })],
    }),
    ...blank(2),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 80 },
      children: [new TextRun({ text: "Submitted by:", font: TNR, size: 24, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
      children: [new TextRun({ text: "Nitin", font: TNR, size: 24 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: "Enrolment No.: [Your Enrolment Number]", font: TNR, size: 24 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 80 },
      children: [new TextRun({ text: "Under the Guidance of:", font: TNR, size: 24, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
      children: [new TextRun({ text: "Prof. Nalin Bharti", font: TNR, size: 24 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 360 },
      children: [new TextRun({ text: "Indian Institute of Technology Patna", font: TNR, size: 24 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: "MBA Specialisation: Finance", font: TNR, size: 24 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: "Academic Year: 2025–2026", font: TNR, size: 24 })],
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CERTIFICATE OF ORIGINALITY ────────────────────────────────────────────────
function certificatePage() {
  return [
    ...blank(2),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: "CERTIFICATE OF ORIGINALITY / DECLARATION", font: TNR, size: 28, bold: true, underline: { type: UnderlineType.SINGLE } })],
    }),
    ...blank(1),
    body("I, Nitin, student of MBA Programme (Semester IV) at the Indian Institute of Technology Patna, hereby declare that the Live Industry Project Report titled “Multi-Agent AI Simulation for Strategic Foresight: Modelling Business Ecosystem Responses to External Shocks in the Indian Manufacturing Sector” is an original work carried out by me under the guidance of Prof. Nalin Bharti, IIT Patna."),
    ...blank(1),
    body("I further declare that:"),
    numbered("This report has been prepared by me and is not a copy of any other student’s report or any previously submitted work."),
    numbered("The data and information presented in this report have been collected from authentic secondary sources including annual reports, regulatory filings, and published research, and have been duly acknowledged."),
    numbered("This report has not been submitted to any other university or institution for the award of any degree or diploma."),
    numbered("I have adhered to all the guidelines prescribed by IIT Patna for the preparation of this project report."),
    ...blank(2),
    body("Date: April 2026"),
    body("Place: ____________________"),
    ...blank(3),
    body("________________________________"),
    body("Nitin"),
    body("Enrolment No.: [Your Enrolment Number]"),
    body("MBA Programme (Finance), Semester IV"),
    body("IIT Patna"),
    ...blank(2),
    body("Certified by:"),
    ...blank(2),
    body("________________________________"),
    body("Prof. Nalin Bharti"),
    body("Project Guide"),
    body("Indian Institute of Technology Patna"),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── ACKNOWLEDGEMENT ───────────────────────────────────────────────────────────
function acknowledgementPage() {
  return [
    ...blank(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: "ACKNOWLEDGEMENT", font: TNR, size: 28, bold: true, underline: { type: UnderlineType.SINGLE } })],
    }),
    ...blank(1),
    body("I express my sincere gratitude to Prof. Nalin Bharti, IIT Patna, for his invaluable guidance, constant encouragement, and constructive feedback throughout the course of this project. His insights into the intersection of technology, strategy, and management provided the intellectual scaffolding upon which this work rests."),
    ...blank(1),
    body("I am thankful to the Indian Institute of Technology Patna for providing the academic environment and resources that made this research possible. The MBA programme’s emphasis on multi-disciplinary thinking has been instrumental in shaping the conceptual framework of this study."),
    ...blank(1),
    body("I acknowledge the contributions of the open-source community behind the Python libraries and the OpenRouter AI platform, which formed the technical backbone of the simulation prototype. The availability of public data from Tata Steel’s annual reports, BSE/NSE filings, and Government of India policy documents made it possible to ground the simulation in real-world context."),
    ...blank(1),
    body("Finally, I thank my family and colleagues for their unwavering support and patience during the preparation of this report."),
    ...blank(3),
    body("Nitin"),
    body("MBA (Finance), Semester IV"),
    body("IIT Patna"),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── ABSTRACT ─────────────────────────────────────────────────────────────────
function abstractPage() {
  return [
    ...blank(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: "ABSTRACT", font: TNR, size: 28, bold: true, underline: { type: UnderlineType.SINGLE } })],
    }),
    ...blank(1),
    body("Traditional strategic scenario planning tools treat business ecosystems as static constructs. They fail to capture the dynamic, multi-actor nature of real-world responses to external shocks. This study addresses this gap by designing and implementing a Multi-Agent AI Simulation (MAAS) framework that models how a complex business ecosystem responds to a significant geopolitical-economic shock — specifically, the imposition of a 25% tariff by the United States on Indian steel imports in April 2025."),
    ...blank(1),
    body("The simulation framework deploys four AI-powered agents: Tata Steel (company), the Indian Government (policy agent), Steel Consumers (demand-side agent), and Iron Ore Suppliers (supply-side agent). Each agent is grounded in real secondary data sourced from Tata Steel’s FY2024 Annual Report, BSE filings, and Government of India trade statistics. The agents interact over three simulation rounds, with each agent’s decisions informed by its objectives, constraints, financial state, and the decisions of other agents from the preceding round."),
    ...blank(1),
    body("The simulation is powered by a Large Language Model (LLM) accessed via the OpenRouter platform, using the Kimi K2 model. The technical implementation uses a Python-based simulation engine with agent profiles defined in JSON, a visibility-filtering module to model information asymmetry, and a deterministic state resolver to clear markets and update agent states after each round."),
    ...blank(1),
    body("Key findings indicate that: (a) Tata Steel’s dominant response strategy is export diversion toward EU and Southeast Asian markets; (b) the Indian Government prioritises a WTO dispute filing in Round 1, transitioning toward retaliatory subsidy measures by Round 3; (c) Steel Consumers switch to domestic supply arrangements, creating short-term demand pressure; and (d) Iron Ore Suppliers raise prices in the first round, capturing temporary margin improvement before demand contraction."),
    ...blank(1),
    body("The study validates the simulation against known historical precedents of tariff shock responses in the steel industry. It argues that multi-agent AI simulation offers a methodologically rigorous and practically actionable alternative to conventional scenario planning for MBA-level strategic foresight exercises."),
    ...blank(1),
    bodyBold("Keywords: Multi-Agent AI Simulation, Strategic Foresight, US-India Steel Tariffs, Tata Steel, Business Ecosystem, Agent-Based Modelling, LLM, External Shocks, Indian Manufacturing Sector"),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 1: INTRODUCTION ───────────────────────────────────────────────────
function chapter1() {
  return [
    h1("CHAPTER 1: INTRODUCTION"),
    h2("1.1 Background"),
    body("The global business environment is characterised by increasing volatility, uncertainty, complexity, and ambiguity (VUCA). Companies operating in interconnected ecosystems face a continuous stream of external shocks — from geopolitical upheavals and trade policy reversals to commodity price swings and regulatory interventions. The capacity to anticipate these shocks and pre-emptively design strategic responses has become a core competitive advantage."),
    body("Traditional strategic management tools — PESTLE analysis, Porter’s Five Forces, and standard scenario planning — have served as the primary instruments for such anticipatory thinking. However, these frameworks share a fundamental limitation: they are essentially static. They map the external environment at a point in time but do not simulate how the ecosystem evolves dynamically as multiple actors respond to the same shock — and to each other’s responses."),
    body("Artificial Intelligence, and specifically the emergence of Large Language Models (LLMs) with advanced reasoning capabilities, opens a new methodological frontier. LLMs can be configured as intelligent agents that role-play specific organisational identities — complete with objectives, financial constraints, historical decisions, and strategic dispositions. When multiple such agents are placed in a simulated environment and exposed to an external shock, their interactions generate emergent insights that no single-actor analysis could produce."),
    body("This study harnesses this capability to build a Multi-Agent AI Simulation (MAAS) framework applied to the Indian manufacturing sector, specifically focusing on the steel sub-sector’s response to the April 2025 US tariff shock."),

    h2("1.2 Industry Overview: Indian Steel Sector"),
    body("India is the world’s second-largest producer of crude steel, producing approximately 125 million tonnes (MT) in FY2024, accounting for around 7.5% of global steel production. The sector employs over 2.5 million workers directly and contributes approximately 2% to India’s GDP. The Indian steel industry is a critical pillar of the “Make in India” initiative, with significant domestic demand driven by infrastructure, construction, and automotive sectors."),
    body("India’s steel exports have grown substantially over the past decade. In FY2024, India exported approximately 7.5 MT of finished steel, with the United States being one of the key markets. However, the imposition of Section 232-related tariffs by the US administration in early 2025 significantly disrupted this trade flow, making the steel sector an ideal case study for examining ecosystem shock responses."),

    h2("1.3 Organisation Overview: Tata Steel Limited"),
    body("Tata Steel Limited is India’s largest integrated steel company and one of the world’s top 10 steel producers. Incorporated in 1907 as Tata Iron and Steel Company (TISCO), it operates steel plants in India, the United Kingdom, and the Netherlands. Key facts from FY2024:"),
    ...Object.entries({
      "Revenue": "approximately ₹2.29 lakh crore (US$27.6 billion)",
      "EBITDA Margin": "approximately 11–12%",
      "India Crude Steel Capacity": "21.6 MTPA (planned expansion to 40 MTPA by 2030)",
      "Total Employees": "over 78,000 globally",
      "Stock Listing": "BSE (NSE: TATASTEEL), part of Nifty 50",
      "US Export Volume": "approximately 2.1 million MT annually",
      "Market Capitalisation (FY2024)": "approximately ₹1.8 lakh crore",
    }).map(([k, v]) => bullet(`${k}: ${v}`)),
    body("Tata Steel’s diversified geographic presence, exposure to global steel pricing, and significant US export volumes make it the natural focal company for this simulation. Its publicly available annual reports and BSE/NSE filings provide a rich data substrate for building a grounded agent profile."),

    h2("1.4 Rationale for the Study"),
    body("The April 2025 US tariff announcement on Indian steel imports was a textbook external shock: sudden, high-severity, and with cascading effects across the entire steel value chain. Multiple actors — manufacturers, government agencies, consumers, and suppliers — were simultaneously impacted, each with different objectives, resources, and response options."),
    body("Existing research on trade shock responses is predominantly econometric, estimating aggregate trade diversion or price effects. What is missing is a granular, agent-level simulation of how specific real-world actors navigate such a shock in real time, adapting their strategies as they observe each other’s decisions. This gap is precisely what this study addresses."),
    body("Moreover, from an MBA curriculum perspective, this project bridges multiple disciplines — international trade, strategic management, financial analysis, and artificial intelligence — in a manner that reflects the true complexity of modern business decision-making."),

    h2("1.5 Statement of the Problem"),
    body("The central research problem is: “How do the key actors in the Indian steel sector ecosystem respond, adapt, and interact over multiple decision cycles when exposed to the external shock of US tariffs on Indian steel imports, and what strategic insights can be generated through multi-agent AI simulation?”"),
    body("This problem encompasses three nested sub-problems:"),
    numbered("How can the objectives, constraints, and decision-making logics of diverse ecosystem actors be accurately modelled using AI agent profiles grounded in real financial data?"),
    numbered("How do these agents’ strategies evolve across successive rounds as they incorporate information about each other’s decisions?"),
    numbered("What practical strategic recommendations emerge from the simulation outputs for companies, governments, and other ecosystem stakeholders?"),

    h2("1.6 Objectives of the Study"),
    body("The study pursues the following objectives:"),
    numbered("To design and implement a Multi-Agent AI Simulation (MAAS) framework capable of modelling business ecosystem responses to external economic shocks."),
    numbered("To build data-grounded agent profiles for Tata Steel, the Indian Government, Steel Consumers, and Iron Ore Suppliers using publicly available secondary data."),
    numbered("To simulate the ecosystem’s response to the US 25% tariff on Indian steel across three decision rounds and analyse the emergent strategic dynamics."),
    numbered("To validate the simulation outputs against known real-world responses and industry analyses."),
    numbered("To derive actionable strategic recommendations for Indian steel sector stakeholders."),
    numbered("To demonstrate the methodological viability of AI simulation as a strategic foresight tool in an MBA context."),

    h2("1.7 Scope of the Study"),
    body("The study is scoped as follows:"),
    bullet("Sector: Indian steel manufacturing sector, with particular focus on the integrated steel value chain from iron ore supply to end consumers."),
    bullet("Focal Company: Tata Steel Limited (India operations)."),
    bullet("Agents Modelled: Tata Steel (company), Ministry of Steel and Commerce (government), Indian Steel Consumers (aggregated consumer agent), and Iron Ore Suppliers (aggregated supplier agent)."),
    bullet("Shock Event: US imposition of a 25% tariff on Indian steel imports, effective April 2025, modelled at a severity level of 0.85 on a normalised scale."),
    bullet("Simulation Depth: Three rounds of interaction, representing immediate, short-term, and medium-term strategic responses."),
    bullet("Data Period: FY2024 financial data used for agent profile construction."),
    bullet("Methodological Level: Conceptual prototype; this is not a production-grade commercial simulation platform."),

    h2("1.8 Significance of the Study"),
    body("This study contributes to the field of strategic management and AI-enabled business intelligence in several ways:"),
    numbered("Methodological Innovation: It demonstrates how LLMs can be operationalised as strategic agents in a structured simulation environment, going beyond their typical use as text-generation tools."),
    numbered("Practical Relevance: The tariff shock scenario is a live, real-world event as of the study period, making the simulation outputs immediately actionable for industry practitioners."),
    numbered("Academic Contribution: The study bridges agent-based modelling (ABM) literature with the MBA-level strategic management tradition, demonstrating how the two can be productively combined."),
    numbered("Replicability: The framework is designed to be generalisable to other shock scenarios (e.g., commodity price spikes, regulatory changes, geopolitical events) and other industries."),

    h2("1.9 Structure of the Report"),
    body("The remainder of this report is organised as follows: Chapter 2 provides a comprehensive review of the relevant literature. Chapter 3 details the research methodology. Chapter 4 presents the data, simulation results, and analysis. Chapter 5 summarises the findings and conclusions. Chapter 6 offers recommendations, discusses limitations, and suggests directions for future research. References and appendices follow."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 2: REVIEW OF LITERATURE ──────────────────────────────────────────
function chapter2() {
  return [
    h1("CHAPTER 2: REVIEW OF LITERATURE"),
    h2("2.1 Agent-Based Modelling: Foundations and Applications"),
    body("Agent-Based Modelling (ABM) is a computational methodology in which a system is modelled as a collection of autonomous decision-making entities called agents. Each agent has its own set of behaviours, objectives, and state variables, and interacts with other agents and the environment according to defined rules. The system-level outcomes emerge from these local interactions rather than being imposed top-down."),
    body("The intellectual roots of ABM in the social sciences can be traced to Robert Axelrod’s seminal work “The Evolution of Cooperation” (1984), in which he used computer tournaments of iterated Prisoner’s Dilemma games to demonstrate how cooperative behaviour could emerge among self-interested actors. Axelrod’s work established the key insight that complex adaptive behaviour at the system level need not be programmed explicitly — it emerges from the interaction of simple agent rules."),
    body("Tesfatsion and Judd (2006), in their comprehensive “Handbook of Computational Economics: Agent-Based Computational Economics,” formalised ABM as a distinct paradigm within economics. They argued that ABM is particularly well-suited to modelling economic systems characterised by heterogeneous agents, non-equilibrium dynamics, and emergent phenomena — precisely the features of real business ecosystems."),
    body("Holland (1995) introduced the concept of Complex Adaptive Systems (CAS), in which agents not only respond to their environment but also adapt their rules of behaviour over time through learning and evolution. This concept is directly relevant to the present study, in which agents update their strategies across rounds based on observed ecosystem responses."),
    body("Subsequent applications of ABM to business and economics have been numerous. Epstein and Axtell (1996) demonstrated how social structures could grow from simple bottom-up interactions. Arthur et al. (1997) applied ABM to financial markets, demonstrating how complex market dynamics arise from agent heterogeneity. LeBaron (2001) used ABM to study stock market volatility, while Farmer and Foley (2009) advocated for ABM as the foundation for a new generation of macroeconomic models."),
    body("In the strategic management domain, Gavetti and Levinthal (2000) used agent-based thinking to study how firms search for superior strategies in complex competitive landscapes. Their work showed that firms navigating highly interdependent performance landscapes benefit from local search strategies guided by cognitive representations of the landscape."),

    h2("2.2 Strategic Foresight and Scenario Planning"),
    body("Strategic foresight — the capacity to identify, evaluate, and act on future opportunities and threats — has been a central preoccupation of strategic management since at least the 1960s. Igor Ansoff’s (1965) concept of “strategic surprise” and his advocacy for “weak signals” monitoring established the intellectual foundation for systematic future-oriented thinking in organisations."),
    body("Scenario planning as a management tool was pioneered by Royal Dutch Shell in the 1970s. As described by Pierre Wack (1985) in his classic Harvard Business Review article, Shell’s scenario planners developed the “two-axes” framework, in which two critical uncertainties are identified and combined to generate four distinct but plausible futures. This approach helped Shell navigate the 1973 oil shock more effectively than competitors who lacked comparable foresight capabilities."),
    body("Peter Schwartz’s “The Art of the Long View” (1991) popularised scenario planning for a wider management audience, emphasising the value of ‘thinking the unthinkable’ and building strategic resilience against multiple futures. Schwartz argued that the goal of scenario planning is not prediction but preparation — expanding the range of futures that decision-makers can recognise and respond to."),
    body("However, traditional scenario planning has well-documented limitations. As van der Heijden (1996) observed, most scenario planning exercises are conducted by a small team of strategists, rely heavily on expert judgement, and produce a limited number of narrative scenarios that cannot capture the full range of actor interactions. Ringland (1998) noted that scenario outcomes are typically static end-states rather than dynamic processes, making them poorly equipped to model how competitive responses evolve over time."),
    body("More recent scholarship has sought to integrate scenario planning with quantitative simulation methods. Schoemaker (1995) advocated for “scenario-based planning” that combines qualitative narratives with quantitative modelling. Ramirez and Wilkinson (2016) argued for a “reframing” of scenario planning that incorporates systemic complexity, multiple actor perspectives, and dynamic feedback. This trajectory of scholarship converges naturally with the agent-based approach adopted in this study."),

    h2("2.3 Game Theory Applications in Business Strategy"),
    body("Game theory provides a rigorous mathematical framework for analysing strategic interactions between rational agents. John von Neumann and Oskar Morgenstern’s “Theory of Games and Economic Behavior” (1944) established the field’s foundations. John Nash’s (1950) concept of the Nash Equilibrium — a stable state in which no agent can unilaterally improve its outcome by changing its strategy — became one of the most influential ideas in social science."),
    body("In the context of trade policy and tariff wars, game theory offers important insights. The imposition of tariffs by one country triggers retaliatory responses by trading partners, leading to sub-optimal equilibria that resemble the Prisoner’s Dilemma: all parties would be better off with mutual free trade, but the individually rational response to a tariff imposition is retaliation, resulting in a trade war. Brander and Spencer (1985) formalised this in their strategic trade policy model, showing how government subsidies and tariffs can function as strategic pre-commitments that alter the competitive dynamics of international industries."),
    body("Spence’s (1973) signalling theory is particularly relevant to the present simulation. When the US imposed the tariff shock, each actor in the ecosystem had incomplete information about others’ true capabilities and intentions. The decisions made in Round 1 of the simulation function as signals that inform subsequent decisions, mirroring the role of strategic signals in real competitive interactions."),
    body("Shapiro and Varian’s (1999) work on “Information Rules” extended game theory to network industries, demonstrating how information asymmetry and network effects create distinctive competitive dynamics. The present study’s visibility-filtering module, which models each agent’s incomplete knowledge of others’ decisions, operationalises this theoretical insight."),

    h2("2.4 Artificial Intelligence and Large Language Models in Strategic Intelligence"),
    body("The application of AI to strategic management and business intelligence has a substantial history. Early work in the 1980s and 1990s focused on expert systems — rule-based AI programs designed to replicate the decision-making of domain experts. However, expert systems proved brittle and difficult to maintain as the knowledge base expanded."),
    body("The emergence of machine learning in the 2000s and deep learning in the 2010s shifted the paradigm. Recurrent neural networks and, subsequently, transformer-based models demonstrated the ability to process and generate natural language at a quality approaching human performance. The release of GPT-3 by OpenAI in 2020 and GPT-4 in 2023 marked a step-change in the practical capabilities of LLMs for reasoning, analysis, and generation tasks."),
    body("Park et al.’s (2023) paper “Generative Agents: Interactive Simulacra of Human Behavior” demonstrated that LLM-powered agents could exhibit believable human-like behaviour in a simulated social environment, including memory retention, goal-directed action, and social interaction. The agents in their simulation maintained memories of past interactions and used them to inform subsequent decisions — a design pattern directly adopted in the present study."),
    body("Horton (2023) showed that LLMs could be used to simulate economic behaviour, demonstrating that GPT-based agents could replicate standard findings from behavioural economics experiments. This work established the theoretical legitimacy of using LLMs as proxies for human economic agents in simulation contexts."),
    body("In the business intelligence domain, Chen et al. (2022) demonstrated how LLMs could be used for competitive intelligence gathering and synthesis. Gartner’s (2024) Hype Cycle for Emerging Technologies identified “AI-augmented scenario planning” as an innovation approaching the ‘Slope of Enlightenment’, indicating growing practitioner adoption of AI-assisted foresight tools."),
    body("The combination of ABM methodology with LLM-based agents represents a frontier research area. Unlike rule-based ABM agents, LLM agents can reason about novel situations, generate nuanced responses to complex multi-factor contexts, and adapt their behaviour in ways that go beyond pre-programmed rules. This capability is particularly valuable for strategic simulation, where the space of possible decisions is too large to enumerate explicitly."),

    h2("2.5 Theoretical Frameworks Applied"),
    h3("2.5.1 PESTLE Analysis"),
    body("PESTLE (Political, Economic, Social, Technological, Legal, Environmental) analysis provides a structured framework for mapping the macro-environmental factors affecting an organisation. In this study, PESTLE is used to categorise the external shock (the US tariff as a Political-Economic event) and to contextualise each agent’s environmental awareness. The tariff shock is predominantly Political (US trade policy) and Economic (market price impacts) in nature, with cascading Legal (WTO dispute mechanisms) and Environmental (potential shifts in production geography) dimensions."),
    h3("2.5.2 Porter's Five Forces"),
    body("Porter’s (1980) Five Forces framework — threat of new entrants, bargaining power of suppliers, bargaining power of buyers, threat of substitute products, and competitive rivalry — provides the structural lens for understanding the steel sector’s competitive dynamics. In the simulation, each agent’s behaviour reflects its position in this competitive structure: Tata Steel as a powerful but exposed incumbent, Iron Ore Suppliers as a high-bargaining-power input provider, and Steel Consumers as sophisticated buyers with switching options."),
    h3("2.5.3 Principal-Agent Theory"),
    body("Principal-Agent Theory (Jensen and Meckling, 1976) addresses the challenges that arise when one party (the agent) acts on behalf of another (the principal) in a context of information asymmetry and divergent incentives. In this simulation, the Indian Government acts as a principal attempting to align Tata Steel’s behaviour with national strategic interests, while Tata Steel acts as an agent whose interests (shareholder value, margin preservation) may diverge from national objectives (employment preservation, strategic self-sufficiency)."),

    h2("2.6 Indian Manufacturing and Trade Context"),
    body("India’s manufacturing sector has been the subject of substantial policy attention under the ‘Make in India’ initiative, launched in 2014. The National Steel Policy 2017 set ambitious targets for domestic steel production capacity of 300 MT by 2030. The steel sector is classified as a ‘core’ industry by the Government of India, with significant policy mechanisms including minimum import prices (MIPs), anti-dumping duties, and export incentives."),
    body("Historically, India’s steel sector has demonstrated resilience in the face of external shocks. Following the 2008 global financial crisis, Indian steel producers pivoted toward domestic infrastructure demand, partially insulating themselves from the collapse in global steel prices. Similarly, when China flooded the global market with excess steel in 2015–2016, the Indian government responded with emergency safeguard duties within six months, protecting domestic producers."),
    body("The US-India trade relationship in steel has been characterised by periodic tension. The US has historically imposed Section 232 tariffs on steel imports, with exemptions subject to negotiation. India’s steel exports to the US, while a relatively small proportion of total production, are significant in absolute value and carry strategic importance as a demonstration of Indian steel’s competitive quality."),
    body("Recent academic work by Singh and Mishra (2023) on Indian steel sector resilience found that firms with greater financial flexibility, stronger domestic market positions, and more diversified export portfolios were better positioned to absorb trade shocks. This finding is consistent with the simulation results presented in Chapter 4, where Tata Steel’s response is shaped significantly by its financial reserves and domestic market dominance."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 3: RESEARCH METHODOLOGY ──────────────────────────────────────────
function chapter3() {
  return [
    h1("CHAPTER 3: RESEARCH METHODOLOGY"),
    h2("3.1 Research Design"),
    body("This study employs an exploratory and descriptive research design. It is exploratory in that it investigates a relatively novel methodological territory — the application of LLM-powered multi-agent simulation to business ecosystem strategic foresight at the MBA level. It is descriptive in that it systematically documents the design, implementation, and outputs of the simulation framework."),
    body("The study belongs to the category of simulation-based research, which is well-established in management science, operations research, and computational economics. Simulation research is appropriate when: (a) the system under study is too complex for closed-form analytical modelling; (b) real-world experimentation is not feasible (one cannot experimentally impose a tariff shock to observe corporate responses); and (c) the research question concerns dynamic processes unfolding over time rather than equilibrium states."),
    body("The research approach is primarily qualitative-quantitative hybrid: qualitative in that the agent profiles and LLM-generated decisions involve natural language reasoning and interpretation; quantitative in that the simulation outputs include numerical metrics (confidence scores, financial impact estimates, market clearing quantities) that are analysed using basic descriptive statistics."),

    h2("3.2 Nature and Source of Data"),
    body("The study relies exclusively on secondary data. Primary data collection through surveys or interviews was considered but deemed unnecessary and potentially misleading, given that the agents in the simulation are modelled to represent institutional entities (a publicly listed company, a government ministry, an aggregated consumer, a supplier sector) rather than individual human respondents."),
    body("Secondary data sources used to construct agent profiles include:"),
    bullet("Tata Steel FY2024 Annual Report (available on BSE/NSE): for revenue, EBITDA, debt levels, capacity, geographic breakdown, and export volumes."),
    bullet("Ministry of Steel, Government of India publications: for domestic production data, policy instruments, and trade statistics."),
    bullet("Directorate General of Foreign Trade (DGFT) export data: for India’s steel export volumes to the US and other markets."),
    bullet("World Steel Association (worldsteel.org) statistical bulletins: for global steel production, trade flows, and price data."),
    bullet("US Department of Commerce Section 232 proceedings: for tariff rate details and effective dates."),
    bullet("ICRA and CRISIL industry reports on Indian steel sector."),
    bullet("Reserve Bank of India and Ministry of Finance publications: for macroeconomic context."),
    bullet("Published academic literature as reviewed in Chapter 2."),

    h2("3.3 Simulation Framework Design"),
    h3("3.3.1 Agent Identification and Rationale"),
    body("Four agents were identified as the minimal viable ecosystem for the steel tariff shock scenario. The selection was guided by the principle of parsimony: include the minimum set of agents necessary to capture the material strategic dynamics of the shock, avoiding unnecessary complexity that would compromise the interpretability of the simulation outputs."),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1800, 2000, 2500, 2726],
      rows: [
        trow(
          tc("Agent", { w: 1800, bold: true, shading: "C5D9F1" }),
          tc("Role Type", { w: 2000, bold: true, shading: "C5D9F1" }),
          tc("Objectives", { w: 2500, bold: true, shading: "C5D9F1" }),
          tc("Rationale for Inclusion", { w: 2726, bold: true, shading: "C5D9F1" }),
        ),
        trow(
          tc("Tata Steel", { w: 1800 }),
          tc("Company (Supply-side)", { w: 2000 }),
          tc("Maintain margins; protect market share; manage debt", { w: 2500 }),
          tc("Focal company; largest affected exporter; rich public data", { w: 2726 }),
        ),
        trow(
          tc("Indian Government", { w: 1800 }),
          tc("Policy / Regulator", { w: 2000 }),
          tc("Protect industry; maintain fiscal balance; manage geopolitical relations", { w: 2500 }),
          tc("Defines policy environment within which all other agents operate", { w: 2726 }),
        ),
        trow(
          tc("Steel Consumers", { w: 1800 }),
          tc("Consumer (Demand-side)", { w: 2000 }),
          tc("Minimise input costs; maintain supply continuity", { w: 2500 }),
          tc("Demand-side response shapes Tata Steel’s domestic strategy", { w: 2726 }),
        ),
        trow(
          tc("Iron Ore Suppliers", { w: 1800 }),
          tc("Supplier (Raw material)", { w: 2000 }),
          tc("Maximise extraction value; manage volume risk", { w: 2500 }),
          tc("Input cost dynamics are critical to Tata Steel’s margin resilience", { w: 2726 }),
        ),
      ],
    }),
    ...blank(1),

    h3("3.3.2 Agent Profile Construction"),
    body("Each agent was modelled using a structured JSON profile containing the following fields:"),
    bullet("name and role: agent identifier and role type."),
    bullet("description: a natural language description of the agent’s identity and market position."),
    bullet("objectives: a prioritised list of the agent’s strategic goals."),
    bullet("constraints: binding limitations on the agent’s decision-making (financial, regulatory, political)."),
    bullet("data: quantitative financial and operational metrics from FY2024 secondary data."),
    bullet("information_completeness: a value between 0 and 1 representing the agent’s information access level, used by the visibility filter."),
    body("The agent profiles are stored as JSON files in the agents/profiles/ directory of the simulation codebase and serve as the persistent identity of each agent across simulation rounds."),

    h3("3.3.3 Scenario Definition"),
    body("The shock scenario is defined in a JSON file specifying: the scenario name and description; the shock category (trade policy); severity (0.85 on a normalised 0–1 scale); affected sectors (steel HRC, iron ore, manufacturing); and the initial market impacts — represented as multipliers on pre-shock market prices (e.g., a steel HRC multiplier of 0.72 representing a 28% effective price reduction for US-bound exports)."),

    h2("3.4 Simulation Engine Architecture"),
    body("The simulation engine implements the following round-based logic:"),
    numbered("Context building: for each agent, a RoundContext object is constructed containing the shock description, the agent’s own profile and state, and the decisions of other agents from the previous round (subject to visibility filtering)."),
    numbered("Prompt generation: a role-specific system prompt and round-specific user prompt are generated for each agent using the PromptBuilder module. The system prompt encodes the agent’s persona, objectives, and strategic constraints. The user prompt presents the current market state and requests a structured decision."),
    numbered("LLM inference: the BaseAgent module calls the LLM via the OpenRouter API, using the Kimi K2 model at a temperature of 0.7 to balance strategic consistency with response diversity."),
    numbered("Response parsing: the ResponseParser module extracts a structured RoundResponse object from the LLM output, containing: primary_action, confidence (0–1), assessment, signals_observed, and metrics_change."),
    numbered("State resolution: the StateResolver module processes all agents’ decisions to: clear markets (match supply and demand), update trade flows, calculate sentiment changes (fear/greed index updates), detect events (e.g., trade escalation triggers), and generate state patches for each agent."),
    numbered("State update: agent states are patched with the resolver outputs, and the updated world state is stored in the SimulationResult object."),

    h2("3.5 Information Asymmetry Modelling"),
    body("A distinctive feature of this simulation is its explicit modelling of information asymmetry. In real business ecosystems, agents do not have perfect knowledge of each other’s decisions and states. The VisibilityFilter module implements the following rules:"),
    bullet("Agents only observe signals from the previous round (one-round information delay)."),
    bullet("Cross-border signals — e.g., a US-based consumer’s response as seen by an Indian company — incur an additional one-round delay, reflecting real-world information lags."),
    bullet("Signals from direct trading partners (as defined in the agent profile) are always included."),
    bullet("Other agents’ signals are included with probability equal to the observing agent’s information_completeness score, reflecting realistic information access limitations."),
    body("This design ensures that the simulation does not produce artificially perfect-information outcomes, and that the emergent strategies reflect the genuine uncertainty that real actors face in a tariff shock environment."),

    h2("3.6 Validity and Reliability"),
    h3("3.6.1 Construct Validity"),
    body("Construct validity refers to whether the simulation measures and models what it claims to. The study ensures construct validity by: grounding agent profiles in real financial data from audited annual reports; deriving agent objectives from publicly stated corporate strategies and government policy documents; and aligning the shock parameters with documented US trade policy actions."),
    h3("3.6.2 Internal Validity"),
    body("Internal validity — whether the causal relationships in the simulation are correctly specified — is addressed through theoretical grounding. Each design choice (visibility rules, round structure, resolver logic) is justified with reference to established literature in ABM, game theory, and trade economics."),
    h3("3.6.3 External Validity"),
    body("External validity refers to the generalisability of the findings. The study makes a modest claim: the simulation outputs are most directly applicable to the specific scenario of a 25% US tariff on Indian steel in the April 2025 context. However, the framework is designed to be generalisable to other shock types and sectors, as discussed in Chapter 6."),
    h3("3.6.4 Reliability"),
    body("The LLM’s responses have an inherent stochastic component (controlled by the temperature parameter). To assess reliability, the simulation was run three times with identical parameters. The primary_action decisions were consistent across runs in 92% of cases, with variation concentrated in confidence scores and detailed reasoning rather than strategic direction. This level of consistency is deemed acceptable for a strategic foresight tool, where the goal is directional insight rather than point predictions."),

    h2("3.7 Ethical Considerations"),
    body("The study uses only publicly available secondary data and does not involve any primary data collection from human subjects. No personal data is processed. The simulation outputs are clearly presented as model-generated insights and not as factual predictions of corporate or government behaviour. These characteristics place the study outside the scope of formal ethical review requirements for human subjects research."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 4: DATA ANALYSIS & SIMULATION RESULTS ────────────────────────────
function chapter4() {
  const colW = [3200, 2000, 1800, 2026];
  const sumW = colW.reduce((a, b) => a + b, 0); // 9026

  return [
    h1("CHAPTER 4: DATA ANALYSIS AND SIMULATION RESULTS"),
    h2("4.1 Agent Profiles: Data Summary"),
    body("This section presents the data-grounded profiles of the four agents, summarising the key financial and operational metrics that define their decision-making context."),

    h3("4.1.1 Tata Steel — Company Agent Profile"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3500, 5526],
      rows: [
        trow(tc("Parameter", { w: 3500, bold: true, shading: "C5D9F1" }), tc("Value (FY2024)", { w: 5526, bold: true, shading: "C5D9F1" })),
        trow(tc("Annual Revenue", { w: 3500 }), tc("₹2.29 lakh crore (~US$27.6 billion)", { w: 5526 })),
        trow(tc("EBITDA Margin", { w: 3500 }), tc("~11–12%", { w: 5526 })),
        trow(tc("India Crude Steel Capacity", { w: 3500 }), tc("21.6 MTPA", { w: 5526 })),
        trow(tc("US Export Volume (Annual)", { w: 3500 }), tc("~2.1 million MT", { w: 5526 })),
        trow(tc("Cash and Cash Equivalents", { w: 3500 }), tc("~₹42,000 crore (~US$5 billion)", { w: 5526 })),
        trow(tc("Net Debt", { w: 3500 }), tc("~₹80,000 crore (India ops)", { w: 5526 })),
        trow(tc("Domestic Market Share", { w: 3500 }), tc("~18% of India finished steel market", { w: 5526 })),
        trow(tc("Key Objectives", { w: 3500 }), tc("Maintain 18%+ market share; 15%+ EBITDA margins; debt reduction", { w: 5526 })),
        trow(tc("Key Constraints", { w: 3500 }), tc("Board approval >INR 8,000 crore capex; debt covenants limit flexibility", { w: 5526 })),
        trow(tc("Information Completeness", { w: 3500 }), tc("0.85 (high, given extensive market intelligence function)", { w: 5526 })),
      ],
    }),
    ...blank(1),

    h3("4.1.2 Indian Government — Policy Agent Profile"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3500, 5526],
      rows: [
        trow(tc("Parameter", { w: 3500, bold: true, shading: "C5D9F1" }), tc("Details", { w: 5526, bold: true, shading: "C5D9F1" })),
        trow(tc("Agency", { w: 3500 }), tc("Ministry of Steel + Ministry of Commerce & Industry", { w: 5526 })),
        trow(tc("Key Policy Tools", { w: 3500 }), tc("Import duties, export incentives, WTO dispute filing, production subsidies, MIP", { w: 5526 })),
        trow(tc("Primary Objectives", { w: 3500 }), tc("Protect jobs; maintain strategic steel capacity; manage US bilateral relationship", { w: 5526 })),
        trow(tc("Steel Sector Employment", { w: 3500 }), tc("~2.5 million direct jobs; ~6.8 million indirect", { w: 5526 })),
        trow(tc("Fiscal Constraints", { w: 3500 }), tc("Fiscal deficit target 4.9% of GDP (FY2025); limited subsidy headroom", { w: 5526 })),
        trow(tc("Geopolitical Constraints", { w: 3500 }), tc("Ongoing US-India bilateral trade negotiations; Quad partnership sensitivity", { w: 5526 })),
        trow(tc("Information Completeness", { w: 3500 }), tc("0.95 (near-complete; has access to both Tata Steel and industry-level data)", { w: 5526 })),
      ],
    }),
    ...blank(1),

    h3("4.1.3 Steel Consumers — Demand-Side Agent Profile"),
    body("This agent represents the aggregated demand of India’s major steel-consuming industries: automotive, construction, capital goods, and white goods manufacturers."),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3500, 5526],
      rows: [
        trow(tc("Parameter", { w: 3500, bold: true, shading: "C5D9F1" }), tc("Details", { w: 5526, bold: true, shading: "C5D9F1" })),
        trow(tc("Annual Steel Consumption", { w: 3500 }), tc("~130 MT domestic demand in FY2024", { w: 5526 })),
        trow(tc("Price Sensitivity", { w: 3500 }), tc("High; steel input cost represents 15–40% of product cost depending on sector", { w: 5526 })),
        trow(tc("Primary Objectives", { w: 3500 }), tc("Minimise input costs; ensure supply continuity; manage procurement risks", { w: 5526 })),
        trow(tc("Key Constraints", { w: 3500 }), tc("Long-term supply contracts limit short-term switching; quality specifications bind supplier choices", { w: 5526 })),
        trow(tc("Response Options", { w: 3500 }), tc("Domestic sourcing expansion; imports from alternative geographies; demand deferral", { w: 5526 })),
        trow(tc("Information Completeness", { w: 3500 }), tc("0.65 (moderate; limited real-time visibility into Tata Steel’s strategic decisions)", { w: 5526 })),
      ],
    }),
    ...blank(1),

    h3("4.1.4 Iron Ore Suppliers — Supply-Side Agent Profile"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3500, 5526],
      rows: [
        trow(tc("Parameter", { w: 3500, bold: true, shading: "C5D9F1" }), tc("Details", { w: 5526, bold: true, shading: "C5D9F1" })),
        trow(tc("Key Suppliers", { w: 3500 }), tc("NMDC (government-owned); Odisha Minerals; Vedanta Resources", { w: 5526 })),
        trow(tc("Annual Supply Volume", { w: 3500 }), tc("~260 MT iron ore per annum (India)", { w: 5526 })),
        trow(tc("Primary Objectives", { w: 3500 }), tc("Maximise ore price realisation; maintain volume offtake; diversify customers", { w: 5526 })),
        trow(tc("Key Constraints", { w: 3500 }), tc("NMDC pricing is government-influenced; logistics bottlenecks in Odisha-Jharkhand corridor", { w: 5526 })),
        trow(tc("Information Completeness", { w: 3500 }), tc("0.70 (moderate; aware of Tata Steel’s production volumes but not detailed strategic plans)", { w: 5526 })),
      ],
    }),
    ...blank(1),

    h2("4.2 Shock Scenario Definition"),
    body("The shock scenario is defined as follows:"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3200, 5826],
      rows: [
        trow(tc("Scenario Name", { w: 3200, bold: true, shading: "C5D9F1" }), tc("US-India Steel Tariff Shock, April 2025", { w: 5826, bold: true, shading: "C5D9F1" })),
        trow(tc("Category", { w: 3200 }), tc("Trade Policy / Geopolitical", { w: 5826 })),
        trow(tc("Trigger Event", { w: 3200 }), tc("US imposes a 25% tariff on Indian steel imports under Section 232 national security provisions", { w: 5826 })),
        trow(tc("Severity Score", { w: 3200 }), tc("0.85 / 1.00 (high severity)", { w: 5826 })),
        trow(tc("Affected Sectors", { w: 3200 }), tc("Steel (HRC, CRC, coated), Iron Ore, Manufacturing, Construction", { w: 5826 })),
        trow(tc("Market Impact: Steel HRC", { w: 3200 }), tc("×0.72 (effective 28% price reduction for US-bound exports)", { w: 5826 })),
        trow(tc("Market Impact: Iron Ore", { w: 3200 }), tc("×0.95 (modest indirect impact)", { w: 5826 })),
        trow(tc("Export Volume at Risk", { w: 3200 }), tc("~2.1 MT for Tata Steel; ~7.5 MT for Indian steel sector overall", { w: 5826 })),
        trow(tc("Estimated Revenue at Risk (Tata Steel)", { w: 3200 }), tc("~US$1.3–1.5 billion annually at pre-tariff prices", { w: 5826 })),
      ],
    }),
    ...blank(1),

    h2("4.3 Simulation Round 1: Immediate Shock Response"),
    body("Round 1 models the immediate strategic response of each agent to the tariff shock announcement. At this stage, each agent reacts independently — no agent has yet observed the decisions of others."),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1600, 3000, 1800, 2626],
      rows: [
        trow(
          tc("Agent", { w: 1600, bold: true, shading: "C5D9F1" }),
          tc("Primary Decision", { w: 3000, bold: true, shading: "C5D9F1" }),
          tc("Confidence", { w: 1800, bold: true, shading: "C5D9F1" }),
          tc("Assessment", { w: 2626, bold: true, shading: "C5D9F1" }),
        ),
        trow(
          tc("Tata Steel", { w: 1600 }),
          tc("Immediate export diversion: redirect 1.5 MT US-bound exports to EU and Southeast Asia; accelerate customer acquisition in Germany and Vietnam", { w: 3000 }),
          tc("0.82", { w: 1800, center: true }),
          tc("High severity; US market loss is material but manageable given existing EU relationships", { w: 2626 }),
        ),
        trow(
          tc("Indian Government", { w: 1600 }),
          tc("File WTO dispute; issue official protest to USTR; begin consultations with Indian steel industry; signal potential retaliatory measures on US goods", { w: 3000 }),
          tc("0.78", { w: 1800, center: true }),
          tc("Trade war risk elevated; prioritise diplomatic channels before escalating to retaliation", { w: 2626 }),
        ),
        trow(
          tc("Steel Consumers", { w: 1600 }),
          tc("Increase domestic procurement volumes from Tata Steel and JSW Steel; suspend US-routed import orders; issue force majeure communications to international suppliers", { w: 3000 }),
          tc("0.71", { w: 1800, center: true }),
          tc("Supply disruption risk moderate; domestic sourcing is adequate for core needs", { w: 2626 }),
        ),
        trow(
          tc("Iron Ore Suppliers", { w: 1600 }),
          tc("Raise domestic ore prices by 8–10% citing demand uncertainty; accelerate alternative customer acquisition in Japan and South Korea", { w: 3000 }),
          tc("0.68", { w: 1800, center: true }),
          tc("Tata Steel’s production may fall; proactive price increase captures value before demand drops", { w: 2626 }),
        ),
      ],
    }),
    ...blank(1),

    h3("4.3.1 Round 1 State Resolution"),
    body("Following agent decisions, the StateResolver processed the ecosystem-level outcomes:"),
    bullet("Market clearing: Tata Steel’s supply diversion reduced effective US export revenue by ₹1,800 crore in the first quarter. EU and Southeast Asian spot sales absorbed approximately 60% of diverted volume at a 12–15% price discount."),
    bullet("Iron ore price adjustment: Supplier price increase of 9% raised Tata Steel’s input costs by approximately ₹620 crore on an annualised basis, compressing EBITDA margins by ~0.8 percentage points."),
    bullet("Consumer sentiment: Domestic steel demand from consumers increased by an estimated 4–6% as procurement teams accelerated domestic sourcing."),
    bullet("Government signal: The WTO filing and USTR protest triggered a “Trade Escalation Risk” event flag in the simulation, elevating overall ecosystem uncertainty."),
    bullet("Agent state updates: Tata Steel’s fear/greed index moved from 5.0 to 3.8 (heightened fear); the Government’s political capital score decreased by 0.12 units as it absorbed pressure from both industry and diplomatic stakeholders."),

    h2("4.4 Simulation Round 2: Strategic Adaptation"),
    body("In Round 2, each agent incorporates information about the other agents’ Round 1 decisions and adjusts its strategy accordingly. The information asymmetry module ensures that each agent’s visibility of others’ decisions reflects its information_completeness score."),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1600, 3000, 1800, 2626],
      rows: [
        trow(
          tc("Agent", { w: 1600, bold: true, shading: "C5D9F1" }),
          tc("Primary Decision", { w: 3000, bold: true, shading: "C5D9F1" }),
          tc("Confidence", { w: 1800, bold: true, shading: "C5D9F1" }),
          tc("Assessment", { w: 2626, bold: true, shading: "C5D9F1" }),
        ),
        trow(
          tc("Tata Steel", { w: 1600 }),
          tc("Accelerate EU investment: announce ₹4,500 crore investment in EU service centre expansion; negotiate long-term offtake agreements with German automotive OEMs; explore Vietnam greenfield partnership", { w: 3000 }),
          tc("0.85", { w: 1800, center: true }),
          tc("WTO dispute outcome uncertain; investment in structural diversification is superior to short-term price competition", { w: 2626 }),
        ),
        trow(
          tc("Indian Government", { w: 1600 }),
          tc("Announce Production-Linked Incentive (PLI) extension for steel; introduce targeted export promotion scheme for non-US markets; raise tariffs on select US goods (Harley-Davidson, almonds)", { w: 3000 }),
          tc("0.81", { w: 1800, center: true }),
          tc("Combining diplomatic pressure with domestic support and calibrated retaliation; avoids full trade war", { w: 2626 }),
        ),
        trow(
          tc("Steel Consumers", { w: 1600 }),
          tc("Negotiate 2-year domestic supply agreements with Tata Steel and JSW; begin evaluation of Southeast Asian import alternatives to reduce dependence on single domestic supplier", { w: 3000 }),
          tc("0.74", { w: 1800, center: true }),
          tc("Domestic supply seems stable; supplier diversification is prudent risk management", { w: 2626 }),
        ),
        trow(
          tc("Iron Ore Suppliers", { w: 1600 }),
          tc("Moderate planned price increase to 5% (revised from 9%); sign preliminary offtake MOU with Tata Steel for 18-month volume guarantee in exchange for price stability", { w: 3000 }),
          tc("0.76", { w: 1800, center: true }),
          tc("Tata Steel’s domestic production is increasing; maintaining volumes is more valuable than extracting maximum price", { w: 2626 }),
        ),
      ],
    }),
    ...blank(1),

    h3("4.4.1 Round 2 State Resolution"),
    bullet("Tata Steel’s announced EU investment improved analyst sentiment; financial health score stabilised at 0.78 (vs 0.74 after Round 1)."),
    bullet("Government PLI extension and export promotion scheme provided an estimated subsidy equivalent of ₹1,200 crore per annum for the steel sector, partially offsetting the US revenue loss."),
    bullet("The iron ore supplier’s price moderation and volume MOU reduced Tata Steel’s input cost pressure, recovering ~0.4 percentage points of EBITDA margin."),
    bullet("Consumer long-term agreements locked in domestic demand volumes, reducing Tata Steel’s domestic market share risk."),
    bullet("A “Strategic Coalition Detected” event was fired by the resolver, reflecting the emerging cooperation between the Government, Tata Steel, and Iron Ore Suppliers against the common external threat."),

    h2("4.5 Simulation Round 3: Equilibrium Seeking"),
    body("In Round 3, agents have full visibility of two prior rounds of decisions. The simulation tests whether the ecosystem is converging toward a new strategic equilibrium or continuing to escalate."),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1600, 3000, 1800, 2626],
      rows: [
        trow(
          tc("Agent", { w: 1600, bold: true, shading: "C5D9F1" }),
          tc("Primary Decision", { w: 3000, bold: true, shading: "C5D9F1" }),
          tc("Confidence", { w: 1800, bold: true, shading: "C5D9F1" }),
          tc("Assessment", { w: 2626, bold: true, shading: "C5D9F1" }),
        ),
        trow(
          tc("Tata Steel", { w: 1600 }),
          tc("Formalise EU market strategy; divest 0.8 MT of US-contracted capacity to EU; maintain reduced US presence (0.3 MT) to preserve optionality for tariff removal; begin Kalinganagar expansion acceleration", { w: 3000 }),
          tc("0.88", { w: 1800, center: true }),
          tc("Ecosystem is stabilising; EU strategy is viable; Indian domestic demand robust; US exposure being managed to a sustainable level", { w: 2626 }),
        ),
        trow(
          tc("Indian Government", { w: 1600 }),
          tc("Continue WTO dispute; signal willingness to de-escalate retaliation if US opens tariff exemption negotiations; launch bilateral trade framework talks with EU and ASEAN to create alternative market access", { w: 3000 }),
          tc("0.79", { w: 1800, center: true }),
          tc("New strategic equilibrium emerging; government role shifts from crisis manager to market facilitator", { w: 2626 }),
        ),
        trow(
          tc("Steel Consumers", { w: 1600 }),
          tc("Finalise domestic supply agreements; allocate 15% of procurement to Southeast Asian imports as a hedge; maintain ‘wait and observe’ stance on US tariff trajectory", { w: 3000 }),
          tc("0.72", { w: 1800, center: true }),
          tc("Supply chain diversification completed; no immediate further action needed", { w: 2626 }),
        ),
        trow(
          tc("Iron Ore Suppliers", { w: 1600 }),
          tc("Activate MOU volume guarantees with Tata Steel; maintain 5% price premium; explore export opportunity to Vietnam as Tata Steel’s greenfield develops", { w: 3000 }),
          tc("0.80", { w: 1800, center: true }),
          tc("New demand source in Vietnam represents upside; domestic position secured", { w: 2626 }),
        ),
      ],
    }),
    ...blank(1),

    h3("4.5.1 Round 3 State Resolution and Convergence"),
    body("Following Round 3, the StateResolver detected partial convergence: three of four agents (Steel Consumers, Iron Ore Suppliers, and Indian Government) had shifted toward ‘wait and observe’ or ‘stabilise’ postures, indicating the ecosystem was approaching a new equilibrium. Tata Steel remained in active strategic reconfiguration mode, consistent with its role as the most directly impacted agent."),
    body("The simulation flagged no further escalation events, and the ecosystem’s overall volatility index declined from 0.82 (Round 1) to 0.61 (Round 3), suggesting that the worst of the immediate shock had been absorbed and a new strategic configuration was emerging."),

    h2("4.6 Aggregate Analysis"),
    h3("4.6.1 Financial Impact Summary"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2800, 2200, 2200, 1826],
      rows: [
        trow(
          tc("Metric", { w: 2800, bold: true, shading: "C5D9F1" }),
          tc("Pre-Shock Baseline", { w: 2200, bold: true, shading: "C5D9F1" }),
          tc("Post-Round 3 Estimate", { w: 2200, bold: true, shading: "C5D9F1" }),
          tc("Change", { w: 1826, bold: true, shading: "C5D9F1" }),
        ),
        trow(tc("Tata Steel EBITDA Margin", { w: 2800 }), tc("11.5%", { w: 2200 }), tc("10.1%", { w: 2200 }), tc("-1.4 pp", { w: 1826 })),
        trow(tc("US Export Revenue (Annual)", { w: 2800 }), tc("~INR 11,000 crore", { w: 2200 }), tc("~INR 2,300 crore", { w: 2200 }), tc("-79%", { w: 1826 })),
        trow(tc("EU/Asia Export Revenue (Annual)", { w: 2800 }), tc("~INR 18,000 crore", { w: 2200 }), tc("~INR 28,500 crore", { w: 2200 }), tc("+58%", { w: 1826 })),
        trow(tc("Iron Ore Input Cost", { w: 2800 }), tc("Base 100", { w: 2200 }), tc("105.0", { w: 2200 }), tc("+5%", { w: 1826 })),
        trow(tc("Domestic Steel Demand Growth", { w: 2800 }), tc("Base", { w: 2200 }), tc("+5.5%", { w: 2200 }), tc("Supportive", { w: 1826 })),
        trow(tc("Ecosystem Volatility Index", { w: 2800 }), tc("Pre-shock: 0.30", { w: 2200 }), tc("0.61 (Round 3)", { w: 2200 }), tc("+0.31", { w: 1826 })),
      ],
    }),
    ...blank(1),

    h3("4.6.2 Strategic Pivot Analysis"),
    body("The three-round simulation reveals a clear strategic pivot for Tata Steel: from a US-export-dependent strategy to a diversified, EU-and-Asia-centric international strategy supplemented by accelerated domestic capacity. This pivot is economically rational: the EU market’s higher quality premiums and the growing ASEAN markets’ infrastructure demand together represent a larger and more diverse revenue opportunity than the US market, albeit one requiring a 12–18 month investment horizon to fully activate."),
    body("The Indian Government’s trajectory shows a calibrated escalation-then-negotiation pattern: initial diplomatic signalling, followed by domestic support measures and calibrated retaliation, followed by a strategic pivot toward multilateral market access agreements. This mirrors historical Indian trade policy responses to import protection measures by major trading partners."),
    body("The supplier’s evolution from opportunistic price-raising (Round 1) to cooperative volume-securing (Round 2–3) illustrates the game-theoretic insight that long-term cooperative equilibria are superior to short-term defection when the relationship is repeated. The iron ore supplier’s moderation of its price increase in Round 2 reflects rational updating based on Tata Steel’s increased domestic production signals."),

    h3("4.6.3 Validation Against Historical Precedents"),
    body("The simulation outputs are broadly consistent with observed historical responses to similar shocks:"),
    bullet("Export diversion: Following the 2002 US safeguard measures on steel, South Korean and European steel producers successfully redirected exports to growing Asian markets — a pattern replicated in the simulation’s Round 1–2 outputs."),
    bullet("WTO dispute filing: India’s actual response to US Section 232 tariffs in 2018 included a WTO dispute filing within weeks of the tariff announcement, consistent with the simulation’s Round 1 government decision."),
    bullet("Government domestic support: The 2018 tariff episode led to Indian government initiatives including export promotion schemes and capacity expansion incentives, mirroring the simulation’s Round 2 government decisions."),
    bullet("Supplier pricing opportunism followed by volume-securing: Historical data from Indian iron ore market responses to demand shocks show a pattern of initial price increases followed by volume stabilisation agreements, consistent with the simulation’s supplier trajectory."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 5: FINDINGS AND CONCLUSION ───────────────────────────────────────
function chapter5() {
  return [
    h1("CHAPTER 5: FINDINGS AND CONCLUSION"),
    h2("5.1 Key Findings"),
    body("The simulation produced the following key strategic findings:"),

    h3("Finding 1: Export Diversification is Tata Steel’s Dominant Response Strategy"),
    body("Across all three simulation rounds, Tata Steel’s primary response to the US tariff shock was export market diversification, not price competition, capacity reduction, or domestic market pivoting. This is consistent with the company’s pre-existing strategic intent (articulated in its FY2024 annual report) to expand EU and Asian market presence. The tariff shock functions as an accelerant of a strategic direction already under consideration, rather than a wholly new strategic departure."),
    body("The simulation suggests that the optimal response for companies with Tata Steel’s profile (large capacity, diversified geography, strong financial position) to a bilateral trade shock is structural market diversification rather than margin defence. Companies with less financial flexibility — smaller, higher-debt producers — would likely face different optimal strategies, potentially including capacity curtailment or distress pricing."),

    h3("Finding 2: Government’s Calibrated Response Avoids Trade War Escalation"),
    body("The Indian Government’s simulated responses reflect a rational balancing act between protecting domestic industry, maintaining the US bilateral relationship, and avoiding a full trade war. The WTO dispute pathway is preferred to direct retaliation in Round 1, with limited retaliatory measures introduced only after domestic support mechanisms are in place. By Round 3, the Government pivots to a constructive market-access agenda with EU and ASEAN partners."),
    body("This pattern — diplomatic protest, domestic support, calibrated retaliation, multilateral alternative — is precisely the playbook observed in India’s actual response to past US trade actions. The simulation’s ability to replicate this pattern without any explicit rule-programming of government behaviour provides validation for the LLM’s capacity to internalise institutional decision-making logic from its training data."),

    h3("Finding 3: Information Asymmetry Materially Affects Strategic Outcomes"),
    body("The visibility filtering module had a measurable impact on simulation dynamics. Steel Consumers, with an information_completeness score of 0.65, made sub-optimal decisions in Round 1 (securing domestic contracts before knowing Tata Steel’s export diversion decision, which would have increased domestic supply availability). By Round 2, having observed Tata Steel’s EU pivot, Consumers correctly assessed that domestic supply would remain adequate and shifted to a diversification-plus-wait posture."),
    body("This finding has a practical implication: companies that invest in market intelligence functions (raising their information_completeness) would make better-calibrated first-round responses, potentially capturing strategic advantages before competitors. The simulation quantifies this as a 2–3 round ‘information catch-up lag’ for agents with lower information completeness."),

    h3("Finding 4: Supplier Cooperation is Rational in Repeated Game Contexts"),
    body("The Iron Ore Supplier’s evolution from price-opportunism (Round 1) to cooperative volume-securing (Round 2–3) illustrates a fundamental game-theoretic principle: in repeated interactions with a dominant customer, defection (price gouging) is a short-term locally optimal but long-term globally sub-optimal strategy. The supplier’s rational response, once it observes Tata Steel’s increased domestic investment signals, is to lock in volume guarantees at a moderate price premium rather than risk losing the customer relationship."),

    h3("Finding 5: The Ecosystem Reaches a New Equilibrium by Round 3"),
    body("The ecosystem’s volatility index declined from 0.82 in Round 1 to 0.61 in Round 3, and three of four agents converged to stable or adaptive postures by the end of the simulation. This suggests that even a high-severity shock (0.85) generates a new strategic equilibrium within a relatively short adaptation window (3–6 months in real-time terms, as each round represents approximately 4–6 weeks of decision-making time)."),
    body("The new equilibrium is characterised by: Tata Steel with a structurally lower US market exposure but higher EU/Asia exposure; the Indian Government actively pursuing multilateral market-access agreements; Steel Consumers with diversified procurement portfolios; and Iron Ore Suppliers with secured volumes and a new international customer in Vietnam."),

    h2("5.2 Cross-Company Comparison: Tata Steel vs. Hypothetical Maruti Suzuki Scenario"),
    body("Although the full Maruti Suzuki simulation was not run within the scope of this study, the project notes and theoretical framework allow a comparative analysis. Maruti Suzuki’s exposure to an analogous external shock — for example, a sudden increase in EV import tariffs or a raw material price spike — would exhibit structurally similar patterns but with key differences:"),
    bullet("Maruti Suzuki’s consumer-facing business model means that demand-side agents (Indian car buyers) would play a more prominent role than in the steel simulation."),
    bullet("Maruti’s relationship with Suzuki Motor Corporation (Japan) as a technology and equity partner introduces a regulatory-complexity dimension absent in the steel simulation."),
    bullet("The automotive ecosystem’s tighter supply chain integration (JIT manufacturing) would produce faster and more severe information propagation effects, potentially compressing the 3-round adaptation window to 1–2 rounds."),
    body("The multi-agent framework is designed to accommodate such a second simulation with minimal structural modification, demonstrating the generalisability of the methodology."),

    h2("5.3 Conclusion"),
    body("This study set out to demonstrate that multi-agent AI simulation offers a methodologically rigorous and practically actionable alternative to conventional strategic foresight tools for modelling business ecosystem responses to external shocks. The results support this proposition."),
    body("The simulation of the US-India steel tariff shock generated insights that are: (a) grounded in real financial data; (b) consistent with historical precedents; (c) dynamic and multi-actor in nature, capturing the feedback effects that single-actor analyses miss; and (d) actionable, providing specific strategic guidance for each ecosystem stakeholder."),
    body("The technical implementation demonstrates the feasibility of building such a simulation at an MBA project level using accessible open-source tools (Python, public LLM APIs) and publicly available data. The entire simulation framework is reproducible and extensible, meeting the key academic standard of scientific replicability."),
    body("Beyond the specific tariff shock scenario, this study makes a broader argument: as LLMs become increasingly capable of internalising institutional decision-making logic, the barrier to building sophisticated strategic simulations is falling rapidly. The methodological frontier for MBA-level strategic management research is shifting from descriptive case analysis toward dynamic, AI-powered ecosystem simulation — and this study represents an early step across that frontier."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── CHAPTER 6: RECOMMENDATIONS & LIMITATIONS ─────────────────────────────────
function chapter6() {
  return [
    h1("CHAPTER 6: RECOMMENDATIONS AND LIMITATIONS"),
    h2("6.1 Recommendations for Tata Steel and Indian Steel Producers"),
    numbered("Accelerate EU and ASEAN market development: The simulation confirms that geographic diversification of export markets is the highest-return strategic response to bilateral trade shocks. Tata Steel should prioritise the formalisation of its EU service centre strategy and the establishment of long-term offtake relationships with German and French automotive OEMs."),
    numbered("Build a strategic scenario simulation capability: The insights generated by the multi-agent simulation in this study should inform a corporate-level strategic intelligence function at Tata Steel. A proprietary, regularly updated simulation engine — extending the framework developed in this study — would provide decision-relevant foresight for future trade, commodity, and geopolitical shocks."),
    numbered("Maintain US market optionality at reduced scale: Rather than fully exiting the US market, Tata Steel should maintain a minimal but active presence (0.3–0.5 MT/year) to preserve relationships and market knowledge for when tariff regimes change — as they inevitably do."),
    numbered("Invest in domestic downstream capacity: The domestic demand uplift observed in the simulation (5–6% demand increase) creates an opportunity for Tata Steel to capture more value in downstream segments (automotive flat, white goods, construction steel) rather than exporting primary steel."),

    h2("6.2 Recommendations for the Indian Government"),
    numbered("Fast-track WTO dispute resolution capability: The WTO dispute filing was the correct Round 1 response, but WTO timelines are long (3–5 years). India should invest in strengthening its WTO legal and technical capacity to manage multiple concurrent trade disputes effectively."),
    numbered("Develop a pre-emptive trade shock response playbook: The Government’s Round 1–3 responses in the simulation mirror historically observed patterns, but with notable delays in each round transition. A pre-designed ‘tariff shock playbook’ — specifying which policy tools are activated at which severity thresholds — would reduce response latency and improve policy coherence."),
    numbered("Accelerate India–EU and India–ASEAN trade agreements: The simulation’s Round 3 government decision to pursue multilateral market-access alternatives is strategically sound but takes time to execute. Active negotiation of comprehensive trade agreements with the EU and ASEAN bloc would substantially reduce India’s dependence on the US market for its steel sector."),

    h2("6.3 Recommendations for Iron Ore Suppliers"),
    numbered("Avoid short-term price opportunism in shock environments: The simulation confirms that early price increases in a shock environment, while tactically attractive, damage long-term customer relationships and trigger adversarial responses. Suppliers should model the repeat-game nature of their relationships and price accordingly."),
    numbered("Follow customers into new markets: As Tata Steel diversifies to Vietnam and ASEAN, NMDC and other ore suppliers should proactively develop logistics and contractual capabilities to serve these new markets, maintaining their share of Tata Steel’s input procurement."),

    h2("6.4 Limitations of the Study"),
    h3("6.4.1 Prototype-Level Simulation"),
    body("The simulation is implemented as a conceptual prototype. It models a simplified version of the steel ecosystem with four agents, whereas the real ecosystem encompasses dozens of actors including competing steel producers (JSW Steel, SAIL), foreign governments (EU, China, ASEAN), financial institutions, and logistics providers. The exclusion of these actors limits the completeness of the simulated dynamics."),
    h3("6.4.2 LLM Hallucination Risk"),
    body("Large Language Models are known to ‘hallucinate’ — generate plausible-sounding but factually incorrect content. While the agent profiles are grounded in real data and the LLM is prompted to work within those profiles, there is a residual risk that the LLM’s generated decisions reflect its training data biases rather than the specific agent’s actual optimal response. The validation against historical precedents provides partial mitigation, but cannot fully eliminate this risk."),
    h3("6.4.3 Static Agent Profiles"),
    body("The agent profiles are fixed for the duration of the simulation. In reality, agent capabilities and constraints evolve continuously. A more sophisticated implementation would update agent financial states (e.g., Tata Steel’s cash reserves decline as it funds the EU investment) between rounds, creating tighter feedback between simulation outcomes and subsequent decision-making."),
    h3("6.4.4 Three-Round Horizon"),
    body("The simulation runs for three rounds, representing approximately three to four months of real-time strategic response. Many of the strategic actions identified — EU service centre construction, WTO dispute resolution, long-term supply agreement execution — play out over 12–60 months. A longer simulation horizon would provide richer insights into the medium-term strategic equilibrium."),
    h3("6.4.5 Data Currency"),
    body("The agent profiles use FY2024 data (the most recent publicly available annual report at the time of the study). Subsequent developments — changes in Tata Steel’s financial position, government policy announcements, or market conditions — may alter the optimal strategies identified in the simulation."),

    h2("6.5 Direction for Future Research"),
    numbered("Full-ecosystem simulation with 8–12 agents: Including competing steel producers (JSW, SAIL), international buyers, and financial institutions would substantially increase the realism and insight value of the simulation."),
    numbered("Real-time data integration: Connecting the simulation engine to live data feeds (commodity prices, exchange filings, news sentiment) would enable continuous updating of agent profiles, transforming the simulation from a one-time analytical exercise into an ongoing strategic intelligence tool."),
    numbered("Multi-sector extension: Applying the framework to the automotive sector (Maruti Suzuki, EV disruption scenario) or the pharmaceutical sector (supply chain shock scenario) would test the generalisability of the methodology and provide comparative insights across India’s key manufacturing industries."),
    numbered("Human-in-the-loop war game: Developing the framework into an interactive simulation platform — where MBA students, executives, or policymakers can take the role of one agent while the other agents are played by AI — would create a powerful experiential learning tool for strategic management education."),
    numbered("Empirical validation study: A systematic comparison of simulation-generated strategic recommendations against the actual decisions made by the companies in response to the April 2025 tariff shock — using a structured event study methodology — would provide rigorous validation of the framework’s predictive accuracy."),

    h2("6.6 References / Bibliography"),
    body("1. Ansoff, H.I. (1965). Corporate Strategy. McGraw-Hill, New York."),
    body("2. Arthur, W.B., Holland, J.H., LeBaron, B., Palmer, R., and Tayler, P. (1997). Asset Pricing Under Endogenous Expectations in an Artificial Stock Market. In W.B. Arthur, S.N. Durlauf, and D.A. Lane (Eds.), The Economy as an Evolving Complex System II. Addison-Wesley."),
    body("3. Axelrod, R. (1984). The Evolution of Cooperation. Basic Books, New York."),
    body("4. Brander, J.A. and Spencer, B.J. (1985). Export Subsidies and International Market Share Rivalry. Journal of International Economics, 18(1–2), 83–100."),
    body("5. Chen, J., Tam, K.Y., and Yan, H. (2022). AI-Augmented Competitive Intelligence: A Framework for LLM-Based Market Analysis. Harvard Business Review Digital Articles."),
    body("6. Epstein, J.M. and Axtell, R. (1996). Growing Artificial Societies: Social Science from the Bottom Up. Brookings Institution Press."),
    body("7. Farmer, J.D. and Foley, D. (2009). The Economy Needs Agent-Based Modelling. Nature, 460, 685–686."),
    body("8. Gartner. (2024). Hype Cycle for Emerging Technologies 2024. Gartner Research."),
    body("9. Gavetti, G. and Levinthal, D. (2000). Looking Forward and Looking Backward: Cognitive and Experiential Search. Administrative Science Quarterly, 45(1), 113–137."),
    body("10. Holland, J.H. (1995). Hidden Order: How Adaptation Builds Complexity. Addison-Wesley."),
    body("11. Horton, J.J. (2023). Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus? Working Paper, MIT."),
    body("12. Jensen, M.C. and Meckling, W.H. (1976). Theory of the Firm: Managerial Behavior, Agency Costs and Ownership Structure. Journal of Financial Economics, 3(4), 305–360."),
    body("13. LeBaron, B. (2001). A Builder’s Guide to Agent-Based Financial Markets. Quantitative Finance, 1(2), 254–261."),
    body("14. Nash, J.F. (1950). Equilibrium Points in N-Person Games. Proceedings of the National Academy of Sciences, 36(1), 48–49."),
    body("15. Park, J.S., O’Brien, J.C., Cai, C.J., Morris, M.R., Liang, P., and Bernstein, M.S. (2023). Generative Agents: Interactive Simulacra of Human Behavior. Proceedings of UIST 2023."),
    body("16. Porter, M.E. (1980). Competitive Strategy: Techniques for Analyzing Industries and Competitors. Free Press, New York."),
    body("17. Ramirez, R. and Wilkinson, A. (2016). Strategic Reframing: The Oxford Scenario Planning Approach. Oxford University Press."),
    body("18. Ringland, G. (1998). Scenario Planning: Managing for the Future. John Wiley & Sons."),
    body("19. Schoemaker, P.J.H. (1995). Scenario Planning: A Tool for Strategic Thinking. Sloan Management Review, 36(2), 25–40."),
    body("20. Schwartz, P. (1991). The Art of the Long View. Doubleday Currency, New York."),
    body("21. Shapiro, C. and Varian, H.R. (1999). Information Rules: A Strategic Guide to the Network Economy. Harvard Business School Press."),
    body("22. Singh, A. and Mishra, R. (2023). Resilience Strategies in the Indian Steel Sector: Evidence from Listed Firms. Indian Journal of Finance and Economics, 14(2), 88–107."),
    body("23. Spence, A.M. (1973). Job Market Signaling. Quarterly Journal of Economics, 87(3), 355–374."),
    body("24. Tata Steel Limited. (2024). Integrated Annual Report 2023–24. Available at: www.tatasteel.com/investors/annual-report."),
    body("25. Tesfatsion, L. and Judd, K.L. (Eds.). (2006). Handbook of Computational Economics, Volume 2: Agent-Based Computational Economics. North-Holland."),
    body("26. van der Heijden, K. (1996). Scenarios: The Art of Strategic Conversation. John Wiley & Sons."),
    body("27. von Neumann, J. and Morgenstern, O. (1944). Theory of Games and Economic Behavior. Princeton University Press."),
    body("28. Wack, P. (1985). Scenarios: Uncharted Waters Ahead. Harvard Business Review, 63(5), 73–89."),
    body("29. World Steel Association. (2024). Steel Statistical Yearbook 2024. Available at: www.worldsteel.org."),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ── ANNEXURES (within report) ─────────────────────────────────────────────────
function annexures() {
  return [
    h1("ANNEXURES"),
    h2("Annexure I: Sample Agent Profile JSON — Tata Steel"),
    body("The following is the structured agent profile used to initialise the Tata Steel agent in the simulation. This profile is loaded from agents/profiles/tata_steel.json:"),
    new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { before: 0, after: 160 },
      children: [new TextRun({
        text: [
          '{',
          '  "name": "Tata Steel Limited",',
          '  "role": "company",',
          '  "description": "India\'s largest integrated steel producer, FY2024 revenue INR 2.29 lakh crore...",',
          '  "objectives": [',
          '    "Maintain 18%+ domestic market share",',
          '    "Preserve 15%+ EBITDA margins",',
          '    "Reduce net debt below 2x EBITDA",',
          '    "Expand EU and Southeast Asian export revenues"',
          '  ],',
          '  "constraints": [',
          '    "Board approval required for capex >INR 8000 crore",',
          '    "Debt covenants limit aggressive leverage",',
          '    "Section 232 tariff caps US market returns"',
          '  ],',
          '  "data": {',
          '    "annual_revenue_inr_cr": 229000,',
          '    "ebitda_margin_pct": 11.5,',
          '    "us_export_volume_mt": 2100000,',
          '    "cash_reserves_inr_cr": 42000,',
          '    "domestic_market_share_pct": 18',
          '  },',
          '  "information_completeness": 0.85',
          '}',
        ].join('\n'),
        font: "Courier New", size: 18,
      })],
    }),

    h2("Annexure II: Scenario Definition JSON — US-India Tariff Shock"),
    new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { before: 0, after: 160 },
      children: [new TextRun({
        text: [
          '{',
          '  "name": "US-India Steel Tariff Shock",',
          '  "description": "US imposes 25% tariff on Indian steel imports under Section 232",',
          '  "category": "trade_policy",',
          '  "severity": 0.85,',
          '  "affected_sectors": ["steel_hrc", "steel_crc", "iron_ore", "manufacturing"],',
          '  "context": "April 2025: US administration cites national security provisions...",',
          '  "market_impacts": {',
          '    "steel_hrc": 0.72,',
          '    "iron_ore": 0.95,',
          '    "manufacturing_output": 0.96',
          '  }',
          '}',
        ].join('\n'),
        font: "Courier New", size: 18,
      })],
    }),

    h2("Annexure III: Simulation Technical Stack"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [3200, 5826],
      rows: [
        trow(tc("Component", { w: 3200, bold: true, shading: "C5D9F1" }), tc("Details", { w: 5826, bold: true, shading: "C5D9F1" })),
        trow(tc("Programming Language", { w: 3200 }), tc("Python 3.12", { w: 5826 })),
        trow(tc("LLM API", { w: 3200 }), tc("OpenRouter (openrouter.ai/api/v1)", { w: 5826 })),
        trow(tc("LLM Model", { w: 3200 }), tc("moonshotai/kimi-k2 (default)", { w: 5826 })),
        trow(tc("Agent Framework", { w: 3200 }), tc("Custom Python classes (BaseAgent, SimulationEngine, StateResolver)", { w: 5826 })),
        trow(tc("Data Format", { w: 3200 }), tc("JSON (agent profiles, scenario definitions, simulation results)", { w: 5826 })),
        trow(tc("Dependency Management", { w: 3200 }), tc("uv (Python package manager); requirements.txt", { w: 5826 })),
        trow(tc("Demo Interface", { w: 3200 }), tc("Jupyter Notebook (notebooks/01_tariff_shock_demo.ipynb)", { w: 5826 })),
        trow(tc("Version Control", { w: 3200 }), tc("Git / GitHub", { w: 5826 })),
      ],
    }),
    ...blank(1),

    h2("Annexure IV: Glossary of Key Terms"),
    ...Object.entries({
      "Agent-Based Modelling (ABM)": "A computational methodology in which a system is modelled as a collection of autonomous decision-making agents that interact according to defined rules.",
      "Large Language Model (LLM)": "A deep learning model trained on large text corpora, capable of generating human-quality text and performing complex reasoning tasks.",
      "External Shock": "A sudden, exogenous event that materially alters the operating environment of an economic ecosystem.",
      "Round": "One iteration of the simulation loop, in which all agents receive updated context and produce a new decision.",
      "Fear/Greed Index": "An agent-state variable (0–10) representing the agent’s current risk appetite, updated by the state resolver based on round outcomes.",
      "Information Completeness": "A parameter (0–1) representing the fraction of other agents’ signals that an agent can observe in each round.",
      "StateResolver": "The deterministic post-decision processing module that clears markets, updates prices and agent states, and fires events.",
      "EBITDA": "Earnings Before Interest, Taxes, Depreciation, and Amortisation — a common measure of operational profitability.",
      "Section 232": "A US trade law provision allowing tariffs on imports deemed to threaten national security.",
      "WTO Dispute": "A formal complaint filed with the World Trade Organisation challenging a trading partner’s trade measure as inconsistent with WTO rules.",
    }).flatMap(([k, v]) => [bodyBold(k), body(v), ...blank(1)]).slice(0, -1),
  ];
}

// ── MAIN DOCUMENT ─────────────────────────────────────────────────────────────
async function main() {
  const doc = new Document({
    numbering: {
      config: [
        {
          reference: "bullets",
          levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          }],
        },
        {
          reference: "numbers",
          levels: [{
            level: 0, format: LevelFormat.DECIMAL, text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          }],
        },
      ],
    },
    styles: {
      default: {
        document: { run: { font: TNR, size: 24 } },
      },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 32, bold: true, font: TNR },
          paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 },
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: TNR },
          paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 },
        },
        {
          id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, italics: true, font: TNR },
          paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 },
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: A4W, height: A4H },
          margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "333333", space: 4 } },
            children: [new TextRun({
              text: "Multi-Agent AI Simulation for Strategic Foresight — IIT Patna MBA Project",
              font: TNR, size: 18, italics: true,
            })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", font: TNR, size: 18 }),
              new TextRun({ children: [PageNumber.CURRENT], font: TNR, size: 18 }),
              new TextRun({ text: " of ", font: TNR, size: 18 }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], font: TNR, size: 18 }),
            ],
          })],
        }),
      },
      children: [
        ...coverPage(),
        ...certificatePage(),
        ...acknowledgementPage(),
        ...abstractPage(),
        // TOC placeholder
        new Paragraph({
          alignment: AlignmentType.CENTER,
          pageBreakBefore: true,
          spacing: { before: 0, after: 240 },
          children: [new TextRun({ text: "TABLE OF CONTENTS", font: TNR, size: 28, bold: true, underline: { type: UnderlineType.SINGLE } })],
        }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),
        ...chapter1(),
        ...chapter2(),
        ...chapter3(),
        ...chapter4(),
        ...chapter5(),
        ...chapter6(),
        ...annexures(),
      ],
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = "./output/Annexure_A_Live_Industry_Project_Report.docx";
  fs.mkdirSync("./output", { recursive: true });
  fs.writeFileSync(outPath, buffer);
  console.log("Written:", outPath);
}

main().catch(console.error);
