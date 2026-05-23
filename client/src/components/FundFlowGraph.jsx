import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { X, AlertTriangle, Clock, Shield, Zap, Radio, Search } from "lucide-react";

// ── Dynamic Graph Data Generator (From Real Stream) ──────────────
const processGraphData = (liveTxns, targetEmp) => {
  const nodesMap = new Map();
  const links = [];

  // Limit to last 200 transactions to keep graph fast and clean
  const recentTxns = Array.isArray(liveTxns) ? liveTxns.slice(-200) : [];

  recentTxns.forEach((tx) => {
    if (!tx.emp_id || !tx.account_touched) return;

    const isAttacker = tx.emp_id === targetEmp;
    const isHoneypot = tx.account_touched.includes("GHOST");
    const isFraud = tx.is_fraud_flag === 1 || tx.cbsi >= 80;

    // 1. Add Employee Node
    if (!nodesMap.has(tx.emp_id)) {
      nodesMap.set(tx.emp_id, {
        id: tx.emp_id,
        type: isAttacker ? "attacker" : "employee",
        val: isAttacker ? 8 : (isFraud ? 5 : 3),
      });
    } else if (isAttacker) {
      nodesMap.get(tx.emp_id).type = "attacker";
      nodesMap.get(tx.emp_id).val = 8;
    }

    // 2. Add Account Node
    if (!nodesMap.has(tx.account_touched)) {
      nodesMap.set(tx.account_touched, {
        id: tx.account_touched,
        type: isHoneypot ? "honeypot" : "account",
        val: isHoneypot ? 6 : 2,
      });
    }

    // 3. Add Edge (Transaction)
    links.push({
      id: tx.transaction_id || `link_${tx.emp_id}_${tx.account_touched}_${Math.random()}`,
      source: tx.emp_id,
      target: tx.account_touched,
      type: isFraud ? "breach" : (isAttacker ? "attacker_std" : "standard"),
      amount: tx.amount,
      cbsi: tx.cbsi
    });
  });

  return { 
    nodes: Array.from(nodesMap.values()), 
    links: links 
  };
};

// ── Timeline & Styles (Kept as is) ───────────────────────────────
const TIMELINE = [
  { time: "LIVE", title: "Anomaly Detected", detail: "High risk pattern triggered agent correlation.", icon: "alert", severity: "warn" },
  { time: "LIVE", title: "Target Isolation Active", detail: "Account suspended. Evidence being compiled for STR.", icon: "shield", severity: "terminal" },
];

const SEVERITY_STYLES = {
  warn:     { dot: "bg-amber-400",  text: "text-amber-400",  border: "border-amber-400/30" },
  terminal: { dot: "bg-red-600 animate-pulse", text: "text-red-300", border: "border-red-600/60" },
};
const IconMap = { radio: Radio, clock: Clock, zap: Zap, shield: Shield, alert: AlertTriangle };

