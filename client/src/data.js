// VaultMind 2.0 — Simulated Data & Scoring Engine
// Generates synthetic 5-month historical + 1-month live Kafka stream data

const EMPLOYEES = Array.from({ length: 500 }, (_, i) => {
  const id = `EMP_${1000 + i}`;
  const roles = ["CLERK", "MANAGER", "IT_ADMIN"];
  const role = roles[i % 3 === 0 ? 2 : i % 5 === 0 ? 1 : 0];
  const branch = `BR_${String((i % 20) + 1).padStart(2, "0")}`;
  // 5% of employees are marked as potential fraudsters
  const isFraudster = Math.random() < 0.05;
  return { emp_id: id, emp_class: role, branch_id: branch, isFraudster };
});

// Add honeypot profile
EMPLOYEES.push({
  emp_id: "EMP_1024_HONEYPOT",
  emp_class: "HONEYPOT",
  branch_id: "BR_05",
  isFraudster: false,
  isHoneypot: true,
  name: "Mirage Decoy Account"
});

const ACTIONS = ["Initiate", "Approve", "DB_Read", "System_Login", "ATM_Withdrawal", "SYSTEM_BULK_EXPORT"];
const CHANNELS = ["UPI", "IMPS", "NEFT", "RTGS", "SYSTEM", "ATM"];
const FRAUD_TEXTS = [
  "Customer reported unauthorized debit and extortion threat.",
  "ALERT: Bulk export of 50000 customer records to external IP.",
  "Suspected money laundering via shell accounts.",
  "Forged manager signature on approval documents.",
  "Employee bribe allegation from whistleblower.",
];

const SENTIMENT_KEYWORDS = [
  /\bstolen\b/i, /\bbribe\b/i, /\bhacked\b/i, /\bextortion\b/i,
  /\bunauthorized\b/i, /\billegal\b/i, /\bthreat\b/i,
  /\bfraud\b/i, /\bmoney.?launder/i, /\bforged?\b/i,
];

