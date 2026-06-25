import sys, os, time, re

path = r'd:\VaultMind\scripts\data_generator_v2.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. SEED
content = content.replace('SEED              = 42',
'''import sys, time
try:
    SEED = int(sys.argv[sys.argv.index('--seed') + 1])
except (ValueError, IndexError):
    SEED = int(os.getenv("VAULTMIND_SEED", str(int(time.time()))))''')

# 2. IT_ADMIN amounts
old_amounts = '''    amounts = np.where(emps["emp_class"].values == "IT_ADMIN", 0.0,
                       np.round(rng.uniform(lo, hi), 2))'''
new_amounts = '''    it_admin_mask = emps["emp_class"].values == "IT_ADMIN"
    it_admin_amounts = np.round(np.clip(rng.lognormal(mean=6, sigma=1, size=it_admin_mask.sum()), 0, 50000), 2)
    amounts = np.round(rng.uniform(lo, hi), 2)
    amounts[it_admin_mask] = it_admin_amounts'''
content = content.replace(old_amounts, new_amounts)

# 3. New columns in build_normal_transactions
old_return = '''    return pd.DataFrame({
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
    })'''
new_return = '''    def compute_dwell(act, emp_cls):
        if act in ["SYSTEM_BULK_EXPORT", "DB_Read"] and emp_cls == "IT_ADMIN":
            return np.round(rng.uniform(0.001, 0.01), 4)
        elif act in ["Fund_Transfer", "Loan_Disbursal"]:
            return np.round(rng.uniform(60, 300), 2)
        else:
            return np.round(rng.uniform(30, 180), 2)

    def compute_records(act, emp_cls):
        if emp_cls == "IT_ADMIN":
            return int(rng.integers(5000, 100001))
        elif emp_cls == "MANAGER":
            return int(rng.integers(15, 51))
        else:
            return int(rng.integers(80, 151))
            
    dwells = [compute_dwell(a, r) for a, r in zip(actions, emps["emp_class"].values)]
    recs = [compute_records(a, r) for a, r in zip(actions, emps["emp_class"].values)]
    dest_acc = [f"ACC_{rng.integers(1000,9999)}" for _ in range(n)]

    return pd.DataFrame({
        "timestamp":          timestamps,
        "transaction_id":     [str(uuid.uuid4()) for _ in range(n)],
        "emp_id":             emps["emp_id"].values,
        "emp_class":          emps["emp_class"].values,
        "branch_id":          emps["branch_id"].values,
        "action_type":        actions,
        "amount":             amounts,
        "account_touched":    [f"ACC_{rng.integers(1000,9999)}" for _ in range(n)],
        "destination_account": dest_acc,
        "ip_address":         [pick_ip(br) for br in emps["branch_id"]],
        "transfer_channel":   channels,
        "records_accessed":   recs,
        "dwell_time_seconds": dwells,
        "raw_complaint_text": complaint_col,
        "hr_remark_text":     hr_col,
        "is_fraud_flag":      0,
    })'''
content = content.replace(old_return, new_return)

# 4. Remove random_state=SEED+...
content = re.sub(r'\.sample\((\d+),\s*random_state=SEED\+\d+\)', r'.sample(\1)', content)
content = re.sub(r'\.sample\((\d+),\s*random_state=SEED\)', r'.sample(\1)', content)

# 5. Add columns to S1-S6 returns
new_keys = r'"destination_account": f"ACC_{rng.integers(5000,6000)}", "records_accessed": int(rng.integers(2000, 5001)), "dwell_time_seconds": round(float(rng.uniform(45, 180)), 2), "is_fraud_flag": 1'
content = content.replace('"is_fraud_flag": 1', new_keys)

# 6. Column Order
old_cols = '''COLUMN_ORDER = [
    "timestamp", "transaction_id", "emp_id", "emp_class", "branch_id",
    "action_type", "amount", "account_touched", "ip_address", "transfer_channel",
    "raw_complaint_text", "hr_remark_text", "is_fraud_flag",
]'''
new_cols = '''COLUMN_ORDER = [
    "timestamp", "transaction_id", "emp_id", "emp_class", "branch_id",
    "action_type", "amount", "account_touched", "destination_account", "ip_address", "transfer_channel",
    "records_accessed", "dwell_time_seconds",
    "raw_complaint_text", "hr_remark_text", "is_fraud_flag",
]'''
content = content.replace(old_cols, new_cols)

# 7. Add assertion fix for destination_account in validate
old_val = '''    assert "transfer_channel" in df.columns,          "transfer_channel missing"'''
new_val = '''    assert "transfer_channel" in df.columns,          "transfer_channel missing"
    assert "destination_account" in df.columns,       "destination_account missing"
    assert "dwell_time_seconds" in df.columns,        "dwell_time_seconds missing"
    assert "records_accessed" in df.columns,          "records_accessed missing"'''
content = content.replace(old_val, new_val)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched successfully!")
