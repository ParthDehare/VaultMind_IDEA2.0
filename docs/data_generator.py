"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         VaultMind 2.0 — Synthetic Dataset Generator                        ║
║         50,000 Transaction Logs | 500 Employees | 6 Months                 ║
║         Senior Data Engineer Template — Modular + Vectorized               ║
╚══════════════════════════════════════════════════════════════════════════════╝

ARCHITECTURE NOTES:
  - No ML scores generated. Backend calculates these live from raw signals.
  - NLP columns (raw_complaint_text, hr_remark_text) are sparse by design.
    Only fraud rows and a small % of normal rows carry text.
  - Output is split into two CSVs:
      * historical_warmup_data.csv  →  Oct 2025 – Feb 2026 (GNN pre-load)
      * live_demo_stream.csv        →  March 2026 only    (Kafka stream)
"""

import os
import uuid
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
SEED               = 42
TOTAL_ROWS         = 50_000
N_EMPLOYEES        = 500
SIM_START          = datetime(2025, 10, 1)
SIM_END            = datetime(2026, 3, 31, 23, 59, 59)
HISTORICAL_CUTOFF  = datetime(2026, 3, 1)          # < this → historical
OUTPUT_DIR         = os.path.join(os.path.dirname(__file__), "data")

random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IN")
fake.seed_instance(SEED)

# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE MASTER
# ─────────────────────────────────────────────────────────────────────────────
def build_employee_master(n: int) -> pd.DataFrame:
    """
    Create 500 employees with realistic PSB role distribution:
      70% Clerks, 25% Managers, 5% IT Admins
    Each employee gets a home branch, peer-cluster ID, and typical work-hour band.
    """
    roles = (
        ["CLERK"]    * int(n * 0.70) +
        ["MANAGER"]  * int(n * 0.25) +
        ["IT_ADMIN"] * (n - int(n * 0.70) - int(n * 0.25))
    )
    random.shuffle(roles)

    employees = pd.DataFrame({
        "emp_id"       : [f"EMP_{1000 + i}" for i in range(n)],
        "emp_class"    : roles,
        "branch_id"    : [f"BR_{random.randint(1, 20):02d}" for _ in range(n)],
        "peer_cluster" : [random.randint(0, 14) for _ in range(n)],
        # Typical hour band: (earliest_start, latest_end) for login
        "work_start_hr": [random.randint(8, 10) for _ in range(n)],
        "work_end_hr"  : [random.randint(17, 19) for _ in range(n)],
    })
    return employees


# ─────────────────────────────────────────────────────────────────────────────
# IP ADDRESS POOL
# ─────────────────────────────────────────────────────────────────────────────
def build_ip_pool() -> dict:
    """
    Returns a dict of internal IPs (per branch) and a small external IP pool.
    Branch IPs follow 10.branch.x.x; external IPs look like public addresses.
    """
    internal = {
        f"BR_{b:02d}": [f"10.{b}.{random.randint(0,255)}.{random.randint(1,254)}"
                        for _ in range(20)]
        for b in range(1, 21)
    }
    external = [fake.ipv4_public() for _ in range(15)]
    return {"internal": internal, "external": external}


# ─────────────────────────────────────────────────────────────────────────────
# NORMAL TRANSACTION BUILDER (vectorized)
# ─────────────────────────────────────────────────────────────────────────────
ACTION_BY_ROLE = {
    "CLERK"   : ["Initiate", "DB_Read", "System_Login"],
    "MANAGER" : ["Approve",  "DB_Read", "System_Login", "Initiate"],
    "IT_ADMIN": ["DB_Read",  "System_Login"],
}

AMOUNT_RANGE_BY_ROLE = {
    "CLERK"   : (1_000,    500_000),
    "MANAGER" : (50_000,  3_000_000),
    "IT_ADMIN": (0,        0),           # IT Admins never touch money
}


def generate_normal_timestamp(row, rng: np.random.Generator) -> pd.Timestamp:
    """Return a working-hours timestamp for a given employee row."""
    day_offset = rng.integers(0, (SIM_END - SIM_START).days)
    base_date  = SIM_START + timedelta(days=int(day_offset))

    # 90% chance: within work hours | 10% chance: mild after-hours (not suspicious)
    if rng.random() < 0.90:
        hour = rng.integers(row["work_start_hr"], row["work_end_hr"] + 1)
    else:
        hour = rng.integers(row["work_end_hr"] + 1, row["work_end_hr"] + 3)

    minute = rng.integers(0, 60)
    second = rng.integers(0, 60)
    return pd.Timestamp(base_date.replace(hour=int(hour), minute=int(minute), second=int(second)))


def build_normal_transactions(employees: pd.DataFrame,
                               ip_pool: dict,
                               n: int,
                               rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate n normal (non-fraud) transactions using weighted employee sampling
    and vectorized column construction wherever possible.
    """
    # Sample employees with replacement, weighted so clerks dominate volume
    weight_map   = {"CLERK": 0.65, "MANAGER": 0.25, "IT_ADMIN": 0.10}
    weights      = employees["emp_class"].map(weight_map).values
    weights      = weights / weights.sum()
    sampled_idx  = rng.choice(len(employees), size=n, p=weights)
    sampled_emps = employees.iloc[sampled_idx].reset_index(drop=True)

    # Timestamps — one per row
    timestamps = pd.to_datetime([
        generate_normal_timestamp(sampled_emps.iloc[i], rng) for i in range(n)
    ])

    # Action types — sample per role
    actions = [
        random.choice(ACTION_BY_ROLE[role])
        for role in sampled_emps["emp_class"]
    ]

    # Amounts — vectorized via numpy
    lo = sampled_emps["emp_class"].map(lambda r: AMOUNT_RANGE_BY_ROLE[r][0]).values.astype(float)
    hi = sampled_emps["emp_class"].map(lambda r: AMOUNT_RANGE_BY_ROLE[r][1]).values.astype(float)
    amounts = np.where(
        sampled_emps["emp_class"].values == "IT_ADMIN",
        0.0,
        np.round(rng.uniform(lo, hi), 2)
    )

    # Account IDs
    account_pool = [f"ACC_{rng.integers(1000, 9999)}" for _ in range(n)]

    # IP Addresses — 95% internal, 5% external (benign)
    def pick_ip(branch: str) -> str:
        if rng.random() < 0.95:
            return random.choice(ip_pool["internal"][branch])
        return random.choice(ip_pool["external"])

    ip_addresses = [pick_ip(br) for br in sampled_emps["branch_id"]]

    # NLP columns — sparse: only ~2% of normal rows carry innocuous HR text
    n_with_text    = max(1, int(n * 0.02))
    text_indices   = rng.choice(n, size=n_with_text, replace=False)
    complaint_col  = [""] * n
    hr_col         = [""] * n

    benign_complaints = [
        "Customer requested KYC update.",
        "Account holder inquired about FD rates.",
        "Complaint regarding delay in NEFT credit.",
        "Customer requested cheque book.",
        "Service request for mobile banking registration.",
    ]
    benign_hr = [
        "Employee performance satisfactory this quarter.",
        "No disciplinary concerns.",
        "Attended mandatory AML training.",
        "Annual leave approved.",
        "",
    ]
    for idx in text_indices:
        complaint_col[idx] = random.choice(benign_complaints)
        hr_col[idx]        = random.choice(benign_hr)

    df = pd.DataFrame({
        "timestamp"         : timestamps,
        "transaction_id"    : [str(uuid.uuid4()) for _ in range(n)],
        "emp_id"            : sampled_emps["emp_id"].values,
        "emp_class"         : sampled_emps["emp_class"].values,
        "branch_id"         : sampled_emps["branch_id"].values,
        "action_type"       : actions,
        "amount"            : amounts,
        "account_touched"   : account_pool,
        "ip_address"        : ip_addresses,
        "raw_complaint_text": complaint_col,
        "hr_remark_text"    : hr_col,
        "is_fraud_flag"     : 0,
    })
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FRAUD SCENARIO INJECTORS
# ─────────────────────────────────────────────────────────────────────────────

