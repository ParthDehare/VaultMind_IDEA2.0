import sys, os, re

path = r'd:\VaultMind\scripts\data_mutator.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Paths
old_paths = '''INPUT_DIR  = "/mnt/user-data/uploads"
OUTPUT_DIR = "/home/claude/vaultmind_production"'''
new_paths = '''BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_DIR = os.path.join(BASE_DIR, "..", "server", "data", "Training_data")
TEST_DIR = os.path.join(BASE_DIR, "Testing_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "server", "data", "vaultmind_production")'''
content = content.replace(old_paths, new_paths)

# 2. File loading
old_loading = '''employees   = pd.read_csv(f"{INPUT_DIR}/employees.csv")
login_logs  = pd.read_csv(f"{INPUT_DIR}/login_logs.csv")
access_logs = pd.read_csv(f"{INPUT_DIR}/access_logs.csv")
transactions= pd.read_csv(f"{INPUT_DIR}/transactions.csv")
warmup      = pd.read_csv(f"{INPUT_DIR}/historical_warmup_data.csv")
live_stream = pd.read_csv(f"{INPUT_DIR}/live_demo_stream.csv")'''
new_loading = '''employees   = pd.read_csv(f"{TRAIN_DIR}/employees.csv")
login_logs  = pd.read_csv(f"{TRAIN_DIR}/login_logs.csv")
access_logs = pd.read_csv(f"{TRAIN_DIR}/access_logs.csv")
transactions= pd.read_csv(f"{TRAIN_DIR}/transactions.csv")
warmup      = pd.read_csv(f"{TEST_DIR}/historical_warmup_data.csv")
live_stream = pd.read_csv(f"{TEST_DIR}/live_demo_stream.csv")'''
content = content.replace(old_loading, new_loading)

# 3. .sum() bug
old_sum = '''print(f"    Slow Boil (EMP_1050):        {(ls['emp_id']=='EMP_1050') & (ls['is_fraud_flag']==1)}.sum()")'''
new_sum = '''print(f"    Slow Boil (EMP_SLOW_BOIL):        {((ls['emp_id']==EMP_SLOW_BOIL) & (ls['is_fraud_flag']==1)).sum()} rows")'''
content = content.replace(old_sum, new_sum)
content = content.replace('''print(f"    Structuring (EMP_1089):       {((ls['emp_id']=='EMP_1089') & (ls['is_fraud_flag']==1)).sum()} rows")''',
                          '''print(f"    Structuring (EMP_STRUCTURING):       {((ls['emp_id']==EMP_STRUCTURING) & (ls['is_fraud_flag']==1)).sum()} rows")''')
content = content.replace('''print(f"    Privilege Escalation (EMP_1302): {((ls['emp_id']=='EMP_1302') & (ls['is_fraud_flag']==1)).sum()} rows")''',
                          '''print(f"    Privilege Escalation (EMP_PRIV_ESC): {((ls['emp_id']==EMP_PRIV_ESC) & (ls['is_fraud_flag']==1)).sum()} rows")''')
content = content.replace('''print(f"    Collusion (EMP_1219+1193):    {((ls['emp_id'].isin(['EMP_1219','EMP_1193'])) & (ls['is_fraud_flag']==1)).sum()} rows")''',
                          '''print(f"    Collusion (EMP_COLLUSION_CLERK+EMP_COLLUSION_MGR):    {((ls['emp_id'].isin([EMP_COLLUSION_CLERK, EMP_COLLUSION_MGR])) & (ls['is_fraud_flag']==1)).sum()} rows")''')


# 4. Dynamic sampling for fraudsters
old_scenario_a_start = '''# ── Fraud Injection: Scenario A — Slow Boil (Clerk gradually increasing volume) ──'''
new_scenario_a_start = '''# ── Dynamic Fraudsters ──
clerks = employees[employees['emp_class'] == 'CLERK']['emp_id'].tolist()
managers = employees[employees['emp_class'] == 'MANAGER']['emp_id'].tolist()
np.random.shuffle(clerks)
np.random.shuffle(managers)
EMP_SLOW_BOIL = clerks.pop()
EMP_STRUCTURING = clerks.pop()
EMP_PRIV_ESC = clerks.pop()
EMP_COLLUSION_CLERK = clerks.pop()
EMP_COLLUSION_MGR = managers.pop()
EMP_MIRAGE_1 = clerks.pop()

# ── Fraud Injection: Scenario A — Slow Boil (Clerk gradually increasing volume) ──'''
content = content.replace(old_scenario_a_start, new_scenario_a_start)

