"""
VaultMind 2.0 — data_mutator.py
Reads the 6 raw CSVs, applies all 8-agent business logic fixes,
and writes production-ready files to /data/vaultmind_production/
"""

import pandas as pd
import numpy as np
from faker import Faker
import uuid, os, warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
fake = Faker('en_IN')
np.random.seed(42)

# ── paths ──────────────────────────────────────────────────────────────────────
INPUT_DIR  = "/mnt/user-data/uploads"
OUTPUT_DIR = "/home/claude/vaultmind_production"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("VaultMind 2.0 — Data Mutator")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# LOAD ALL RAW FILES
# ══════════════════════════════════════════════════════════════
print("\n[1/7] Loading raw files...")
employees   = pd.read_csv(f"{INPUT_DIR}/employees.csv")
login_logs  = pd.read_csv(f"{INPUT_DIR}/login_logs.csv")
access_logs = pd.read_csv(f"{INPUT_DIR}/access_logs.csv")
transactions= pd.read_csv(f"{INPUT_DIR}/transactions.csv")
warmup      = pd.read_csv(f"{INPUT_DIR}/historical_warmup_data.csv")
live_stream = pd.read_csv(f"{INPUT_DIR}/live_demo_stream.csv")

print(f"  employees:   {len(employees)} rows")
print(f"  login_logs:  {len(login_logs)} rows")
print(f"  access_logs: {len(access_logs)} rows")
print(f"  transactions:{len(transactions)} rows")
print(f"  warmup:      {len(warmup)} rows")
print(f"  live_stream: {len(live_stream)} rows")

# ══════════════════════════════════════════════════════════════
# FIX 1: EMPLOYEES — add hierarchy & context columns
# ══════════════════════════════════════════════════════════════
print("\n[2/7] Fixing employees.csv...")

# peer_cluster_id: 1–5 per role class (role-based clustering)
def assign_cluster(row):
    base = {'CLERK': 0, 'MANAGER': 2, 'IT_ADMIN': 4}.get(row['emp_class'], 0)
    branch_num = int(row['branch_id'].replace('BR_', ''))
    return (base + (branch_num % 2)) + 1  # clusters 1–5

employees['peer_cluster_id'] = employees.apply(assign_cluster, axis=1)

# join_date: random within last 5 years, ~5% new hires (< 30 days)
today = datetime(2026, 3, 31)
n = len(employees)
# 95% are established employees (30 days to 5 years ago)
join_dates = [
    today - timedelta(days=np.random.randint(31, 1825))
    for _ in range(n)
]
# Override ~5% (25 employees) as new hires
new_hire_idx = np.random.choice(n, size=25, replace=False)
for i in new_hire_idx:
    join_dates[i] = today - timedelta(days=np.random.randint(1, 30))
employees['join_date'] = [d.strftime('%Y-%m-%d') for d in join_dates]

# zone_id: based on branch
def assign_zone(branch_id):
    num = int(branch_id.replace('BR_', ''))
    if num <= 7:   return 'Tier-1'
    elif num <= 15: return 'Tier-2'
    else:           return 'Tier-3'

employees['zone_id'] = employees['branch_id'].apply(assign_zone)

# role_level: 1–3 seniority within role
def assign_role_level(row):
    emp_num = int(row['emp_id'].replace('EMP_', ''))
    return (emp_num % 3) + 1  # 1, 2, or 3

employees['role_level'] = employees.apply(assign_role_level, axis=1)

# is_new_hire flag (for cold-start logic)
employees['is_new_hire'] = employees['join_date'].apply(
    lambda d: 1 if (today - datetime.strptime(d, '%Y-%m-%d')).days < 30 else 0
)

print(f"  peer_cluster distribution:\n{employees['peer_cluster_id'].value_counts().sort_index().to_dict()}")
print(f"  new hires (< 30 days): {employees['is_new_hire'].sum()}")
print(f"  zone distribution:\n{employees['zone_id'].value_counts().to_dict()}")

# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def add_dwell_time(df):
    """Add dwell_time_seconds based on role, action type, and fraud flag."""
    dwell = np.zeros(len(df))
    for i, row in df.iterrows():
        idx = df.index.get_loc(i)
        is_fraud = row.get('is_fraud_flag', 0)
        emp_class = row.get('emp_class', 'CLERK')
        action = row.get('action_type', '')

        if action in ['SYSTEM_BULK_EXPORT', 'DB_Read'] and emp_class == 'IT_ADMIN':
            # IT Admin batch — machine speed
            dwell[idx] = round(np.random.uniform(0.001, 0.01), 4)
        elif is_fraud == 1:
            dwell[idx] = round(np.random.uniform(45, 180), 1)
        else:
            dwell[idx] = round(np.random.uniform(30, 300), 1)
    return dwell

def add_records_accessed(df):
    """Add records_accessed based on role and fraud flag."""
    records = np.zeros(len(df), dtype=int)
    for i, row in df.iterrows():
        idx = df.index.get_loc(i)
        is_fraud = row.get('is_fraud_flag', 0)
        emp_class = row.get('emp_class', 'CLERK')

        if emp_class == 'IT_ADMIN':
            records[idx] = np.random.randint(5000, 100001)
        elif emp_class == 'MANAGER':
            if is_fraud:
                records[idx] = np.random.randint(150, 500)
            else:
                records[idx] = np.random.randint(15, 51)
        else:  # CLERK
            if is_fraud:
                records[idx] = np.random.randint(2000, 5001)  # bulk download
            else:
                records[idx] = np.random.randint(80, 151)
    return records

def add_calendar_context(df):
    """Assign calendar context: 90% NORMAL, 5% QUARTER_END, 5% FYE."""
    n = len(df)
    contexts = np.random.choice(
        ['NORMAL', 'QUARTER_END', 'FYE'],
        size=n,
        p=[0.90, 0.05, 0.05]
    )
    # Override March rows to FYE
    if 'timestamp' in df.columns:
        ts = pd.to_datetime(df['timestamp'])
        contexts[ts.dt.month == 3] = 'FYE'
        contexts[(ts.dt.month.isin([6,9,12])) & (ts.dt.day >= 25)] = 'QUARTER_END'
    return contexts

# NLP text pools
NORMAL_COMPLAINT_TEXTS = [
    "Customer verified transaction manually. No issues reported.",
    "Standard NEFT processing — customer confirmed.",
    "Routine account inquiry. Resolved satisfactorily.",
    "KYC update verified. Documents in order.",
    "Minor delay in credit. Resolved within SLA.",
    "Customer query regarding statement. Clarified.",
    "Loan EMI processed as per schedule.",
    "Account balance inquiry. Normal operation.",
    "IMPS transfer confirmed by customer.",
    "Signature mismatch resolved after verification.",
    np.nan  # 10% null — left intentionally
]
NORMAL_COMPLAINT_WEIGHTS = [0.09]*9 + [0.19]  # last = NaN at 19% — total ~10% null

NORMAL_HR_TEXTS = [
    "Annual leave approved.",
    "Attended mandatory AML training.",
    "Performance review: Satisfactory.",
    "Completed CBS upgrade training.",
    "Transferred to BR_05 on mutual request.",
    "Promoted to Senior Clerk. Effective April 2026.",
    "Medical leave approved — 3 days.",
    "Completed fraud awareness workshop.",
    "Target achieved for Q3 2025.",
    np.nan
]
NORMAL_HR_WEIGHTS = [0.09]*9 + [0.19]