def inject_maker_checker_collusion(employees: pd.DataFrame,
                                    ip_pool: dict,
                                    rng: np.random.Generator) -> pd.DataFrame:
    """
    SCENARIO 1 — Maker-Checker Collusion Ring
    ─────────────────────────────────────────
    A Clerk INITIATES a ₹5 Crore loan at 8:00 PM.
    A Manager APPROVES it exactly 40 seconds later.
    Normal review time: 8–20 minutes. 40 seconds is a red flag.

    Fraud signals:  
      • action_type=Initiate at 20:00:00 (after hours)
      • Paired Approve at 20:00:40 by a Manager (same branch)
      • amount = ₹5,00,00,000
      • Temporal proximity: review_time = 40s (normal = 480–1200s)
    """
    clerks   = employees[employees["emp_class"] == "CLERK"].sample(1, random_state=SEED)
    managers = employees[employees["emp_class"] == "MANAGER"].sample(1, random_state=SEED + 1)

    collusion_account = f"ACC_{rng.integers(5000, 6000)}"
    branch            = clerks.iloc[0]["branch_id"]
    initiate_ip       = random.choice(ip_pool["internal"][branch])
    approve_ip        = random.choice(ip_pool["internal"][branch])

    # Spread across multiple days in March (live stream window) for demo impact
    fraud_dates = [
        datetime(2026, 3, 5,  20, 0, 0),
        datetime(2026, 3, 12, 20, 0, 0),
        datetime(2026, 3, 19, 20, 0, 0),
    ]

    rows = []
    for base_ts in fraud_dates:
        clerk_row = {
            "timestamp"         : pd.Timestamp(base_ts),
            "transaction_id"    : str(uuid.uuid4()),
            "emp_id"            : clerks.iloc[0]["emp_id"],
            "emp_class"         : "CLERK",
            "branch_id"         : branch,
            "action_type"       : "Initiate",
            "amount"            : 50_000_000.0,       # ₹5 Crore
            "account_touched"   : collusion_account,
            "ip_address"        : initiate_ip,
            "raw_complaint_text": "",
            "hr_remark_text"    : "",
            "is_fraud_flag"     : 1,
        }
        manager_row = {
            "timestamp"         : pd.Timestamp(base_ts + timedelta(seconds=40)),
            "transaction_id"    : str(uuid.uuid4()),
            "emp_id"            : managers.iloc[0]["emp_id"],
            "emp_class"         : "MANAGER",
            "branch_id"         : branch,
            "action_type"       : "Approve",
            "amount"            : 50_000_000.0,
            "account_touched"   : collusion_account,
            "ip_address"        : approve_ip,
            "raw_complaint_text": "",
            "hr_remark_text"    : "",
            "is_fraud_flag"     : 1,
        }
        rows.extend([clerk_row, manager_row])

    return pd.DataFrame(rows)


