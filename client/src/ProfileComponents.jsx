import React, { useState, useEffect } from "react";
import { Play, BrainCircuit, ShieldAlert, GitMerge } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// --- 1. Forensic Timeline ("CCTV Playback") ---
export function ForensicTimeline({ events = [] }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [visibleCount, setVisibleCount] = useState(0);

  const mockEvents = events.length ? events : [
    { time: "02:14 AM", text: "Off-hours system login detected", tier: "WATCH" },
    { time: "02:17 AM", text: "Escalated DB_GRANT_ACCESS privileges", tier: "HIGH" },
    { time: "02:22 AM", text: "Initiated SYSTEM_BULK_EXPORT", tier: "CRITICAL" },
    { time: "02:24 AM", text: "Transfer of Rs.8.5M via RTGS", tier: "CRITICAL" }
  ];

  useEffect(() => {
    if (isPlaying && visibleCount < mockEvents.length) {
      const timer = setTimeout(() => setVisibleCount((v) => v + 1), 600);
      return () => clearTimeout(timer);
    } else if (visibleCount === mockEvents.length) {
      setTimeout(() => setIsPlaying(false), 1000);
    }
  }, [isPlaying, visibleCount, mockEvents.length]);

  const handlePlay = () => {
    setVisibleCount(0);
    setIsPlaying(true);
  };

  return (
    <div className="p-5 rounded-xl border border-[#333333] bg-[#232323] shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[13px] font-bold uppercase tracking-[2px] text-gray-400">Forensic Timeline</h3>
        <button 
          onClick={handlePlay}
          disabled={isPlaying}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#E50914] text-white text-xs font-semibold hover:bg-red-700 transition disabled:opacity-50 cursor-pointer"
        >
          <Play size={12} fill="currentColor" /> {isPlaying ? "Simulating..." : "Play CCTV"}
        </button>
      </div>

      <div className="pl-4 border-l-2 border-[#333333] space-y-4 py-2 relative">
        <AnimatePresence>
          {mockEvents.slice(0, visibleCount === 0 && !isPlaying ? mockEvents.length : visibleCount).map((ev, i) => (
            <motion.div 
              key={i} 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="relative"
            >
              <div 
                className={`absolute -left-[23px] w-3 h-3 rounded-full border-[3px] border-[#232323] ${
                  ev.tier === 'CRITICAL' ? 'bg-[#E50914]' : ev.tier === 'HIGH' ? 'bg-[#FFB300]' : 'bg-[#00B4D8]'
                }`} 
              />
              <div className="text-xs text-gray-500 font-mono mb-0.5">{ev.time}</div>
              <div className="text-sm text-white">{ev.text}</div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

// --- 2. Glass-Box Explainability Engine ---
export function GlassBoxEngine({ score = 100, emp_id = "EMP_1024", context = null }) {
  const isCritical = score > 75;
  const [explanation, setExplanation] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;
    setLoading(true);
    setError("");
    setExplanation("");

    const payload = {
      emp_id,
      cbsi: score,
      action_type: context?.action_type,
      amount: context?.amount,
      transfer_channel: context?.transfer_channel,
      timestamp: context?.timestamp,
      remarks: context?.raw_complaint_text || context?.hr_remark_text || "",
      transaction_id: context?.transaction_id
    };

    fetch(`http://localhost:8000/api/explain/${emp_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then((res) => res.json())
      .then((data) => {
        if (!isActive) return;
        setExplanation(data?.explanation || "No explanation available.");
      })
      .catch((err) => {
        if (!isActive) return;
        setError("Failed to load AI explanation.");
        console.error("Explain API error:", err);
      })
      .finally(() => {
        if (!isActive) return;
        setLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [emp_id, score, context?.transaction_id, context?.timestamp]);

  return (
    <div className={`p-5 rounded-xl border shadow-[0_0_15px_rgba(0,0,0,0.5)] ${isCritical ? 'border-[#E50914] bg-[#231010]' : 'border-[#00D4AA] bg-[#102320]'}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-[13px] font-bold uppercase tracking-[2px] flex items-center gap-2 ${isCritical ? 'text-[#E50914]' : 'text-[#00D4AA]'}`}>
          <BrainCircuit size={16} /> AI Decision Logic
        </h3>
      </div>
      <div className={`min-h-[80px] p-4 rounded-md border relative overflow-hidden ${isCritical ? 'bg-[#140505] border-[#E50914]/50' : 'bg-[#051410] border-[#00D4AA]/50'}`}>
        {loading ? (
          <p className={`text-sm font-mono leading-relaxed ${isCritical ? 'text-red-200' : 'text-teal-200'}`}>
            Loading AI explanation...
          </p>
        ) : error ? (
          <p className="text-sm font-mono leading-relaxed text-red-300">{error}</p>
        ) : (
          <p className={`text-sm font-mono leading-relaxed ${isCritical ? 'text-red-200' : 'text-teal-200'}`}>
            {explanation}
          </p>
        )}
      </div>
    </div>
  );
}

// --- 3. Blast Radius (Contagion Risk) ---
export function BlastRadius({ targetId = "EMP_1099" }) {
  return (
    <div className="p-5 rounded-xl border border-[#E50914] bg-[#232323] shadow-[0_0_15px_rgba(229,9,20,0.1)]">
      <div className="flex items-center gap-2 mb-4 text-[#E50914]">
        <ShieldAlert size={18} />
        <h3 className="text-[13px] font-bold uppercase tracking-[2px]">Peer Risk Assessment</h3>
      </div>

      <div className="space-y-3">
        <div className="p-3 rounded-lg bg-[#141414] border border-[#333333] flex items-start gap-3">
          <GitMerge size={16} className="text-[#FFB300] mt-0.5 shrink-0" />
          <div>
            <div className="text-sm font-semibold text-white mb-1">Warning: Lateral Movement Risk</div>
            <div className="text-xs text-gray-400 leading-tight">
              <span className="text-white font-mono">{targetId}</span> shares the same VPN terminal IP and branch with <span className="text-white font-mono">EMP_{Math.floor(Math.random() * 8000 + 1000)}</span>. Elevating peer risk by <span className="text-[#FFB300] font-bold">+20 CBSI</span>.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- 4. ShapSimulator (CBSI WhyScore) ---
export function ShapSimulator({ initialScore = 50, isCritical = false }) {
  const [vol, setVol] = useState(isCritical ? 85 : 20);
  const [time, setTime] = useState(isCritical ? 70 : 10);
  const [nlp, setNlp] = useState(isCritical ? 90 : 0);
  const [hops, setHops] = useState(isCritical ? 12 : 2);

  const simScore = Math.min(100, Math.max(0, Math.round((vol * 0.35) + (time * 0.2) + (nlp * 0.3) + (hops * 2.5))));

  return (
    <div className={`p-5 rounded-xl border shadow-[0_0_15px_rgba(0,0,0,0.5)] ${isCritical ? 'border-[#E50914] bg-[#231010]' : 'border-[#00D4AA] bg-[#102320]'}`}>
      <div className="flex justify-between items-center mb-6">
        <h3 className={`text-[13px] font-bold uppercase tracking-[2px] ${isCritical ? 'text-[#E50914]' : 'text-[#00D4AA]'}`}>
          CBSI 'WhyScore' Simulator
        </h3>
      </div>
      
      <div className="flex items-center justify-between gap-8">
        <div className="flex-1 space-y-5">
          <div>
            <div className="flex justify-between text-[11px] uppercase tracking-wider text-gray-400 mb-2"><span>Transaction Volume</span><span className="font-mono text-white">{vol}%</span></div>
            <input type="range" min="0" max="100" value={vol} onChange={e=>setVol(Number(e.target.value))} className={`w-full h-1 rounded-lg appearance-none cursor-pointer ${isCritical ? 'accent-[#E50914] bg-[#E50914]/20' : 'accent-[#00D4AA] bg-[#00D4AA]/20'}`} />
          </div>
          <div>
            <div className="flex justify-between text-[11px] uppercase tracking-wider text-gray-400 mb-2"><span>Time of Day Anomaly</span><span className="font-mono text-white">{time}%</span></div>
            <input type="range" min="0" max="100" value={time} onChange={e=>setTime(Number(e.target.value))} className={`w-full h-1 rounded-lg appearance-none cursor-pointer ${isCritical ? 'accent-[#E50914] bg-[#E50914]/20' : 'accent-[#00D4AA] bg-[#00D4AA]/20'}`} />
          </div>
          <div>
            <div className="flex justify-between text-[11px] uppercase tracking-wider text-gray-400 mb-2"><span>NLP Risk (Agent 4)</span><span className="font-mono text-white">{nlp}%</span></div>
            <input type="range" min="0" max="100" value={nlp} onChange={e=>setNlp(Number(e.target.value))} className={`w-full h-1 rounded-lg appearance-none cursor-pointer ${isCritical ? 'accent-[#E50914] bg-[#E50914]/20' : 'accent-[#00D4AA] bg-[#00D4AA]/20'}`} />
          </div>
          <div>
            <div className="flex justify-between text-[11px] uppercase tracking-wider text-gray-400 mb-2"><span>Network Hops (Agent 2)</span><span className="font-mono text-white">{hops}</span></div>
            <input type="range" min="0" max="20" value={hops} onChange={e=>setHops(Number(e.target.value))} className={`w-full h-1 rounded-lg appearance-none cursor-pointer ${isCritical ? 'accent-[#E50914] bg-[#E50914]/20' : 'accent-[#00D4AA] bg-[#00D4AA]/20'}`} />
          </div>
        </div>
        
        <div className="text-center shrink-0 w-32 border-l border-[#333] pl-6 py-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">Simulated CBSI</div>
          <div className={`text-6xl font-bold font-mono ${simScore > 75 ? 'text-[#E50914]' : simScore > 40 ? 'text-[#FFB300]' : 'text-[#00E676]'}`}>
            {simScore}
          </div>
        </div>
      </div>
    </div>
  );
}
