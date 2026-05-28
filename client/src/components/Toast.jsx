import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, X } from "lucide-react";
import { useEffect } from "react";

export function Toast({ message, visible, onClose }) {
  useEffect(() => {
    if (visible) {
      const timer = setTimeout(onClose, 3000);
      return () => clearTimeout(timer);
    }
  }, [visible, onClose]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -40, x: 20 }}
          animate={{ opacity: 1, y: 0, x: 0 }}
          exit={{ opacity: 0, y: -40 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
          className="fixed top-6 right-6 z-[9999] flex items-center gap-3 px-5 py-3 rounded-lg shadow-2xl border"
          style={{
            background: "rgba(10, 10, 10, 0.95)",
            borderColor: "rgba(0, 230, 118, 0.3)",
            backdropFilter: "blur(12px)",
          }}
        >
          <CheckCircle size={18} style={{ color: "#00E676" }} />
          <span className="text-sm font-mono text-white tracking-wide">{message}</span>
          <button onClick={onClose} className="ml-2 cursor-pointer opacity-50 hover:opacity-100 transition">
            <X size={14} style={{ color: "#888" }} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
