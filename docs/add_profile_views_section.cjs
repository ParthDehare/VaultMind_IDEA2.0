const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, BorderStyle, AlignmentType, ShadingType } = require('docx');
const fs = require('fs');
const path = require('path');

// We'll read the existing doc and append — but docx library doesn't support editing existing .docx
// So we create a standalone section document and then we write a complete replacement.
// We load the existing content by regenerating from scratch using the README as the source of truth.

// ---------- HELPER BUILDERS ----------
const h1 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 200 } });
const h2 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 320, after: 160 } });
const h3 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 240, after: 120 } });
const h4 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_4, spacing: { before: 200, after: 100 } });
const para = (text, bold = false, color = undefined) => new Paragraph({
  children: [new TextRun({ text, bold, color })],
  spacing: { after: 160 },
});
const bullet = (text, level = 0) => new Paragraph({
  text,
  bullet: { level },
  spacing: { after: 80 },
});
const codePara = (text) => new Paragraph({
  children: [new TextRun({ text, font: 'Courier New', size: 18, color: '444444' })],
  spacing: { after: 60 },
  shading: { type: ShadingType.SOLID, color: 'F3F4F6', fill: 'F3F4F6' },
});
const hr = () => new Paragraph({ text: '─────────────────────────────────────────────────────────', spacing: { before: 200, after: 200 }, alignment: AlignmentType.CENTER });
const tableRow2 = (cell1, cell2, isHeader = false) => new TableRow({
  children: [
    new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: cell1, bold: isHeader })] })], width: { size: 35, type: WidthType.PERCENTAGE } }),
    new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: cell2, bold: isHeader })] })], width: { size: 65, type: WidthType.PERCENTAGE } }),
  ],
});
const tableRow3 = (c1, c2, c3, isHeader = false) => new TableRow({
  children: [
    new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c1, bold: isHeader })] })], width: { size: 25, type: WidthType.PERCENTAGE } }),
    new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c2, bold: isHeader })] })], width: { size: 25, type: WidthType.PERCENTAGE } }),
    new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: c3, bold: isHeader })] })], width: { size: 50, type: WidthType.PERCENTAGE } }),
  ],
});

