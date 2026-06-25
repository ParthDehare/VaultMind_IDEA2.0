import { useState } from "react";
import { Loader2 } from "lucide-react";
import { forceDownloadPDF } from '../utils.js';
import { fetchWithAuth } from '../apiService';

export function EnforcementMatrix({ emp_id, onConfirm, userRole, onToast }) {
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
      await fetchWithAuth(`api/feedback/${emp_id}`, {
        method: "POST",
        body: JSON.stringify({ action: actionType, feedback_text: `Marked as ${actionType} by user` })
      });
      if (onToast) onToast("Action Logged: Feedback sent to AI Retraining Pipeline.");
    } catch (e) { console.error("Feedback error", e); }
    
    if (actionType === "CONFIRM") {
      setStatus("done");
      if (onConfirm) onConfirm(emp_id);
    } else {
      setTimeout(() => setStatus("done"), 2000);
    }
  };

  const handleDownload = (e) => {
    e.stopPropagation();
    const targetUrl = `api/evidence/download?emp_id=${emp_id}`;
    forceDownloadPDF(targetUrl, emp_id);
  };

  const downloadBtn = (
    <button 
      onClick={handleDownload}
      className="px-2 py-1 text-[9px] font-mono font-bold border border-blue-500 text-blue-500 hover:bg-blue-900/40 transition-colors uppercase rounded-sm cursor-pointer"
    >
      [ 📥 DOWNLOAD EVIDENCE ]
    </button>
  );

  if (userRole === "analyst") {
    return (
      <div className="mt-3 flex items-center gap-2 pt-2 border-t border-[#222]">
        {downloadBtn}
        <span className="text-[9px] font-mono font-bold text-gray-500 tracking-widest">[ ANALYST: VIEW-ONLY MODE ]</span>
      </div>
    );
  }

  return (
    <div className="mt-3 flex items-center gap-2 pt-2 border-t border-[#222]">
      {downloadBtn}
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