def inject_midnight_harvest(employees: pd.DataFrame,
                             ip_pool: dict,
                             rng: np.random.Generator) -> pd.DataFrame:
    """
    SCENARIO 2 — Midnight Harvest (IT Admin Data Exfiltration)
    ───────────────────────────────────────────────────────────
    An IT Admin performs a massive DB_Read of 50,000 records
    at 2:47 AM from an EXTERNAL IP address (not an internal server).

    Fraud signals:
      • login_hour = 2 (deep night)
      • ip_address is EXTERNAL (not 10.x.x.x)
      • action_type = DB_Read
      • amount = 0 but records_accessed proxy = very high (encoded in hr_remark_text)
    """
    it_admins = employees[employees["emp_class"] == "IT_ADMIN"].sample(1, random_state=SEED + 2)
    exfil_ip  = random.choice(ip_pool["external"])

    fraud_dates = [
        datetime(2026, 3, 8,  2, 47, 13),
        datetime(2026, 3, 22, 2, 47, 55),
    ]

    rows = []
    for base_ts in fraud_dates:
        rows.append({
            "timestamp"         : pd.Timestamp(base_ts),
            "transaction_id"    : str(uuid.uuid4()),
            "emp_id"            : it_admins.iloc[0]["emp_id"],
            "emp_class"         : "IT_ADMIN",
            "branch_id"         : it_admins.iloc[0]["branch_id"],
            "action_type"       : "DB_Read",
            "amount"            : 0.0,
            "account_touched"   : "SYSTEM_BULK_EXPORT",
            "ip_address"        : exfil_ip,
            # Metadata about the bulk export encoded for Agent 4/6 NLP pickup
            "raw_complaint_text": "",
            "hr_remark_text"    : "ALERT: Unusual bulk export of 50000 customer records to external IP detected in system audit trail.",
            "is_fraud_flag"     : 1,
        })
    return pd.DataFrame(rows)


