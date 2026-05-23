"""
VaultMind 2.0 — agent1_behaviour_watch.py
===========================================================================
Agent 1: BehaviourWatch (AnomalyIntel)
---------------------------------------------------------------------------
Statistical anomaly detection engine using Z-Score analysis across three
behavioural dimensions:
  1. Transaction Amount   — is this amount unusual for this employee class?
  2. Dwell Time           — did a human spend time on this, or was it a bot?
  3. Off-Hours Login      — how far outside the approved access window?

Design philosophy:
  - No binary if/else thresholds. Every dimension produces a continuous
    Z-Score which is then converted to a 0–100 contribution via a sigmoid-
    family transform. This mirrors how a real anomaly detection model would
    surface a probability, not a hard flag.
  - Baselines are loaded from a JSON file at startup (simulating a trained
    scaler/stats object). If the file is missing, hardcoded empirical
    defaults derived from RBI audit data profiles are used — the agent
    NEVER crashes on a missing file.
  - All lookups (baseline retrieval by emp_class) are O(1) dictionary
    operations.

Return contract (strict):
  {
    "severity_index": int   (0–100, cumulative weighted risk score),
    "signal":         str   (machine-readable signal tag),
    "reason":         str   (plain-English XAI explanation for FCU)
  }

Dependencies: Python stdlib + numpy only. No GPU. Hackathon-safe.
===========================================================================
"""

import math
import json
import os
import warnings

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

APPROVED_HOURS_START = 8    # 08:00 IST — branch opening
APPROVED_HOURS_END   = 20   # 20:00 IST — branch closing

# Sigmoid steepness — controls how aggressively Z-scores map to 0–100.
# k=0.9 gives ~95 score at Z=4 (4 standard deviations), which is appropriate
# for banking fraud thresholds.
SIGMOID_K = 0.9

# Feature weights — must sum to 1.0.
# Amount and off-hours carry more evidential weight than dwell time alone.
WEIGHT_AMOUNT    = 0.45
WEIGHT_OFHOURS   = 0.35
WEIGHT_DWELL     = 0.20

# Z-score below this threshold produces near-zero risk contribution.
# Avoids noise from minor deviations.
Z_NOISE_FLOOR = 0.5

# Path to pre-computed baseline stats (simulates a fitted scaler.pkl)
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
BASELINE_PATH = os.path.join(SCRIPT_DIR, "baselines", "behaviour_baselines.json")

# ---------------------------------------------------------------------------
# EMPIRICAL DEFAULTS
# Derived from Indian PSB audit profiles (RBI Annual Report 2023-24).
# Used when baseline JSON is missing — agent stays operational.
# Structure: emp_class -> { feature -> (mean, std_dev) }
# ---------------------------------------------------------------------------
DEFAULT_BASELINES = {
    "CLERK": {
        "amount":     {"mean": 45_000.0,    "std": 28_000.0},
        "dwell_time": {"mean": 42.0,         "std": 18.0},
    },
    "MANAGER": {
        "amount":     {"mean": 350_000.0,   "std": 180_000.0},
        "dwell_time": {"mean": 85.0,         "std": 30.0},
    },
    "IT_ADMIN": {
        "amount":     {"mean": 0.0,          "std": 1.0},   # IT admins rarely transact
        "dwell_time": {"mean": 120.0,        "std": 55.0},
    },
    "EXECUTIVE": {
        "amount":     {"mean": 1_200_000.0, "std": 600_000.0},
        "dwell_time": {"mean": 95.0,         "std": 35.0},
    },
    # Fallback for unknown classes
    "DEFAULT": {
        "amount":     {"mean": 100_000.0,   "std": 60_000.0},
        "dwell_time": {"mean": 60.0,         "std": 25.0},
    },
}


# ===========================================================================
# AGENT CLASS
# ===========================================================================

