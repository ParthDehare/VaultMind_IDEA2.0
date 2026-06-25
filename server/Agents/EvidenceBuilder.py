import os, hashlib, json, io, random
from datetime import datetime
import qrcode
from PIL import Image
from supabase import create_client, Client

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader

# ── Config & Constants ─────────────────────────────────────
BANK_CONFIG = {
    "bank_name":        "Union Bank of India",
    "bank_short":       "UBI",
    "branch_unit":      "Central Fraud Risk & Compliance Division",
    "rbi_circular":     "RBI/2024-25/16",
    "rbi_full":         "Master Direction on Fraud Risk Management, 2024",
    "fiu_ref":          "FIU-IND/STR/2026/VM",
    "pmla":             "Prevention of Money Laundering Act, 2002 — Section 12",
    "bsa":              "Bharatiya Sakshya Adhiniyam 2023 — Section 63",
    "system":           "VaultMind 2.0 Behavioural Intelligence Platform",
    "version":          "v2.4.1-PROD",
    "swift_prefix":     "UBININBB",
}

# Colors
C_NAVY   = HexColor("#0F2A5E")
C_BLUE   = HexColor("#1A3C6E")
C_TEAL   = HexColor("#0D5C6E")
C_RED    = HexColor("#8B1A1A")
C_AMBER  = HexColor("#7A4A00")
C_GREY   = HexColor("#F4F6F9")
C_MGREY  = HexColor("#DDE3EC")
C_DARK   = HexColor("#1C2833")
C_MID    = HexColor("#4A5568")
C_GREEN  = HexColor("#145A32")
C_WHITE  = white
C_LGREY  = HexColor("#E8ECF0")

# ── Watermark Canvas ───────────────────────────────────────
class WatermarkCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, watermark_text="CONFIDENTIAL — INTERNAL AUDIT ONLY", **kwargs):
        super().__init__(*args, **kwargs)
        self._watermark_text = watermark_text

    def showPage(self):
        self._draw_watermark()
        super().showPage()

    def save(self):
        self._draw_watermark()
        super().save()

    def _draw_watermark(self):
        self.saveState()
        self.setFillColor(Color(0.75, 0.75, 0.75, alpha=0.18))
        self.setFont("Helvetica-Bold", 38)
        w, h = A4
        self.translate(w / 2, h / 2)
        self.rotate(42)
        self.drawCentredString(0, 30,  self._watermark_text)
        self.drawCentredString(0, -30, self._watermark_text)
        self.restoreState()

# ── Helpers ────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

def _table(data, widths, style_cmds):
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle(style_cmds))
    return t

def mock_swift(branch_id: str) -> str:
    branch_num = str(branch_id).replace("BR_", "").zfill(3)
    return f"{BANK_CONFIG['swift_prefix']}{branch_num}"

def mock_mac() -> str:
    return ":".join(f"{random.randint(0,255):02X}" for _ in range(6))

def mock_device_ip(branch_id: str) -> str:
    b = str(branch_id).replace("BR_", "")
    try: b_int = int(b)
    except: b_int = 1
    return f"10.{b_int}.{random.randint(1,254)}.{random.randint(1,254)}"

