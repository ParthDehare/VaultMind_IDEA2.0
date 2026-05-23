# VaultMind 2.0 — AI-Driven Early Warning System for Internal Bank Fraud

> **iDEA 2.0 Hackathon | PSBs Series 2026 | Union Bank of India**
> Problem Statement PS1 — AI-Driven Early Warning System for Internal & Privileged User Fraud
> Team: VaultMind | Yeshwantrao Chavan College of Engineering , Nagpur

---

## What This Is

Most bank fraud detection focuses outward — on customers, on transactions, on external attackers. VaultMind looks inward.

Internal fraud by privileged employees — loan officers, IT admins, branch managers — accounts for a disproportionate share of banking losses in India, and it almost always goes undetected for 14 to 18 months before anyone notices. By that point, the money is gone and the audit trail is cold.

VaultMind is an 8-agent AI system that monitors 500 internal bank employees in real time, correlates behavioural signals across CBS, Treasury, Loan Origination, and Customer Database layers, and generates court-admissible evidence automatically. Mean time to detect drops from 14 months to under 5 minutes.

It was built specifically for Indian PSB constraints — legacy Finacle on 2 Mbps BSNL lines, strict data sovereignty, RBI audit compliance, and the political reality of bank unions.

---

## The 8 Agents

Each agent runs as an independent microservice on a dedicated Kafka topic. The Orchestrator (Agent 0) aggregates all scores into a single Unified Threat Score using a dynamically weighted ensemble that updates via investigator feedback.

| Agent | Name | Model | What It Catches | Latency |
|-------|------|-------|-----------------|---------|
| A1 | BehaviourWatch | LSTM + Isolation Forest | Off-hours logins, bulk record access, transaction spikes vs personal baseline and peer cluster | 70ms |
| A2 | FundFlow | GNN + NetworkX | Collusion rings, layering, circular transactions, dormant account awakening | 85ms |
| A3 | VendorGuard | API Sequence Analytics | Compromised vendor credentials — same volume, different API call order | 40ms |
| A4 | ComplaintSignal | NLP + Gemini API | Customer complaint surges + negative sentiment linked to specific officers | 120ms |
| A5 | NetworkIntel | GNN + Louvain | Two connected employees both spiking in the same 30-minute window = collusion | 90ms |
| A6 | RegulatoryAI | RAG + RBI Corpus | Tags every alert with the exact RBI/PMLA regulation violated — legal defensibility | 30ms |
| A7 | EvidenceBuilder | SHA-256 + Hyperledger Besu + ReportLab | Blockchain-anchored evidence packages, auto-files STR to FIU-IND in 3.1 seconds | 150ms |
| A8 | DeceptionGuard | Honeypot + Session Fingerprinting | 10 fake HNI accounts — any human access = instant 100/100 confirmed fraud | 5ms |

**Scoring:** `UnifiedScore = Σ(AgentScore_i × Weight_i)` where weights sum to 1.0 and update daily via HITL feedback. Alert tiers: NORMAL < 40 | WATCH 40–59 | HIGH 60–79 | CRITICAL 80–99 | CONFIRMED = 100.

---

## Tech Stack

```
ML / Data       Python 3.10, PyTorch, PyTorch Geometric, scikit-learn, NetworkX, SHAP, Faker
Backend         FastAPI, Kafka (Confluent 3.5), PostgreSQL 15, Redis 7, WebSockets
Blockchain      Hyperledger Besu 23.10, web3.py, ReportLab PDF
NLP / AI        Google Gemini API, sentence-transformers, LangChain, ChromaDB
Frontend        React.js (Vite), Recharts, Zustand, Cytoscape.js, Radix UI, socket.io
Infrastructure  Docker Compose (7 services), 3-tier Hub-and-Spoke deployment
```

---

## Project Structure