// ---------- SECTION CONTENT ----------
const profileSection = [
  hr(),
  h1('Phase 8 — Profile Detail View: Context-Sensitive Investigator UI'),
  para('When an investigator clicks any employee card on the Employee Watch screen, the system renders one of two entirely different panel layouts depending on the employee\'s Unified Threat Score.'),
  para('The goal of each view is different:', true),
  bullet('Forensic View (Score 90–100): Prove fraud and enable legal action.'),
  bullet('Baseline View (Score 0–40): Prove innocence and provide reassurance.'),

  hr(),

  // -------- HIGH RISK --------
  h2('HIGH-RISK PROFILE (Score: 90–100) — "The Forensic View"'),
  para('Investigator Intent: Investigate & Take Action', true),
  para('This view is shown when the Unified Threat Score is between 90 and 100. Every panel is purpose-built to help the FCU investigator build a legally defensible case. The layout uses dark-accented styling with red warning highlights throughout.'),

  h3('Panel 1 — Threat Spike Graph (Time-Series)'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Recharts <AreaChart> or <LineChart>')], spacing: { after: 80 } }),
  bullet('X-axis: Last 30 days (daily tick marks)'),
  bullet('Y-axis: Unified Threat Score (0–100)'),
  bullet('Line rendered in a gradient from amber (#F59E0B) at baseline to crimson (#DC2626) at peak'),
  bullet('A vertical dashed annotation line marks the Anomaly Onset Date — the first day the score crossed the alert threshold'),
  bullet('Two behavioural patterns are distinguishable: Sudden Spike (one-day jump > 40 points) and Slow Boil (linear rise over 30+ days)'),
  bullet('Tooltip on hover shows: Date | Score | Dominant Agent'),
  para('Purpose: Proves WHEN the anomaly began — critical for linking it to a real-world event (loan approval, system access, fund transfer).', false, '1D4ED8'),

  h3('Panel 2 — FundFlow Network Graph (GNN View)'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Cytoscape.js with cose-bilkent or dagre layout')], spacing: { after: 80 } }),
  para('RENDER CONDITION: This panel only renders if Agent 2 (FundFlow) or Agent 5 (NetworkIntel) contributed a score > 0. If neither fired, this panel is replaced with: "No network anomaly detected by Agent 2."', true),
  bullet('Node types: Employee (blue circle), Shell Company (red hexagon), Relative/Linked Account (orange diamond), External Bank (grey square)'),
  bullet('Edge colours: Green = normal flow | Red = flagged circular routing | Dashed = indirect/inferred link'),
  bullet('Fraudulent loop highlighted with pulsing red edge animation: Manager → Shell Company → Relative → Manager'),
  bullet('Node size encodes transaction volume (larger = more money moved)'),
  bullet('Clicking a node opens a tooltip: Entity Name | Role | Total Flow (₹) | First Seen'),
  para('Purpose: Visually proves the Circular Routing pattern — the backbone of layering fraud. A non-technical judge or auditor can understand this graph without reading any log files.', false, '1D4ED8'),

  h3('Panel 3 — Counterfactual Sliders (XAI / SHAP Interface)'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Radix UI <Slider> components — debounced API call to /api/xai/counterfactual/{employee_id}')], spacing: { after: 120 } }),
  para('Three sliders exposed to the investigator:'),
  new Table({
    rows: [
      tableRow3('Slider', 'Range', 'What It Modifies', true),
      tableRow3('Transaction Time', '6 AM → 11 PM', 'Shifts login/transaction hour toward business hours'),
      tableRow3('Daily Volume', '0 → 500% of peer avg', 'Reduces record access count toward peer median'),
      tableRow3('Transaction Amount', '₹0 → ₹50,00,000', 'Adjusts the single largest transaction in the window'),
    ],
    width: { size: 100, type: WidthType.PERCENTAGE },
  }),
  new Paragraph({ text: '', spacing: { after: 160 } }),
  bullet('Live score readout: Unified Threat Score updates in real time (debounced 300ms) as sliders are dragged'),
  bullet('Critical Threshold Line: A horizontal line at score = 60 shows exactly how far parameters need to shift before the employee drops out of CRITICAL status'),
  para('Purpose: Answers the key legal question "Why did the AI flag this person?" Investigator can demonstrate in court that the score would have been ~24/100 if the employee had worked normal hours — proving the AI responds to measurable behavioural deviation, not personal bias.', false, '1D4ED8'),

  h3('Panel 4 — Action Block'),
  para('Layout: Full-width bottom panel, pinned to the bottom of the scrollable detail view.'),
  new Paragraph({ children: [new TextRun({ text: 'PRIMARY BUTTON: ', bold: true }), new TextRun('[Generate STR Evidence]', )], spacing: { after: 80 } }),
  bullet('Colour: #DC2626 (red), white text label, subtle pulse animation on initial render'),
  bullet('On click: triggers Agent 7 pipeline — SHA-256 hash, Hyperledger Besu anchoring, 20-page PDF, STR draft to FIU-IND. Shows 4-step progress modal with live timer.'),
  bullet('After completion: button state changes to [STR Filed — View Evidence]'),
  new Paragraph({ children: [new TextRun({ text: 'SECONDARY BUTTON: ', bold: true }), new TextRun('[Mark as False Positive]')], spacing: { after: 80 } }),
  bullet('Colour: outlined grey, no fill'),
  bullet('On click: opens confirmation dialog requiring typed justification (minimum 50 characters)'),
  bullet('On confirm: submits HITL signal to weight_manager.py, reducing contributing agents\' weights. Logs investigator ID and timestamp.'),
  bullet('Below buttons: Read-only regulatory tag strip (from Agent 6): e.g., PMLA Rule 3 | RBI Master Direction 2024 §12.4 | BSA 2023 §63'),

  hr(),

  // -------- NORMAL PROFILE --------
  h2('NORMAL PROFILE (Score: 0–40) — "The Baseline View"'),
  para('Investigator Intent: Reassurance — Prove why this employee is safe', true),
  para('This view is shown when the Unified Threat Score is between 0 and 40. The design language shifts from red/dark-threat to green/calm. No fraud-investigation panels are shown. Instead, the UI visually proves the employee\'s normalcy through positive evidence.'),

  h3('Panel 1 — Peer Comparison Radar Chart'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Recharts <RadarChart> with two overlapping datasets')], spacing: { after: 80 } }),
  para('Six radar axes (dimensions):'),
  bullet('Daily Transaction Volume'),
  bullet('Working Hours (spread of login/logout times)'),
  bullet('Record Access Rate'),
  bullet('Geographic Consistency (IP location variance)'),
  bullet('After-Hours Activity'),
  bullet('Peer Deviation Score'),
  para('Two shapes rendered simultaneously:'),
  bullet('Blue fill = This employee\'s normalised scores on all 6 dimensions'),
  bullet('Grey fill = Median of all ~50 clerks in the same branch K-Means peer cluster (same role)'),
  bullet('Visual indicator: If cosine similarity > 0.85, green banner appears: "Behavioural Profile Consistent with Peer Cluster"'),
  para('NOTE: The GNN graph is NOT rendered in this view. Keeping the panel uncluttered is intentional — the absence of a network graph is itself a signal of normalcy.', true),
  para('Purpose: The most powerful reassurance visual. Proves at a glance that this employee is not an outlier — their behaviour is typical of their role, branch, and peer group.', false, '166534'),

  h3('Panel 2 — Activity Heatmap (GitHub-style Contribution Graph)'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Custom SVG grid or react-calendar-heatmap')], spacing: { after: 80 } }),
  bullet('Layout: 52 columns × 7 rows (7 days × 52 weeks = 1 year rolling view)'),
  para('Cell colour scale:'),
  bullet('0 transactions → #1A1A2E (dark, near-black)'),
  bullet('Low activity (9 AM–1 PM) → #166534 (muted green)'),
  bullet('Normal activity (9 AM–6 PM) → #16A34A (standard green)'),
  bullet('High activity → #4ADE80 (bright green)'),
  bullet('RULE: Any cell outside the 6 AM–8 PM window is capped at minimum colour — visually proving the employee is inactive at night'),
  para('Key visual signatures for a clean profile:'),
  bullet('Weekdays show consistent green; weekends are near-black'),
  bullet('No cells outside 9 AM–6 PM show elevated activity'),
  bullet('Pattern is regular and rhythmic — no sudden colour spikes'),
  bullet('Tooltip on hover: Date | Day | Hour range | Transaction count'),
  para('Purpose: One glance proves the employee works 9-to-5, never touches the system on weekends, and has shown no behavioural change over the past year.', false, '166534'),

  h3('Panel 3 — Threat Trend (Flatline Graph)'),
  new Paragraph({ children: [new TextRun({ text: 'Library: ', bold: true }), new TextRun('Recharts <LineChart>')], spacing: { after: 80 } }),
  bullet('X-axis: Last 30 days'),
  bullet('Y-axis: Unified Threat Score — CAPPED AT 50 to visually emphasise the low operating range'),
  bullet('Line colour: #22C55E (green)'),
  bullet('Shaded band: Light green fill between score 10 and 30 — the "normal operating band"'),
  bullet('Behaviour: Line appears flat, oscillating between 15 and 25 with no meaningful trend'),
  bullet('Annotation label at far right: "30-day average: 19.4 — Stable"'),
  para('Purpose: Proves the employee has shown no score escalation, no sudden jumps, and no "slow boil" drift over the past month.', false, '166534'),

  h3('Panel 4 — Network Status Message'),
  para('Design: A single clean info card with a green left border. The Cytoscape.js GNN graph is NOT rendered.'),
  para('Card content (exact text):'),
  codePara('  System Health: Normal'),
  codePara(''),
  codePara('  No suspicious internal or external network connections detected by'),
  codePara('  Agent 2 (FundFlow) or Agent 5 (NetworkIntel) for this employee'),
  codePara('  in the last 30 days.'),
  codePara(''),
  codePara('  Peer cluster status: STABLE'),
  codePara('  Last Agent 2 scan: [Timestamp]'),
  codePara('  Last Agent 5 scan: [Timestamp]'),
  para('Rationale for NOT rendering the GNN: Rendering an empty graph or one with no suspicious edges adds visual clutter and confusion. The plain-language message communicates the same information more clearly and definitively.', true),
  para('Purpose: Definitively states that the two network agents found nothing linking this employee to any suspicious network. This is the clean bill of health from the AI.', false, '166534'),

  hr(),

  // -------- IMPLEMENTATION NOTES --------
  h2('UI/UX Implementation Notes (Both Views)'),
  new Table({
    rows: [
      tableRow2('Concern', 'Decision', true),
      tableRow2('How does frontend know which view to render?', 'The /api/employees/{id}/profile endpoint returns a viewType field: "forensic" or "baseline", determined server-side from the current Unified Threat Score'),
      tableRow2('Can the view change mid-session?', 'Yes. The profile panel subscribes to the employee\'s WebSocket stream. If a new score crosses the 40/90 threshold, the panel re-renders with an animated transition'),
      tableRow2('What about scores 40–89 (WATCH/HIGH)?', 'Hybrid view: Peer Radar + Activity Heatmap from Baseline, plus Threat Spike Graph + Action Block with a yellow [Request Deeper Review] button instead of the red STR button'),
      tableRow2('Mobile / small screen?', 'Panels stack vertically. Radar Chart and Network Graph use min-width 320px before switching to a simplified table-based fallback'),
      tableRow2('Accessibility', 'All chart colours have WCAG AA-compliant non-colour indicators (pattern, label, or icon) so the view is usable for colour-blind investigators'),
    ],
    width: { size: 100, type: WidthType.PERCENTAGE },
  }),
  new Paragraph({ text: '', spacing: { after: 400 } }),
];

// ---------- WRITE OUTPUT ----------
const doc = new Document({
  sections: [{
    children: [
      new Paragraph({
        children: [new TextRun({ text: 'VaultMind 2.0 — Profile Detail View UI Specification', bold: true, size: 32 })],
        heading: HeadingLevel.TITLE,
        spacing: { after: 400 },
      }),
      new Paragraph({
        children: [new TextRun({ text: 'Addendum to: VaultMind_Complete_Build_Guide.docx', italics: true, color: '666666' })],
        spacing: { after: 600 },
      }),
      ...profileSection,
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = path.join(__dirname, '04_Wireframe_UI_Flow_Updated.docx');
  fs.writeFileSync(outPath, buffer);
  console.log('SUCCESS: Written to', outPath);
}).catch(err => {
  console.error('ERROR:', err.message);
});