FRAUD_COMPLAINT_TEXTS = [
    "Customer reported that branch manager demanded bribe for loan approval. Amount: ₹50,000.",
    "Unauthorized debit reported by account holder.",
    "Customer reports money missing after employee interaction.",
    "Suspected phishing transaction — customer did not initiate this.",
    "Account holder complained: demanded bribe and threatened to delay processing.",
    "Formal complaint filed — demanded bribe, senior manager witness present.",
    "Manager demanded bribe for loan approval; customer refused and lodged written complaint.",
    "Second complaint this month: demanded bribe from small business owner.",
    "Multiple customers report same employee demanding cash for expedited service.",
    "Customer alleges forged signature on loan documents by bank official.",
]
FRAUD_HR_TEXTS = [
    "Employee under departmental inquiry for misconduct. Conduct unsatisfactory.",
    "Second written warning issued. Allegations of financial impropriety being investigated.",
    "Disciplinary proceedings initiated per Staff Regulation 14(3). Do not reassign.",
    "HR flagged for integrity review. Loan file irregularities noted by internal audit.",
    "Performance review withheld pending Ethics Committee decision.",
    "ALERT: Unusual bulk export of 50000 customer records to external IP detected.",
    "Employee terminated for gross misconduct — pending appeal.",
    "Suspended pending investigation. Access revoked.",
    "Show-cause notice issued. Employee failed to respond within stipulated time.",
    "CBI referral recommended by internal audit committee.",
]

def inject_nlp_text(df):
    """Fix 98% null NLP text — inject realistic synthetic text."""
    complaint_texts = []
    hr_remark_texts = []

    for i, row in df.iterrows():
        is_fraud = row.get('is_fraud_flag', 0)
        if is_fraud == 1:
            complaint_texts.append(np.random.choice(FRAUD_COMPLAINT_TEXTS))
            hr_remark_texts.append(np.random.choice(FRAUD_HR_TEXTS))
        else:
            # 85% get normal text, 15% null
            if np.random.random() < 0.85:
                # Pick from normal pool excluding NaN
                complaint_texts.append(np.random.choice(NORMAL_COMPLAINT_TEXTS[:-1]))
                hr_remark_texts.append(np.random.choice(NORMAL_HR_TEXTS[:-1]))
            else:
                complaint_texts.append(np.nan)
                hr_remark_texts.append(np.nan)

    df['raw_complaint_text'] = complaint_texts
    df['hr_remark_text'] = hr_remark_texts
    return df

# ══════════════════════════════════════════════════════════════
# FIX 2: TRANSACTIONS — financial constraints + features
# ══════════════════════════════════════════════════════════════
print("\n[3/7] Fixing transactions.csv...")

# Cap CLERK amounts at 499999 for normal rows
mask_clerk_normal = (transactions['emp_class'] == 'CLERK') & (transactions['is_fraud_flag'] == 0)
over_limit = transactions.loc[mask_clerk_normal, 'amount'] > 499999
transactions.loc[mask_clerk_normal & over_limit, 'amount'] = np.random.randint(1000, 499999, over_limit.sum())

# IT_ADMIN: force amount = 0, add SYSTEM_BULK_EXPORT action type
mask_it = transactions['emp_class'] == 'IT_ADMIN'
transactions.loc[mask_it, 'amount'] = 0
# 20% of IT_ADMIN rows get SYSTEM_BULK_EXPORT
it_bulk = transactions[mask_it].sample(frac=0.2, random_state=42).index
transactions.loc[it_bulk, 'action_type'] = 'SYSTEM_BULK_EXPORT'

# Add new columns
transactions['dwell_time_seconds'] = add_dwell_time(transactions)
transactions['records_accessed']   = add_records_accessed(transactions)
transactions['calendar_context']   = add_calendar_context(transactions)
transactions = inject_nlp_text(transactions)

# Add login_hour
transactions['login_hour'] = pd.to_datetime(transactions['timestamp']).dt.hour
transactions['off_hours_flag'] = transactions['login_hour'].apply(
    lambda h: 1 if h < 8 or h > 20 else 0
)

print(f"  CLERK amount cap applied to {over_limit.sum()} rows")
print(f"  IT_ADMIN SYSTEM_BULK_EXPORT rows: {(transactions['action_type']=='SYSTEM_BULK_EXPORT').sum()}")
print(f"  NLP null rate after fix: {transactions['raw_complaint_text'].isnull().mean():.1%}")

# ══════════════════════════════════════════════════════════════
# FIX 3: HISTORICAL WARMUP — add features
# ══════════════════════════════════════════════════════════════
print("\n[4/7] Fixing historical_warmup_data.csv...")