```
vaultmind/
├── data/
│   ├── generate_employees.py       # 500 employee profiles, 15 K-Means peer clusters
│   ├── generate_normal_logs.py     # 975,000 rows of role-appropriate behaviour
│   └── inject_fraud_scenarios.py   # 8 fraud story arcs, 25,000 rows
│
├── agents/
│   ├── agent1_behaviourwatch/      # LSTM + Isolation Forest
│   ├── agent2_fundflow/            # GNN + NetworkX (Louvain community detection)
│   ├── agent3_vendorguard/         # API call sequence fingerprinting
│   ├── agent4_complaintsignal/     # NLP + Gemini sentiment & entity extraction
│   ├── agent5_networkintel/        # Employee relationship graph, collusion detection
│   ├── agent6_regulatoryai/        # RAG over RBI Master Directions + PMLA corpus
│   ├── agent7_evidencebuilder/     # SHA-256 hashing, Hyperledger anchoring, PDF + STR
│   └── agent8_deceptionguard/      # Honeypot session fingerprinting
│
├── orchestrator/
│   ├── scoring_engine.py           # Weighted ensemble from all 9 Kafka topics
│   ├── weight_manager.py           # HITL gradient-descent weight updates
│   └── alert_router.py            # 3-tier routing (Branch → Zonal → Board/RBI)
│
├── api/
│   ├── main.py                     # FastAPI entry point, CORS, JWT auth
│   ├── routers/                    # alerts, employees, evidence, agents
│   └── websocket_manager.py        # Redis pub/sub → WebSocket broadcast
│
├── frontend/
│   └── src/
│       ├── pages/                  # CommandCentre, EmployeeWatch, XAI, DeceptionGuard, Evidence, PreCrime
│       ├── components/             # RiskHeatmap, AlertFeed, AgentPanel, ScoreSlider
│       └── hooks/                  # useWebSocket, useAlertStream
│
├── edge_agent/
│   └── log_shipper.py              # Reads CBS audit log tail, compresses, ships to Kafka
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Dataset

The system trains and validates against a synthetic 1-million-row dataset generated to mirror real PSB employee behaviour patterns.

| Parameter | Value |
|-----------|-------|
| Total rows | 1,000,000 |
| Employees | 500 (350 Clerks, 125 Managers, 25 IT Admins) |
| Simulation period | October 2025 – March 2026 (6 months) |
| Fraud injection rate | 2.5% = 25,000 rows |
| Random seed | 42 (fully reproducible) |

**The 8 fraud scenarios injected:**

1. **Midnight Harvest** — IT Admin exfiltrates 10,000 records to an external IP at 2 AM (Agents 1, 3)
2. **Manager Collusion Ring** — Manager approves ₹3 Cr loan files in 4 seconds each (Agents 1, 2, 5)
3. **Dormant Account Awakening** — Clerk reactivates 5-year dormant account, funds transferred 6 hours later (Agents 1, 2, 6)
4. **Structuring / Smurfing** — 6 transactions in one day, all just below ₹10L reporting threshold (Agents 1, 6)
5. **Slow Boil (84 days)** — Access volume increases by 10 records/week; LSTM adapts but peer deviation keeps rising (Agent 1 drift detection)
6. **Privilege Escalation** — IT Admin accesses `/approve_transfer` and `SALARY_MASTER` table outside role permissions (Agents 1, 5, 6)
7. **Mirage Account Access** — Any employee with score > 70 opens a honeypot account via UI; dwell time confirms human session (Agent 8)
8. **Vendor API Compromise** — Valid vendor key, valid IP, normal volume — but `/export_customer_data` injected into call sequence (Agents 3, 2)

Each scenario is injected as a **sequential story arc**, not isolated anomalous rows. The model must learn the sequence pattern.

---

## Running Locally

**Prerequisites:** Python 3.10+, Node.js 18+, Docker 24+

```bash
# 1. Clone and install Python dependencies
git clone https://github.com/your-team/vaultmind
cd vaultmind
pip install -r requirements.txt

# 2. Generate synthetic dataset
python data/generate_employees.py
python data/generate_normal_logs.py
python data/inject_fraud_scenarios.py

# 3. Start all infrastructure services
docker-compose up -d
# Verify: all 7 containers show "Up"

# 4. Create Kafka topics
for topic in agent1-events agent2-events agent3-events agent4-events agent5-events agent6-events agent7-events agent8-events unified-alerts; do
  kafka-topics.sh --create --topic $topic --bootstrap-server localhost:9092 --partitions 3
done

