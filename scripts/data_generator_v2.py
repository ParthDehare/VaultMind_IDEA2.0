"""
VaultMind 2.0 - Data Generator v2.0
Fixes: ~2% fraud rate | 6 fraud scenarios | transfer_channel | peer_cluster
       Zero-Day Loan (Agent1) | ATM_Withdrawal (Agent6) | NLP label integrity
Output: Testing_data/{historical_warmup_data.csv, live_demo_stream.csv, employees_master.csv}
"""

import os, uuid, random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

SEED              = 42
TOTAL_ROWS        = 50_000
N_EMPLOYEES       = 500
SIM_START         = datetime(2025, 10, 1)
SIM_END           = datetime(2026, 3, 31, 23, 59, 59)
HISTORICAL_CUTOFF = datetime(2026, 3, 1)
OUTPUT_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Testing_data")

random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IN")
fake.seed_instance(SEED)

# ── Helpers ───────────────────────────────────────────────────────────────────

def rand_date(start: datetime, end: datetime) -> datetime:
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))

def spread_dates(n: int, start: datetime = SIM_START, end: datetime = SIM_END) -> list:
    step = (end - start).days / n
    return [start + timedelta(days=int(i * step), hours=random.randint(8, 20),
                              minutes=random.randint(0, 59)) for i in range(n)]

def get_transfer_channel(action: str, amount: float) -> str:
    if action in ("System_Login", "DB_Read"):
        return "SYSTEM"
    if action == "ATM_Withdrawal":
        return "ATM"
    if amount < 10_000:
        return random.choice(["UPI", "IMPS"])
    elif amount < 200_000:
        return random.choice(["UPI", "NEFT", "IMPS"])
    else:
        return random.choice(["NEFT", "RTGS"])

# ── Employee Master ───────────────────────────────────────────────────────────

def build_employees(n: int) -> pd.DataFrame:
    roles = (["CLERK"] * int(n * 0.70) +
             ["MANAGER"] * int(n * 0.25) +
             ["IT_ADMIN"] * (n - int(n * 0.70) - int(n * 0.25)))
    random.shuffle(roles)
    return pd.DataFrame({
        "emp_id":        [f"EMP_{1000 + i}" for i in range(n)],
        "emp_class":     roles,
        "branch_id":     [f"BR_{random.randint(1,20):02d}" for _ in range(n)],
        "peer_cluster":  [random.randint(0, 14) for _ in range(n)],
        "work_start_hr": [random.randint(8, 10) for _ in range(n)],
        "work_end_hr":   [random.randint(17, 19) for _ in range(n)],
    })

# ── IP Pool ───────────────────────────────────────────────────────────────────

def build_ip_pool() -> dict:
    return {
        "internal": {f"BR_{b:02d}": [f"10.{b}.{random.randint(0,255)}.{random.randint(1,254)}"
                                      for _ in range(20)] for b in range(1, 21)},
        "external": [fake.ipv4_public() for _ in range(15)],
    }

# ── Normal Transactions ───────────────────────────────────────────────────────

ACTION_BY_ROLE = {
    "CLERK":    ["Initiate", "DB_Read", "System_Login"],
    "MANAGER":  ["Approve",  "DB_Read", "System_Login", "Initiate"],
    "IT_ADMIN": ["DB_Read",  "System_Login"],
}
AMOUNT_RANGE = {
    "CLERK":    (1_000,    500_000),
    "MANAGER":  (50_000, 3_000_000),
    "IT_ADMIN": (0, 0),
}
BENIGN_COMPLAINTS = [
    "Customer requested KYC update.",
    "Account holder inquired about FD rates.",
    "Complaint regarding delay in NEFT credit.",
    "Customer requested cheque book.",
    "Service request for mobile banking registration.",
    "Request for account statement for visa application.",
    "Customer asked about locker facility availability.",
]
BENIGN_HR = [
    "Employee performance satisfactory this quarter.",
    "No disciplinary concerns.",
    "Attended mandatory AML training.",
    "Annual leave approved.",
    "",
]

