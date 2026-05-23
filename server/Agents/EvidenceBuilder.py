import os
import hashlib
import json
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
import qrcode
from io import BytesIO

# Config & Colors from your Colab
BANK_CONFIG = {
    "bank_name": "Union Bank of India",
    "rbi_circular": "RBI/2024-25/16",
    "bsa_section": "Bharatiya Sakshya Adhiniyam 2023 — Section 63",
    "system_name": "VaultMind 2.0"
}

DARK_BLUE = HexColor("#1A3C6E")
TEAL      = HexColor("#0D7377")
RED       = HexColor("#DC2626")
AMBER     = HexColor("#D97706")
GREEN     = HexColor("#16A34A")
LIGHT_GREY= HexColor("#F8FAFC")
MID_GREY  = HexColor("#E2E8F0")
TEXT_DARK = HexColor("#1C2833")

def add_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 36)
    canvas.setStrokeColorRGB(0.85, 0.85, 0.85)
    canvas.setFillColorRGB(0.85, 0.85, 0.85)
    canvas.setFillAlpha(0.2)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "CONFIDENTIAL - INTERNAL AUDIT ONLY")
    canvas.restoreState()

class EvidenceBuilder:
    def __init__(self):
        self.agent_name = "EvidenceBuilder (Agent 7)"
        self.output_dir = 'evidence_output/pdf_reports'
        self.chain_dir = 'evidence_output/blockchain_chain'
        self.str_dir = 'evidence_output/str_reports'
        
        for d in [self.output_dir, self.chain_dir, self.str_dir]:
            os.makedirs(d, exist_ok=True)
            
        self.chain_file = os.path.join(self.chain_dir, "evidence_chain.json")
        self.chain = self._load_chain()

    def _load_chain(self):
        if os.path.exists(self.chain_file):
            with open(self.chain_file) as f:
                return json.load(f)
        genesis = {
            "block_id": 0,
            "timestamp": "2026-01-01T00:00:00",
            "alert_id": "GENESIS",
            "data_hash": "0" * 64,
            "previous_hash": "0" * 64,
            "block_hash": hashlib.sha256(b"VaultMind_Genesis").hexdigest(),
        }
        return [genesis]

    def _save_chain(self):
        with open(self.chain_file, 'w') as f:
            json.dump(self.chain, f, indent=2)

    def S(self, name, **kw):
        return ParagraphStyle(name, **kw)

    def generate_evidence_package(self, transaction, cbsi_score, triggered_signals):
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        emp_id = transaction.get('emp_id', 'UNKNOWN')
        alert_id = f"EVD-{timestamp_str}"
        
        # 1. Blockchain Hash
        canonical = json.dumps({
            "tx_id": str(transaction.get("transaction_id", "")),
            "emp_id": emp_id,
            "amount": str(transaction.get("amount", "")),
            "score": cbsi_score
        }, sort_keys=True)
        data_hash = hashlib.sha256(canonical.encode()).hexdigest()
        
        prev = self.chain[-1]
        content = f"{len(self.chain)}{datetime.datetime.now().isoformat()}{alert_id}{data_hash}{prev['block_hash']}"
        block_hash = hashlib.sha256(content.encode()).hexdigest()
        
        block = {
            "block_id": len(self.chain),
            "timestamp": datetime.datetime.now().isoformat(),
            "alert_id": alert_id,
            "data_hash": data_hash,
            "previous_hash": prev["block_hash"],
            "block_hash": block_hash,
        }
        self.chain.append(block)
        self._save_chain()

        # 2. Dummy SHAP Logic for Professional Look (until ML is fully wired)

        # 3. Build The PDF (Exactly like your Colab)
        pdf_path = os.path.join(self.output_dir, f"{alert_id}_{emp_id}.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.6*inch)
        story = []

        # Header & QR
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(block["block_hash"])
        qr.make(fit=True)
        img_buffer = BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        header_text = Paragraph("<b>VAULTMIND 2.0 — FRAUD INVESTIGATION EVIDENCE PACKAGE</b>", self.S("hd", fontSize=14, textColor=white, fontName="Helvetica-Bold"))
        h = Table([[header_text, Image(img_buffer, width=1.1*inch, height=1.1*inch)]])
        story.append(h)
        doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
        return pdf_path