# Cap CLERK amounts
mask_clerk_w = (warmup['emp_class'] == 'CLERK') & (warmup['is_fraud_flag'] == 0)
over_w = warmup.loc[mask_clerk_w, 'amount'] > 499999
warmup.loc[mask_clerk_w & over_w, 'amount'] = np.random.randint(1000, 499999, over_w.sum())

# IT_ADMIN
mask_it_w = warmup['emp_class'] == 'IT_ADMIN'
warmup.loc[mask_it_w, 'amount'] = 0
it_bulk_w = warmup[mask_it_w].sample(frac=0.2, random_state=42).index
warmup.loc[it_bulk_w, 'action_type'] = 'SYSTEM_BULK_EXPORT'

warmup['dwell_time_seconds'] = add_dwell_time(warmup)
warmup['records_accessed']   = add_records_accessed(warmup)
warmup['calendar_context']   = add_calendar_context(warmup)
warmup = inject_nlp_text(warmup)
warmup['login_hour'] = pd.to_datetime(warmup['timestamp']).dt.hour
warmup['off_hours_flag'] = warmup['login_hour'].apply(lambda h: 1 if h < 8 or h > 20 else 0)

print(f"  Warmup rows: {len(warmup)}")
print(f"  NLP null rate after fix: {warmup['raw_complaint_text'].isnull().mean():.1%}")

# ══════════════════════════════════════════════════════════════
# FIX 4: ACCESS LOGS — add features
# ══════════════════════════════════════════════════════════════
print("\n[5/7] Fixing access_logs.csv...")
access_logs['dwell_time_seconds'] = add_dwell_time(access_logs)
access_logs['records_accessed']   = add_records_accessed(access_logs)
access_logs['login_hour'] = pd.to_datetime(access_logs['timestamp']).dt.hour
access_logs['off_hours_flag'] = access_logs['login_hour'].apply(lambda h: 1 if h < 8 or h > 20 else 0)

# Sync fraud flag from transactions by session_id
tx_fraud_sessions = set(
    transactions.loc[transactions['is_fraud_flag'] == 1, 'session_id'].dropna()
)
access_logs['is_fraud_flag'] = access_logs['session_id'].apply(
    lambda s: 1 if s in tx_fraud_sessions else 0
)
print(f"  Fraud rows synced into access_logs: {access_logs['is_fraud_flag'].sum()}")

# ══════════════════════════════════════════════════════════════
# FIX 5: LOGIN LOGS — extract temporal features, sync fraud
# ══════════════════════════════════════════════════════════════
print("\n[6/7] Fixing login_logs.csv...")
login_logs['login_hour'] = pd.to_datetime(login_logs['timestamp']).dt.hour
login_logs['off_hours_flag'] = login_logs['login_hour'].apply(
    lambda h: 1 if h < 8 or h > 20 else 0
)

# Sync fraud flag: if emp_id appears in fraud transactions on same date, flag login
tx_fraud_emp_dates = set(
    transactions.loc[transactions['is_fraud_flag'] == 1]
    .apply(lambda r: (r['emp_id'], r['timestamp'][:10]), axis=1)
)
login_logs['is_fraud_flag'] = login_logs.apply(
    lambda r: 1 if (r['emp_id'], r['timestamp'][:10]) in tx_fraud_emp_dates else 0,
    axis=1
)
print(f"  Fraud logins synced: {login_logs['is_fraud_flag'].sum()}")

# ══════════════════════════════════════════════════════════════
# FIX 6: LIVE STREAM — class imbalance + MIRAGE accounts
# ══════════════════════════════════════════════════════════════
print("\n[7/7] Fixing live_demo_stream.csv (critical overhaul)...")

# First apply same fixes as transactions
mask_clerk_ls = (live_stream['emp_class'] == 'CLERK') & (live_stream['is_fraud_flag'] == 0)
over_ls = live_stream.loc[mask_clerk_ls, 'amount'] > 499999
live_stream.loc[mask_clerk_ls & over_ls, 'amount'] = np.random.randint(1000, 499999, over_ls.sum())

mask_it_ls = live_stream['emp_class'] == 'IT_ADMIN'
live_stream.loc[mask_it_ls, 'amount'] = 0

