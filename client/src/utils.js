export const DARK = {
  bg: "#0a0a0a", card: "#121212", cardAlt: "#0f0f0f", border: "#222222",
  text: "#FFFFFF", text2: "#A0A0A0", accent: "#E50914",
  teal: "#00D4AA", cyan: "#00B4D8", red: "#E50914",
  amber: "#FFB300", green: "#00E676",
};

export const LIGHT = {
  bg: "#F5F5F5", card: "#FFFFFF", cardAlt: "#F8F9FA", border: "#E0E0E0",
  text: "#1A1A1A", text2: "#666", accent: "#D32F2F",
  teal: "#00897B", cyan: "#0288D1", red: "#D32F2F",
  amber: "#F57F17", green: "#2E7D32",
};

export const TIER_COLORS = (t) => ({
  CRITICAL: t.red, HIGH: t.amber, WATCH: t.cyan, NORMAL: t.green,
});

export const ROWS_PER_PAGE = 20;

import { fetchWithAuth } from './apiService';
export const riskTier = (score) => {
  if (score >= 70) return "CRITICAL";
  if (score >= 50) return "HIGH";
  if (score >= 30) return "WATCH";
  return "NORMAL";
};

export const forceDownloadPDF = async (pdfUrl, empId) => {
  try {
    const response = await fetchWithAuth(pdfUrl);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Fraud_Evidence_${empId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Download error:", error);
  }
};