# 5. Train ML models (run in order — each depends on the previous)
python agents/agent1_behaviourwatch/train.py
python agents/agent2_fundflow/train.py
python agents/agent5_networkintel/train.py
python agents/agent6_regulatoryai/index_corpus.py   # one-time ChromaDB setup
# Agents 3, 4, 8 require no training — configuration only

# 6. Start all agents + orchestrator
python orchestrator/scoring_engine.py &
for i in 1 2 3 4 5 6 7 8; do python agents/agent${i}_*/main.py & done

# 7. Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 8. Start frontend
cd frontend && npm install && npm run dev
# Open: http://localhost:3000
```

Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` before starting.

---

## Architecture

The system uses a 3-tier Hub-and-Spoke deployment designed specifically for Indian PSB infrastructure constraints.

```
Branch (Tier 1)                Regional Hub (Tier 2)           HQ Command Centre (Tier 3)
─────────────────              ─────────────────────           ──────────────────────────
Edge Agent                     Kafka (9 topics)                FastAPI + React Dashboard
  │                              │                               │
  ├─ Reads CBS audit log          ├─ Agent 1: BehaviourWatch       ├─ FCU Alert Queue
  │  (read-only, no CBS change)   ├─ Agent 2: FundFlow             ├─ Evidence Downloads
  ├─ Compresses delta rows        ├─ Agent 3: VendorGuard          └─ STR Filing Status
  │  to 1KB JSON packets          ├─ Agent 4: ComplaintSignal
  └─ Sends on 5-second cycle      ├─ Agent 5: NetworkIntel
     < 10KB/minute/branch         ├─ Agent 6: RegulatoryAI         Blockchain (Hyperledger)
     (fits on 2 Mbps line)        ├─ Agent 7: EvidenceBuilder      ──────────────────────
                                  ├─ Agent 8: DeceptionGuard       SHA-256 evidence anchoring
                                  └─ Orchestrator → Unified Score   Tamper-proof audit trail
```

**Data flow:** CBS Audit Log → Edge Agent → Kafka → 8 Agents (parallel) → Orchestrator → PostgreSQL → React Dashboard → FCU Action → HITL Weight Update

**Raw CBS data never leaves the branch server.** Only 1KB scored JSON packets travel to the Regional Hub.

### The Architecture: Static Data to Live Stream (The Magic Trick)

In a hackathon or testing setting, we don't have a live core banking system pumping out real transactions. To simulate a true live environment and prove our real-time streaming architecture works, we use a "Magic Trick" approach:

1. **The CSV (Static Data):** Our data generators produce a static CSV dataset (e.g., 1 Lakh rows). We do *not* let the backend read this file directly.
2. **The Kafka Producer Script (The Simulator):** A Python script (`stream_simulator.py` or the Edge Agent) opens the CSV and loops through it row by row. After reading each row, it executes `time.sleep(0.5)` (a half-second pause) and then pushes that data to the Kafka topic.
3. **The Kafka Broker (The Live Pipeline):** As far as Kafka is concerned, it is receiving a brand new transaction every 0.5 seconds. For the pipeline, this *is* live data!
4. **The Backend Consumer (FastAPI + AI):** The FastAPI backend consumes the data from Kafka as it arrives, the AI processes it instantly, and the resulting score is pushed via WebSocket to the React UI. The investigator sees a live, ticking dashboard, proving the end-to-end streaming capability without needing a real bank backend.

---

## Key Design Decisions (and Why)

**Why read the audit log instead of the live CBS feed?**
Finacle/BaNCS already writes an audit log to disk continuously. Reading the tail of that file is a read-only operation with zero write pressure on the CBS transaction engine. The impact is equivalent to one analyst running a `SELECT` query every 5 seconds.

**Why 5-second micro-batch instead of real-time streaming?**
Real-time streaming at branch scale would saturate 2 Mbps BSNL lines. Five-second micro-batches keep the payload under 10KB/minute/branch while still detecting anomalies well within the 0.3-second dashboard latency requirement.

**Why 10 Mirage Accounts instead of alerts for suspicious browsing?**
Behavioural anomalies always have false positive risk. A confirmed human touching a honeypot account is mathematically impossible to explain away — it is zero-false-positive evidence. The session fingerprinting (dwell time > 2s = human, < 0.001s = batch script) ensures EOD jobs scanning Mirage Accounts at machine speed never trigger an alert.