live_stream['dwell_time_seconds'] = add_dwell_time(live_stream)
live_stream['records_accessed']   = add_records_accessed(live_stream)
live_stream['calendar_context']   = add_calendar_context(live_stream)
live_stream = inject_nlp_text(live_stream)
live_stream['login_hour'] = pd.to_datetime(live_stream['timestamp']).dt.hour
live_stream['off_hours_flag'] = live_stream['login_hour'].apply(lambda h: 1 if h < 8 or h > 20 else 0)

# ── Fraud Injection: Scenario A — Slow Boil (Clerk gradually increasing volume) ──
print("  Injecting Slow Boil fraud scenario...")
slow_boil_rows = []
base_date = datetime(2026, 3, 1)
for day in range(28):
    ts = base_date + timedelta(days=day, hours=np.random.randint(9, 18))
    records = 80 + (day * 8)  # starts normal, grows linearly
    amount  = np.random.randint(10000, 100000) if day < 14 else np.random.randint(100000, 499999)
    slow_boil_rows.append({
        'timestamp':            ts.strftime('%Y-%m-%d %H:%M:%S'),
        'transaction_id':       str(uuid.uuid4()),
        'emp_id':               'EMP_1050',
        'emp_class':            'CLERK',
        'branch_id':            'BR_05',
        'action_type':          'DB_Read',
        'amount':               float(amount),
        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.5.100.99',
        'is_fraud_flag':        1 if day >= 14 else 0,  # first 14 days normal, last 14 fraud
        'dwell_time_seconds':   round(np.random.uniform(45, 180), 1),
        'records_accessed':     records,
        'calendar_context':     'FYE',
        'login_hour':           ts.hour,
        'off_hours_flag':       0,
        'raw_complaint_text':   np.random.choice(FRAUD_COMPLAINT_TEXTS) if day >= 14 else np.random.choice(NORMAL_COMPLAINT_TEXTS[:-1]),
        'hr_remark_text':       np.random.choice(FRAUD_HR_TEXTS) if day >= 14 else np.random.choice(NORMAL_HR_TEXTS[:-1]),
    })

# ── Fraud Injection: Scenario B — Structuring (just below ₹50,000 threshold) ──
print("  Injecting Structuring fraud scenario...")
structuring_rows = []
for i in range(60):
    ts = datetime(2026, 3, np.random.randint(5, 25),
                  np.random.randint(10, 16), np.random.randint(0, 59))
    amount = np.random.randint(42000, 49999)  # just below ₹50k STR threshold
    structuring_rows.append({
        'timestamp':            ts.strftime('%Y-%m-%d %H:%M:%S'),
        'transaction_id':       str(uuid.uuid4()),
        'emp_id':               'EMP_1089',
        'emp_class':            'CLERK',
        'branch_id':            'BR_12',
        'action_type':          'Initiate',
        'amount':               float(amount),
        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.12.50.77',
        'is_fraud_flag':        1,
        'dwell_time_seconds':   round(np.random.uniform(45, 90), 1),
        'records_accessed':     np.random.randint(80, 150),
        'calendar_context':     'NORMAL',
        'login_hour':           ts.hour,
        'off_hours_flag':       0,
        'raw_complaint_text':   np.random.choice(FRAUD_COMPLAINT_TEXTS),
        'hr_remark_text':       np.random.choice(FRAUD_HR_TEXTS),
    })

# ── Fraud Injection: Scenario C — Privilege Escalation (Clerk doing Approve) ──
print("  Injecting Privilege Escalation fraud scenario...")
priv_rows = []
for i in range(50):
    ts = datetime(2026, 3, np.random.randint(10, 28),
                  np.random.randint(20, 23), np.random.randint(0, 59))
    amount = float(np.random.randint(5000000, 25000000))  # Manager-level amount
    priv_rows.append({
        'timestamp':            ts.strftime('%Y-%m-%d %H:%M:%S'),
        'transaction_id':       str(uuid.uuid4()),
        'emp_id':               'EMP_1302',
        'emp_class':            'CLERK',
        'branch_id':            'BR_08',
        'action_type':          'Approve',  # CLERK should not do Approve — escalation
        'amount':               amount,
        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.8.200.15',
        'is_fraud_flag':        1,
        'dwell_time_seconds':   round(np.random.uniform(4, 8), 1),  # too fast — suspicious
        'records_accessed':     np.random.randint(80, 150),
        'calendar_context':     'NORMAL',
        'login_hour':           ts.hour,
        'off_hours_flag':       1,
        'raw_complaint_text':   np.random.choice(FRAUD_COMPLAINT_TEXTS),
        'hr_remark_text':       np.random.choice(FRAUD_HR_TEXTS),
    })