def build_normal_transactions(employees: pd.DataFrame, ip_pool: dict,
                               n: int, rng: np.random.Generator) -> pd.DataFrame:
    weight_map  = {"CLERK": 0.65, "MANAGER": 0.25, "IT_ADMIN": 0.10}
    weights     = employees["emp_class"].map(weight_map).values
    weights     = weights / weights.sum()
    idx         = rng.choice(len(employees), size=n, p=weights)
    emps        = employees.iloc[idx].reset_index(drop=True)

    timestamps = []
    for i in range(n):
        row    = emps.iloc[i]
        offset = rng.integers(0, (SIM_END - SIM_START).days)
        base   = SIM_START + timedelta(days=int(offset))
        if rng.random() < 0.90:
            hr = rng.integers(row["work_start_hr"], row["work_end_hr"] + 1)
        else:
            hr = rng.integers(row["work_end_hr"] + 1, row["work_end_hr"] + 3)
        timestamps.append(pd.Timestamp(base.replace(hour=int(hr),
                                                     minute=int(rng.integers(0,60)),
                                                     second=int(rng.integers(0,60)))))

    actions = [random.choice(ACTION_BY_ROLE[r]) for r in emps["emp_class"]]
    lo = emps["emp_class"].map(lambda r: AMOUNT_RANGE[r][0]).values.astype(float)
    hi = emps["emp_class"].map(lambda r: AMOUNT_RANGE[r][1]).values.astype(float)
    amounts = np.where(emps["emp_class"].values == "IT_ADMIN", 0.0,
                       np.round(rng.uniform(lo, hi), 2))

    def pick_ip(branch):
        return (random.choice(ip_pool["internal"][branch]) if rng.random() < 0.95
                else random.choice(ip_pool["external"]))

    complaint_col = [""] * n
    hr_col        = [""] * n
    text_idx      = rng.choice(n, size=max(1, int(n * 0.02)), replace=False)
    for i in text_idx:
        complaint_col[i] = random.choice(BENIGN_COMPLAINTS)
        hr_col[i]        = random.choice(BENIGN_HR)

    channels = [get_transfer_channel(a, amt) for a, amt in zip(actions, amounts)]

    return pd.DataFrame({
        "timestamp":          timestamps,
        "transaction_id":     [str(uuid.uuid4()) for _ in range(n)],
        "emp_id":             emps["emp_id"].values,
        "emp_class":          emps["emp_class"].values,
        "branch_id":          emps["branch_id"].values,
        "action_type":        actions,
        "amount":             amounts,
        "account_touched":    [f"ACC_{rng.integers(1000,9999)}" for _ in range(n)],
        "ip_address":         [pick_ip(br) for br in emps["branch_id"]],
        "transfer_channel":   channels,
        "raw_complaint_text": complaint_col,
        "hr_remark_text":     hr_col,
        "is_fraud_flag":      0,
    })

# ── FRAUD SCENARIO 1: Maker-Checker Collusion ─────────────────────────────────

def inject_maker_checker(employees, ip_pool, rng, n_instances=20):
    clerk   = employees[employees["emp_class"] == "CLERK"].sample(1, random_state=SEED).iloc[0]
    manager = employees[employees["emp_class"] == "MANAGER"].sample(1, random_state=SEED+1).iloc[0]
    branch  = clerk["branch_id"]
    acct    = f"ACC_{rng.integers(5000,6000)}"
    c_ip    = random.choice(ip_pool["internal"][branch])
    m_ip    = random.choice(ip_pool["internal"][branch])
    dates   = spread_dates(n_instances)
    rows    = []
    for ts in dates:
        base = datetime(ts.year, ts.month, ts.day, 20, 0, 0)
        rows.append({"timestamp": pd.Timestamp(base), "transaction_id": str(uuid.uuid4()),
                     "emp_id": clerk["emp_id"], "emp_class": "CLERK", "branch_id": branch,
                     "action_type": "Initiate", "amount": 50_000_000.0, "account_touched": acct,
                     "ip_address": c_ip, "transfer_channel": "RTGS",
                     "raw_complaint_text": "", "hr_remark_text": "", "is_fraud_flag": 1})
        rows.append({"timestamp": pd.Timestamp(base + timedelta(seconds=40)),
                     "transaction_id": str(uuid.uuid4()),
                     "emp_id": manager["emp_id"], "emp_class": "MANAGER", "branch_id": branch,
                     "action_type": "Approve", "amount": 50_000_000.0, "account_touched": acct,
                     "ip_address": m_ip, "transfer_channel": "RTGS",
                     "raw_complaint_text": "", "hr_remark_text": "", "is_fraud_flag": 1})
    return pd.DataFrame(rows)