**Why blockchain for evidence?**
Bharatiya Sakshya Adhiniyam (BSA) 2023, Section 63 recognises electronic records as admissible with a certificate of authenticity. SHA-256 anchoring on Hyperledger Besu provides that certificate — it proves the log existed at a specific timestamp and has not been altered since. The score is not the evidence; the blockchain-anchored CBS events are.

**Why SHAP over a simpler explanation?**
SHAP waterfall charts are the only method that produces both (a) a mathematically rigorous attribution of each feature's contribution to the score and (b) output that a non-technical FCU investigator can read: *"Alert fired because login at 2:47 AM (+28 points), 4,847 records accessed — 24x above normal (+22 points), unknown IP address (+18 points)."* Every data point in that narrative is a verifiable, timestamped entry in the bank's own CBS log.

---

## Handling the Hard Problems

**The EOD batch false positive:** Session fingerprinting classifies any access with dwell time < 0.001s per record as BATCH. All registered service account IDs are whitelisted in DeceptionGuard config. EOD scripts can scan every Mirage Account nightly without triggering a single alert.

**Year-end false alarms:** A calendar normalisation layer maintains a bank-calendar table of high-volume periods (FYE March 25–31, quarter-end weeks, salary processing days). During these windows, anomaly thresholds scale proportionally with the branch-wide surge multiplier. An employee at 1.1x their peer average during FYE is normal; at 3x, it is not.

**Slow Boil / model poisoning:** Three-layer defence: (1) peer group anchoring — even if personal LSTM adapts to 200 records/day, the peer cluster stays at 90–110; (2) drift velocity monitoring — deliberate poisoning shows unnaturally linear weekly increases; (3) immutable 90-day anchor baseline that can only be reset with dual FCU supervisor authorisation and a documented justification.

**Who watches the CRO:** Tier-3 alerts (CRO, Zonal Head, Board-level) are simultaneously and automatically pushed to the Board Audit Committee (independent directors), the RBI Department of Supervision, and a pre-designated independent forensic partner. They are completely excluded from the Command Centre dashboard that the executive controls. No single individual within the bank can suppress, dismiss, or delay a Tier-3 alert.

**Infrastructure failure (ransomware, outage):** Graceful 3-phase degradation — Phase 1 (0–5 min): Kafka reconnect attempts, dashboard shows "CBS Connection Degraded", no customer impact. Phase 2 (5–30 min): pre-compiled static rule engine activates automatically, no ML required. Phase 3 (30+ min): Fail-Open with local encrypted buffer flagged PENDING\_REVIEW; retroactive analysis completes within 60 seconds of connectivity restoration.

---

## Dashboard — 7 Screens

| Screen | What It Shows |
|--------|---------------|
| **Cinematic Intro** | 10-second animated fraud detection story for Employee 4471 (auto-plays on load) |
| **Command Centre** | Global threat level, live alert feed, 500-employee risk heatmap, 8-agent status panel |
| **Employee Watch** | Full table of all 500 employees, filterable by alert tier, sparkline trend per employee |
| **Alert Detail Modal** | Unified score, per-agent breakdown, 24h event timeline, SHAP explanation, action buttons |
| **XAI / WhyScore** | Counterfactual slider — drag login time, watch score drop live. Answers "what would clear this alert?" |
| **DeceptionGuard** | 10 Mirage Account status cards, trigger simulation button, zero-false-positive counter |
| **Evidence & STR** | Court-admissible PDF downloads, blockchain verification panel, FIU-IND STR filing status |
| **Pre-Crime Forecast** | Markov chain 24h trajectory for all 500 employees — advisory only, no access restrictions |

---

## Profile Detail View — Context-Sensitive Investigator UI

When an investigator clicks any employee card on the Employee Watch screen, the system renders one of two entirely different panel layouts depending on the employee's Unified Threat Score. The goal of each view is different: one is built to **prove fraud**, the other is built to **prove innocence**.

---

### 🔴 High-Risk Profile (Score: 90–100) — "The Forensic View"

**Investigator intent:** *Investigate & Take Action*

This view is shown when the Unified Threat Score is between **90 and 100**. Every panel is purpose-built to help the FCU investigator build a legally defensible case. The layout is dark-accented with red warning highlights throughout.

