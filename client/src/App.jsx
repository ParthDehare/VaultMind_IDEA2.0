import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import FundFlowGraph from './components/FundFlowGraph';
import {
  Sun, Moon, Search, Shield, Users, User, GitBranch, FileText,
  AlertTriangle, Activity, ChevronLeft, ChevronRight, Download,
  Loader2, Radio, TrendingUp
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, Legend
} from "recharts";
import { ForensicTimeline, GlassBoxEngine, BlastRadius, ShapSimulator } from "./ProfileComponents.jsx";
import { motion } from "framer-motion";
import { getTriggeredRules, extractNlpFlags } from "./data";
// ✨ Supabase Import Added Here ✨
import { supabase } from './supabaseClient';

// ─── Theme Tokens ────────────────────────────────────────────
const DARK = {
  bg: "#0a0a0a", card: "#121212", cardAlt: "#0f0f0f", border: "#222222",
  text: "#FFFFFF", text2: "#A0A0A0", accent: "#E50914",
  teal: "#00D4AA", cyan: "#00B4D8", red: "#E50914",
  amber: "#FFB300", green: "#00E676",
};
const LIGHT = {
  bg: "#F5F5F5", card: "#FFFFFF", cardAlt: "#F8F9FA", border: "#E0E0E0",
  text: "#1A1A1A", text2: "#666", accent: "#D32F2F",
  teal: "#00897B", cyan: "#0288D1", red: "#D32F2F",
  amber: "#F57F17", green: "#2E7D32",
};

const TIER_COLORS = (t) => ({
  CRITICAL: t.red, HIGH: t.amber, WATCH: t.cyan, NORMAL: t.green,
});

const ROWS_PER_PAGE = 20;

const riskTier = (score) => {
  if (score >= 70) return "CRITICAL";
  if (score >= 50) return "HIGH";
  if (score >= 30) return "WATCH";
  return "NORMAL";
};

// ─── Badge Component ─────────────────────────────────────────
function Badge({ tier, t }) {
  const colors = TIER_COLORS(t);
  const c = colors[tier] || t.text2;
  return (
    <span
      className="px-2.5 py-0.5 rounded-sm text-xs font-mono font-semibold border"
      style={{ color: c, borderColor: c, background: `${c}22` }}
    >
      {tier}
    </span>
  );
}