# Replace the hardcoded EMPs in the scenarios with the dynamic ones
content = content.replace("'EMP_1050'", "EMP_SLOW_BOIL")
content = content.replace("'EMP_1089'", "EMP_STRUCTURING")
content = content.replace("'EMP_1302'", "EMP_PRIV_ESC")
content = content.replace("('EMP_1219','CLERK','Initiate')", "(EMP_COLLUSION_CLERK,'CLERK','Initiate')")
content = content.replace("('EMP_1193','MANAGER','Approve')", "(EMP_COLLUSION_MGR,'MANAGER','Approve')")
content = content.replace("emp != 'EMP_1193'", "emp != EMP_COLLUSION_MGR")
content = content.replace("['EMP_1001', 'EMP_1050', 'EMP_1089', 'EMP_1219']", "[EMP_MIRAGE_1, EMP_SLOW_BOIL, EMP_STRUCTURING, EMP_COLLUSION_CLERK]")
content = content.replace("['EMP_1219','EMP_1193']", "[EMP_COLLUSION_CLERK, EMP_COLLUSION_MGR]")

# 5. Fix dataframe iterrows slow vectorization (plan says "vectorize iterrows")
old_dwell = '''def add_dwell_time(df):
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
    return dwell'''
new_dwell = '''def add_dwell_time(df):
    """Add dwell_time_seconds based on role, action type, and fraud flag."""
    n = len(df)
    dwell = np.round(np.random.uniform(30, 300, n), 1)
    
    is_fraud_mask = df.get('is_fraud_flag', 0) == 1
    dwell[is_fraud_mask] = np.round(np.random.uniform(45, 180, is_fraud_mask.sum()), 1)
    
    it_mask = (df.get('emp_class', '') == 'IT_ADMIN') & (df.get('action_type', '').isin(['SYSTEM_BULK_EXPORT', 'DB_Read']))
    dwell[it_mask] = np.round(np.random.uniform(0.001, 0.01, it_mask.sum()), 4)
    
    return dwell'''
content = content.replace(old_dwell, new_dwell)

old_records = '''def add_records_accessed(df):
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
    return records'''
new_records = '''def add_records_accessed(df):
    """Add records_accessed based on role and fraud flag."""
    n = len(df)
    records = np.random.randint(80, 151, n)
    
    is_fraud = df.get('is_fraud_flag', 0) == 1
    emp_class = df.get('emp_class', 'CLERK')
    
    records[(emp_class == 'CLERK') & is_fraud] = np.random.randint(2000, 5001, ((emp_class == 'CLERK') & is_fraud).sum())
    records[(emp_class == 'MANAGER') & ~is_fraud] = np.random.randint(15, 51, ((emp_class == 'MANAGER') & ~is_fraud).sum())
    records[(emp_class == 'MANAGER') & is_fraud] = np.random.randint(150, 500, ((emp_class == 'MANAGER') & is_fraud).sum())
    records[emp_class == 'IT_ADMIN'] = np.random.randint(5000, 100001, (emp_class == 'IT_ADMIN').sum())
    
    return records'''
content = content.replace(old_records, new_records)

# Add destination_account and transfer_channel
old_sb = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.5.100.99','''
new_sb = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'destination_account':  f'ACC_{np.random.randint(1000,9999)}',
        'transfer_channel':     'SYSTEM',
        'ip_address':           '10.5.100.99','''
content = content.replace(old_sb, new_sb)

old_st = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.12.50.77','''
new_st = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'destination_account':  f'ACC_{np.random.randint(1000,9999)}',
        'transfer_channel':     'IMPS',
        'ip_address':           '10.12.50.77','''
content = content.replace(old_st, new_st)

old_pr = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'ip_address':           '10.8.200.15','''
new_pr = '''        'account_touched':      f'ACC_{np.random.randint(1000,9999)}',
        'destination_account':  f'ACC_{np.random.randint(1000,9999)}',
        'transfer_channel':     'RTGS',
        'ip_address':           '10.8.200.15','''
content = content.replace(old_pr, new_pr)

old_co = '''            'account_touched':      f'ACC_{np.random.randint(5000,5099)}',
            'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}','''
new_co = '''            'account_touched':      f'ACC_{np.random.randint(5000,5099)}',
            'destination_account':  f'ACC_{np.random.randint(5000,5099)}',
            'transfer_channel':     'NEFT',
            'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}','''
content = content.replace(old_co, new_co)

old_mi = '''        'account_touched':      mirage_id,
        'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}','''
new_mi = '''        'account_touched':      mirage_id,
        'destination_account':  mirage_id,
        'transfer_channel':     'SYSTEM',
        'ip_address':           f'10.{np.random.randint(1,20)}.{np.random.randint(1,250)}.{np.random.randint(1,250)}','''
content = content.replace(old_mi, new_mi)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Mutator patched successfully!")