// ── Incident Panel ───────────────────────────────────────────────
function IncidentPanel({ target, targetEmp, onClose, onGenerateEvidence }) {
  const [pdfState, setPdfState] = useState("idle");
  const [strState, setStrState] = useState("idle");

  const title = target?.type === "breach"
    ? `BREACH EDGE DETECTED`
    : target?.type === "honeypot"
    ? `HONEYPOT TRIGGERED — ${target.id}`
    : `PROFILE — ${target?.id || targetEmp}`;

  return (
    <div
      className="fixed top-0 right-0 h-full w-[420px] z-50 flex flex-col"
      style={{
        background: "#0e0e0e", borderLeft: "1px solid rgba(239,68,68,0.25)",
        boxShadow: "-8px 0 40px rgba(239,68,68,0.08)", animation: "slideIn 0.28s cubic-bezier(0.16,1,0.3,1)",
      }}
    >
      <div className="flex items-start justify-between p-5 border-b border-red-500/20">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[10px] font-mono tracking-widest text-red-400 uppercase">Live Intel Report</span>
          </div>
          <h2 className="text-sm font-mono text-white leading-snug">{title}</h2>
        </div>
        <button onClick={onClose} className="mt-0.5 p-1.5 rounded text-slate-500 hover:text-white hover:bg-white/10 transition-colors">
          <X size={15} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-px border-b border-white/5">
        {[["RISK", "Critical"], ["ACTION", "Isolate"], ["TRACE", "Active"]].map(([k, v]) => (
          <div key={k} className="p-3 bg-[#111]">
            <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-0.5">{k}</p>
            <p className="text-xs font-mono text-red-400 font-medium">{v}</p>
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-0">
        <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-4">Live Incident Log</p>
        {TIMELINE.map((evt, idx) => {
          const s   = SEVERITY_STYLES[evt.severity] || SEVERITY_STYLES.warn;
          const Icon = IconMap[evt.icon] || AlertTriangle;
          const isLast = idx === TIMELINE.length - 1;
          return (
            <div key={idx} className="relative flex gap-4">
              {!isLast && <div className="absolute left-[18px] top-8 bottom-0 w-px" style={{ background: "rgba(255,255,255,0.06)" }} />}
              <div className={`relative z-10 w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 border ${s.border}`} style={{ background: "rgba(0,0,0,0.6)" }}>
                <Icon size={14} className={s.text} />
              </div>
              <div className={`pb-5 flex-1`}>
                <span className={`text-[10px] font-mono ${s.text} mb-1 block`}>{evt.time}</span>
                <p className="text-xs text-white font-medium mb-1">{evt.title}</p>
                <p className="text-[11px] text-slate-400 leading-relaxed">{evt.detail}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 pb-12 border-t border-white/5 flex gap-2">
        <button
          onClick={() => {
            if (pdfState !== "idle") return;
            setPdfState("loading");
            if (onGenerateEvidence) onGenerateEvidence(target?.id || targetEmp);
            setTimeout(() => setPdfState("done"), 1500);
          }}
          className={`flex-1 py-2 text-xs font-mono border rounded transition-colors ${pdfState === "done" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : "bg-red-500/10 hover:bg-red-500/20 text-red-400 border-red-500/25"}`}
        >
          {pdfState === "idle" && "Generate Evidence PDF"}
          {pdfState === "loading" && "Generating..."}
          {pdfState === "done" && "[ PDF GENERATED ]"}
        </button>
      </div>
      <style>{`@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
    </div>
  );
}

// ── Canvas Renderers ─────────────────────────────────────────────
function drawNode(node, ctx, globalScale, hoveredId, targetEmp) {
  if (typeof node.x !== 'number' || typeof node.y !== 'number') return;

  const isAttacker  = node.type === "attacker";
  const isHoneypot  = node.type === "honeypot";
  const isEmployee  = node.type === "employee";
  const isHovered   = node.id === hoveredId;
  const r           = node.val * 2;

  ctx.save();

  if (isAttacker) {
    const grd = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 3.5);
    grd.addColorStop(0, "rgba(220,38,38,0.35)"); grd.addColorStop(1, "rgba(220,38,38,0)");
    ctx.beginPath(); ctx.arc(node.x, node.y, r * 3.5, 0, 2 * Math.PI); ctx.fillStyle = grd; ctx.fill();
    
    ctx.beginPath(); ctx.arc(node.x, node.y, r, 0, 2 * Math.PI); ctx.fillStyle = isHovered ? "#ff4444" : "#dc2626"; ctx.fill();
    ctx.beginPath(); ctx.arc(node.x, node.y, r + 2.5, 0, 2 * Math.PI); ctx.strokeStyle = "rgba(220,38,38,0.6)"; ctx.stroke();
    
    ctx.font = `bold ${Math.max(4, 8 / globalScale)}px monospace`; ctx.fillStyle = "#fff"; ctx.textAlign = "center";
    ctx.fillText(node.id, node.x, node.y + r + 8 / globalScale);
  } else if (isHoneypot) {
    ctx.beginPath(); ctx.save(); ctx.translate(node.x, node.y); ctx.rotate(Math.PI / 4);
    ctx.fillStyle = isHovered ? "#fde047" : "#eab308"; const s = r * 0.85; ctx.fillRect(-s, -s, s * 2, s * 2); ctx.restore();
    ctx.beginPath(); ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI); ctx.strokeStyle = "rgba(234,179,8,0.55)"; ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = isEmployee ? (isHovered ? "rgba(0,212,170,0.9)" : "rgba(0,212,170,0.6)") : (isHovered ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.4)");
    ctx.fill();
  }

  ctx.restore();
}

function drawLink(link, ctx, hoveredLinkId) {
  const isBreach  = link.type === "breach";
  const isAtkStd  = link.type === "attacker_std";
  const isHovered = link.id === hoveredLinkId;

  ctx.save(); ctx.beginPath();
  ctx.moveTo(link.source.x || 0, link.source.y || 0); ctx.lineTo(link.target.x || 0, link.target.y || 0);

  if (isBreach) {
    ctx.strokeStyle = isHovered ? "#ff2222" : "#dc2626"; ctx.lineWidth = isHovered ? 3 : 2; ctx.setLineDash([]);
  } else if (isAtkStd) {
    ctx.strokeStyle = "rgba(220,38,38,0.28)"; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4]);
  } else {
    ctx.strokeStyle = isHovered ? "rgba(0,212,170,0.4)" : "rgba(255,255,255,0.1)"; ctx.lineWidth = 0.5; ctx.setLineDash([]);
  }
  ctx.stroke(); ctx.restore();
}

// ── MAIN COMPONENT ───────────────────────────────────────────────
export default function FundFlowGraph({ liveTxns, onGenerateEvidence }) {
  const graphRef        = useRef(null);
  const [panel, setPanel]         = useState(null);
  const [hoveredNode, setHovered] = useState(null);
  const [hoveredLink, setHovLink] = useState(null);
  const [dims, setDims]           = useState({ w: window.innerWidth, h: window.innerHeight });
  const [targetEmp, setTargetEmp] = useState("EMP_1024");
  const [searchVal, setSearchVal] = useState("");

  // MAGIC HAPPENS HERE: Graph data updates automatically when liveTxns changes
  const graphData = useMemo(() => processGraphData(liveTxns, targetEmp), [liveTxns, targetEmp]);

  useEffect(() => {
    const handle = () => setDims({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener("resize", handle);
    return () => window.removeEventListener("resize", handle);
  }, []);

  useEffect(() => {
    if (!graphRef.current) return;
    graphRef.current.d3Force("link").distance(() => 60);
    graphRef.current.d3Force("charge").strength(-120);
  }, []);

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#0a0a0a" }}>
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={dims.w} height={dims.h} backgroundColor="#0a0a0a"
        nodeCanvasObject={(node, ctx, scale) => drawNode(node, ctx, scale, hoveredNode, targetEmp)}
        nodeCanvasObjectMode={() => "replace"}
        linkCanvasObject={(link, ctx) => drawLink(link, ctx, hoveredLink)}
        linkCanvasObjectMode={() => "replace"}
        onNodeClick={(n) => { if (n.type === "attacker" || n.type === "honeypot" || n.type === "employee") setPanel(n); }}
        onLinkClick={(l) => { if (l.type === "breach") setPanel(l); }}
        onNodeHover={(n) => setHovered(n?.id ?? null)}
        onLinkHover={(l) => setHovLink(l?.id ?? null)}
        enableNodeDrag enableZoomInteraction cooldownTicks={120}
      />

      {/* HUD — Top Left */}
      <div className="absolute top-5 left-5 pointer-events-none select-none z-10">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-mono text-emerald-400 tracking-widest uppercase">Live Network Intel</span>
        </div>
        <p className="text-[10px] font-mono text-slate-600 mb-4">
          {graphData.nodes.length} nodes · {graphData.links.length} edges · Auto-sync active
        </p>
        
        {/* Search Bar */}
        <div className="pointer-events-auto flex gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-500" />
            <input type="text" placeholder="Search Employee..." value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && searchVal.trim()) setTargetEmp(searchVal.trim().toUpperCase()); }}
              className="pl-8 pr-3 py-2 text-xs font-mono bg-black/40 border border-white/10 rounded text-white focus:outline-none focus:border-red-500/50 w-48"
            />
          </div>
          <button onClick={() => { if (searchVal.trim()) setTargetEmp(searchVal.trim().toUpperCase()); }} className="px-3 py-2 text-xs font-mono bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/25 rounded transition-colors cursor-pointer">
            Trace
          </button>
        </div>
      </div>

      {/* Incident Panel */}
      {panel && <IncidentPanel target={panel} targetEmp={targetEmp} onClose={() => setPanel(null)} onGenerateEvidence={onGenerateEvidence} />}
    </div>
  );
}