# ── FRAUD SCENARIO 2: Midnight Harvest ───────────────────────────────────────

def inject_midnight_harvest(employees, ip_pool, rng, n_instances=15):
    admin  = employees[employees["emp_class"] == "IT_ADMIN"].sample(1, random_state=SEED+2).iloc[0]
    ex_ip  = random.choice(ip_pool["external"])
    dates  = spread_dates(n_instances)
    rows   = []
    for ts in dates:
        base = datetime(ts.year, ts.month, ts.day, 2, 47, random.randint(0, 59))
        rows.append({"timestamp": pd.Timestamp(base), "transaction_id": str(uuid.uuid4()),
                     "emp_id": admin["emp_id"], "emp_class": "IT_ADMIN",
                     "branch_id": admin["branch_id"], "action_type": "DB_Read",
                     "amount": 0.0, "account_touched": "SYSTEM_BULK_EXPORT",
                     "ip_address": ex_ip, "transfer_channel": "SYSTEM",
                     "raw_complaint_text": "",
                     "hr_remark_text": "ALERT: Bulk export of 50000 customer records to external IP.",
                     "is_fraud_flag": 1})
    return pd.DataFrame(rows)

# ── FRAUD SCENARIO 3: Toxic NLP Signal ───────────────────────────────────────

BRIBE_TEXTS = [
    "Customer reported that branch manager demanded bribe for loan approval. Amount: Rs.50,000.",
    "Account holder complained: demanded bribe and threatened to delay processing.",
    "Formal complaint filed — demanded bribe for loan approval, senior manager witness present.",
    "Manager demanded bribe; customer refused and lodged written complaint.",
    "Second complaint this month: demanded bribe from small business owner.",
    "Bribe demand confirmed by two witnesses. Police complaint filed by customer.",
    "Customer alleges manager extorted Rs.1 lakh before approving home loan.",
]
NEGATIVE_HR = [
    "Employee under departmental inquiry for misconduct. Conduct unsatisfactory.",
    "Second written warning issued. Allegations of financial impropriety under investigation.",
    "Disciplinary proceedings initiated per Staff Regulation 14(3). Do not reassign.",
    "HR flagged for integrity review. Loan file irregularities noted by internal audit.",
    "Performance review withheld pending Ethics Committee decision.",
]

def inject_toxic_nlp(employees, ip_pool, rng, n_instances=50):
    manager = employees[employees["emp_class"] == "MANAGER"].sample(1, random_state=SEED+3).iloc[0]
    branch  = manager["branch_id"]
    m_ip    = random.choice(ip_pool["internal"][branch])
    acct    = f"ACC_{rng.integers(7000,8000)}"
    dates   = spread_dates(n_instances)
    rows    = []
    for i, ts in enumerate(dates):
        base = datetime(ts.year, ts.month, ts.day, ts.hour, ts.minute, 0)
        rows.append({"timestamp": pd.Timestamp(base), "transaction_id": str(uuid.uuid4()),
                     "emp_id": manager["emp_id"], "emp_class": "MANAGER", "branch_id": branch,
                     "action_type": "Approve", "amount": float(rng.integers(200_000, 800_000)),
                     "account_touched": acct, "ip_address": m_ip, "transfer_channel": "NEFT",
                     "raw_complaint_text": BRIBE_TEXTS[i % len(BRIBE_TEXTS)],
                     "hr_remark_text": NEGATIVE_HR[i % len(NEGATIVE_HR)],
                     "is_fraud_flag": 1})
    return pd.DataFrame(rows)

# ── FRAUD SCENARIO 4: Zero-Day Loan Velocity (Agent 1 Primary Target) ─────────