def inject_toxic_nlp_signal(employees: pd.DataFrame,
                             ip_pool: dict,
                             rng: np.random.Generator) -> pd.DataFrame:
    """
    SCENARIO 3 — Toxic NLP Signal (Bribe + Negative HR Remark)
    ────────────────────────────────────────────────────────────
    A Manager repeatedly touches the same account across multiple
    transactions. Customer complaint text contains bribery language.
    HR remark is independently negative — double NLP signal for Agent 4 & 6.

    Fraud signals:
      • Same account_touched repeated across multiple rows (pattern)
      • raw_complaint_text contains bribery keyword
      • hr_remark_text is negative / disciplinary
    """
    managers   = employees[employees["emp_class"] == "MANAGER"].sample(
        1, random_state=SEED + 3
    )
    mgr        = managers.iloc[0]
    branch     = mgr["branch_id"]
    mgr_ip     = random.choice(ip_pool["internal"][branch])
    toxic_acct = f"ACC_{rng.integers(7000, 8000)}"

    bribe_complaints = [
        "Customer reported that branch manager demanded bribe for loan approval. Amount: ₹50,000.",
        "Account holder complained: demanded bribe for loan approval and threatened to delay processing.",
        "Formal complaint filed — demanded bribe for loan approval, senior manager witness present.",
        "Manager demanded bribe for loan approval; customer refused and lodged written complaint.",
        "Second complaint this month: demanded bribe for loan approval from small business owner.",
    ]
    negative_hr = [
        "Employee under departmental inquiry for misconduct. Conduct unsatisfactory.",
        "Second written warning issued. Allegations of financial impropriety being investigated.",
        "Disciplinary proceedings initiated per Staff Regulation 14(3). Do not reassign.",
        "HR flagged for integrity review. Loan file irregularities noted by internal audit.",
        "Performance review withheld pending Ethics Committee decision.",
    ]

    fraud_dates = [
        datetime(2026, 3, 3,  14, 22, 0),
        datetime(2026, 3, 10, 15,  5, 0),
        datetime(2026, 3, 17, 11, 45, 0),
        datetime(2026, 3, 24, 16, 30, 0),
        datetime(2026, 3, 28, 14, 10, 0),
    ]

    rows = []
    for i, base_ts in enumerate(fraud_dates):
        rows.append({
            "timestamp"         : pd.Timestamp(base_ts),
            "transaction_id"    : str(uuid.uuid4()),
            "emp_id"            : mgr["emp_id"],
            "emp_class"         : "MANAGER",
            "branch_id"         : branch,
            "action_type"       : "Approve",
            "amount"            : float(rng.integers(200_000, 800_000)),
            "account_touched"   : toxic_acct,
            "ip_address"        : mgr_ip,
            "raw_complaint_text": bribe_complaints[i % len(bribe_complaints)],
            "hr_remark_text"    : negative_hr[i % len(negative_hr)],
            "is_fraud_flag"     : 1,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# DATA SPLITTING
# ─────────────────────────────────────────────────────────────────────────────

def split_and_save(df: pd.DataFrame, output_dir: str) -> None:
    """
    Splits the full dataset into:
      1. historical_warmup_data.csv  →  Oct 2025 – Feb 2026
         Purpose: Pre-load into GNN (Agent 2/5) on backend startup so the
                  graph already knows entity relationships before the live
                  stream begins.

      2. live_demo_stream.csv        →  March 2026 only
         Purpose: Fed row-by-row through stream_simulator.py into Kafka.
                  Sorted by timestamp so events arrive in chronological order.
    """
    os.makedirs(output_dir, exist_ok=True)

    mask_historical = df["timestamp"] < HISTORICAL_CUTOFF
    historical      = df[mask_historical].sort_values("timestamp").reset_index(drop=True)
    live_stream     = df[~mask_historical].sort_values("timestamp").reset_index(drop=True)

    hist_path   = os.path.join(output_dir, "historical_warmup_data.csv")
    stream_path = os.path.join(output_dir, "live_demo_stream.csv")

    historical.to_csv(hist_path,   index=False)
    live_stream.to_csv(stream_path, index=False)

    print(f"\n{'─'*60}")
    print(f"  historical_warmup_data.csv  →  {len(historical):>6,} rows  (Oct 2025 – Feb 2026)")
    print(f"  live_demo_stream.csv        →  {len(live_stream):>6,} rows  (March 2026)")
    print(f"  Fraud rows (total)          →  {df['is_fraud_flag'].sum():>6,} rows")
    print(f"  Fraud in live stream        →  {live_stream['is_fraud_flag'].sum():>6,} rows")
    print(f"  Saved to: {output_dir}")
    print(f"{'─'*60}\n")


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_dataset(df: pd.DataFrame) -> None:
    """Sanity checks before saving. Raises AssertionError on failure."""
    assert len(df) == TOTAL_ROWS,               f"Expected {TOTAL_ROWS} rows, got {len(df)}"
    assert df["transaction_id"].nunique() == len(df), "Duplicate transaction IDs found!"
    assert df["is_fraud_flag"].isin([0, 1]).all(),    "is_fraud_flag must be binary"
    assert not df["timestamp"].isna().any(),           "Null timestamps found"
    assert not df["emp_id"].isna().any(),              "Null emp_ids found"
    assert "agent1_score"  not in df.columns,          "CRITICAL: agent scores must NOT be in raw data"
    assert "unified_score" not in df.columns,          "CRITICAL: unified_score must NOT be in raw data"
    assert "raw_complaint_text" in df.columns,         "NLP column 'raw_complaint_text' missing"
    assert "hr_remark_text"     in df.columns,         "NLP column 'hr_remark_text' missing"

    # Validate fraud scenarios
    fraud_df = df[df["is_fraud_flag"] == 1]
    assert (fraud_df["action_type"] == "Initiate").any(),  "Maker-Checker Initiate row missing"
    assert (fraud_df["action_type"] == "Approve").any(),   "Maker-Checker Approve row missing"
    assert (fraud_df["action_type"] == "DB_Read").any(),   "Midnight Harvest DB_Read row missing"
    assert fraud_df["raw_complaint_text"].str.contains("bribe", case=False).any(), \
        "Toxic NLP bribe signal missing"

    print("  ✅  All validation checks passed.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═"*60)
    print("  VaultMind 2.0 — Data Generator v1.0")
    print("  Target: 50,000 rows | 500 employees | 6 months")
    print("═"*60)

    rng = np.random.default_rng(SEED)

    # ── Step 1: Build employee master ──────────────────────────────────────
    print("\n[1/5] Building employee master table...")
    employees = build_employee_master(N_EMPLOYEES)
    print(f"      {len(employees)} employees created  |  "
          f"Clerks: {(employees['emp_class']=='CLERK').sum()}  "
          f"Managers: {(employees['emp_class']=='MANAGER').sum()}  "
          f"IT Admins: {(employees['emp_class']=='IT_ADMIN').sum()}")

    # ── Step 2: Build IP pool ──────────────────────────────────────────────
    print("\n[2/5] Building IP address pool...")
    ip_pool = build_ip_pool()
    print(f"      Internal subnets: {len(ip_pool['internal'])}  |  External IPs: {len(ip_pool['external'])}")

    # ── Step 3: Generate fraud rows ────────────────────────────────────────
    print("\n[3/5] Injecting fraud scenarios...")

    df_collusion  = inject_maker_checker_collusion(employees, ip_pool, rng)
    df_midnight   = inject_midnight_harvest(employees, ip_pool, rng)
    df_toxic_nlp  = inject_toxic_nlp_signal(employees, ip_pool, rng)

    df_fraud      = pd.concat([df_collusion, df_midnight, df_toxic_nlp], ignore_index=True)
    n_fraud       = len(df_fraud)

    print(f"      Scenario 1 — Maker-Checker Collusion : {len(df_collusion)} rows")
    print(f"      Scenario 2 — Midnight Harvest        : {len(df_midnight)} rows")
    print(f"      Scenario 3 — Toxic NLP Signal        : {len(df_toxic_nlp)} rows")
    print(f"      Total fraud rows injected             : {n_fraud}")

    # ── Step 4: Generate normal transactions ───────────────────────────────
    n_normal = TOTAL_ROWS - n_fraud
    print(f"\n[4/5] Generating {n_normal:,} normal transactions (vectorized)...")
    df_normal = build_normal_transactions(employees, ip_pool, n_normal, rng)
    print(f"      Done. Normal rows: {len(df_normal):,}")

    # ── Step 5: Combine, validate, sort, split, save ───────────────────────
    print("\n[5/5] Combining, validating, and saving...")

    df_final = pd.concat([df_normal, df_fraud], ignore_index=True)
    df_final  = df_final.sort_values("timestamp").reset_index(drop=True)

    # Enforce column order
    column_order = [
        "timestamp", "transaction_id", "emp_id", "emp_class", "branch_id",
        "action_type", "amount", "account_touched", "ip_address",
        "raw_complaint_text", "hr_remark_text", "is_fraud_flag",
    ]
    df_final = df_final[column_order]

    validate_dataset(df_final)
    split_and_save(df_final, OUTPUT_DIR)

    print(f"  Total rows generated     : {len(df_final):,}")
    print(f"  Date range               : {df_final['timestamp'].min()} → {df_final['timestamp'].max()}")
    print(f"  Unique employees covered : {df_final['emp_id'].nunique()}")
    print(f"  Fraud rate               : {df_final['is_fraud_flag'].mean()*100:.2f}%")
    print(f"\n  ✅  Generation complete.\n")


if __name__ == "__main__":
    main()
