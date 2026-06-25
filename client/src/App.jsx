import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import FundFlowGraph from './components/FundFlowGraph';
import {
  Sun, Moon, Search, Shield, Users, User, GitBranch, FileText,
  AlertTriangle, Activity, ChevronLeft, ChevronRight, Download,
  Loader2, Radio, TrendingUp, LogOut
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, Legend
} from "recharts";
import { ForensicTimeline, GlassBoxEngine, BlastRadius, ShapSimulator, GNNThreatNode, HistoricalContext } from "./ProfileComponents.jsx";
import { motion } from "framer-motion";
import { getTriggeredRules, extractNlpFlags } from "./data";
import { supabase } from './supabaseClient';
import LoginPage from './components/LoginPage';
import { authStore } from './authStore';
import { useAppStore } from './store';

import { DARK, LIGHT, TIER_COLORS, ROWS_PER_PAGE, riskTier, forceDownloadPDF } from "./utils.js";
import { Badge } from "./components/Badge.jsx";
import { Card } from "./components/Card.jsx";
import { KpiCard } from "./components/KpiCard.jsx";
import { Section } from "./components/Section.jsx";
import { LoadingShimmer } from "./components/LoadingShimmer.jsx";

import { fetchWithAuth, API_BASE } from './apiService';

import { GraphSkeleton } from "./components/GraphSkeleton.jsx";
import { EnforcementMatrix } from "./components/EnforcementMatrix.jsx";
import { ProfileTabs } from "./components/ProfileTabs.jsx";
import { Toast } from "./components/Toast.jsx";

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!authStore.getUser());
  const [user, setUser] = useState(authStore.getUser());
  const userRole = user?.role || '';
  const [downloading, setDownloading] = useState(null);
  
  const theme = useAppStore(s => s.theme);
  const setTheme = useAppStore(s => s.setTheme);
  const page = useAppStore(s => s.page);
  const setPage = useAppStore(s => s.setPage);
  const profileSearch = useAppStore(s => s.profileSearch);
  const setProfileSearch = useAppStore(s => s.setProfileSearch);
  const rosterPage = useAppStore(s => s.rosterPage);
  const setRosterPage = useAppStore(s => s.setRosterPage);
  const rosterSearch = useAppStore(s => s.rosterSearch);
  const setRosterSearch = useAppStore(s => s.setRosterSearch);
  const rosterRole = useAppStore(s => s.rosterRole);
  const setRosterRole = useAppStore(s => s.setRosterRole);
  const rosterTier = useAppStore(s => s.rosterTier);
  const setRosterTier = useAppStore(s => s.setRosterTier);
  const graphSearch = useAppStore(s => s.graphSearch);
  const setGraphSearch = useAppStore(s => s.setGraphSearch);
  const selectedNode = useAppStore(s => s.selectedNode);
  const setSelectedNode = useAppStore(s => s.setSelectedNode);
  const graphRef = useRef(null);

  const scoredTxns = useAppStore(s => s.scoredTxns);
  const setScoredTxns = useAppStore(s => s.setScoredTxns);
  const employeeMetadata = useAppStore(s => s.employeeMetadata);
  const setEmployeeMetadata = useAppStore(s => s.setEmployeeMetadata);
  const isLoadingInitial = useAppStore(s => s.isLoadingInitial);
  const setIsLoadingInitial = useAppStore(s => s.setIsLoadingInitial);
  const autoRefresh = useAppStore(s => s.autoRefresh);
  const setAutoRefresh = useAppStore(s => s.setAutoRefresh);

  const MAX_TRANSACTIONS = 10000;

  const evidencePage = useAppStore(s => s.evidencePage);
  const setEvidencePage = useAppStore(s => s.setEvidencePage);
  const newEvidenceIds = useAppStore(s => s.newEvidenceIds);
  const setNewEvidenceIds = useAppStore(s => s.setNewEvidenceIds);
  const EVIDENCE_PER_PAGE = 20;
  const [evidenceSearch, setEvidenceSearch] = useState("");

  const vaultEvidence = useAppStore(s => s.vaultEvidence);
  const setVaultEvidence = useAppStore(s => s.setVaultEvidence);

  const confirmedIncidents = useAppStore(s => s.confirmedIncidents);
  const setConfirmedIncidents = useAppStore(s => s.setConfirmedIncidents);
  const falseAlarms = useAppStore(s => s.falseAlarms);
  const setFalseAlarms = useAppStore(s => s.setFalseAlarms);
  const generateTarget = useAppStore(s => s.generateTarget);
  const setGenerateTarget = useAppStore(s => s.setGenerateTarget);
  const isGeneratingDossier = useAppStore(s => s.isGeneratingDossier);
  const setIsGeneratingDossier = useAppStore(s => s.setIsGeneratingDossier);
  const [lastGenerated, setLastGenerated] = useState(null);

  const [toastVisible, setToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const showToast = useCallback((msg) => {
    setToastMessage(msg);
    setToastVisible(true);
  }, []);

  const handleConfirmIncident = useCallback((emp_id) => {
    const normalized = (emp_id || "").toUpperCase();
    if (!normalized) return;
    
    fetchWithAuth(`api/feedback/${normalized}`, {
      method: "POST",
      body: JSON.stringify({ action: "CONFIRM", feedback_text: "Incident confirmed by Auditor" })
    }).catch(err => console.error("Failed to submit feedback", err));

    setConfirmedIncidents((prev) => {
      if (prev.some((e) => e.emp_id === normalized)) return prev;
      return [{ emp_id: normalized, timestamp: new Date().toISOString() }, ...prev];
    });
    showToast("Action Logged: Feedback sent to AI Retraining Pipeline.");
  }, []);

  const handleFalseAlarm = useCallback((emp_id) => {
    const normalized = (emp_id || "").toUpperCase();
    if (!normalized) return;
    
    fetchWithAuth(`api/feedback/${normalized}`, {
      method: "POST",
      body: JSON.stringify({ action: "FALSE_ALARM", feedback_text: "Model retraining initiated by Auditor" })
    }).catch(err => console.error("Failed to submit feedback", err));

    setFalseAlarms((prev) => {
      if (prev.includes(normalized)) return prev;
      return [...prev, normalized];
    });
    showToast("Action Logged: Feedback sent to AI Retraining Pipeline.");
  }, []);

  useEffect(() => {
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
    const subscription = supabase
      .channel('evidence_logs_changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'evidence_logs' }, payload => {
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
        setNewEvidenceIds(prev => new Set([...prev, newEvd.id]));
        setTimeout(() => setNewEvidenceIds(prev => { const n = new Set(prev); n.delete(newEvd.id); return n; }), 3000);
        setVaultEvidence(prev => [newEvd, ...prev]);
        setEvidencePage(1);
      })
      .subscribe();
    return () => { supabase.removeChannel(subscription); };
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

  useEffect(() => {
    if (isAuthenticated) {
      setIsLoadingInitial(true);
      
      fetchWithAuth(`api/system/start-stream`, { method: "POST" }).catch(e => console.error("Auto stream start failed", e));

      fetchWithAuth(`api/roster/employees`)
        .then(r => r.json())
        .then((data) => {
          if (data.employees && Array.isArray(data.employees)) {
            const metadataMap = {};
            data.employees.forEach((emp) => {
              metadataMap[emp.emp_id] = { emp_class: emp.emp_class || "UNKNOWN", branch_id: emp.branch_id || "UNKNOWN" };
            });
            setEmployeeMetadata(metadataMap);
          }
        })
        .catch((err) => console.warn("Employee metadata fetch failed", err));

      fetchWithAuth(`api/dashboard-init`)
        .then(r => r.json())
        .then((payload) => {
          const rows = Array.isArray(payload) ? payload : Array.isArray(payload?.data) ? payload.data : [];
          const normalized = rows.map((tx) => ({
            ...tx,
            cbsi: tx.cbsi ?? tx.cbsi_score ?? tx.predicted_cbsi_score ?? 0,
            risk_tier: tx.risk_tier ?? riskTier(tx.cbsi ?? tx.cbsi_score ?? tx.predicted_cbsi_score ?? 0)
          }));
          setScoredTxns(normalized);
        })
        .catch((err) => console.error("Initial load failed", err))
        .finally(() => setIsLoadingInitial(false));
    }
  }, [isAuthenticated]);

  const normalizeTransaction = useCallback((newTxn) => {
    if (!newTxn || !newTxn.emp_id) return null;
    const normalized = {
      ...newTxn,
      cbsi: newTxn.cbsi ?? newTxn.cbsi_score ?? newTxn.predicted_cbsi_score ?? 0,
      risk_tier: newTxn.risk_tier ?? riskTier(newTxn.cbsi ?? newTxn.cbsi_score ?? newTxn.predicted_cbsi_score ?? 0)
    };
    if (newTxn.emp_class || newTxn.branch_id) {
      setEmployeeMetadata(prev => ({
        ...prev,
        [newTxn.emp_id]: {
          emp_class: newTxn.emp_class || prev[newTxn.emp_id]?.emp_class || "UNKNOWN",
          branch_id: newTxn.branch_id || prev[newTxn.emp_id]?.branch_id || "UNKNOWN"
        }
      }));
    }
    return normalized;
  }, []);

  const fetchNextTransaction = useCallback(() => {
    return fetchWithAuth("get-next-transaction")
      .then((res) => res.json())
      .then((newTxn) => {
        const normalized = normalizeTransaction(newTxn);
        if (normalized) {
          setScoredTxns((prev) => [...(Array.isArray(prev) ? prev : []), normalized].slice(-MAX_TRANSACTIONS));
        }
      })
      .catch((err) => console.error("Live update failed", err));
  }, [normalizeTransaction]);


  useEffect(() => {
    if (!autoRefresh || !isAuthenticated) return;
    let ws;
    let reconnectTimeout;
    let isMounted = true;

    const connect = () => {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      // If deployed, point directly to your Cloudflare domain
      const wsHost = isLocal ? 'localhost:8000' : (import.meta.env.VITE_API_DOMAIN || 'api.vaultmind.systems');
      const wsProto = isLocal ? 'ws:' : 'wss:';
      ws = new WebSocket(`${wsProto}//${wsHost}/ws/alerts`);
      ws.onopen = () => {
        if (!isMounted) { ws.close(); return; }
        console.log("🟢 Connected to WebSocket for live alerts");
      };
      ws.onmessage = (event) => {
        try {
          const newTxn = JSON.parse(event.data);
          const normalized = normalizeTransaction(newTxn);
          if (normalized) {
            setScoredTxns((prev) => [...(Array.isArray(prev) ? prev : []), normalized].slice(-MAX_TRANSACTIONS));
          }
        } catch (err) {
          console.error("Error processing WebSocket message", err);
        }
      };
      ws.onerror = (err) => console.error("WebSocket error:", err);
      ws.onclose = () => {
        console.log("🔴 WebSocket disconnected");
        if (isMounted && autoRefresh) {
          console.log("🔄 Reconnecting in 3s...");
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null; // Prevent reconnect on intentional unmount
        if (ws.readyState === 1) ws.close();
        else if (ws.readyState === 0) ws.onopen = () => ws.close();
        else ws.close();
      }
    };
  }, [autoRefresh, normalizeTransaction, isAuthenticated]);

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
    const employees = Array.from(
      new Set(scoredTxns.map(tx => tx.emp_id).filter(Boolean))
    ).map(emp_id => ({ emp_id }));

    return employees.map((e) => {
      const isFalseAlarm = falseAlarms.includes(e.emp_id);
      const s = map[e.emp_id] || { max: 0, sum: 0, count: 0 };
      const meta = employeeMetadata[e.emp_id] || { emp_class: "UNKNOWN", branch_id: "UNKNOWN" };
      const peakScore = isFalseAlarm ? 0 : s.max;
      return {
        ...e,
        emp_class: meta.emp_class,
        branch_id: meta.branch_id,
        peak: peakScore,
        avg: s.count ? Math.round((s.sum / s.count) * 10) / 10 : 0,
        txnCount: s.count,
        status: riskTier(peakScore),
      };
    }).sort((a, b) => b.peak - a.peak);
  }, [scoredTxns, employeeMetadata, falseAlarms]);

  const stats = useMemo(() => {
    const total = scoredTxns.length;
    const critical = scoredTxns.filter((x) => (x.cbsi || 0) >= 70).length;
    const high = scoredTxns.filter((x) => (x.cbsi || 0) >= 50 && (x.cbsi || 0) < 70).length;
    const fraud = confirmedIncidents.length;
    const avg = total ? Math.round((scoredTxns.reduce((s, x) => s + (x.cbsi || 0), 0) / total) * 10) / 10 : 0;
    return { total, critical, high, fraud, avg };
  }, [scoredTxns, confirmedIncidents]);

  const NAV = [
    { id: "command", label: "Command Centre", icon: Shield },
    { id: "roster", label: "Employee Roster", icon: Users },
    { id: "profile", label: "Employee Profile", icon: User },
    { id: "deception", label: "DeceptionGuard", icon: Radio },
    { id: "graph", label: "Fund Flow Graph", icon: GitBranch },
    { id: "evidence", label: "Evidence Vault", icon: FileText },
  ];

  const handleLogin = (token, user) => {
    authStore.setAuth(user);
    setIsAuthenticated(true);
    setUser(user);
  };

  const handleLogout = () => {
    authStore.clearAuth();
    setIsAuthenticated(false);
    setUser(null);
  };

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} t={t} />;
  }

  return (
    <div className="flex min-h-screen" style={{ background: t.bg, color: t.text }}>
      <aside
        className="w-60 h-screen fixed left-0 top-0 flex flex-col z-20 shadow-xl border-r"
        style={{ background: t.card, borderColor: t.border }}
      >
        <div className="flex items-center justify-between py-5 px-4 border-b" style={{ borderColor: t.border }}>
          <div>
            <div className="text-lg font-bold tracking-[2px]" style={{ color: t.text }}>VAULTMIND</div>
            <div className="text-[10px] tracking-[3px]" style={{ color: t.text2 }}>FRAUD INTELLIGENCE 2.0</div>
          </div>
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
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors cursor-pointer text-red-500 border-red-500/20 bg-red-500/5 hover:bg-red-500/10"
          >
            <LogOut size={14} />
            Logout
          </button>
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
            Transactions: {scoredTxns.length.toLocaleString()}
          </div>
        </div>
      </aside>

      <main
        className="flex-1 ml-60 p-6 space-y-6 overflow-y-auto min-h-screen"
        style={{ transition: "all 0.5s ease-in-out" }}
      >
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
                    const safeBuffer = Array.isArray(scoredTxns) ? scoredTxns : [];
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
                          <EnforcementMatrix emp_id={tx.emp_id} onConfirm={handleConfirmIncident} userRole={userRole} onToast={showToast} />
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
                    const safeBuffer = Array.isArray(scoredTxns) ? scoredTxns : [];
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
                      scoredTxns.slice(-500).forEach((tx) => { counts[riskTier(tx.cbsi || 0)]++; });
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
                if (eid === "EMP_1024") {
                  peak = 100;
                }
                const tier = riskTier(peak);
                const c = tc[tier];
                const isConfirmed = confirmedIncidents.some((inc) => inc.emp_id === eid);
                const displayRole = eid === "EMP_1024" ? "IT Admin" : (emp?.emp_class || "Unknown");
                const isDanger = peak >= 75;

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
                const isFalseAlarm = falseAlarms.includes(eid);

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
                      {userRole !== 'analyst' ? (
                        <div className="mt-4 flex items-center gap-3 flex-wrap">
                          <button
                            onClick={() => handleConfirmIncident(eid)}
                            disabled={isConfirmed || isFalseAlarm}
                            className="px-3 py-1.5 text-[10px] font-mono font-bold border border-[#E50914] text-[#E50914] hover:bg-[#E50914] hover:text-white transition-colors uppercase rounded-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            [ CONFIRM INCIDENT ]
                          </button>
                          <button
                            onClick={() => handleFalseAlarm(eid)}
                            disabled={isFalseAlarm || isConfirmed}
                            className="px-3 py-1.5 text-[10px] font-mono font-bold border border-[#FFB300] text-[#FFB300] hover:bg-[#FFB300] hover:text-black transition-colors uppercase rounded-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isFalseAlarm ? "[ RETRAINING AI... ]" : "[ FALSE ALARM / RETRAIN ]"}
                          </button>
                          <button
                            onClick={() => {
                              const pdfUrl = `api/evidence/download?emp_id=${eid}`;
                              forceDownloadPDF(pdfUrl, eid);
                            }}
                            className="px-3 py-1.5 text-[10px] font-mono font-bold border border-blue-500 text-blue-500 hover:bg-blue-900/40 transition-colors uppercase rounded-sm cursor-pointer"
                          >
                            [ 📥 DOWNLOAD DOSSIER ]
                          </button>
                          {isConfirmed && (
                            <span className="text-[10px] font-mono font-bold text-[#00E676] uppercase tracking-widest">
                              INCIDENT CONFIRMED
                            </span>
                          )}
                        </div>
                      ) : (
                        <div className="mt-4 flex items-center gap-3 flex-wrap">
                          <span className="text-[10px] font-mono font-bold text-gray-500 tracking-widest">[ ANALYST: VIEW-ONLY MODE ]</span>
                          <button
                            onClick={() => {
                              const pdfUrl = `api/evidence/download?emp_id=${eid}`;
                              forceDownloadPDF(pdfUrl, eid);
                            }}
                            className="px-3 py-1.5 text-[10px] font-mono font-bold border border-blue-500 text-blue-500 hover:bg-blue-900/40 transition-colors uppercase rounded-sm cursor-pointer"
                          >
                            [ 📥 DOWNLOAD DOSSIER ]
                          </button>
                        </div>
                      )}
                    </Card>

                    <GNNThreatNode isCritical={peak >= 85} />
                    <HistoricalContext emp_id={eid} />

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 my-4">
                      <ShapSimulator initialScore={peak} isCritical={peak > 75} />
                      <GlassBoxEngine score={peak} emp_id={eid} context={latestTxn} />
                    </div>

                    {(tier === "CRITICAL" || tier === "HIGH" || eid === "EMP_1024" || eid === "EMP_1024_HONEYPOT") && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 my-4">
                        <BlastRadius targetId={eid} />
                        <ForensicTimeline events={(() => {
                          // Use all flagged transactions first (sorted by time, most recent last)
                          const sorted = [...flaggedTxns].sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
                          // If fewer than 3 flagged, backfill with recent employee txns
                          let pool = sorted;
                          if (sorted.length < 3) {
                            const recentTxns = [...txns]
                              .sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''))
                              .filter(tx => !sorted.some(s => s.transaction_id === tx.transaction_id));
                            pool = [...recentTxns.slice(-10), ...sorted];
                          }
                          return pool.slice(-15).map(tx => ({
                            time: tx.timestamp ? tx.timestamp.slice(11, 19) : 'N/A',
                            text: `${tx.action_type} - Rs.${(tx.amount || 0).toLocaleString()}`,
                            tier: riskTier(tx.cbsi)
                          }));
                        })()} />
                      </div>
                    )}

                    <ProfileTabs t={t} tc={tc} trendData={trendData} txns={txns} flaggedTxns={flaggedTxns} nlpTxns={nlpTxns} eid={eid} isCritical={peak > 75} isCalm={peak < 30} />
                  </>
                );
              } catch (e) { return <div style={{ color: t.red }}>Profile error: {String(e)}</div>; }
            })()}
          </div>
        )}

        {page === "evidence" && (() => {
          const filteredEvidence = vaultEvidence.filter(evd => 
            (evd.emp_id || "").toLowerCase().includes(evidenceSearch.toLowerCase())
          );
          const totalPages = Math.max(1, Math.ceil(filteredEvidence.length / EVIDENCE_PER_PAGE));
          const evPage = Math.min(evidencePage, totalPages);
          const evSlice = filteredEvidence.slice((evPage - 1) * EVIDENCE_PER_PAGE, evPage * EVIDENCE_PER_PAGE);
          return (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold">Evidence Vault</h1>

              <div className="relative">
                <Search size={14} className="absolute left-3 top-3" style={{ color: t.text2 }} />
                <input 
                  value={evidenceSearch} 
                  onChange={(e) => { setEvidenceSearch(e.target.value); setEvidencePage(1); }}
                  placeholder="🔍 Search by EMP_ID..." 
                  className="w-full rounded-lg border pl-9 pr-3 py-2 text-sm"
                  style={{ background: t.card, borderColor: t.border, color: t.text }} 
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <KpiCard title="PDF Evidence Packages" value={String(filteredEvidence.length)} color={t.teal} t={t} />
                <KpiCard title="STR JSON Filings" value={String(filteredEvidence.length)} color={t.cyan} t={t} />
              </div>

              <Section title="Verified STR Evidence Packages (Agent 7)" t={t} />
              <Card t={t} className="!p-0 overflow-hidden mb-2">
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
                    {evSlice.map((evd) => (
                      <tr
                        key={evd.id}
                        className="hover:bg-[#1a1a1a] transition-colors"
                        style={newEvidenceIds.has(evd.id) ? { background: "rgba(0,230,118,0.08)" } : {}}
                      >
                        <td className="p-4 text-[#00D4AA] font-bold">
                          <div className="flex items-center gap-2">
                            {evd.status === "Generated" && <FileText size={14} className="text-[#00D4AA]" />}
                            {newEvidenceIds.has(evd.id) && <span className="text-[9px] font-mono text-green-400 animate-pulse">NEW</span>}
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
                              onClick={(e) => {
                                e.stopPropagation();
                                const cleanFilename = evd.filename.split('\\').pop().split('/').pop();
                                const pdfUrl = `api/evidence/download?filename=${encodeURIComponent(cleanFilename)}`;
                                forceDownloadPDF(pdfUrl, evd.emp_id);
                              }}
                              className="px-3 py-1.5 text-[10px] font-mono font-bold border border-blue-500 text-blue-500 hover:bg-blue-900/40 transition-colors uppercase rounded-sm cursor-pointer"
                            >
                              [ 📥 DOWNLOAD EVIDENCE ]
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <div className="flex justify-between items-center text-xs" style={{ color: t.text2 }}>
                <span>Showing {(evPage - 1) * EVIDENCE_PER_PAGE + 1}–{Math.min(evPage * EVIDENCE_PER_PAGE, filteredEvidence.length)} of {filteredEvidence.length}</span>
                <div className="flex items-center gap-3">
                  <button onClick={() => setEvidencePage(Math.max(1, evPage - 1))} disabled={evPage <= 1}
                    className="p-1.5 rounded border cursor-pointer disabled:opacity-30" style={{ borderColor: t.border, color: t.text2 }}>
                    <ChevronLeft size={14} />
                  </button>
                  <span className="font-mono">Page {evPage} / {totalPages}</span>
                  <button onClick={() => setEvidencePage(Math.min(totalPages, evPage + 1))} disabled={evPage >= totalPages}
                    className="p-1.5 rounded border cursor-pointer disabled:opacity-30" style={{ borderColor: t.border, color: t.text2 }}>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>

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
          );
        })()}

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

        {/* ── DECEPTIONGUARD ─────────────────────────────────── */}
        {page === "deception" && (() => {
          // ERR5: Data-driven from live scoredTxns
          const honeypotBreaches = scoredTxns.filter(tx =>
            tx.account_touched && (tx.account_touched.includes("MIRAGE") || tx.account_touched.includes("GHOST")) ||
            (tx.decision === "ISOLATE" && tx.dominant_agent === "DeceptionGuard")
          );
          const liveBreachTx = honeypotBreaches[honeypotBreaches.length - 1];
          const staticHoneypotBreach = {
            accountId: liveBreachTx?.account_touched || "ACC_GHOST_07",
            attackerId: liveBreachTx?.emp_id || "EMP_1024",
            attackerRole: liveBreachTx?.emp_class || "IT Admin",
            threatOrigin: liveBreachTx ? `${liveBreachTx.emp_id} (${liveBreachTx.emp_class || 'Unknown'}) | Branch: ${liveBreachTx.branch_id || 'Unknown'}` : "EMP_1024 (IT Admin) | IP: 192.168.1.45 (Mumbai_BR_05)"
          };
          return (
            <div className="space-y-6 pb-12">
              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-bold font-mono tracking-[4px] uppercase" style={{ color: t.accent }}>DeceptionGuard</h1>
                {honeypotBreaches.length > 0 && (
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-red-500/20 text-red-400 animate-pulse">
                    {honeypotBreaches.length} LIVE BREACH{honeypotBreaches.length > 1 ? 'ES' : ''} DETECTED
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Section title="Honeypot Node Radar" t={t} />
                  <Card t={t} className="flex flex-col items-center justify-center !py-12 relative overflow-hidden h-[400px]">
                    <div className="absolute inset-0 opacity-10 pointer-events-none"
                      style={{ background: 'linear-gradient(rgba(0, 255, 0, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 0, 0.1) 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
                    <div className="relative flex items-center justify-center w-64 h-64 border border-[#333] rounded-full">
                      <div className="absolute w-48 h-48 border border-[#333] rounded-full"></div>
                      <div className="absolute w-32 h-32 border border-[#333] rounded-full"></div>
                      <div className="absolute w-16 h-16 border border-[#333] rounded-full text-center flex items-center justify-center font-mono text-[8px] text-[#333]">CORE</div>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                        className="absolute w-full h-full rounded-full"
                        style={{
                          background: "conic-gradient(from 0deg, rgba(0, 230, 118, 0.05) 0deg, transparent 60deg, transparent 360deg)",
                          borderRight: "1px solid rgba(0, 230, 118, 0.4)"
                        }}
                      />
                      <motion.div animate={{ opacity: [0.1, 1, 0.1] }} transition={{ duration: 2, repeat: Infinity, delay: 0.2 }}
                        className="absolute w-1.5 h-1.5 bg-[#00E676] rounded-full top-10 left-20 shadow-[0_0_8px_#00E676]" />
                      <motion.div animate={{ opacity: [0.1, 1, 0.1] }} transition={{ duration: 2.5, repeat: Infinity, delay: 1 }}
                        className="absolute w-2 h-2 bg-[#FFB300] rounded-full top-12 right-16 shadow-[0_0_10px_#FFB300]" />
                      {honeypotBreaches.length > 0 ? (
                        <motion.div animate={{ opacity: [0.1, 1, 0.1] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}
                          className="absolute bottom-12 left-12 flex items-center gap-1.5">
                          <div className="w-2.5 h-2.5 bg-[#E50914] rounded-full shadow-[0_0_12px_#E50914]" />
                          <span className="text-[8px] font-mono font-bold text-[#E50914] tracking-widest whitespace-nowrap opacity-90 mix-blend-screen">[BREACH: {staticHoneypotBreach.accountId}]</span>
                        </motion.div>
                      ) : (
                        <motion.div animate={{ opacity: [0.1, 1, 0.1] }} transition={{ duration: 3, repeat: Infinity, delay: 0.5 }}
                          className="absolute bottom-12 left-12 flex items-center gap-1.5">
                          <div className="w-2 h-2 bg-[#E50914] rounded-full shadow-[0_0_10px_#E50914]" />
                          <span className="text-[8px] font-mono font-bold text-[#E50914] tracking-widest whitespace-nowrap opacity-80 mix-blend-screen">[TARGET PING: MUMBAI]</span>
                        </motion.div>
                      )}
                      <motion.div animate={{ opacity: [0.1, 1, 0.1] }} transition={{ duration: 1.5, repeat: Infinity, delay: 2 }}
                        className="absolute w-1.5 h-1.5 bg-[#00E676] rounded-full bottom-20 right-12 shadow-[0_0_8px_#00E676]" />
                    </div>
                    <div className="mt-8 text-xs font-mono text-[#00E676] animate-pulse uppercase tracking-widest flex items-center gap-2">
                      <span className="w-2 h-2 bg-[#00E676] rounded-sm"></span>
                      {honeypotBreaches.length > 0 ? `${honeypotBreaches.length} Breach(es) Detected` : "Scanning Subnets..."}
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
                            {/* Live breach rows from real data */}
                            {honeypotBreaches.slice(-5).reverse().map((tx, i) => (
                              <tr key={`${tx.transaction_id || i}-${i}`} className="hover:bg-[#1a1a1a] transition-colors bg-[#2a1313]">
                                <td className="p-4 text-[#E50914] font-bold">{tx.account_touched}</td>
                                <td className="p-4">Rs.{(tx.amount || 0).toLocaleString()}</td>
                                <td className="p-4 text-xs text-[#E50914] font-bold animate-pulse">
                                  BREACH DETECTED
                                  <button
                                    onClick={() => { setProfileSearch(tx.emp_id); setPage("profile"); }}
                                    className="ml-3 px-2 py-0.5 bg-[#E50914] text-white text-[9px] uppercase tracking-wider rounded font-bold hover:bg-red-700 transition cursor-pointer"
                                  >[ Investigate ]</button>
                                </td>
                                <td className="p-4 text-[11px] text-[#FFB300] font-bold">{tx.emp_id} | {tx.branch_id || "Unknown Branch"}</td>
                              </tr>
                            ))}
                            {/* Static monitored accounts */}
                            <tr className="hover:bg-[#1a1a1a] transition-colors">
                              <td className="p-4 text-[#00B4D8] font-bold">ACC-MIRAGE-001</td>
                              <td className="p-4">Rs.50,00,000</td>
                              <td className="p-4 text-xs text-gray-400">Monitoring for lookup</td>
                              <td className="p-4 text-[10px] text-gray-600">-</td>
                            </tr>
                            <tr className="hover:bg-[#1a1a1a] transition-colors">
                              <td className="p-4 text-[#00B4D8] font-bold">ACC-MIRAGE-002</td>
                              <td className="p-4">Rs.1,20,00,000</td>
                              <td className="p-4 text-xs text-gray-400">Decoy credential deployed</td>
                              <td className="p-4 text-[10px] text-gray-600">Awaiting trace...</td>
                            </tr>
                            <tr className="hover:bg-[#1a1a1a] transition-colors">
                              <td className="p-4 text-[#00B4D8] font-bold">ACC-MIRAGE-005</td>
                              <td className="p-4">Rs.25,00,000</td>
                              <td className="p-4 text-xs text-gray-400">Await access trigger</td>
                              <td className="p-4 text-[10px] text-gray-600">Dormant</td>
                            </tr>
                            <tr className="hover:bg-[#1a1a1a] transition-colors">
                              <td className="p-4 text-[#00B4D8] font-bold">ACC-MIRAGE-007</td>
                              <td className="p-4">Rs.75,00,000</td>
                              <td className="p-4 text-xs text-gray-400">Credential logged</td>
                              <td className="p-4 text-[10px] text-gray-600">Monitoring</td>
                            </tr>
                            <tr className="hover:bg-[#1a1a1a] transition-colors">
                              <td className="p-4 text-[#00B4D8] font-bold">ACC-MIRAGE-010</td>
                              <td className="p-4">Rs.3,50,00,000</td>
                              <td className="p-4 text-xs text-gray-400">Premium decoy deployed</td>
                              <td className="p-4 text-[10px] text-gray-600">Armed</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            </div>
          );
        })()}

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
        <Toast message={toastMessage} visible={toastVisible} onClose={() => setToastVisible(false)} />
      </main>
    </div>
  );
}