def inject_zero_day_loan(employees, ip_pool, rng, n_bursts=25, loans_per_burst=15):
    """
    A clerk processes 15 loan initiations within 25 minutes (normal: 2-3/hour).
    One manager auto-approves all of them. Velocity anomaly = Agent 1 trigger.
    """
    clerks   = employees[employees["emp_class"] == "CLERK"].sample(3, random_state=SEED+4)
    managers = employees[employees["emp_class"] == "MANAGER"].sample(3, random_state=SEED+5)
    dates    = spread_dates(n_bursts)
    rows     = []
    for i, ts in enumerate(dates):
        clerk   = clerks.iloc[i % len(clerks)]
        manager = managers.iloc[i % len(managers)]
        branch  = clerk["branch_id"]
        c_ip    = random.choice(ip_pool["internal"][branch])
        m_ip    = random.choice(ip_pool["internal"][branch])
        base    = datetime(ts.year, ts.month, ts.day, ts.hour, 0, 0)
        for j in range(loans_per_burst):
            offset_sec = j * 100          # one loan every ~100 seconds → 25 min total
            acct = f"ACC_{rng.integers(2000,4000)}"
            amt  = float(rng.integers(500_000, 5_000_000))
            rows.append({
                "timestamp":          pd.Timestamp(base + timedelta(seconds=offset_sec)),
                "transaction_id":     str(uuid.uuid4()),
                "emp_id":             clerk["emp_id"],
                "emp_class":          "CLERK",
                "branch_id":          branch,
                "action_type":        "Initiate",
                "amount":             amt,
                "account_touched":    acct,
                "ip_address":         c_ip,
                "transfer_channel":   get_transfer_channel("Initiate", amt),
                "raw_complaint_text": "",
                "hr_remark_text":     "",
                "is_fraud_flag":      1,
            })
        # Manager rapid-approves all loans in the burst (one approval row)
        rows.append({
            "timestamp":          pd.Timestamp(base + timedelta(seconds=loans_per_burst * 100 + 30)),
            "transaction_id":     str(uuid.uuid4()),
            "emp_id":             manager["emp_id"],
            "emp_class":          "MANAGER",
            "branch_id":          branch,
            "action_type":        "Approve",
            "amount":             float(rng.integers(500_000, 5_000_000)),
            "account_touched":    f"ACC_{rng.integers(2000,4000)}",
            "ip_address":         m_ip,
            "transfer_channel":   "RTGS",
            "raw_complaint_text": "",
            "hr_remark_text":     "",
            "is_fraud_flag":      1,
        })
    return pd.DataFrame(rows)

# ── FRAUD SCENARIO 5: ATM Harvest / PMLA Structuring (Agent 6 Target) ─────────

ATM_VICTIM_ACCOUNTS = [f"CUST_ATM_{i:03d}" for i in range(1, 11)]

def inject_atm_harvest(employees, ip_pool, rng, n_events=35, withdrawals_per_event=8):
    """
    A watchlisted customer account shows 8 near-limit ATM withdrawals within 2 hours.
    Modeled as teller-processed ATM events linked to the employee who enabled access.
    This is the PMLA structuring pattern Agent 6 monitors.
    """
    clerks = employees[employees["emp_class"] == "CLERK"].sample(5, random_state=SEED+6)
    dates  = spread_dates(n_events)
    rows   = []
    for i, ts in enumerate(dates):
        clerk      = clerks.iloc[i % len(clerks)]
        branch     = clerk["branch_id"]
        c_ip       = random.choice(ip_pool["internal"][branch])
        victim_acc = ATM_VICTIM_ACCOUNTS[i % len(ATM_VICTIM_ACCOUNTS)]
        base       = datetime(ts.year, ts.month, ts.day, ts.hour, 0, 0)
        for j in range(withdrawals_per_event):
            amt = round(random.uniform(9_500, 10_000), 2)
            rows.append({
                "timestamp":          pd.Timestamp(base + timedelta(minutes=j * 14)),
                "transaction_id":     str(uuid.uuid4()),
                "emp_id":             clerk["emp_id"],
                "emp_class":          "CLERK",
                "branch_id":          branch,
                "action_type":        "ATM_Withdrawal",
                "amount":             amt,
                "account_touched":    victim_acc,
                "ip_address":         c_ip,
                "transfer_channel":   "ATM",
                "raw_complaint_text": "",
                "hr_remark_text":     "",
                "is_fraud_flag":      1,
            })
    return pd.DataFrame(rows)