// ─── Card Component ──────────────────────────────────────────
function Card({ children, t, className = "", style = {}, ...props }) {
  return (
    <div
      className={`rounded-sm border p-5 transition-colors duration-200 ${className}`}
      style={{
        background: t.card, borderColor: t.border,
        boxShadow: "0 0 10px rgba(0,0,0,0.4)",
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

// ─── KPI Card ────────────────────────────────────────────────
function KpiCard({ title, value, color, t }) {
  return (
    <Card t={t}>
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-1" style={{ color: t.text2 }}>
        {title}
      </div>
      <div className="text-3xl font-bold font-mono" style={{ color }}>{value}</div>
    </Card>
  );
}

// ─── Section Header ──────────────────────────────────────────
function Section({ title, t }) {
  return (
    <div
      className="text-[13px] font-bold uppercase tracking-[2px] py-2.5 border-b mb-4"
      style={{ color: t.text2, borderColor: t.border }}
    >
      {title}
    </div>
  );
}

function LoadingShimmer({ t }) {
  return (
    <div className="space-y-4">
      {Array(5).fill(0).map((_, i) => (
        <div
          key={i}
          className="h-16 rounded-sm animate-pulse"
          style={{ background: `${t.border}44` }}
        />
      ))}
    </div>
  );
}

function GraphSkeleton({ t, height = 300 }) {
  return (
    <div
      className="w-full rounded-lg animate-pulse overflow-hidden"
      style={{ height, background: `${t.border}33` }}
    >
      <div className="h-full w-full flex items-end gap-3 p-6">
        {Array(8).fill(0).map((_, i) => (
          <div
            key={i}
            className="rounded-sm"
            style={{
              width: "12%",
              height: `${30 + i * 8}px`,
              background: `${t.border}66`
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [page, setPage] = useState("command");
  const [profileSearch, setProfileSearch] = useState("");
  const [rosterPage, setRosterPage] = useState(1);
  const [rosterSearch, setRosterSearch] = useState("");
  const [rosterRole, setRosterRole] = useState("ALL");
  const [rosterTier, setRosterTier] = useState("ALL");
  const [downloading, setDownloading] = useState(null);
  const [graphSearch, setGraphSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const graphRef = useRef(null);

  // API-Driven State
  const [scoredTxns, setScoredTxns] = useState([]);
  const [displayBuffer, setDisplayBuffer] = useState([]);
  const [employeeMetadata, setEmployeeMetadata] = useState({});
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const MAX_TRANSACTIONS = 500;
  const DISPLAY_BUFFER_MAX = 100;

  // ✨ Supabase Data State (Dummy Removed) ✨
  const [vaultEvidence, setVaultEvidence] = useState([]);

  // Other UI States
  const [confirmedIncidents, setConfirmedIncidents] = useState([]);
  const [generateTarget, setGenerateTarget] = useState("");
  const [isGeneratingDossier, setIsGeneratingDossier] = useState(false);
  const [lastGenerated, setLastGenerated] = useState(null);

  const handleConfirmIncident = useCallback((emp_id) => {
    const normalized = (emp_id || "").toUpperCase();
    if (!normalized) return;
    setConfirmedIncidents((prev) => {
      if (prev.some((e) => e.emp_id === normalized)) return prev;
      return [{ emp_id: normalized, timestamp: new Date().toISOString() }, ...prev];
    });
  }, []);

  // ✨ NEW: SUPABASE LIVE FETCH EFFECT ✨
  useEffect(() => {
    // 1. Initial Load
    const fetchEvidence = async () => {
      try {
        const { data, error } = await supabase
          .from('evidence_logs')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) throw error;

        if (data) {
          const formattedData = data.map(log => ({
            id: log.id || `EVD-${Math.random()}`,
            emp_id: log.employee_id || "UNKNOWN",
            filename: log.evidence_path ? log.evidence_path.split('/').pop() : `EVD-${log.transaction_id}.pdf`,
            hash: log.id ? `0x${log.id.replace(/-/g, '').slice(0, 16)}` : "0x000000",
            blockId: `#${log.transaction_id ? String(log.transaction_id).substring(0,8) : "0000"}`,
            timestamp: new Date(log.created_at).toISOString().replace("T", " ").slice(0, 19) + "Z",
            status: "Generated",
            risk: log.risk_level
          }));
          setVaultEvidence(formattedData);
        }
      } catch (err) {
        console.error("Failed to fetch from Supabase:", err);
      }
    };

    fetchEvidence();

    // 2. Real-Time Subscription
    const subscription = supabase
      .channel('evidence_logs_changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'evidence_logs' }, payload => {
        console.log("🔥 New fraud log from DB:", payload);
        const log = payload.new;
        const newEvd = {
          id: log.id || `EVD-${Math.random()}`,
          emp_id: log.employee_id || "UNKNOWN",
          filename: log.evidence_path ? log.evidence_path.split('/').pop() : `EVD-${log.transaction_id}.pdf`,
          hash: log.id ? `0x${log.id.replace(/-/g, '').slice(0, 16)}` : "0x000000",
          blockId: `#${log.transaction_id ? String(log.transaction_id).substring(0,8) : "0000"}`,
          timestamp: new Date(log.created_at).toISOString().replace("T", " ").slice(0, 19) + "Z",
          status: "Generated",
          risk: log.risk_level
        };
        setVaultEvidence(prev => [newEvd, ...prev]);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(subscription);
    };
  }, []);


  useEffect(() => {
    if (!confirmedIncidents.length) return;
    setVaultEvidence((prev) => {
      const pending = new Set(prev.filter((e) => e.status === "Pending Dossier").map((e) => e.emp_id));
      const existing = new Set(prev.filter((e) => e.status !== "Pending Dossier").map((e) => e.emp_id));
      const additions = confirmedIncidents
        .filter((inc) => !pending.has(inc.emp_id) && !existing.has(inc.emp_id))
        .map((inc) => ({
          id: `EVD-PENDING-${inc.emp_id}-${inc.timestamp.replace(/[-:.TZ]/g, "")}`,
          emp_id: inc.emp_id,
          filename: "PENDING...",
          hash: "PENDING...",
          blockId: "PENDING...",
          timestamp: inc.timestamp.replace("T", " ").slice(0, 19) + "Z",
          status: "Pending Dossier"
        }));
      if (!additions.length) return prev;
      const updated = [...additions, ...prev];
      
      // Auto-convert pending items to generated after 2 seconds
      setTimeout(() => {
        setVaultEvidence((current) =>
          current.map((item) =>
            item.status === "Pending Dossier" && additions.some((add) => add.id === item.id)
              ? { ...item, status: "Generated", filename: `EVD-${Date.now()}.pdf` }
              : item
          )
        );
      }, 2000);
      
      return updated;
    });
  }, [confirmedIncidents]);

  const handleGenerateDossier = useCallback(() => {
    const target = generateTarget.trim().toUpperCase();
    if (!target) return;
    setIsGeneratingDossier(true);
    setTimeout(() => {
      setIsGeneratingDossier(false);
      setVaultEvidence(prev => {
        const existingIdx = prev.findIndex(e => e.emp_id === target && e.status === "Pending Dossier");
        const newEvd = {
          id: `EVD-${Date.now()}`,
          emp_id: target,
          filename: `EVD-${target}-${Date.now()}.pdf`,
          hash: "0x9f8...a1b2",
          blockId: `#${Math.floor(Math.random() * 100000) + 900000}`,
          timestamp: new Date().toISOString().replace("T", " ").slice(0, 19) + "Z",
          status: "Generated"
        };
        
        if (existingIdx !== -1) {
           const next = [...prev];
           next[existingIdx] = newEvd;
           return next;
        } else {
           return [newEvd, ...prev];
        }
      });
      setLastGenerated({ emp_id: target, hash: "0x9f8...a1b2" });
    }, 2000);
  }, [generateTarget]);

  useEffect(() => {
    if (!lastGenerated) return;
    if (!generateTarget || lastGenerated.emp_id !== generateTarget) {
      setLastGenerated(null);
    }
  }, [generateTarget, lastGenerated]);

  const dossierOptions = useMemo(() => {
    const pendingTargets = Array.from(
      new Set(vaultEvidence.filter((e) => e.status === "Pending Dossier").map((e) => e.emp_id))
    );
    const baseOptions = [
      { value: "EMP_1024", label: "EMP_1024 (Critical)" },
      { value: "EMP_1337", label: "EMP_1337 (High)" },
      { value: "EMP_9999", label: "EMP_9999 (Critical)" }
    ];
    const pendingOptions = pendingTargets.map((empId) => ({
      value: empId,
      label: `${empId} (Pending)`
    }));
    const seen = new Set();
    return [...pendingOptions, ...baseOptions].filter((opt) => {
      if (seen.has(opt.value)) return false;
      seen.add(opt.value);
      return true;
    });
  }, [vaultEvidence]);

  const t = theme === "dark" ? DARK : LIGHT;
  const tc = TIER_COLORS(t);

  // 1. Initial Load (Dashboard Foundation) - crash-safe
  useEffect(() => {
    setIsLoadingInitial(true);
    
    // Load employee metadata
    fetch("http://localhost:8000/api/roster/employees")
      .then((res) => res.json())
      .then((data) => {
        if (data.employees && Array.isArray(data.employees)) {
          const metadataMap = {};
          data.employees.forEach((emp) => {
            metadataMap[emp.emp_id] = {
              emp_class: emp.emp_class || "UNKNOWN",
              branch_id: emp.branch_id || "UNKNOWN"
            };
          });
          setEmployeeMetadata(metadataMap);
        }
      })
      .catch((err) => console.warn("Employee metadata fetch failed (non-critical)", err));
    
    // Load transaction data
    fetch("http://localhost:8000/api/dashboard-init")
      .then((res) => res.json())
      .then((payload) => {
        const rows = Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.data)
            ? payload.data
            : [];
        const normalized = rows.map((tx) => ({
          ...tx,
          cbsi: tx.cbsi ?? tx.predicted_cbsi_score ?? tx.cbsi_score ?? 0,
          risk_tier: tx.risk_tier ?? riskTier(tx.cbsi ?? tx.predicted_cbsi_score ?? tx.cbsi_score ?? 0)
        }));
        setScoredTxns(normalized);
        setDisplayBuffer(normalized.slice(-DISPLAY_BUFFER_MAX));
      })
      .catch((err) => console.error("Initial load failed", err))
      .finally(() => setIsLoadingInitial(false));
  }, []);

  // 2. Live Stream (Delta Update) - crash-safe via WebSocket
  const fetchNextTransaction = useCallback(() => {
    return fetch("http://localhost:8000/get-next-transaction")
      .then((res) => res.json())
      .then((newTxn) => {
        if (newTxn && newTxn.emp_id) {
          const normalized = {
            ...newTxn,
            cbsi: newTxn.cbsi ?? newTxn.predicted_cbsi_score ?? newTxn.cbsi_score ?? 0,
            risk_tier: newTxn.risk_tier ?? riskTier(newTxn.cbsi ?? newTxn.predicted_cbsi_score ?? newTxn.cbsi_score ?? 0)
          };
          setScoredTxns((prev) => {
            const safePrev = Array.isArray(prev) ? prev : [];
            return [...safePrev, normalized].slice(-MAX_TRANSACTIONS);
          });
          setDisplayBuffer((prev) => {
            const safePrev = Array.isArray(prev) ? prev : [];
            return [...safePrev, normalized].slice(-DISPLAY_BUFFER_MAX);
          });
        }
      })
      .catch((err) => console.error("Live update failed", err));
  }, []);

  // Listen to WebSocket for live stream instead of polling
  useEffect(() => {
    if (!autoRefresh) return;
    
    const ws = new WebSocket("ws://localhost:8000/ws/alerts");
    
    ws.onopen = () => {
      console.log("🟢 Connected to WebSocket for live alerts");
    };

    ws.onmessage = (event) => {
      try {
        const newTxn = JSON.parse(event.data);
        if (newTxn && newTxn.emp_id) {
          const normalized = {
            ...newTxn,
            cbsi: newTxn.cbsi ?? newTxn.predicted_cbsi_score ?? newTxn.cbsi_score ?? 0,
            risk_tier: newTxn.risk_tier ?? riskTier(newTxn.cbsi ?? newTxn.predicted_cbsi_score ?? newTxn.cbsi_score ?? 0)
          };
          setScoredTxns((prev) => {
            const safePrev = Array.isArray(prev) ? prev : [];
            return [...safePrev, normalized].slice(-MAX_TRANSACTIONS);
          });
          setDisplayBuffer((prev) => {
            const safePrev = Array.isArray(prev) ? prev : [];
            return [...safePrev, normalized].slice(-DISPLAY_BUFFER_MAX);
          });
        }
      } catch (err) {
        console.error("Error processing WebSocket message", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("🔴 WebSocket disconnected");
    };

    return () => {
      ws.close();
    };
  }, [autoRefresh]);

  // ── Employee scores (API-Driven) ────────────────────────────────
  const empScores = useMemo(() => {
    const map = {};
    for (const tx of scoredTxns) {
      const eid = tx?.emp_id;
      if (!eid) continue;
      if (!map[eid]) map[eid] = { max: 0, sum: 0, count: 0 };
      const score = tx.cbsi || 15;
      map[eid].max = Math.max(map[eid].max, score);
      map[eid].sum += score;
      map[eid].count++;
    }
    
    // Create employee list from scored transactions
    const employees = Array.from(
      new Set(scoredTxns.map(tx => tx.emp_id).filter(Boolean))
    ).map(emp_id => ({ emp_id }));

    return employees.map((e) => {
      const s = map[e.emp_id] || { max: 0, sum: 0, count: 0 };
      const meta = employeeMetadata[e.emp_id] || { emp_class: "UNKNOWN", branch_id: "UNKNOWN" };
      return {
        ...e,
        emp_class: meta.emp_class,
        branch_id: meta.branch_id,
        peak: s.max,
        avg: s.count ? Math.round((s.sum / s.count) * 10) / 10 : 0,
        txnCount: s.count,
        status: riskTier(s.max),
      };
    }).sort((a, b) => b.peak - a.peak);
  }, [scoredTxns, employeeMetadata]);

  // ── KPI Stats (Dashboard uses DisplayBuffer) ───────────────
  const stats = useMemo(() => {
    const total = displayBuffer.length;
    const critical = displayBuffer.filter((x) => x.cbsi >= 70).length;
    const high = displayBuffer.filter((x) => x.cbsi >= 40 && x.cbsi < 70).length;
    const fraud = displayBuffer.filter((x) => x.is_fraud_flag === 1).length;
    const avg = total ? Math.round((displayBuffer.reduce((s, x) => s + x.cbsi, 0) / total) * 10) / 10 : 0;
    return { total, critical, high, fraud, avg };
  }, [displayBuffer]);

  // ── Nav Items ──────────────────────────────────────────────
  const NAV = [
    { id: "command", label: "Command Centre", icon: Shield },
    { id: "roster", label: "Employee Roster", icon: Users },
    { id: "profile", label: "Employee Profile", icon: User },
    { id: "deception", label: "DeceptionGuard", icon: Radio },
    { id: "graph", label: "Fund Flow Graph", icon: GitBranch },
    { id: "evidence", label: "Evidence Vault", icon: FileText },
  ];
  const honeypotBreach = {
    accountId: "ACC_GHOST_07",
    attackerId: "EMP_1024",
    attackerRole: "IT Admin",
    threatOrigin: "EMP_1024 (IT Admin) | IP: 192.168.1.45 (Mumbai_BR_05)"
  };

  return (
    <div className="flex min-h-screen" style={{ background: t.bg, color: t.text }}>
      {/* ══════ SIDEBAR ══════ */}
      <aside
        className="w-60 flex-shrink-0 flex flex-col border-r fixed h-screen overflow-y-auto z-50"
        style={{ background: t.card, borderColor: t.border }}
      >
        <div className="text-center py-5 border-b" style={{ borderColor: t.border }}>
          <div className="text-lg font-bold tracking-[2px]" style={{ color: t.text }}>VAULTMIND</div>
          <div className="text-[10px] tracking-[3px]" style={{ color: t.text2 }}>FRAUD INTELLIGENCE 2.0</div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              style={{
                background: page === id ? `${t.accent}22` : "transparent",
                color: page === id ? t.accent : t.text2,
              }}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        <div className="px-4 pb-4 space-y-3 border-t pt-4" style={{ borderColor: t.border }}>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors cursor-pointer"
            style={{ borderColor: t.border, color: t.text2, background: t.cardAlt }}
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </button>

          <div className="flex items-center gap-2 text-[11px]" style={{ color: t.text2 }}>
            <div className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: t.green }} />
            KAFKA STREAM ACTIVE
          </div>

          <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: t.text2 }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Live Stream (WebSocket)
          </label>

          <button
            onClick={fetchNextTransaction}
            className="w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer"
            style={{ background: t.accent, color: "#fff" }}
          >
            Fetch Next Target
          </button>

          <div className="text-[10px] text-center" style={{ color: t.text2 }}>
            Display Buffer: {displayBuffer.length} / {DISPLAY_BUFFER_MAX}
          </div>
        </div>
      </aside>

      {/* ══════ MAIN CONTENT ══════ */}
      <main
        className="flex-1 ml-60 p-6 space-y-6 overflow-y-auto min-h-screen"
        style={{ transition: "all 0.5s ease-in-out" }}
      >

        {/* ── COMMAND CENTRE ──────────────────────────────── */}
        {page === "command" && (
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">Command Centre</h1>
              <div className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: t.green }} />
              <span className="text-xs" style={{ color: t.text2 }}>LIVE</span>
            </div>

            <div className="grid grid-cols-5 gap-4">
              {isLoadingInitial ? (
                <LoadingShimmer t={t} />
              ) : (
                <>
                  <KpiCard title="Transactions Scanned" value={stats.total.toLocaleString()} color={t.teal} t={t} />
                  <KpiCard title="Critical Alerts" value={stats.critical} color={t.red} t={t} />
                  <KpiCard title="High-Risk Flags" value={stats.high} color={t.amber} t={t} />
                  <KpiCard title="Confirmed Fraud" value={stats.fraud} color={t.red} t={t} />
                  <KpiCard title="Avg CBSI Score" value={stats.avg} color={t.cyan} t={t} />
                </>
              )}
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <Section title="Recent Critical Alerts" t={t} />
                {isLoadingInitial ? (
                  <LoadingShimmer t={t} />
                ) : (() => {
                  try {
                    const safeBuffer = Array.isArray(displayBuffer) ? displayBuffer : [];
                    if (!safeBuffer.length) {
                      return <div className="text-sm" style={{ color: t.text2 }}>Loading Live Stream...</div>;
                    }
                    const crits = safeBuffer.filter((x) => x.cbsi >= 70).slice(-8).reverse();
                    if (!crits.length) return <div className="text-sm" style={{ color: t.text2 }}>No critical alerts.</div>;
                    return crits.map((tx, i) => {
                      const tier = riskTier(tx.cbsi);
                      const c = tc[tier];
                      return (
                        <Card 
                          key={tx.transaction_id} 
                          t={t} 
                          style={{ borderLeft: `3px solid ${c}` }} 
                          className="!py-3 !px-4 mb-2 cursor-pointer hover:bg-[#1a1a1a] transition-colors"
                          onClick={() => { setProfileSearch(tx.emp_id); setPage("profile"); }}
                        >
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="font-bold font-mono" style={{ color: c }}>{tx?.emp_id || "N/A"}</span>
                              <span className="text-[11px] font-mono uppercase" style={{ color: t.text2 }}>{tx?.action_type || "N/A"} | {tx?.transfer_channel || "N/A"}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <Badge tier={tier} t={t} />
                              <span className="text-lg font-bold font-mono" style={{ color: c }}>{tx.cbsi}</span>
                            </div>
                          </div>
                          <EnforcementMatrix emp_id={tx.emp_id} onConfirm={handleConfirmIncident} />
                        </Card>
                      );
                    });
                  } catch { return <div style={{ color: t.text2 }}>Alert feed error</div>; }
                })()}
              </div>

              <div>
                <Section title="Live Transaction Stream" t={t} />
                {isLoadingInitial ? (
                  <LoadingShimmer t={t} />
                ) : (() => {
                  try {
                    const safeBuffer = Array.isArray(displayBuffer) ? displayBuffer : [];
                    if (!safeBuffer.length) {
                      return <div className="text-sm" style={{ color: t.text2 }}>Loading Live Stream...</div>;
                    }
                    const recent = safeBuffer.slice(-8).reverse();
                    if (!recent.length) return <div className="text-sm" style={{ color: t.text2 }}>No recent transactions.</div>;
                    return recent.map((tx, i) => {
                      const tier = riskTier(tx.cbsi);
                      const c = tc[tier] || t.text2;
                      return (
                        <Card 
                          key={tx.transaction_id} 
                          t={t} 
                          style={{ borderLeft: `3px solid ${c}` }} 
                          className="!py-3 !px-4 mb-2 cursor-pointer hover:bg-[#1a1a1a] transition-colors"
                          onClick={() => { setProfileSearch(tx.emp_id); setPage("profile"); }}
                        >
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="font-bold font-mono" style={{ color: t.text }}>{tx?.emp_id || "N/A"}</span>
                              <span className="text-xs" style={{ color: t.text2 }}>{tx?.action_type || "N/A"}</span>
                              <span className="text-xs font-mono" style={{ color: t.text2 }}>Rs.{(tx?.amount || 0).toLocaleString()}</span>
                            </div>
                            <div className="text-sm font-bold font-mono" style={{ color: c }}>CBSI: {tx.cbsi}</div>
                          </div>
                        </Card>
                      );
                    });
                  } catch { return <div style={{ color: t.text2 }}>Stream error</div>; }
                })()}
              </div>
            </div>

            <div className="grid grid-cols-5 gap-6">
              <div className="col-span-3">
                <Section title="CBSI Trend Over Time" t={t} />
                <Card t={t}>
                  {isLoadingInitial ? (
                    <GraphSkeleton t={t} height={300} />
                  ) : (() => {
                    try {
                      const pulseData = [
                        { t: "T-9", score: 15 },
                        { t: "T-8", score: 22 },
                        { t: "T-7", score: 28 },
                        { t: "T-6", score: 35 },
                        { t: "T-5", score: 42 },
                        { t: "T-4", score: 55 },
                        { t: "T-3", score: 68 },
                        { t: "T-2", score: 78 },
                        { t: "T-1", score: 86 },
                        { t: "T-0", score: 92 }
                      ];
                      return (
                        <ResponsiveContainer width="100%" height={300}>
                          <AreaChart data={pulseData}>
                            <defs>
                              <linearGradient id="cbsiFill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.35} />
                                <stop offset="60%" stopColor="#00B4D8" stopOpacity={0.18} />
                                <stop offset="100%" stopColor="#00B4D8" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid 
                              strokeDasharray="3 6" 
                              vertical={false} 
                              stroke="#333"
                              opacity={0.35}
                            />
                            <XAxis 
                              dataKey="t" 
                              tick={{ fill: "#888", fontSize: 10 }} 
                              axisLine={{ stroke: "#333" }}
                              tickLine={{ stroke: "#333" }}
                            />
                            <YAxis 
                              domain={[0, 100]} 
                              tick={{ fill: "#888", fontSize: 10 }}
                              axisLine={{ stroke: "#333" }}
                              tickLine={{ stroke: "#333" }}
                            />
                            <Tooltip 
                              content={({ active, payload, label }) => {
                                if (active && payload && payload.length) {
                                  const score = payload[0].value;
                                  const isCritical = score >= 76;
                                  return (
                                    <div className="bg-[#121212] border border-[#333] px-3 py-2 rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
                                      <div className="text-[#888] text-[11px] mb-1 font-mono tracking-wider">
                                        {label}
                                      </div>
                                      <div className="text-white text-sm font-bold font-mono">
                                        CBSI Score: <span style={{ color: isCritical ? "#ef4444" : "#00B4D8" }}>{score}</span>
                                      </div>
                                    </div>
                                  );
                                }
                                return null;
                              }}
                              cursor={{ stroke: '#333', strokeWidth: 1, strokeDasharray: '4 4' }}
                            />
                            <Area 
                              type="monotone" 
                              dataKey="score" 
                              stroke="#00B4D8" 
                              fill="url(#cbsiFill)" 
                              strokeWidth={2}
                              dot={({ cx, cy, payload }) => {
                                if (!payload || payload.score <= 75) return null;
                                return (
                                  <g>
                                    <circle cx={cx} cy={cy} r={8} className="animate-ping" fill="#ef4444" opacity={0.6} />
                                    <circle cx={cx} cy={cy} r={3} fill="#ef4444" />
                                  </g>
                                );
                              }}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      );
                    } catch { return <div style={{ color: t.text2 }}>Chart rendering error</div>; }
                  })()}
                </Card>
              </div>

              <div className="col-span-2">
                <Section title="Risk Distribution" t={t} />
                <Card t={t}>
                  {isLoadingInitial ? (
                    <GraphSkeleton t={t} height={300} />
                  ) : (() => {
                    try {
                      const counts = { CRITICAL: 0, HIGH: 0, WATCH: 0, NORMAL: 0 };
                      displayBuffer.forEach((tx) => { counts[riskTier(tx.cbsi)]++; });
                      const data = Object.entries(counts).map(([k, v]) => ({ name: k, value: v }));
                      const colors = [t.red, t.amber, t.cyan, t.green];
                      return (
                        <ResponsiveContainer width="100%" height={300}>
                          <PieChart>
                            <Pie data={data} cx="50%" cy="50%" innerRadius={70} outerRadius={110} dataKey="value" label={false}>
                              {data.map((_, i) => <Cell key={i} fill={colors[i]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ background: t.card, border: `1px solid ${t.border}`, color: t.text, borderRadius: 8 }} />
                            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px', color: t.text2 }} formatter={(value) => <span style={{ color: t.text2 }}>{value}</span>} />
                          </PieChart>
                        </ResponsiveContainer>
                      );
                    } catch { return <div style={{ color: t.text2 }}>Pie chart error</div>; }
                  })()}
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* ── EMPLOYEE ROSTER ─────────────────────────────── */}
        {page === "roster" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Employee Roster</h1>

            {(() => {
              try {
                let filtered = [...empScores];
                if (rosterRole !== "ALL") filtered = filtered.filter((e) => e.emp_class === rosterRole);
                if (rosterTier !== "ALL") filtered = filtered.filter((e) => e.status === rosterTier);
                if (rosterSearch.trim()) filtered = filtered.filter((e) => e.emp_id.toLowerCase().includes(rosterSearch.toLowerCase()));
                const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
                const cp = Math.min(rosterPage, totalPages);
                const slice = filtered.slice((cp - 1) * ROWS_PER_PAGE, cp * ROWS_PER_PAGE);

                return (
                  <>
                    <div className="grid grid-cols-3 gap-4">
                      <select value={rosterRole} onChange={(e) => { setRosterRole(e.target.value); setRosterPage(1); }}
                        className="rounded-lg border px-3 py-2 text-sm" style={{ background: t.card, borderColor: t.border, color: t.text }}>
                        <option value="ALL">All Roles</option>
                        <option value="CLERK">CLERK</option>
                        <option value="MANAGER">MANAGER</option>
                        <option value="IT_ADMIN">IT_ADMIN</option>
                      </select>
                      <select value={rosterTier} onChange={(e) => { setRosterTier(e.target.value); setRosterPage(1); }}
                        className="rounded-lg border px-3 py-2 text-sm" style={{ background: t.card, borderColor: t.border, color: t.text }}>
                        <option value="ALL">All Statuses</option>
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="WATCH">WATCH</option>
                        <option value="NORMAL">NORMAL</option>
                      </select>
                      <div className="relative">
                        <Search size={14} className="absolute left-3 top-3" style={{ color: t.text2 }} />
                        <input value={rosterSearch} onChange={(e) => { setRosterSearch(e.target.value); setRosterPage(1); }}
                          placeholder="Search EMP_ID..." className="w-full rounded-lg border pl-9 pr-3 py-2 text-sm"
                          style={{ background: t.card, borderColor: t.border, color: t.text }} />
                      </div>
                    </div>

                    <div className="text-xs" style={{ color: t.text2 }}>
                      Showing {(cp - 1) * ROWS_PER_PAGE + 1}-{Math.min(cp * ROWS_PER_PAGE, filtered.length)} of {filtered.length} | Page {cp}/{totalPages}
                    </div>

                    <Card t={t} className="!p-0 overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr style={{ background: t.cardAlt }}>
                            {["Employee ID", "Role", "Branch", "Peak CBSI", "Avg CBSI", "Transactions", "Status"].map((h) => (
                              <th key={h} className="px-4 py-3 text-left text-[11px] uppercase tracking-wider font-semibold" style={{ color: t.text2 }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {slice.map((e) => (
                            <tr key={e.emp_id} className="border-t cursor-pointer hover:opacity-80" style={{ borderColor: t.border }}
                              onClick={() => { setProfileSearch(e.emp_id); setPage("profile"); }}>
                              <td className="px-4 py-3 font-mono font-semibold" style={{ color: tc[e.status] || t.text }}>{e.emp_id}</td>
                              <td className="px-4 py-3" style={{ color: t.text2 }}>{e.emp_class}</td>
                              <td className="px-4 py-3" style={{ color: t.text2 }}>{e.branch_id}</td>
                              <td className="px-4 py-3 font-mono font-bold" style={{ color: tc[e.status] }}>{e.peak}</td>
                              <td className="px-4 py-3 font-mono" style={{ color: t.text2 }}>{e.avg}</td>
                              <td className="px-4 py-3 font-mono" style={{ color: t.text2 }}>{e.txnCount}</td>
                              <td className="px-4 py-3"><Badge tier={e.status} t={t} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </Card>

                    <div className="flex justify-center items-center gap-4">
                      <button onClick={() => setRosterPage(Math.max(1, cp - 1))} disabled={cp <= 1}
                        className="p-2 rounded-lg border cursor-pointer disabled:opacity-30" style={{ borderColor: t.border, color: t.text2 }}>
                        <ChevronLeft size={16} />
                      </button>
                      <span className="text-sm font-mono" style={{ color: t.text2 }}>Page {cp} / {totalPages}</span>
                      <button onClick={() => setRosterPage(Math.min(totalPages, cp + 1))} disabled={cp >= totalPages}
                        className="p-2 rounded-lg border cursor-pointer disabled:opacity-30" style={{ borderColor: t.border, color: t.text2 }}>
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </>
                );
              } catch (e) { return <div style={{ color: t.red }}>Roster error: {String(e)}</div>; }
            })()}
          </div>
        )}

        {/* ── EMPLOYEE PROFILE ────────────────────────────── */}
        {page === "profile" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Employee Profile Search</h1>
            <div className="relative max-w-lg">
              <Search size={16} className="absolute left-3 top-3" style={{ color: t.text2 }} />
              <input value={profileSearch} onChange={(e) => setProfileSearch(e.target.value)}
                placeholder="e.g. EMP_1001" className="w-full rounded-lg border pl-10 pr-4 py-2.5 text-sm"
                style={{ background: t.card, borderColor: t.border, color: t.text }} />
            </div>

            {(() => {
              try {
                const eid = profileSearch.trim().toUpperCase();
                if (!eid) return (
                  <Card t={t} className="text-center !py-16">
                    <div className="text-base" style={{ color: t.text2 }}>Enter an Employee ID to view their forensic profile</div>
                    <div className="text-xs mt-2" style={{ color: t.text2 }}>Example: EMP_1001, EMP_1416, EMP_1200</div>
                  </Card>
                );

                const emp = scoredTxns.find((tx) => tx?.emp_id === eid);
                const txns = scoredTxns.filter((tx) => tx?.emp_id === eid);
                const latestTxn = txns[txns.length - 1];
                if (!emp && !txns.length) return <div className="text-sm" style={{ color: t.amber }}>No data found for {eid}.</div>;

                let peak = txns.length ? Math.max(...txns.map((x) => x.cbsi)) : 0;
                // CRITICAL: If this is the attacker (EMP_1024), set score to 100 (Critical)
                if (eid === "EMP_1024") {
                  peak = 100;
                }
                const tier = riskTier(peak);
                const c = tc[tier];
                const isConfirmed = confirmedIncidents.some((inc) => inc.emp_id === eid);
                const displayRole = eid === "EMP_1024" ? "IT Admin" : (emp?.emp_class || "Unknown");
                const isDanger = peak >= 75;
                const borderColor = isDanger ? t.red : t.green;
                const bgColor = isDanger ? "bg-red-500/10" : "bg-emerald-500/10";

                // Daily trend
                const dailyMap = {};
                txns.forEach((tx) => {
                  const d = tx?.timestamp?.slice(0, 10);
                  if (!d) return;
                  if (!dailyMap[d]) dailyMap[d] = { sum: 0, count: 0 };
                  dailyMap[d].sum += tx.cbsi;
                  dailyMap[d].count++;
                });
                let trendData = Object.entries(dailyMap)
                  .map(([d, v]) => ({ date: d, cbsi: Math.round((v.sum / v.count) * 10) / 10 }))
                  .sort((a, b) => a.date.localeCompare(b.date));

                if (trendData.length < 2) {
                  const formatDate = (d) => d.toISOString().slice(0, 10);
                  const latestRaw = txns[txns.length - 1]?.timestamp;
                  let baseDate = latestRaw ? new Date(latestRaw) : new Date();
                  if (Number.isNaN(baseDate.getTime())) {
                    baseDate = new Date();
                  }
                  const baseScore = peak || (txns[txns.length - 1]?.cbsi ?? 15);
                  trendData = Array.from({ length: 7 }, (_, idx) => {
                    const d = new Date(baseDate);
                    d.setDate(d.getDate() - (6 - idx));
                    const jitter = (idx % 3 - 1) * 2;
                    const score = Math.max(5, Math.min(100, Math.round(baseScore + jitter)));
                    return { date: formatDate(d), cbsi: score };
                  });
                }

                if (peak < 30) {
                  trendData = trendData.map(d => ({ ...d, cbsi: 15 }));
                } else if (peak > 75) {
                  trendData = trendData.map((d, i) => ({ ...d, cbsi: Math.min(100, 20 + i * 15) }));
                }

                const flaggedTxns = txns.filter((x) => x.cbsi >= 40).sort((a, b) => b.cbsi - a.cbsi).slice(0, 20);
                const nlpTxns = txns.filter((tx) => tx?.raw_complaint_text?.trim());

                return (
                  <>
                    <Card t={t} style={{ borderLeft: `4px solid ${c}` }}>
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="text-xl font-bold">{eid}</div>
                          <div className="text-sm" style={{ color: t.text2 }}>{displayRole} | {emp?.branch_id || "Unknown"}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-4xl font-bold font-mono" style={{ color: c }}>{peak}</div>
                          <Badge tier={tier} t={t} />
                        </div>
                      </div>
                      <div className="mt-4 flex items-center gap-3">
                        <button
                          onClick={() => handleConfirmIncident(eid)}
                          disabled={isConfirmed}
                          className="px-3 py-1.5 text-[10px] font-mono font-bold border border-[#E50914] text-[#E50914] hover:bg-[#E50914] hover:text-white transition-colors uppercase rounded-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          [ CONFIRM INCIDENT ]
                        </button>
                         <button
                           onClick={() => showToast("False Positive", "Model retraining initiated...", "amber")}
                           className="px-3 py-1.5 text-[10px] font-mono font-bold border border-[#FFB300] text-[#FFB300] hover:bg-[#FFB300] hover:text-black transition-colors uppercase rounded-sm cursor-pointer"
                         >
                           [ FALSE ALARM / RETRAIN ]
                         </button>
                        {isConfirmed && (
                          <span className="text-[10px] font-mono font-bold text-[#00E676] uppercase tracking-widest">
                            INCIDENT CONFIRMED
                          </span>
                        )}
                      </div>
                    </Card>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 my-4">
                      <ShapSimulator initialScore={peak} isCritical={peak > 75} />
                      <GlassBoxEngine score={peak} emp_id={eid} context={latestTxn} />
                    </div>

                    {(tier === "CRITICAL" || tier === "HIGH" || eid === "EMP_1024" || eid === "EMP_1024_HONEYPOT") && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 my-4">
                        <BlastRadius targetId={eid} />
                        <ForensicTimeline events={flaggedTxns.map(tx => ({ time: tx.timestamp.slice(11, 19), text: `${tx.action_type} - Rs.${(tx.amount || 0).toLocaleString()}`, tier: riskTier(tx.cbsi) })).slice(0, 5)} />
                      </div>
                    )}

                    <ProfileTabs t={t} tc={tc} trendData={trendData} txns={txns} flaggedTxns={flaggedTxns} nlpTxns={nlpTxns} eid={eid} isCritical={peak > 75} isCalm={peak < 30} />
                  </>
                );
              } catch (e) { return <div style={{ color: t.red }}>Profile error: {String(e)}</div>; }
            })()}
          </div>
        )}

{/* ── FUND FLOW GRAPH ─────────────────────────────── */}
        {page === "graph" && (
          <div className="-m-6 h-screen overflow-hidden">
            {isLoadingInitial ? (
              <div className="p-6">
                <GraphSkeleton t={t} height={600} />
              </div>
            ) : (
              <FundFlowGraph 
                liveTxns={scoredTxns} 
                onGenerateEvidence={handleConfirmIncident} 
              />
            )}
          </div>
        )}

        {/* ── EVIDENCE VAULT ──────────────────────────────── */}
        {page === "evidence" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Evidence Vault</h1>

            <div className="grid grid-cols-2 gap-4">
              <KpiCard title="PDF Evidence Packages" value={String(vaultEvidence.length)} color={t.teal} t={t} />
              <KpiCard title="STR JSON Filings" value={String(vaultEvidence.length)} color={t.cyan} t={t} />
            </div>

            <Section title="Verified STR Evidence Packages (Agent 7)" t={t} />
            <Card t={t} className="!p-0 overflow-hidden mb-6">
              <table className="w-full text-left text-sm font-mono">
                <thead className="bg-[#111] text-gray-500 text-[10px] uppercase">
                  <tr>
                    <th className="p-4 border-b border-[#222]">Filename</th>
                    <th className="p-4 border-b border-[#222]">SHA-256 Hash</th>
                    <th className="p-4 border-b border-[#222]">Block ID</th>
                    <th className="p-4 border-b border-[#222]">Timestamp</th>
                    <th className="p-4 border-b border-[#222]">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#222]">
                  {vaultEvidence.map((evd) => {
                    return (
                      <tr key={evd.id} className="hover:bg-[#1a1a1a] transition-colors">
                        <td className="p-4 text-[#00D4AA] font-bold">
                          <div className="flex items-center gap-2">
                            {evd.status === "Generated" && <FileText size={14} className="text-[#00D4AA]" />}
                            <span className={evd.status === "Generated" ? "" : "text-gray-500"}>{evd.filename}</span>
                          </div>
                        </td>
                        <td className="p-4 text-xs text-gray-400">{evd.hash}</td>
                        <td className="p-4 text-xs text-gray-400">{evd.blockId}</td>
                        <td className="p-4 text-[10px] text-gray-500">{evd.timestamp}</td>
                        <td className="p-4">
                          {evd.status === "Pending Dossier" ? (
                            <span className="text-xs text-[#FFB300] font-bold animate-pulse">PENDING DOSSIER</span>
                          ) : (
                            <button
                              onClick={() => {
                                setDownloading(evd.filename);
                                setTimeout(() => setDownloading(null), 2000);
                              }}
                              className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#E50914] text-white text-[10px] uppercase font-bold hover:bg-red-700 transition cursor-pointer"
                              disabled={downloading === evd.filename}
                            >
                              {downloading === evd.filename ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                              Download
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>

            <Section title="Generate New Evidence" t={t} />
            <Card t={t} className="flex items-center justify-between p-6">
              <div className="text-sm" style={{ color: t.text2 }}>
                Select a critical employee to package their forensic history into an immutable dossier.
              </div>
              <div className="flex items-center gap-4">
                <select 
                  value={generateTarget} 
                  onChange={(e) => setGenerateTarget(e.target.value)}
                  className="bg-[#111] border border-[#333] text-white px-4 py-2 rounded font-mono text-sm outline-none cursor-pointer"
                >
                  <option value="">Select Target...</option>
                  {dossierOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                {isGeneratingDossier ? (
                  <div className="px-6 py-2 flex items-center gap-2 bg-[#00D4AA] text-[#111] font-bold uppercase tracking-wider rounded">
                    <Loader2 size={16} className="animate-spin" /> GENERATING...
                  </div>
                ) : lastGenerated && lastGenerated.emp_id === generateTarget ? (
                  <div className="px-4 py-2 flex items-center gap-2 rounded border border-[#333] bg-[#111] text-xs font-mono text-gray-300">
                    <FileText size={14} className="text-[#00D4AA]" />
                    {lastGenerated.hash}
                  </div>
                ) : (
                  <button 
                    onClick={handleGenerateDossier}
                    disabled={!generateTarget}
                    className="px-6 py-2 flex items-center gap-2 bg-[#00D4AA] text-[#111] font-bold uppercase tracking-wider rounded hover:bg-[#00b390] transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    [ GENERATE FIU DOSSIER ]
                  </button>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* ── DECEPTIONGUARD ─────────────────────────────────── */}
        {page === "deception" && (
          <div className="space-y-6 pb-12">
            <h1 className="text-2xl font-bold font-mono tracking-[4px] uppercase" style={{ color: t.accent }}>DeceptionGuard</h1>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <Section title="Honeypot Node Radar" t={t} />
                <Card t={t} className="flex flex-col items-center justify-center !py-12 relative overflow-hidden h-[400px]">
                  <div className="absolute inset-0 opacity-10 pointer-events-none" 
                    style={{ background: 'linear-gradient(rgba(0, 255, 0, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 0, 0.1) 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
                  
                  <div className="relative flex items-center justify-center w-64 h-64 border border-[#333] rounded-full">
                    {/* Concentric circles */}
                    <div className="absolute w-48 h-48 border border-[#333] rounded-full"></div>
                    <div className="absolute w-32 h-32 border border-[#333] rounded-full"></div>
                    <div className="absolute w-16 h-16 border border-[#333] rounded-full text-center flex items-center justify-center font-mono text-[8px] text-[#333]">CORE</div>
                    
                    {/* Clean Radar Arm */}
                    <motion.div 
                      animate={{ rotate: 360 }}
                      transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                      className="absolute w-full h-full rounded-full"
                      style={{ 
                        background: "conic-gradient(from 0deg, rgba(0, 230, 118, 0.05) 0deg, transparent 60deg, transparent 360deg)",
                        borderRight: "1px solid rgba(0, 230, 118, 0.4)"
                      }}
                    />
                    
                    {/* Clean Wireframe Pulsing Nodes */}
                    <motion.div 
                      animate={{ opacity: [0.1, 1, 0.1] }}
                      transition={{ duration: 2, repeat: Infinity, delay: 0.2 }}
                      className="absolute w-1.5 h-1.5 bg-[#00E676] rounded-full top-10 left-20 shadow-[0_0_8px_#00E676]"
                    />
                    <motion.div 
                      animate={{ opacity: [0.1, 1, 0.1] }}
                      transition={{ duration: 2.5, repeat: Infinity, delay: 1 }}
                      className="absolute w-2 h-2 bg-[#FFB300] rounded-full top-12 right-16 shadow-[0_0_10px_#FFB300]"
                    />
                    <motion.div 
                      animate={{ opacity: [0.1, 1, 0.1] }}
                      transition={{ duration: 3, repeat: Infinity, delay: 0.5 }}
                      className="absolute bottom-12 left-12 flex items-center gap-1.5"
                    >
                      <div className="w-2 h-2 bg-[#E50914] rounded-full shadow-[0_0_10px_#E50914]" />
                      <span className="text-[8px] font-mono font-bold text-[#E50914] tracking-widest whitespace-nowrap opacity-80 mix-blend-screen">[TARGET PING: MUMBAI]</span>
                    </motion.div>
                    <motion.div 
                      animate={{ opacity: [0.1, 1, 0.1] }}
                      transition={{ duration: 1.5, repeat: Infinity, delay: 2 }}
                      className="absolute w-1.5 h-1.5 bg-[#00E676] rounded-full bottom-20 right-12 shadow-[0_0_8px_#00E676]"
                    />
                  </div>
                  <div className="mt-8 text-xs font-mono text-[#00E676] animate-pulse uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-[#00E676] rounded-sm"></span> Scanning Subnets...
                  </div>
                </Card>
              </div>

              <div>
                <Section title="Active Ghost Accounts" t={t} />
                <Card t={t} className="!p-0 overflow-hidden">
                  <div className="h-[400px] flex flex-col">
                    <table className="w-full text-left text-sm font-mono flex-shrink-0">
                      <thead className="bg-[#111] text-gray-500 text-[10px] uppercase sticky top-0 z-10">
                        <tr>
                          <th className="p-4 border-b border-[#222] w-1/4">Account ID</th>
                          <th className="p-4 border-b border-[#222] w-1/4">Honey Balance</th>
                          <th className="p-4 border-b border-[#222] w-1/4">Status</th>
                          <th className="p-4 border-b border-[#222] w-1/4">Threat Origin</th>
                        </tr>
                      </thead>
                    </table>
                    <div className="overflow-y-auto flex-1">
                      <table className="w-full text-left text-sm font-mono">
                        <tbody className="divide-y divide-[#222]">
                      <tr className="hover:bg-[#1a1a1a] transition-colors">
                        <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_99</td>
                        <td className="p-4">Rs.50,00,000</td>
                        <td className="p-4 text-xs text-gray-400">Monitoring for lookup</td>
                        <td className="p-4 text-[10px] text-gray-600">-</td>
                      </tr>
                      <tr className="hover:bg-[#1a1a1a] transition-colors">
                        <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_42</td>
                        <td className="p-4">Rs.1,20,00,000</td>
                        <td className="p-4 text-xs text-gray-400">Decoy credential deployed</td>
                        <td className="p-4 text-[10px] text-gray-600">Awaiting trace...</td>
                      </tr>
                      <tr className="hover:bg-[#1a1a1a] transition-colors bg-[#2a1313]">
                        <td className="p-4 text-[#E50914] font-bold">{honeypotBreach.accountId}</td>
                        <td className="p-4">Rs.8,00,000</td>
                        <td className="p-4 text-xs text-[#E50914] font-bold animate-pulse">
                          BREACH DETECTED
                          <button 
                            onClick={() => { setProfileSearch(honeypotBreach.attackerId); setPage("profile"); }}
                            className="ml-4 px-3 py-1 bg-[#E50914] text-white text-[10px] uppercase tracking-wider rounded font-bold hover:bg-red-700 transition cursor-pointer"
                          >
                            [ Investigate ]
                          </button>
                        </td>
                        <td className="p-4 text-[11px] text-[#FFB300] font-bold tracking-tight">{honeypotBreach.threatOrigin}</td>
                      </tr>
                       <tr className="hover:bg-[#1a1a1a] transition-colors">
                         <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_15</td>
                         <td className="p-4">Rs.25,00,000</td>
                         <td className="p-4 text-xs text-gray-400">Await access trigger</td>
                         <td className="p-4 text-[10px] text-gray-600">Dormant</td>
                       </tr>
                       <tr className="hover:bg-[#1a1a1a] transition-colors">
                         <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_61</td>
                         <td className="p-4">Rs.75,00,000</td>
                         <td className="p-4 text-xs text-gray-400">Credential logged</td>
                         <td className="p-4 text-[10px] text-gray-600">Monitoring</td>
                       </tr>
                       <tr className="hover:bg-[#1a1a1a] transition-colors">
                         <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_88</td>
                         <td className="p-4">Rs.3,50,00,000</td>
                         <td className="p-4 text-xs text-gray-400">Premium decoy deployed</td>
                         <td className="p-4 text-[10px] text-gray-600">Armed</td>
                       </tr>
                       <tr className="hover:bg-[#1a1a1a] transition-colors">
                         <td className="p-4 text-[#00B4D8] font-bold">ACC_GHOST_33</td>
                         <td className="p-4">Rs.1,00,000</td>
                         <td className="p-4 text-xs text-gray-400">Micro-transaction trap</td>
                         <td className="p-4 text-[10px] text-gray-600">Idle</td>
                       </tr>
                    </tbody>
                  </table>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* ── FOOTER TELEMETRY ──────────────────────────────── */}
        <div className="fixed bottom-0 left-60 right-0 border-t py-1.5 px-6 flex items-center justify-between z-50 text-[10px] font-mono tracking-widest" style={{ background: t.cardAlt, borderColor: t.border, color: t.text2 }}>
          <div className="flex items-center gap-3">
            <span className="text-[#00E676] animate-pulse">●</span> 
            [SYS_OP] NODE 44 ACTIVE | PINGING CORE_DB... 12MS | KAFKA OFFSET: 902834
          </div>
          <div>
            THREAT LEVEL: <span className="text-[#E50914] font-bold ml-1">ELEVATED</span>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─── Enforcement Matrix Component ──────────────────────────────
function EnforcementMatrix({ emp_id, onConfirm }) {
  const [status, setStatus] = useState("idle");

  if (status === "done") {
    return <div className="mt-3 text-[10px] font-mono text-[#00E676] font-bold">STATUS: RESOLVED</div>;
  }

  if (status === "recalibrating") {
    return (
      <div className="mt-3 text-[10px] font-mono text-[#FFB300] flex items-center gap-2">
        <Loader2 size={12} className="animate-spin" /> RECALIBRATING ISOLATION FOREST THRESHOLDS...
      </div>
    );
  }

  const handleAction = async (actionType) => {
    if (actionType === "FALSE_ALARM") setStatus("recalibrating");
    try {
      await fetch(`http://localhost:8000/api/feedback/${emp_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: actionType })
      });
    } catch (e) { console.error("Feedback error", e); }
    
    if (actionType === "CONFIRM") {
      setStatus("done");
      if (onConfirm) onConfirm(emp_id);
    } else {
      setTimeout(() => setStatus("done"), 2000);
    }
  };

  return (
    <div className="mt-3 flex items-center gap-2 pt-2 border-t border-[#222]">
      <button 
        onClick={(e) => { e.stopPropagation(); handleAction("CONFIRM"); }}
        className="px-2 py-1 text-[9px] font-mono font-bold border border-[#E50914] text-[#E50914] hover:bg-[#E50914] hover:text-white transition-colors uppercase rounded-sm cursor-pointer"
      >
        [ Confirm Incident ]
      </button>
      <button 
        onClick={(e) => { e.stopPropagation(); handleAction("FALSE_ALARM"); }}
        className="px-2 py-1 text-[9px] font-mono font-bold border border-gray-600 text-gray-500 hover:border-[#FFB300] hover:bg-[#FFB300] hover:text-[#0a0a0a] transition-colors uppercase rounded-sm cursor-pointer"
      >
        [ False Alarm / Retrain ]
      </button>
    </div>
  );
}

// ─── Profile Tabs Sub-Component ──────────────────────────────
function ProfileTabs({ t, tc, trendData, txns, flaggedTxns, nlpTxns, eid, isCritical, isCalm }) {
  const [tab, setTab] = useState("trend");
  const tabs = [
    { id: "trend", label: "Risk Trend" },
    { id: "txns", label: "Transactions" },
    { id: "rules", label: "Triggered Rules" },
    { id: "nlp", label: "NLP Flags" },
  ];

  const chartColor = isCritical ? t.red : isCalm ? t.teal : t.accent;

  return (
    <div>
      <div className="flex border-b mb-4" style={{ borderColor: t.border }}>
        {tabs.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)}
            className="px-5 py-2.5 text-sm font-semibold transition-colors cursor-pointer"
            style={{
              color: tab === id ? chartColor : t.text2,
              borderBottom: tab === id ? `2px solid ${chartColor}` : "2px solid transparent",
            }}
          >{label}</button>
        ))}
      </div>

      {tab === "trend" && (
        <Card t={t}>
          <Section title={`Historical Risk Trend - ${eid}`} t={t} />
          {trendData.length ? (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="profileStroke" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="25%" stopColor="#ef4444" />
                    <stop offset="25%" stopColor="#00B4D8" />
                    <stop offset="100%" stopColor="#00B4D8" />
                  </linearGradient>
                  <linearGradient id="profileFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="25%" stopColor="#ef4444" stopOpacity={0.35} />
                    <stop offset="25%" stopColor="#00B4D8" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#00B4D8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke={t.border} opacity={0.25} />
                <XAxis dataKey="date" tick={{ fill: t.text2, fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: t.text2, fontSize: 10 }} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: t.card, border: `1px solid ${t.border}`, color: t.text, borderRadius: 8 }} />
                <Area type="monotone" dataKey="cbsi" stroke="url(#profileStroke)" strokeWidth={2} fill="url(#profileFill)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <div className="text-sm py-8 text-center" style={{ color: t.text2 }}>Not enough data</div>}
        </Card>
      )}

      {tab === "txns" && (
        <Card t={t} className="!p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr style={{ background: t.cardAlt }}>
              {["Timestamp", "Action", "Amount", "Channel", "Account", "CBSI", "Fraud"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-[11px] uppercase tracking-wider" style={{ color: t.text2 }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {txns.slice(-50).reverse().map((tx, i) => (
                <tr key={i} className="border-t" style={{ borderColor: t.border }}>
                  <td className="px-3 py-2 text-xs" style={{ color: t.text2 }}>{tx?.timestamp?.slice(0, 19)}</td>
                  <td className="px-3 py-2 text-xs">{tx?.action_type}</td>
                  <td className="px-3 py-2 text-xs font-mono">Rs.{(tx?.amount || 0).toLocaleString()}</td>
                  <td className="px-3 py-2 text-xs" style={{ color: t.text2 }}>{tx?.transfer_channel}</td>
                  <td className="px-3 py-2 text-xs font-mono" style={{ color: t.text2 }}>{tx?.account_touched}</td>
                  <td className="px-3 py-2 font-mono font-bold" style={{ color: tc[riskTier(tx.cbsi)] }}>{tx.cbsi}</td>
                  <td className="px-3 py-2">{tx?.is_fraud_flag ? <span style={{ color: t.red }}>YES</span> : <span style={{ color: t.green }}>NO</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {tab === "rules" && (
        <div className="space-y-2">
          {flaggedTxns.length ? flaggedTxns.map((tx, i) => {
            const rules = getTriggeredRules(tx);
            if (!rules.length) return null;
            return rules.map((r, j) => (
              <Card key={`${i}-${j}`} t={t} style={{ borderLeft: `3px solid ${t.amber}` }} className="!py-2.5 !px-4">
                <div className="flex justify-between">
                  <span className="text-xs font-semibold" style={{ color: t.amber }}>{r}</span>
                  <span className="text-[11px]" style={{ color: t.text2 }}>{tx?.timestamp?.slice(0, 19)}</span>
                </div>
              </Card>
            ));
          }) : <div className="text-sm py-8 text-center" style={{ color: t.text2 }}>No rule triggers</div>}
        </div>
      )}

      {tab === "nlp" && (
        <div className="space-y-2">
          {nlpTxns.length ? nlpTxns.slice(0, 15).map((tx, i) => {
            const flags = extractNlpFlags(tx);
            return (
              <div key={i}>
                {flags.map((f, j) => (
                  <Card key={j} t={t} style={{ borderLeft: `3px solid ${t.red}` }} className="!py-2.5 !px-4 mb-1">
                    <div className="flex justify-between">
                      <span className="text-xs font-semibold" style={{ color: t.red }}>NLP MATCH: {f}</span>
                      <span className="text-[11px]" style={{ color: t.text2 }}>{tx?.timestamp?.slice(0, 19)}</span>
                    </div>
                  </Card>
                ))}
                <div className="text-[11px] px-4 mb-2" style={{ color: t.text2 }}>
                  Text: <em>{tx?.raw_complaint_text?.slice(0, 200)}</em>
                </div>
              </div>
            );
          }) : <div className="text-sm py-8 text-center" style={{ color: t.text2 }}>No NLP-relevant text found</div>}
        </div>
      )}
    </div>
  );
}