#### Panel 1 — Threat Spike Graph (Time-Series)

- **Library:** Recharts `<AreaChart>` or `<LineChart>`
- **X-axis:** Last 30 days (daily tick marks)
- **Y-axis:** Unified Threat Score (0–100)
- **Visuals:**
  - The line is rendered in a gradient from amber (`#F59E0B`) at baseline to crimson (`#DC2626`) at peak
  - A vertical dashed annotation line marks the exact **Anomaly Onset Date** — the first day the score crossed the alert threshold
  - Two behavioural patterns are distinguishable: **Sudden Spike** (one-day jump > 40 points) and **Slow Boil** (linear rise over 30+ days, characteristic of the 84-day fraud scenario)
  - A tooltip on hover shows: `Date | Score | Dominant Agent`
- **Purpose:** Proves *when* the anomaly began, which is critical for linking it to a real-world event (a loan approval, a system access, a fund transfer).

#### Panel 2 — FundFlow Network Graph (GNN View)

- **Library:** Cytoscape.js with a `cose-bilkent` or `dagre` layout
- **Render condition:** This panel **only renders** if Agent 2 (FundFlow) or Agent 5 (NetworkIntel) contributed a score > 0. If neither fired, this panel is replaced by a grey placeholder card: *"No network anomaly detected by Agent 2."*
- **Visuals:**
  - **Node types:** Employee (blue circle), Shell Company (red hexagon), Relative/Linked Account (orange diamond), External Bank (grey square)
  - **Edge colours:** Green = normal fund flow; Red = flagged circular routing path; Dashed = indirect/inferred link
  - The circular routing pattern is highlighted with a **pulsing red edge animation** on the fraudulent loop: `Manager → Shell Company → Relative → Manager`
  - Node size encodes transaction volume (larger = more money moved)
  - Clicking a node opens a tooltip: `Entity Name | Role | Total Flow (₹) | First Seen`
- **Purpose:** Visually proves the "Circular Routing" pattern that is the backbone of layering fraud. A non-technical judge or auditor can understand this graph without reading any log files.

#### Panel 3 — Counterfactual Sliders (XAI / SHAP Interface)

- **Library:** Radix UI `<Slider>` components, backed by live SHAP recalculation via a debounced API call to `/api/xai/counterfactual/{employee_id}`
- **Three sliders exposed:**

  | Slider | Range | What It Modifies |
  |--------|-------|-----------------|
  | **Transaction Time** | 6 AM → 11 PM | Shifts login/transaction hour toward business hours |
  | **Daily Volume** | 0 → 500% of peer average | Reduces record access count toward peer median |
  | **Transaction Amount** | ₹0 → ₹50,00,000 | Adjusts the single largest transaction in the window |

- **Live score readout:** As the investigator drags any slider, the Unified Threat Score readout updates in real time (debounced 300ms). The score drops as parameters move toward normal.
- **Critical Threshold Line:** A horizontal line at score = 60 (the HIGH alert threshold). The investigator can see exactly how far the parameters need to shift before this employee would drop out of CRITICAL status.
- **Purpose:** Answers the key legal question: *"Why did the AI flag this person?"* The investigator can demonstrate in court that the score would have been 24/100 if the employee had worked normal hours — proving the AI is not biased against the individual, it is responding to measurable behavioural deviation.

##### The Architecture of the "What-If" Slider
1. **The Read-Only Rule (Backend Level):**
   When the dashboard is opened, the FastAPI backend serves Core Banking logs in strictly **Read-Only** mode. VaultMind's backend has no APIs exposed to `UPDATE` or `DELETE` these logs. The original transaction records remain immutable (like a line carved in stone) in PostgreSQL.
2. **The In-Memory Sandbox (React Level):**
   As the FCU investigator adjusts the sliders, they are manipulating an in-memory sandbox in the browser's RAM, not the actual data.
   - We maintain an `actualData` state (which remains fixed).
   - We maintain a `simulatedData` state (which reacts to the slider).
   When the investigator shifts the 'Time' slider from 2 AM to 2 PM, the React frontend sends a "Dummy Payload" to the AI model querying: *"If the time was 2 PM, what would the score be?"* The AI responds with the hypothetical score (e.g., 41), which the UI then displays. Crucially, the actual database retains the 2 AM timestamp and the original 96 threat score.