# ── FRAUD SCENARIO 6: Ghost Layering / UPI Circular Flow (Agent 2 GNN Target) ─

def inject_ghost_layering(employees, ip_pool, rng, n_events=25, transfers_per_event=10):
    """
    An employee rapidly routes funds through a fixed small pool of accounts (layering).
    The GNN will detect the dense circular subgraph as a fraud cluster.
    """
    GHOST_ACCOUNTS = [f"ACC_{8000 + i}" for i in range(10)]
    clerks = employees[employees["emp_class"] == "CLERK"].sample(4, random_state=SEED+7)
    dates  = spread_dates(n_events)
    rows   = []
    for i, ts in enumerate(dates):
        clerk  = clerks.iloc[i % len(clerks)]
        branch = clerk["branch_id"]
        c_ip   = random.choice(ip_pool["internal"][branch])
        base   = datetime(ts.year, ts.month, ts.day, ts.hour, 0, 0)
        for j in range(transfers_per_event):
            amt = float(rng.integers(100_000, 500_000))
            rows.append({
                "timestamp":          pd.Timestamp(base + timedelta(minutes=j * 3)),
                "transaction_id":     str(uuid.uuid4()),
                "emp_id":             clerk["emp_id"],
                "emp_class":          "CLERK",
                "branch_id":          branch,
                "action_type":        "Initiate",
                "amount":             amt,
                "account_touched":    GHOST_ACCOUNTS[j % len(GHOST_ACCOUNTS)],
                "ip_address":         c_ip,
                "transfer_channel":   "UPI",
                "raw_complaint_text": "",
                "hr_remark_text":     "",
                "is_fraud_flag":      1,
            })
    return pd.DataFrame(rows)

# ── Split & Save ──────────────────────────────────────────────────────────────

COLUMN_ORDER = [
    "timestamp", "transaction_id", "emp_id", "emp_class", "branch_id",
    "action_type", "amount", "account_touched", "ip_address", "transfer_channel",
    "raw_complaint_text", "hr_remark_text", "is_fraud_flag",
]

def split_and_save(df: pd.DataFrame, employees: pd.DataFrame) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    mask_hist  = df["timestamp"] < HISTORICAL_CUTOFF
    historical = df[mask_hist].sort_values("timestamp").reset_index(drop=True)
    live       = df[~mask_hist].sort_values("timestamp").reset_index(drop=True)

    historical.to_csv(os.path.join(OUTPUT_DIR, "historical_warmup_data.csv"), index=False)
    live.to_csv(os.path.join(OUTPUT_DIR, "live_demo_stream.csv"), index=False)
    employees.to_csv(os.path.join(OUTPUT_DIR, "employees_master.csv"), index=False)

    print(f"\n  historical_warmup_data.csv : {len(historical):>7,} rows | "
          f"fraud: {historical['is_fraud_flag'].sum()}")
    print(f"  live_demo_stream.csv       : {len(live):>7,} rows | "
          f"fraud: {live['is_fraud_flag'].sum()}")
    print(f"  employees_master.csv       : {len(employees):>7,} rows")
    print(f"  Saved to: {OUTPUT_DIR}")