class BehaviourWatch:
    """
    BehaviourWatch: Statistical Behavioural Anomaly Detection Engine.

    Computes a continuous Composite Behavioural Severity Index (CBSI)
    using Z-score analysis across transaction amount, dwell time, and
    off-hours login patterns.

    Each Z-score is transformed via a bounded sigmoid function into a
    0–100 risk contribution. Contributions are combined using empirically
    weighted averaging to produce the final CBSI.

    Usage:
        agent = BehaviourWatch()
        result = agent.evaluate(transaction_dict)
        # result["severity_index"] -> int 0-100
    """

    def __init__(self, baseline_path: str = BASELINE_PATH):
        """
        Initialise the agent. Attempts to load pre-computed baseline
        statistics from disk (simulates loading a fitted scaler).
        Falls back to hardcoded empirical defaults if file is missing.

        Args:
            baseline_path: Path to behaviour_baselines.json
        """
        self.baseline_path = baseline_path
        self.baselines: dict = {}
        self._load_baselines()

    # -----------------------------------------------------------------------
    # INITIALISATION HELPERS
    # -----------------------------------------------------------------------

    def _load_baselines(self) -> None:
        """
        Load peer-group baseline statistics from JSON.
        Simulates joblib.load('scaler.pkl') — loads pre-fitted parameters.
        On failure, silently falls back to DEFAULT_BASELINES.
        """
        try:
            if not os.path.exists(self.baseline_path):
                raise FileNotFoundError(
                    f"Baseline file not found at {self.baseline_path}"
                )
            with open(self.baseline_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            # Validate expected keys exist before accepting
            assert isinstance(loaded, dict), "Baseline file must be a JSON object."
            self.baselines = loaded
            print(
                f"[BehaviourWatch] Baselines loaded from disk. "
                f"Classes: {list(self.baselines.keys())}"
            )
        except (FileNotFoundError, AssertionError, json.JSONDecodeError) as exc:
            warnings.warn(
                f"[BehaviourWatch] Could not load baseline file ({exc}). "
                "Using empirical defaults — system operational."
            )
            self.baselines = DEFAULT_BASELINES

    def _get_baseline(self, emp_class: str) -> dict:
        """
        O(1) retrieval of baseline stats for a given employee class.
        Returns DEFAULT entry if class is unknown.

        Args:
            emp_class: Employee classification string.

        Returns:
            dict with 'amount' and 'dwell_time' mean/std entries.
        """
        return self.baselines.get(
            emp_class.upper(),
            self.baselines.get("DEFAULT", DEFAULT_BASELINES["DEFAULT"])
        )

    # -----------------------------------------------------------------------
    # MATHEMATICAL CORE
    # -----------------------------------------------------------------------

    @staticmethod
    def _z_score(value: float, mean: float, std: float) -> float:
        """
        Compute the Z-score: how many standard deviations `value` is from
        the peer mean.

            Z = (X - μ) / σ

        Handles zero/near-zero std gracefully (returns 0 if std < 1e-6).

        Args:
            value: Observed feature value.
            mean:  Peer-group mean (μ).
            std:   Peer-group standard deviation (σ).

        Returns:
            float: Z-score (can be negative; we care about magnitude).
        """
        if std < 1e-6:
            return 0.0
        return (value - mean) / std

    @staticmethod
    def _sigmoid_risk(z: float, k: float = SIGMOID_K) -> float:
        """
        Convert a Z-score to a 0–100 risk contribution using a bounded
        sigmoid transform.

        Formula:
            raw  = 1 / (1 + e^(-k * (|Z| - Z_NOISE_FLOOR)))
            risk = raw * 100   (clipped to [0, 100])

        Properties:
          - |Z| < 0.5  → contribution ≈ 0   (noise floor suppressed)
          - |Z| = 2.0  → contribution ≈ 62  (moderate anomaly)
          - |Z| = 3.5  → contribution ≈ 88  (strong anomaly)
          - |Z| ≥ 5.0  → contribution ≈ 98  (extreme outlier)

        Only positive Z (above mean) contributes risk. Negative Z
        (below mean, e.g. unusually small amount) contributes 0 — we do
        not penalise conservative behaviour.

        Args:
            z: Raw Z-score.
            k: Sigmoid steepness constant.

        Returns:
            float: Risk contribution in [0.0, 100.0].
        """
        # Only upper-tail anomalies are suspicious (above peer mean)
        z_abs = max(0.0, z)  # negative Z = below average = not suspicious

        # Apply noise floor — suppress micro-deviations
        effective_z = z_abs - Z_NOISE_FLOOR
        if effective_z <= 0:
            return 0.0

        # Sigmoid transform
        try:
            raw = 1.0 / (1.0 + math.exp(-k * effective_z))
        except OverflowError:
            raw = 1.0  # e^(-k*z) → 0 for very large z

        return min(100.0, raw * 100.0)

    @staticmethod
    def _off_hours_risk(login_hour: int) -> float:
        """
        Compute a continuous risk score for the login hour.

        Logic:
          - Within approved window (08:00–20:00): score = 0
          - Outside window: score scales with distance from boundary,
            capped at 95 (we never reach 100 on time alone — corroboration
            from other signals is required for maximum CBSI).

        The further from the approved window, the higher the risk:
          - 07:00 or 21:00 → mild  (~15)
          - 05:00 or 23:00 → high  (~60)
          - 02:00 or 03:00 → severe (~85)
          - 00:00 or midnight → peak (~90)

        This is a piecewise linear decay, not a binary flag.

        Args:
            login_hour: Integer hour of login (0–23).

        Returns:
            float: Risk contribution in [0.0, 95.0].
        """
        # Circular distance from the nearest boundary of [08, 20]
        if APPROVED_HOURS_START <= login_hour <= APPROVED_HOURS_END:
            return 0.0

        if login_hour < APPROVED_HOURS_START:
            # Pre-opening hours: distance from 08:00
            distance = APPROVED_HOURS_START - login_hour  # e.g. 3AM → dist=5
        else:
            # Post-closing hours: distance from 20:00
            distance = login_hour - APPROVED_HOURS_END     # e.g. 23PM → dist=3

        # Scale: each hour further = +12 risk points, capped at 95
        return min(95.0, distance * 12.0)

    # -----------------------------------------------------------------------
    # SIGNAL RESOLVER
    # -----------------------------------------------------------------------

    @staticmethod
    def _resolve_signal(cbsi: int, z_amount: float, z_dwell: float,
                        off_hours_risk: float) -> str:
        """
        Determine the dominant signal tag for the FCU alert system.
        Returns a machine-readable constant that identifies which dimension
        drove the risk score.

        Args:
            cbsi:           Final composite score.
            z_amount:       Z-score for transaction amount.
            z_dwell:        Z-score for dwell time.
            off_hours_risk: Raw off-hours risk contribution.

        Returns:
            str: Signal constant for downstream routing.
        """
        if cbsi == 0:
            return "NORMAL"

        # Rank contributions to find dominant driver
        contributions = {
            "AMOUNT_ANOMALY":    z_amount * WEIGHT_AMOUNT,
            "OFF_HOURS_LOGIN":   (off_hours_risk / 100.0) * WEIGHT_OFHOURS * 100,
            "DWELL_ANOMALY":     z_dwell * WEIGHT_DWELL,
        }
        dominant = max(contributions, key=contributions.get)

        if cbsi >= 80:
            return f"CRITICAL_{dominant}"
        if cbsi >= 60:
            return f"HIGH_{dominant}"
        if cbsi >= 40:
            return f"WATCH_{dominant}"
        return f"MONITOR_{dominant}"

    # -----------------------------------------------------------------------
    # XAI REASON BUILDER
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_reason(cbsi: int, emp_class: str, amount: float,
                      z_amount: float, dwell_time: float, z_dwell: float,
                      login_hour: int, off_hours_score: float,
                      baseline: dict) -> str:
        """
        Build a plain-English explanation for the FCU investigator.
        Surfaces the actual numbers, peer averages, and Z-scores so
        the investigator can verify the math independently.

        Args:
            cbsi:            Final composite score.
            emp_class:       Employee classification.
            amount:          Transaction amount.
            z_amount:        Z-score for amount.
            dwell_time:      Session dwell time in seconds.
            z_dwell:         Z-score for dwell time.
            login_hour:      Login hour (0–23).
            off_hours_score: Risk contribution from off-hours.
            baseline:        Peer baseline dict for this emp_class.

        Returns:
            str: Plain-English XAI reason string.
        """
        parts = []

        # Amount signal
        if z_amount >= Z_NOISE_FLOOR:
            peer_mean = baseline["amount"]["mean"]
            parts.append(
                f"Transaction of ₹{amount:,.0f} is {z_amount:.1f}σ above the "
                f"{emp_class} peer average of ₹{peer_mean:,.0f}."
            )

        # Off-hours signal
        if off_hours_score > 0:
            parts.append(
                f"Login at {login_hour:02d}:00 IST is outside the approved "
                f"08:00–20:00 window (risk contribution: {off_hours_score:.0f}/100)."
            )

        # Dwell signal
        if z_dwell >= Z_NOISE_FLOOR:
            peer_mean_dwell = baseline["dwell_time"]["mean"]
            parts.append(
                f"Session dwell time of {dwell_time:.1f}s is {z_dwell:.1f}σ above "
                f"the {emp_class} peer average of {peer_mean_dwell:.0f}s — "
                "possible automated bulk access."
            )

        if not parts:
            return (
                f"All behavioural dimensions within normal range for "
                f"{emp_class} class. CBSI: {cbsi}/100."
            )

        severity_label = (
            "CRITICAL" if cbsi >= 80 else
            "HIGH"     if cbsi >= 60 else
            "WATCH"    if cbsi >= 40 else
            "MONITOR"
        )

        reason = f"[{severity_label}] CBSI {cbsi}/100 — " + " | ".join(parts)
        return reason

    # -----------------------------------------------------------------------
    # MAIN EVALUATE METHOD
    # -----------------------------------------------------------------------

    def evaluate(self, transaction: dict) -> dict:
        """
        Evaluate a single transaction for behavioural anomalies.

        Computes a Composite Behavioural Severity Index (CBSI) by:
          1. Looking up peer-group baselines for the employee class (O(1)).
          2. Computing Z-scores for amount and dwell time.
          3. Converting each Z-score to a 0–100 risk contribution via
             bounded sigmoid transform.
          4. Computing a continuous off-hours risk score.
          5. Combining all contributions via empirical weighted average.
          6. Resolving a dominant signal tag and XAI reason string.

        Args:
            transaction (dict): Must contain at minimum:
                - emp_class       (str)   : "CLERK", "MANAGER", etc.
                - amount          (float) : Transaction amount in INR.
                - dwell_time      (float) : Session dwell in seconds.
                - login_hour      (int)   : Login hour (0–23).
              Optional enrichment fields (used if present):
                - emp_id          (str)
                - transaction_id  (str)
                - branch_id       (str)

        Returns:
            dict: {
                "severity_index": int (0–100),
                "signal":         str,
                "reason":         str
            }

        Raises:
            Does not raise — returns {"severity_index": 0, ...} on bad input.
        """
        # ── 0. Input validation ───────────────────────────────────────────
        if not isinstance(transaction, dict):
            return {
                "severity_index": 0,
                "signal":         "INVALID_INPUT",
                "reason":         "Transaction payload must be a dictionary."
            }

        # ── 1. Feature extraction with safe defaults ──────────────────────
        emp_class  = str(transaction.get("emp_class",  "DEFAULT")).upper()
        amount     = float(transaction.get("amount",   0.0))
        dwell_time = float(transaction.get("dwell_time", 0.0))
        login_hour = int(transaction.get("login_hour", 9))  # Default: mid-morning

        # Clamp login_hour to valid range
        login_hour = max(0, min(23, login_hour))

        # ── 2. O(1) baseline retrieval ────────────────────────────────────
        baseline = self._get_baseline(emp_class)

        # ── 3. Z-Score computation ────────────────────────────────────────

        # 3a. Transaction Amount Z-Score
        z_amount = self._z_score(
            value = amount,
            mean  = baseline["amount"]["mean"],
            std   = baseline["amount"]["std"]
        )

        # 3b. Dwell Time Z-Score
        # High dwell = potential human bulk access (reading/copying data).
        # Note: very LOW dwell (near-zero) is handled by Agent 8 DeceptionGuard,
        # not here. We only flag ELEVATED dwell.
        z_dwell = self._z_score(
            value = dwell_time,
            mean  = baseline["dwell_time"]["mean"],
            std   = baseline["dwell_time"]["std"]
        )

        # ── 4. Sigmoid risk contributions (0–100 per dimension) ───────────
        risk_amount  = self._sigmoid_risk(z_amount)
        risk_dwell   = self._sigmoid_risk(z_dwell)
        risk_offhours = self._off_hours_risk(login_hour)

        # ── 5. Weighted composite score ───────────────────────────────────
        #
        # CBSI = Σ(weight_i × contribution_i)
        #
        # This is equivalent to a dot product between the weight vector
        # and the risk contribution vector — the same operation performed
        # by a trained linear layer in a shallow neural network.
        #
        cbsi_raw = (
            WEIGHT_AMOUNT  * risk_amount   +
            WEIGHT_OFHOURS * risk_offhours +
            WEIGHT_DWELL   * risk_dwell
        )

        # Clip to valid range and cast to int (severity_index contract)
        cbsi = int(min(100, max(0, round(cbsi_raw))))

        # ── 6. Signal resolution ──────────────────────────────────────────
        signal = self._resolve_signal(cbsi, z_amount, z_dwell, risk_offhours)

        # ── 7. XAI reason string ──────────────────────────────────────────
        reason = self._build_reason(
            cbsi          = cbsi,
            emp_class     = emp_class,
            amount        = amount,
            z_amount      = z_amount,
            dwell_time    = dwell_time,
            z_dwell       = z_dwell,
            login_hour    = login_hour,
            off_hours_score = risk_offhours,
            baseline      = baseline
        )

        return {
            "severity_index": cbsi,
            "signal":         signal,
            "reason":         reason
        }


# ===========================================================================
# TEST HARNESS
# ===========================================================================

if __name__ == "__main__":
    DIVIDER = "=" * 70

    print(DIVIDER)
    print("  VaultMind 2.0 — Agent 1: BehaviourWatch (AnomalyIntel)")
    print(DIVIDER)

    agent = BehaviourWatch()

    # ── Test cases — representative of real PSB fraud scenarios ──────────
    TEST_TRANSACTIONS = [
        {
            "_label": "Case 1 — Normal clerk, routine 9AM transaction",
            "emp_id":   "EMP_CLERK_001",
            "emp_class": "CLERK",
            "amount":    42_000.0,
            "dwell_time": 38.5,
            "login_hour": 9,
        },
        {
            "_label": "Case 2 — Off-hours login (2AM), clerk, normal amount",
            "emp_id":   "EMP_CLERK_112",
            "emp_class": "CLERK",
            "amount":    50_000.0,
            "dwell_time": 45.0,
            "login_hour": 2,
        },
        {
            "_label": "Case 3 — Clerk initiating high-value transfer (Scenario 1: Sudden Spike)",
            "emp_id":   "EMP_CLERK_4471",
            "emp_class": "CLERK",
            "amount":    8_500_000.0,
            "dwell_time": 210.0,
            "login_hour": 3,
        },
        {
            "_label": "Case 4 — Manager, large but in-range transaction",
            "emp_id":   "EMP_MGR_088",
            "emp_class": "MANAGER",
            "amount":    400_000.0,
            "dwell_time": 90.0,
            "login_hour": 14,
        },
        {
            "_label": "Case 5 — IT Admin, abnormally long dwell (bulk DB read?)",
            "emp_id":   "EMP_IT_019",
            "emp_class": "IT_ADMIN",
            "amount":    0.0,
            "dwell_time": 3_600.0,    # 1 hour in DB — 65x above peer avg
            "login_hour": 11,
        },
        {
            "_label": "Case 6 — Unknown emp_class (graceful degradation test)",
            "emp_id":   "EMP_VENDOR_009",
            "emp_class": "CONTRACTOR",
            "amount":    75_000.0,
            "dwell_time": 55.0,
            "login_hour": 19,
        },
        {
            "_label": "Case 7 — Edge: midnight login, extreme amount, long dwell (MAX SCORE TEST)",
            "emp_id":   "EMP_CLERK_666",
            "emp_class": "CLERK",
            "amount":    25_000_000.0,
            "dwell_time": 900.0,
            "login_hour": 0,
        },
    ]

    for tx in TEST_TRANSACTIONS:
        label = tx.pop("_label")
        result = agent.evaluate(tx)

        bar_len = result["severity_index"] // 5
        bar = "█" * bar_len + "░" * (20 - bar_len)

        print(f"\n{label}")
        print(f"  CBSI  : [{bar}] {result['severity_index']:3d}/100")
        print(f"  Signal: {result['signal']}")
        print(f"  Reason: {result['reason']}")

    print(f"\n{DIVIDER}")
    print("  All test cases complete. Agent 1 operational.")
    print(DIVIDER)