3. **The "Audit Trail" (Taking Action):**
   If the investigator determines after using the sliders that the alert is genuinely a "False Positive" (i.e., not fraud), they can leave the slider in place and click the `[Mark as False Positive]` button. This will log their decision and trigger the necessary HITL adjustments.

#### Panel 4 — Action Block

- **Layout:** Full-width bottom panel, pinned to the bottom of the scrollable detail view
- **Primary Button:** `[🚨 Generate STR Evidence]`
  - Colour: `#DC2626` (red), with a white text label and a subtle pulse animation on initial render
  - On click: triggers Agent 7 (EvidenceBuilder) pipeline — SHA-256 hash, Hyperledger Besu anchoring, 20-page PDF generation, and STR auto-draft to FIU-IND. Shows a progress modal with 4 steps and a live timer.
  - After completion: button state changes to `[✅ STR Filed — View Evidence]`
- **Secondary Button:** `[Mark as False Positive]`
  - Colour: outlined grey, no fill
  - On click: opens a confirmation dialog requiring a typed justification (minimum 50 characters). On confirm, submits a HITL signal to the Orchestrator's `weight_manager.py`, reducing the contributing agents' weights for future scoring. Logs the investigator ID and timestamp in the audit trail.
- **Below the buttons:** A read-only regulatory tag strip showing the exact RBI/PMLA regulations violated (populated by Agent 6): e.g., `PMLA Rule 3 | RBI Master Direction 2024 §12.4 | BSA 2023 §63`

---

### 🟢 Normal Profile (Score: 0–40) — "The Baseline View"

**Investigator intent:** *Reassurance — prove why this employee is safe*

This view is shown when the Unified Threat Score is between **0 and 40**. The design language shifts from red/dark-threat to green/calm. No fraud-investigation panels are shown. Instead, the UI visually proves the employee's *normalcy* through positive evidence.

#### Panel 1 — Peer Comparison Radar Chart

- **Library:** Recharts `<RadarChart>` with two overlapping datasets
- **Axes (6 dimensions):**
  1. Daily Transaction Volume
  2. Working Hours (spread of login/logout times)
  3. Record Access Rate
  4. Geographic Consistency (IP location variance)
  5. After-Hours Activity
  6. Peer Deviation Score

- **Two radar shapes rendered:**
  - **Blue fill (this employee):** The selected employee's normalised scores on all 6 dimensions
  - **Grey fill (peer cluster median):** The median of all ~50 clerks in the same branch peer cluster (K-Means cluster, same role)
- **Visual indicator:** If the two shapes largely **overlap** (cosine similarity > 0.85), a green banner appears: *"✅ Behavioural Profile Consistent with Peer Cluster"*
- **Purpose:** This is the most powerful reassurance visual. It shows at a glance that this employee is not an outlier — their behaviour is typical of their role, branch, and peer group. The GNN graph is **not rendered** in this view to keep the panel uncluttered and unambiguous.

#### Panel 2 — Activity Heatmap (GitHub-style Contribution Graph)

- **Library:** Custom SVG grid or a library like `react-calendar-heatmap`
- **Layout:** 52 columns × 7 rows (7 days × 52 weeks = 1 year rolling view)
- **Cell colour scale:**
  - `0 transactions` → `#1A1A2E` (dark, near-black)
  - Low activity (9 AM–1 PM) → `#166534` (muted green)
  - Normal activity (9 AM–6 PM) → `#16A34A` (standard green)
  - High activity → `#4ADE80` (bright green)
  - **Any cell outside 6 AM–8 PM window is capped at minimum colour** — visually proving the employee is inactive at night

- **Key visual signatures for a clean profile:**
  - Weekdays show consistent green; weekends are near-black (no after-hours work)
  - No cells outside the 9 AM–6 PM window show elevated activity
  - Pattern is visually **regular and rhythmic** — no sudden colour spikes

- **Tooltip on hover:** `Date | Day | Hour range | Transaction count`
- **Purpose:** One glance proves the employee works 9-to-5, never touches the system on weekends, and has shown no behavioural change over the past year. This is the kind of evidence that protects an employee from false accusation.