# ── Validation ────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> None:
    assert len(df) == TOTAL_ROWS,                   f"Row count {len(df)} != {TOTAL_ROWS}"
    assert df["transaction_id"].nunique() == len(df),"Duplicate transaction IDs"
    assert df["is_fraud_flag"].isin([0,1]).all(),    "Non-binary fraud flag"
    assert not df["timestamp"].isna().any(),          "Null timestamps"
    assert "transfer_channel" in df.columns,          "transfer_channel missing"
    assert "ATM_Withdrawal" in df["action_type"].values, "ATM_Withdrawal action missing"
    fraud_rate = df["is_fraud_flag"].mean()
    assert 0.01 <= fraud_rate <= 0.05,               f"Fraud rate {fraud_rate:.4f} out of 1-5% range"
    fraud_df = df[df["is_fraud_flag"] == 1]
    assert (fraud_df["action_type"] == "ATM_Withdrawal").any(), "ATM Harvest scenario missing"
    assert fraud_df["raw_complaint_text"].str.contains("bribe", case=False).any(), "Toxic NLP missing"
    # Zero-Day Loan: many Initiate rows close together in time
    zd = fraud_df[fraud_df["action_type"] == "Initiate"]
    assert len(zd) > 100,                            f"Zero-Day Loan rows too few: {len(zd)}"
    # NLP label leak check: normal rows must not have fraud complaint keywords
    normal_complaint = df[df["is_fraud_flag"] == 0]["raw_complaint_text"].fillna("")
    assert not normal_complaint.str.contains("fraud|bribe|unauthorized", case=False).any(), \
        "LABEL LEAK: fraud keywords found in normal rows!"
    print("  All validation checks passed.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  VaultMind 2.0 - Data Generator v2.0")
    print("  Target: 50,000 rows | ~2% fraud | 6 scenarios")
    print("=" * 65)

    rng       = np.random.default_rng(SEED)
    employees = build_employees(N_EMPLOYEES)
    ip_pool   = build_ip_pool()

    print(f"\n[1/4] Employees: {len(employees)} | "
          f"Clerks:{(employees['emp_class']=='CLERK').sum()} "
          f"Managers:{(employees['emp_class']=='MANAGER').sum()} "
          f"IT:{(employees['emp_class']=='IT_ADMIN').sum()}")

    print("\n[2/4] Injecting 6 fraud scenarios...")
    s1 = inject_maker_checker(employees, ip_pool, rng, n_instances=20)
    s2 = inject_midnight_harvest(employees, ip_pool, rng, n_instances=15)
    s3 = inject_toxic_nlp(employees, ip_pool, rng, n_instances=50)
    s4 = inject_zero_day_loan(employees, ip_pool, rng, n_bursts=25, loans_per_burst=15)
    s5 = inject_atm_harvest(employees, ip_pool, rng, n_events=35, withdrawals_per_event=8)
    s6 = inject_ghost_layering(employees, ip_pool, rng, n_events=25, transfers_per_event=10)

    df_fraud = pd.concat([s1,s2,s3,s4,s5,s6], ignore_index=True)
    print(f"  S1 Maker-Checker  : {len(s1):>4} rows")
    print(f"  S2 Midnight Harvest: {len(s2):>4} rows")
    print(f"  S3 Toxic NLP      : {len(s3):>4} rows")
    print(f"  S4 Zero-Day Loan  : {len(s4):>4} rows  <-- Agent 1 signal")
    print(f"  S5 ATM Harvest    : {len(s5):>4} rows  <-- Agent 6 signal")
    print(f"  S6 Ghost Layering : {len(s6):>4} rows  <-- Agent 2 GNN signal")
    print(f"  Total fraud       : {len(df_fraud):>4} rows  ({len(df_fraud)/TOTAL_ROWS*100:.2f}%)")

    n_normal = TOTAL_ROWS - len(df_fraud)
    print(f"\n[3/4] Generating {n_normal:,} normal transactions...")
    df_normal = build_normal_transactions(employees, ip_pool, n_normal, rng)

    print("\n[4/4] Combining, validating, splitting, saving...")
    df_final  = pd.concat([df_normal, df_fraud], ignore_index=True)
    df_final  = df_final.sort_values("timestamp").reset_index(drop=True)
    df_final  = df_final[COLUMN_ORDER]

    validate(df_final)
    split_and_save(df_final, employees)

    print(f"\n  Total rows   : {len(df_final):,}")
    print(f"  Fraud rate   : {df_final['is_fraud_flag'].mean()*100:.2f}%")
    print(f"  Date range   : {df_final['timestamp'].min()} -> {df_final['timestamp'].max()}")
    print(f"  Unique emps  : {df_final['emp_id'].nunique()}")
    print(f"\n  Generation complete.\n")

if __name__ == "__main__":
    main()