# ── Fraud Injection: Scenario D — Collusion Ring (additional pairs) ──
print("  Injecting additional Collusion Ring rows...")
collusion_rows = []
for i in range(60):
    ts = datetime(2026, 3, np.random.randint(1, 28),
                  20, np.random.randint(0, 5))
    amount = float(np.random.randint(2000000, 50000000))
    for emp, role, action in [('EMP_1219','CLERK','Initiate'), ('EMP_1193','MANAGER','Approve')]:
        collusion_rows.append({
            'timestamp':            ts.strftime('%Y-%m-%d %H:%M:%S'),
            'transaction_id':       str(uuid.uuid4()),
            'emp_id':               emp,
            'emp_class':            role,
            'branch_id':            'BR_10',
            'action_type':          action,
            'amount':               amount,
            'account_touched':      f'ACC_{np.random.randint(5000,5099)}',
            'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}',
            'is_fraud_flag':        1,
            'dwell_time_seconds':   4.0 if role == 'MANAGER' else 30.0,  # 4s approval = too fast
            'records_accessed':     np.random.randint(15, 50),
            'calendar_context':     'FYE',
            'login_hour':           20,
            'off_hours_flag':       1,
            'raw_complaint_text':   np.random.choice(FRAUD_COMPLAINT_TEXTS),
            'hr_remark_text':       np.random.choice(FRAUD_HR_TEXTS),
        })

# ── MIRAGE ACCOUNT rows ──────────────────────────────────────────────────────
print("  Injecting Mirage Account (DeceptionGuard) rows...")
mirage_rows = []
mirage_emps = ['EMP_1001', 'EMP_1050', 'EMP_1089', 'EMP_1219']
for i in range(15):
    emp   = np.random.choice(mirage_emps)
    mirage_id = f'ACC-MIRAGE-{(i % 10) + 1:03d}'
    ts = datetime(2026, 3, np.random.randint(15, 30),
                  np.random.randint(10, 18), np.random.randint(0, 59))
    mirage_rows.append({
        'timestamp':            ts.strftime('%Y-%m-%d %H:%M:%S'),
        'transaction_id':       str(uuid.uuid4()),
        'emp_id':               emp,
        'emp_class':            'CLERK' if emp != 'EMP_1193' else 'MANAGER',
        'branch_id':            f'BR_{np.random.randint(1,20):02d}',
        'action_type':          'DB_Read',
        'amount':               0.0,
        'account_touched':      mirage_id,
        'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}',
        'is_fraud_flag':        1,
        'dwell_time_seconds':   12.0,           # human UI — 12 seconds on a honeypot
        'records_accessed':     1,
        'calendar_context':     'NORMAL',
        'login_hour':           ts.hour,
        'off_hours_flag':       0,
        'raw_complaint_text':   "HONEYPOT TRIGGERED: Employee accessed restricted Mirage Account.",
        'hr_remark_text':       "DeceptionGuard: Confirmed fraud access to decoy account. Immediate escalation initiated.",
    })

# ── Combine everything ────────────────────────────────────────────────────────
all_new_rows = (
    pd.DataFrame(slow_boil_rows) if slow_boil_rows else pd.DataFrame()
)
for rows in [structuring_rows, priv_rows, collusion_rows, mirage_rows]:
    if rows:
        all_new_rows = pd.concat([all_new_rows, pd.DataFrame(rows)], ignore_index=True)

# Align columns with live_stream before concat
for col in live_stream.columns:
    if col not in all_new_rows.columns:
        all_new_rows[col] = np.nan