#### Panel 3 — Threat Trend (Flatline Graph)

- **Library:** Recharts `<LineChart>`
- **X-axis:** Last 30 days
- **Y-axis:** Unified Threat Score (0–100), **Y-axis capped at 50** to visually emphasise the low range
- **Line colour:** `#22C55E` (green)
- **Shaded band:** A light green fill between score 10 and 30 — the "normal operating band" for this employee
- **Behaviour:** The line should visually appear **flat**, oscillating between 15 and 25 with no meaningful trend
- **Annotation:** A label at the far right: *"30-day average: 19.4 — Stable"*
- **Purpose:** Proves the employee has shown no score escalation, no sudden jumps, and no "slow boil" drift over the past month.

#### Panel 4 — Network Status Message

- **Design:** A single clean info card with a green left border
- **Content:**

  ```
  ✅  System Health: Normal

  No suspicious internal or external network connections detected by Agent 2 (FundFlow)
  or Agent 5 (NetworkIntel) for this employee in the last 30 days.

  Peer cluster status: STABLE
  Last Agent 2 scan: [Timestamp]
  Last Agent 5 scan: [Timestamp]
  ```

- **The GNN (Cytoscape.js) graph is not rendered in this view.** Rendering an empty graph or a graph with no suspicious edges would add visual clutter and confusion. The plain-language message communicates the same information more clearly.
- **Purpose:** Definitively states that the two network agents — which are responsible for detecting collusion, circular routing, and fund layering — found nothing linking this employee to any suspicious network. This is the equivalent of a clean bill of health from the AI.

---

### UI/UX Implementation Notes for Both Views

| Concern | Decision |
|---------|----------|
| **How does the frontend know which view to render?** | The `/api/employees/{id}/profile` endpoint returns a `viewType` field: `"forensic"` or `"baseline"`, determined server-side from the current Unified Threat Score |
| **Can the view change mid-session?** | Yes. The profile panel subscribes to the employee's WebSocket stream. If a new score pushes across the 40/90 threshold, the panel re-renders with an animated transition |
| **What about scores 40–89 (WATCH / HIGH)?** | These render a **hybrid view** — the Peer Radar and Activity Heatmap from the Baseline View plus the Threat Spike Graph and Action Block (with a yellow `[Request Deeper Review]` button instead of the red STR button) |
| **Mobile / small screen?** | Panels stack vertically. The Radar Chart and Network Graph use a minimum width of 320px before switching to a simplified table-based fallback |
| **Accessibility** | All chart colours have a WCAG AA-compliant non-colour indicator (pattern, label, or icon) so the view is usable for colour-blind investigators |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Alert generation latency | < 0.3 seconds (Kafka ingestion to dashboard) |
| MTTD reduction | 14–18 months → < 5 minutes |
| False positive rate | < 5% via HITL retraining |
| Catch rate | 95% on synthetic test set |
| Evidence generation | < 3.5 seconds (SHA-256 + blockchain + 20-page PDF + STR) |
| Edge Agent footprint | < 50MB RAM, < 2% CPU |
| Network payload | < 10KB/minute/branch |
| Uptime | 99.5% with graceful degradation |
| Concurrent FCU investigators | Up to 200 simultaneous sessions |

---

## Regulatory Compliance

- **RBI Master Directions 2024** — all monitoring operates on legally mandated audit logs
- **PMLA Rules 2005 (amended)** — structuring detection, STR auto-filing to FIU-IND
- **Bharatiya Sakshya Adhiniyam (BSA) 2023, Section 63** — blockchain evidence admissibility
- **Basel III** — risk categorisation and reporting integration
- **RBI/2024-25/16** — circular reference visible on evidence page
- **RBI Explainability Mandate** — every alert has SHAP-based explanation, legally defensible for HR and court proceedings

Employee identifiers are pseudonymised at ingestion. Name-to-ID mapping is held in a separate encrypted vault. Unmasking requires dual FCU supervisor authorisation and generates its own audit record. No raw employee data leaves the branch server at any point.

---

## Team

**VaultMind** 

Built for iDEA 2.0 Hackathon, PSBs Series 2026, Union Bank of India.