function randomDate(start, end) {
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

function generateTransactions(count, startDate, endDate) {
  const txns = [];
  for (let i = 0; i < count; i++) {
    const emp = EMPLOYEES[Math.floor(Math.random() * EMPLOYEES.length)];
    // Only fraudsters commit high-risk transactions
    const isFraud = emp.isFraudster ? Math.random() < 0.025 : false;
    
    let action = ACTIONS[Math.floor(Math.random() * (ACTIONS.length - 1))];
    let channel = CHANNELS[Math.floor(Math.random() * CHANNELS.length)];
    let amount = Math.round(Math.random() * 45000); // 0 to 45k (safe)
    
    if (!isFraud) {
       if (emp.emp_class === "CLERK" && action === "Approve") action = "Initiate";
       if (emp.emp_class === "IT_ADMIN") amount = 0;
       if (!["IT_ADMIN", "ADMIN"].includes(emp.emp_class) && ["SYSTEM_BULK_EXPORT", "DB_GRANT_ACCESS"].includes(action)) {
           action = "DB_Read";
       }
    } else {
       action = Math.random() > 0.5 ? "SYSTEM_BULK_EXPORT" : action;
       amount = Math.round(Math.random() * 9000000 + 1000000);
    }

    // Force off-hours only for fraudsters
    let ts = randomDate(startDate, endDate);
    if (!isFraud) {
       // ensure hour is between 8 and 20
       ts.setHours(8 + Math.floor(Math.random() * 12));
    } else if (Math.random() < 0.3) {
       // off-hours
       ts.setHours(2 + Math.floor(Math.random() * 4));
    }

    const text = isFraud && Math.random() < 0.4 ? FRAUD_TEXTS[Math.floor(Math.random() * FRAUD_TEXTS.length)] : "";

    txns.push({
      transaction_id: `TXN_${Date.now()}_${i}`,
      timestamp: ts.toISOString(),
      emp_id: emp.emp_id,
      emp_class: emp.emp_class,
      branch_id: emp.branch_id,
      action_type: action,
      amount,
      account_touched: `ACC_${Math.floor(Math.random() * 8000 + 1000)}`,
      transfer_channel: channel,
      raw_complaint_text: text,
      is_fraud_flag: isFraud ? 1 : 0,
    });
  }
  return txns.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

// Scoring engine replicating Agents 3-6
function scoreTransaction(tx) {
  let score = 15;
  const amt = tx?.amount || 0;
  const role = (tx?.emp_class || "").toUpperCase();
  const action = tx?.action_type || "";
  const channel = (tx?.transfer_channel || "").toUpperCase();
  const text = tx?.raw_complaint_text || "";

  // Agent 5: ProfileAudit
  if (role === "CLERK" && amt > 5000000) score = Math.max(score, 85);
  if (!["IT_ADMIN", "ADMIN"].includes(role) && ["SYSTEM_BULK_EXPORT", "DB_GRANT_ACCESS"].includes(action))
    score = Math.max(score, 95);
  if (role === "IT_ADMIN" && amt > 0) score = Math.max(score, 90);
  if (role === "CLERK" && action === "Approve") score += 25;

  // Agent 6: RegulatoryAI
  const limits = { UPI: 200000, IMPS: 500000, NEFT: 1000000, RTGS: 100000000 };
  if (limits[channel] && amt > limits[channel]) score = Math.max(score, 100);
  if (amt >= 49000 && amt <= 49999) score = Math.max(score, 60);

  // Agent 4: NLP
  if (text) {
    for (const pat of SENTIMENT_KEYWORDS) {
      if (pat.test(text)) { score += 25; break; }
    }
  }

  // Off-hours
  try {
    const hour = new Date(tx?.timestamp).getHours();
    if (hour < 7 || hour > 21) score += 12;
  } catch {}

  // Fraud flag boost
  if (tx?.is_fraud_flag === 1 && score < 50) score += 35;

  return Math.min(100, Math.max(0, Math.round(score)));
}

function riskTier(score) {
  if (score >= 70) return "CRITICAL";
  if (score >= 40) return "HIGH";
  if (score >= 25) return "WATCH";
  return "NORMAL";
}

function getTriggeredRules(tx) {
  const rules = [];
  const amt = tx?.amount || 0;
  const role = (tx?.emp_class || "").toUpperCase();
  const action = tx?.action_type || "";
  const channel = (tx?.transfer_channel || "").toUpperCase();

  if (role === "CLERK" && amt > 5000000) rules.push(`A5: CLERK txn Rs.${amt.toLocaleString()} exceeds 5M`);
  if (!["IT_ADMIN", "ADMIN"].includes(role) && ["SYSTEM_BULK_EXPORT", "DB_GRANT_ACCESS"].includes(action))
    rules.push(`A5: ${role} attempted restricted '${action}'`);
  if (role === "IT_ADMIN" && amt > 0) rules.push(`A5: IT_ADMIN financial transfer Rs.${amt.toLocaleString()}`);
  if (role === "CLERK" && action === "Approve") rules.push("A5: CLERK performed APPROVE (needs MANAGER)");

  const limits = { UPI: 200000, IMPS: 500000, NEFT: 1000000, RTGS: 100000000 };
  if (limits[channel] && amt > limits[channel])
    rules.push(`A6: ${channel} Rs.${amt.toLocaleString()} exceeds Rs.${limits[channel].toLocaleString()}`);
  if (amt >= 49000 && amt <= 49999) rules.push(`A6: Structuring suspected near 50k`);
  return rules;
}

function extractNlpFlags(tx) {
  const flags = [];
  const text = tx?.raw_complaint_text || "";
  if (text) {
    for (const pat of SENTIMENT_KEYWORDS) {
      const m = text.match(pat);
      if (m) flags.push(`Keyword: '${m[0]}'`);
    }
  }
  return flags;
}

// Generate all data
const HISTORICAL = generateTransactions(40000, new Date("2025-10-01"), new Date("2026-02-28"), 0.021);
const LIVE_STREAM = generateTransactions(8000, new Date("2026-03-01"), new Date("2026-03-30"), 0.02);

export {
  EMPLOYEES, HISTORICAL, LIVE_STREAM,
  scoreTransaction, riskTier, getTriggeredRules, extractNlpFlags,
  SENTIMENT_KEYWORDS
};