all_new_rows = all_new_rows[[c for c in live_stream.columns if c in all_new_rows.columns]]

live_stream_final = pd.concat([live_stream, all_new_rows], ignore_index=True)
live_stream_final = live_stream_final.sort_values('timestamp').reset_index(drop=True)

total_fraud = live_stream_final['is_fraud_flag'].sum()
total_rows  = len(live_stream_final)
print(f"  Live stream rows: {total_rows}")
print(f"  Fraud rows: {total_fraud} ({total_fraud/total_rows*100:.1f}%)")
print(f"  Mirage Account rows: {live_stream_final['account_touched'].str.startswith('ACC-MIRAGE', na=False).sum()}")

# ══════════════════════════════════════════════════════════════
# SAVE ALL PRODUCTION FILES
# ══════════════════════════════════════════════════════════════
print("\n[Saving production files...]")

save_map = {
    'employees_production.csv':             employees,
    'login_logs_production.csv':            login_logs,
    'access_logs_production.csv':           access_logs,
    'transactions_production.csv':          transactions,
    'historical_warmup_production.csv':     warmup,
    'live_demo_stream_production.csv':      live_stream_final,
}

for filename, df in save_map.items():
    path = f"{OUTPUT_DIR}/{filename}"
    df.to_csv(path, index=False)
    fraud_count = df['is_fraud_flag'].sum() if 'is_fraud_flag' in df.columns else 'N/A'
    print(f"  ✓ {filename}: {len(df)} rows | fraud={fraud_count}")

# ══════════════════════════════════════════════════════════════
# FINAL QUALITY REPORT
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PRODUCTION DATA QUALITY REPORT")
print("=" * 60)

print("\nemployees_production.csv:")
print(f"  Columns: {list(employees.columns)}")
print(f"  New hires: {employees['is_new_hire'].sum()}")
print(f"  Zone distribution: {employees['zone_id'].value_counts().to_dict()}")

print("\nlive_demo_stream_production.csv:")
ls = live_stream_final
print(f"  Total rows: {len(ls)}")
print(f"  Fraud rows: {ls['is_fraud_flag'].sum()} ({ls['is_fraud_flag'].mean()*100:.1f}%)")
print(f"  Fraud scenarios present:")
print(f"    Slow Boil (EMP_1050):        {(ls['emp_id']=='EMP_1050') & (ls['is_fraud_flag']==1)}.sum()")
print(f"    Structuring (EMP_1089):       {((ls['emp_id']=='EMP_1089') & (ls['is_fraud_flag']==1)).sum()} rows")
print(f"    Privilege Escalation (EMP_1302): {((ls['emp_id']=='EMP_1302') & (ls['is_fraud_flag']==1)).sum()} rows")
print(f"    Collusion (EMP_1219+1193):    {((ls['emp_id'].isin(['EMP_1219','EMP_1193'])) & (ls['is_fraud_flag']==1)).sum()} rows")
print(f"    Mirage Account triggers:      {ls['account_touched'].str.startswith('ACC-MIRAGE', na=False).sum()} rows")
print(f"    Original fraud (EMP_1001,1416): {((ls['emp_id'].isin(['EMP_1001','EMP_1416'])) & (ls['is_fraud_flag']==1)).sum()} rows")

print("\ntransactions_production.csv:")
tx = transactions
print(f"  NLP text null rate: {tx['raw_complaint_text'].isnull().mean():.1%} (target: ~15%)")
print(f"  CLERK amounts > 499999 (non-fraud): {((tx['emp_class']=='CLERK') & (tx['is_fraud_flag']==0) & (tx['amount']>499999)).sum()} (should be 0)")
print(f"  IT_ADMIN SYSTEM_BULK_EXPORT rows: {(tx['action_type']=='SYSTEM_BULK_EXPORT').sum()}")
print(f"  Off-hours activity: {tx['off_hours_flag'].sum()} rows ({tx['off_hours_flag'].mean()*100:.1f}%)")

print("\n✅ All files saved to:", OUTPUT_DIR)
print("=" * 60)