# ── Agent 7 Main Class ─────────────────────────────────────
class EvidenceBuilder:
    def __init__(self):
        self.agent_name = "EvidenceBuilder (Agent 7)"
        self.output_dir = 'evidence_output/pdf_reports'
        self.chain_dir = 'evidence_output/blockchain_chain'
        self.str_dir = 'evidence_output/str_reports'
        
        SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
        if SUPABASE_URL and SUPABASE_KEY:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            self.supabase = None
        
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

    def generate_evidence_package(self, transaction, cbsi_score, dominant_reason):
        """Builds the Enterprise PDF Docket based on Colab specifications"""
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        emp_id = transaction.get('emp_id', 'UNKNOWN')
        branch_id = transaction.get('branch_id', 'BR_01')
        alert_id = f"EVD-{timestamp_str}"
        now_str = datetime.now().strftime("%d %B %Y  |  %H:%M:%S IST")

        # 1. Update Blockchain
        canonical = json.dumps(transaction, sort_keys=True, default=str)
        data_hash = hashlib.sha256(canonical.encode()).hexdigest()
        
        prev = self.chain[-1]
        content = f"{len(self.chain)}{datetime.now().isoformat()}{alert_id}{data_hash}{prev['block_hash']}"
        block_hash = hashlib.sha256(content.encode()).hexdigest()
        
        block = {
            "block_id": len(self.chain),
            "timestamp": datetime.now().isoformat(),
            "alert_id": alert_id,
            "data_hash": data_hash,
            "previous_hash": prev["block_hash"],
            "block_hash": block_hash,
        }
        self.chain.append(block)
        self._save_chain()

        # 2. Build PDF
        output_path = os.path.join(self.output_dir, f"{alert_id}_{emp_id}.pdf")
        doc = SimpleDocTemplate(
            output_path, pagesize=A4, rightMargin=0.65*inch, leftMargin=0.65*inch,
            topMargin=0.65*inch, bottomMargin=0.65*inch, canvasmaker=WatermarkCanvas
        )
        W = 7.2 * inch
        story = []

        cbsi_col = C_RED if cbsi_score >= 80 else (HexColor("#7A4A00") if cbsi_score >= 60 else C_GREEN)
        
        # QR Code
        qr_obj = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=4, border=2)
        qr_obj.add_data(block_hash)
        qr_obj.make(fit=True)
        qr_pil = qr_obj.make_image(fill_color="black", back_color="white")
        qr_buf = io.BytesIO()
        qr_pil.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        from reportlab.platypus import Image as RLImage
        qr_rl = RLImage(qr_buf, width=1.05*inch, height=1.05*inch)

        # Header
        header_data = [[
            Paragraph(
                f"<b>UNION BANK OF INDIA</b><br/>"
                f"<font size='8'>Central Fraud Risk &amp; Compliance Division</font><br/>"
                f"<font size='7'>{BANK_CONFIG['rbi_full']}</font>",
                S("hb", fontSize=14, textColor=C_WHITE, fontName="Helvetica-Bold", leading=18)
            ),
            Paragraph(
                f"<b>FRAUD INVESTIGATION<br/>EVIDENCE DOCKET</b>",
                S("ht", fontSize=11, textColor=C_WHITE, fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=16)
            ),
        ]]
        story.append(_table(header_data, [4.8*inch, 2.4*inch], [
            ("BACKGROUND", (0,0),(-1,-1), C_NAVY),
            ("TOPPADDING", (0,0),(-1,-1), 14), ("BOTTOMPADDING", (0,0),(-1,-1), 14),
            ("LEFTPADDING", (0,0),(-1,-1), 14), ("RIGHTPADDING", (0,0),(-1,-1), 14),
            ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(Spacer(1, 4))

        story.append(_table([[
            Paragraph(f"<b>RESTRICTED — CLASSIFICATION: CONFIDENTIAL | REF: {alert_id}</b>",
                S("cl", fontSize=8, textColor=C_WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER))
        ]], [W], [("BACKGROUND", (0,0),(-1,-1), C_RED), ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5)]))
        story.append(Spacer(1, 8))

        swift_code = mock_swift(branch_id)
        device_ip  = mock_device_ip(branch_id)
        device_mac = mock_mac()

        meta_left = [
            ["Document Reference:",  alert_id],
            ["Date of Generation:",  now_str],
            ["Issuing Authority:",    BANK_CONFIG["bank_name"]],
            ["Issuing Division:",     BANK_CONFIG["branch_unit"]],
            ["Regulatory Basis:",     BANK_CONFIG["rbi_circular"]],
            ["Legal Basis:",          BANK_CONFIG["bsa"]],
            ["System Identifier:",    f"{BANK_CONFIG['system']} {BANK_CONFIG['version']}"],
            ["Branch SWIFT Code:",    swift_code],
            ["Device IP Address:",    device_ip],
            ["Device MAC/Proxy:",     device_mac],
        ]
        meta_para = [[Paragraph(f"<b>{k}</b>", S("mk", fontSize=7.5, fontName="Helvetica-Bold", textColor=C_BLUE)),
                      Paragraph(v, S("mv", fontSize=7.5, fontName="Courier", textColor=C_DARK))] for k,v in meta_left]

        meta_t = _table(meta_para, [1.9*inch, 3.5*inch], [
            ("FONTSIZE", (0,0),(-1,-1), 7.5), ("TOPPADDING", (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3), ("LEFTPADDING", (0,0),(-1,-1), 6),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_GREY]), ("GRID", (0,0),(-1,-1), 0.3, C_MGREY),
        ])

        qr_label = Paragraph("<font size='6'>Scan to verify<br/>blockchain record</font>", S("ql", fontSize=6, alignment=TA_CENTER, textColor=C_MID))
        qr_block = _table([[qr_rl], [qr_label]], [1.1*inch], [("ALIGN", (0,0),(-1,-1), "CENTER"), ("BOX", (0,0),(-1,-1), 0.5, C_MGREY)])

        story += [_table([[meta_t, qr_block]], [5.5*inch, 1.2*inch], [("VALIGN", (0,0),(-1,-1), "TOP")]), Spacer(1, 12)]

        def sec(title, subtitle=""):
            rows = [[Paragraph(f"<b>{title}</b>", S("sh", fontSize=10, textColor=C_WHITE, fontName="Helvetica-Bold"))]]
            if subtitle: rows[0].append(Paragraph(subtitle, S("ss", fontSize=8, textColor=HexColor("#B0C4D8"), fontName="Helvetica")))
            return _table([rows[0]], [W] if not subtitle else [4*inch, 3.2*inch], [
                ("BACKGROUND", (0,0),(-1,-1), C_BLUE), ("TOPPADDING", (0,0),(-1,-1), 7),
                ("BOTTOMPADDING", (0,0),(-1,-1), 7), ("LEFTPADDING", (0,0),(-1,-1), 10), ("VALIGN", (0,0),(-1,-1), "MIDDLE")
            ])

        story += [sec("SECTION I — SUBJECT PERSONNEL PROFILE & INCIDENT SUMMARY"), Spacer(1,6)]

        profile_data = [
            ["Subject Personnel ID:", emp_id, "CBSI Score:", Paragraph(f"<b>{cbsi_score}/100</b>", S("cb", fontSize=16, textColor=cbsi_col, fontName="Helvetica-Bold"))],
            ["Role Classification:", transaction.get("emp_class","—"), "Escalation Class:", "CRITICAL NON-COMPLIANCE" if cbsi_score >= 80 else "SEVERE BREACH"],
            ["Reporting Unit:", branch_id, "Reg. Non-Compliance Flag:","CONFIRMED" if transaction.get("is_fraud_flag")==1 else "SUSPECTED"],
            ["Transaction Reference:", str(transaction.get("transaction_id","—"))[:28], "Instruction Category:", transaction.get("action_type","—")],
            ["Incident Timestamp:", str(transaction.get("timestamp","—")), "Transaction Quantum:", f"INR {float(transaction.get('amount',0)):,.2f}"],
        ]
        pf_rows = [[Paragraph(f"<b>{r[0]}</b>", S("pk", fontSize=8, fontName="Helvetica-Bold", textColor=C_BLUE)), Paragraph(str(r[1]), S("pv", fontSize=8, fontName="Helvetica", textColor=C_DARK)),
                    Paragraph(f"<b>{r[2]}</b>", S("pk", fontSize=8, fontName="Helvetica-Bold", textColor=C_BLUE)), r[3] if isinstance(r[3], Paragraph) else Paragraph(str(r[3]), S("pv", fontSize=8, fontName="Helvetica", textColor=C_DARK))] for r in profile_data]
        story += [_table(pf_rows, [1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch], [("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_GREY]), ("GRID", (0,0),(-1,-1), 0.3, C_MGREY), ("VALIGN", (0,0),(-1,-1), "MIDDLE")]), Spacer(1,12)]

        story += [sec("SECTION II — FORENSIC COMPLIANCE FINDINGS"), Spacer(1,8)]
        story.append(Paragraph(
            "The VaultMind Behavioural Intelligence Platform identified the following specific deviations from the subject's established behavioural baseline. "
            f"<br/><br/><b>Primary Finding:</b> {dominant_reason}",
            S("body", fontSize=8.5, fontName="Helvetica", textColor=C_DARK, leading=13, alignment=TA_JUSTIFY, spaceAfter=8)
        ))

        story += [sec("SECTION III — IMMUTABLE EVIDENCE CHAIN (SHA-256)"), Spacer(1,6)]
        chain_data = [
            ["Ledger Block Number:", str(block["block_id"])],
            ["Data Integrity Hash:", block["data_hash"]],
            ["Antecedent Block Hash:", block["previous_hash"]],
            ["Current Block Hash:", block["block_hash"]],
        ]
        ch_rows = [[Paragraph(f"<b>{k}</b>", S("ck", fontSize=7.5, fontName="Helvetica-Bold", textColor=C_BLUE)), Paragraph(v, S("cv", fontSize=7.5, fontName="Courier", textColor=C_DARK))] for k,v in chain_data]
        story += [_table(ch_rows, [1.9*inch, 5.3*inch], [("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_GREY]), ("GRID", (0,0),(-1,-1), 0.3, C_MGREY)]), Spacer(1,14)]

        story += [sec("SECTION IV — MAKER / CHECKER DUAL AUTHORIZATION"), Spacer(1,8)]
        sig_header = _table([[Paragraph("<b>MAKER (Investigating Officer)</b>", S("mh", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE, alignment=TA_CENTER)),
                              Paragraph("<b>CHECKER (Reviewing Authority)</b>", S("ch", fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE, alignment=TA_CENTER))]], [3.55*inch, 3.55*inch], [("BACKGROUND", (0,0),(-1,-1), C_BLUE), ("GRID", (0,0),(-1,-1), 0.5, C_MGREY)])
        story.append(sig_header)
        
        sig_fields = [("Investigator Name:", "Reviewing Authority:"), ("Employee ID:", "Employee ID:"), ("Date:", "Date:"), ("Signature:", "Signature:")]
        sig_rows = [[Paragraph(f"<b>{r[0]}</b>", S("sf", fontSize=8, fontName="Helvetica-Bold", textColor=C_DARK)), Paragraph(f"<b>{r[1]}</b>", S("sf", fontSize=8, fontName="Helvetica-Bold", textColor=C_DARK))] for r in sig_fields]
        story += [_table(sig_rows, [3.55*inch, 3.55*inch], [("GRID", (0,0),(-1,-1), 0.5, C_MGREY), ("TOPPADDING", (0,0),(-1,-1), 10), ("BOTTOMPADDING", (0,0),(-1,-1), 10)])]

        doc.build(story)
        
        if hasattr(self, 'supabase') and self.supabase:
            with open(output_path, "rb") as f:
                file_bytes = f.read()
            self.supabase.storage.from_("evidence-vault").upload(f"{alert_id}_{emp_id}.pdf", file_bytes, {"content-type": "application/pdf", "upsert": "true"})
            return self.supabase.storage.from_("evidence-vault").get_public_url(f"{alert_id}_{emp_id}.pdf")
            
        return output_path