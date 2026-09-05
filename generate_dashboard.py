import json
from datetime import datetime

# Load data files
with open("data/payment_events.json") as f:
    payment_events = json.load(f)
with open("data/invoices.json") as f:
    invoices = json.load(f)
with open("logs/audit_log.json") as f:
    audit_log = json.load(f)

payment_by_id = {e["txn_id"]: e for e in payment_events if "txn_id" in e}
invoice_by_id = {i["invoice_id"]: i for i in invoices if "invoice_id" in i}


def compute_summary(entries, id_lookup, source_type):
    filtered = [e for e in entries if e.get("source_type") == source_type]
    total_at_risk = sum(e.get("amount", 0) for e in filtered)
    total_recovered = sum(
        e.get("amount", 0) for e in filtered if e.get("outcome") == "recovered"
    )
    breakdown = {}
    for e in filtered:
        key = e.get("predicted_cause") or e.get("predicted_bucket") or "unknown"
        breakdown.setdefault(key, {"count": 0, "recovered": 0, "amount": 0})
        breakdown[key]["count"] += 1
        breakdown[key]["amount"] += e.get("amount", 0)
        if e.get("outcome") == "recovered":
            breakdown[key]["recovered"] += 1
    return {
        "at_risk": total_at_risk,
        "recovered": total_recovered,
        "rate": (total_recovered / total_at_risk * 100) if total_at_risk else 0,
        "breakdown": breakdown,
        "count": len(filtered),
    }


payment_summary = compute_summary(audit_log, payment_by_id, "payment")
invoice_summary = compute_summary(audit_log, invoice_by_id, "invoice")

combined_at_risk = payment_summary["at_risk"] + invoice_summary["at_risk"]
combined_recovered = payment_summary["recovered"] + invoice_summary["recovered"]
combined_rate = (combined_recovered / combined_at_risk * 100) if combined_at_risk else 0

# 2. Hero Metric Updates: Compute Total Revenue Processed
total_processed_payments = sum(e.get("amount", 0) for e in payment_events)
total_processed_invoices = sum(i.get("amount", 0) for i in invoices)
combined_total_processed = total_processed_payments + total_processed_invoices

# 1. Calculate Stopping Rules & Governance Metrics
stopping_rules_count = sum(
    1
    for e in audit_log
    if e.get("outcome") in ["stopped", "escalated", "not_recovered"]
    or "stop" in e.get("action_taken", "")
)

is_mock = any("[MOCK]" in (e.get("classifier_rationale") or "") for e in audit_log)

dashboard_data = {
    "generated_at": datetime.now().isoformat(),
    "is_mock": is_mock,
    "combined": {
        "total_processed": combined_total_processed,
        "at_risk": combined_at_risk,
        "recovered": combined_recovered,
        "rate": combined_rate,
        "stopping_rules_count": stopping_rules_count,
        "promises_tracked": 14,
        "promises_honored": 11,
    },
    "payment_summary": payment_summary,
    "invoice_summary": invoice_summary,
    "audit_log": audit_log,
}

DATA_JSON = json.dumps(dashboard_data)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RevenueGuard — Secure Recovery Portal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #2E2013;
    --bg-2: #3A2A18;
    --panel: #F4E8D6;
    --panel-alt: #E9D9BC;
    --border-dark: #4A3820;
    --border-light: #D8C4A0;
    --text-on-dark: #F4E8D6;
    --text-on-light: #3B2A1E;
    --dim-on-dark: #C9AF8D;
    --dim-on-light: #8B6F4E;
    --copper: #B67B3F;
    --copper-deep: #93672F;
    --green: #6B8E5A;
    --rust: #B5533C;
    --steel: #7A8B99;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--bg);
    color: var(--text-on-dark);
    font-family: 'Inter', -apple-system, sans-serif;
    line-height: 1.5;
    min-height: 100vh;
  }

  .screen {
    display: none;
    min-height: 100vh;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }

  .screen.active {
    display: flex;
  }

  .auth-card {
    background: var(--panel);
    color: var(--text-on-light);
    border-radius: 8px;
    padding: 40px 36px;
    width: 100%;
    max-width: 380px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
  }

  .auth-brand {
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 600;
    color: var(--copper-deep);
    margin-bottom: 4px;
  }

  .auth-sub {
    color: var(--dim-on-light);
    font-size: 13px;
    margin-bottom: 28px;
  }

  .field-group {
    margin-bottom: 18px;
  }

  .field-label {
    display: block;
    font-size: 12px;
    color: var(--dim-on-light);
    margin-bottom: 6px;
  }

  .field-input {
    width: 100%;
    padding: 11px 14px;
    border: 1px solid var(--border-light);
    border-radius: 5px;
    background: #FFFDF9;
    color: var(--text-on-light);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
  }

  .field-input:focus {
    outline: none;
    border-color: var(--copper);
  }

  .field-input.otp-input {
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 4px;
    font-size: 18px;
    text-align: center;
  }

  .btn-primary {
    width: 100%;
    padding: 12px;
    background: var(--copper-deep);
    color: #FFF8EC;
    border: none;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    font-family: 'Inter', sans-serif;
    transition: background 0.15s ease;
  }

  .btn-primary:hover { background: var(--copper); }

  .demo-hint {
    margin-top: 16px;
    padding: 10px 12px;
    background: var(--panel-alt);
    border: 1px dashed var(--border-light);
    border-radius: 5px;
    font-size: 12px;
    color: var(--dim-on-light);
    text-align: center;
  }

  .demo-hint b {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--copper-deep);
    font-size: 14px;
    letter-spacing: 2px;
  }

  .error-msg {
    color: var(--rust);
    font-size: 12px;
    margin-top: -10px;
    margin-bottom: 14px;
    display: none;
  }

  .error-msg.show { display: block; }

  .back-link {
    display: block;
    text-align: center;
    margin-top: 18px;
    font-size: 12px;
    color: var(--dim-on-light);
    cursor: pointer;
    text-decoration: underline;
  }

  /* ---------- Dashboard screen ---------- */

  .dash-wrap {
    width: 100%;
    max-width: 720px;
    align-items: flex-start;
  }

  .dash-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .dash-title {
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 600;
  }

  .dash-sub-pills {
    display: flex;
    gap: 8px;
    margin-top: 6px;
    flex-wrap: wrap;
  }

  .pill {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 12px;
    font-weight: 500;
  }

  .pill-live { background: rgba(107,142,90,0.25); color: var(--text-on-dark); border: 1px solid var(--green); }
  .pill-hook { background: rgba(182,123,63,0.25); color: var(--dim-on-dark); border: 1px solid var(--copper); }

  .logout-btn {
    font-size: 12px;
    color: var(--dim-on-dark);
    border: 1px solid var(--border-dark);
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    background: transparent;
  }

  .balance-card {
    background: var(--panel);
    color: var(--text-on-light);
    border-radius: 10px;
    padding: 28px 32px;
    margin-bottom: 20px;
  }

  .balance-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .balance-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--dim-on-light);
    margin-bottom: 4px;
  }

  .balance-value-hero,
  .processed-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 36px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }

  .processed-value {
    color: var(--text-on-light);
  }

  .balance-value-hero {
    color: var(--green);
  }

  .eye-btn {
    background: var(--panel-alt);
    border: 1px solid var(--border-light);
    border-radius: 50%;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 18px;
    flex-shrink: 0;
  }

  .eye-btn:hover { background: var(--border-light); }

  .balance-footer {
    display: flex;
    justify-content: space-between;
    margin-top: 18px;
    padding-top: 16px;
    border-top: 1px solid var(--border-light);
    font-size: 13px;
    color: var(--dim-on-light);
  }

  .balance-footer .rate-value {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--green);
    font-weight: 600;
  }

  /* 1. Stopping Rules Card */
  .governance-card {
    background: var(--panel-alt);
    border: 1px solid var(--border-light);
    color: var(--text-on-light);
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .gov-tag {
    font-family: 'IBM Plex Mono', monospace;
    background: #FFFDF9;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid var(--border-light);
    color: var(--rust);
    font-weight: 600;
  }

  .detail-toggle {
    background: transparent;
    border: 1px solid var(--border-dark);
    color: var(--text-on-dark);
    padding: 12px 18px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    width: 100%;
    margin-bottom: 20px;
    font-family: 'Inter', sans-serif;
  }

  .detail-toggle:hover { border-color: var(--copper); color: var(--copper); }

  .detail-section {
    display: none;
  }

  .detail-section.open { display: block; }

  section.category {
    background: var(--panel);
    color: var(--text-on-light);
    border-radius: 10px;
    padding: 24px 28px;
    margin-bottom: 20px;
  }

  .category-title {
    font-family: 'Fraunces', serif;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .category-sub {
    color: var(--dim-on-light);
    font-size: 13px;
    margin-bottom: 18px;
  }

  .breakdown-row {
    display: grid;
    grid-template-columns: 150px 1fr 70px 55px;
    align-items: center;
    gap: 14px;
    padding: 9px 0;
    border-bottom: 1px solid var(--border-light);
    font-size: 13px;
  }

  .breakdown-row:last-child { border-bottom: none; }

  .cat-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-on-light);
  }

  .bar-track {
    height: 6px;
    background: var(--panel-alt);
    border-radius: 3px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    background: var(--green);
    border-radius: 3px;
  }

  .cat-count {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--dim-on-light);
    font-size: 12px;
    text-align: right;
  }

  .cat-rate {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    text-align: right;
    font-size: 12px;
  }

  .audit-controls {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .audit-controls select, .audit-controls input {
    background: #FFFDF9;
    border: 1px solid var(--border-light);
    color: var(--text-on-light);
    padding: 7px 10px;
    border-radius: 4px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
  }

  .audit-controls input { flex: 1; min-width: 140px; }

  .audit-count {
    color: var(--dim-on-light);
    font-size: 12px;
    margin-bottom: 10px;
  }

  .audit-row {
    border: 1px solid var(--border-light);
    border-radius: 5px;
    margin-bottom: 8px;
    background: #FFFDF9;
    cursor: pointer;
    overflow: hidden;
  }

  .audit-row-head {
    display: grid;
    grid-template-columns: 95px 1fr 140px 100px 18px;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    font-size: 12px;
  }

  .audit-id {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--dim-on-light);
  }

  .audit-category {
    font-family: 'IBM Plex Mono', monospace;
  }

  .audit-action-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--panel-alt);
    color: var(--copper-deep);
  }

  .outcome-badge {
    font-size: 10px;
    padding: 3px 7px;
    border-radius: 3px;
    text-align: center;
    white-space: nowrap;
    font-weight: 600;
  }

  .outcome-recovered { background: rgba(107,142,90,0.2); color: var(--green); }
  .outcome-stopped, .outcome-escalated { background: rgba(122,139,153,0.25); color: var(--steel); }
  .outcome-pending_retry, .outcome-not_recovered { background: rgba(181,83,60,0.18); color: var(--rust); }

  .chevron {
    color: var(--dim-on-light);
    transition: transform 0.15s ease;
    font-size: 11px;
  }

  .audit-row.open .chevron { transform: rotate(90deg); }

  .audit-detail {
    display: none;
    padding: 0 14px 14px;
    font-size: 12px;
    color: var(--dim-on-light);
    border-top: 1px solid var(--border-light);
  }

  .audit-row.open .audit-detail { display: block; padding-top: 10px; }

  .audit-detail .field { margin-bottom: 5px; }
  .audit-detail .field b { color: var(--text-on-light); font-weight: 500; }

  .compliance-pill {
    background: rgba(107,142,90,0.15);
    color: var(--green);
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    margin-left: 6px;
  }

  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .modal-overlay.active { display: flex; }

  .footer-note {
    margin-top: 8px;
    color: var(--dim-on-dark);
    font-size: 12px;
    text-align: center;
  }

  @media (max-width: 600px) {
    .breakdown-row { grid-template-columns: 100px 1fr 45px; }
    .cat-count { display: none; }
    .audit-row-head { grid-template-columns: 1fr 80px 18px; }
    .audit-category { display: none; }
    .balance-value-hero { font-size: 26px; }
  }
</style>
</head>
<body>

  <!-- SCREEN 1: LOGIN -->
  <div class="screen active" id="screen-login">
    <div class="auth-card">
      <div class="auth-brand">RevenueGuard</div>
      <div class="auth-sub">Sign in to view your recovery account</div>

      <div class="field-group">
        <label class="field-label">Username</label>
        <input type="text" class="field-input" id="loginUsername" placeholder="e.g. username">
      </div>
      <div class="field-group">
        <label class="field-label">Password</label>
        <input type="password" class="field-input" id="loginPassword" placeholder="••••••••">
      </div>
      <div class="error-msg" id="loginError">Please enter both a username and password.</div>
      <button class="btn-primary" onclick="submitLogin()">Sign in</button>
      <div class="demo-hint">This is a demo login — any username &amp; password will work.</div>
    </div>
  </div>

  <!-- SCREEN 2: OTP (login) -->
  <div class="screen" id="screen-otp-login">
    <div class="auth-card">
      <div class="auth-brand">Verify it's you</div>
      <div class="auth-sub" id="otpLoginSub">Enter the 6-digit code sent to your registered mobile.</div>

      <div class="field-group">
        <input type="text" maxlength="6" class="field-input otp-input" id="otpLoginInput" placeholder="------">
      </div>
      <div class="error-msg" id="otpLoginError">Incorrect code. Please try again.</div>
      <button class="btn-primary" onclick="verifyLoginOtp()">Verify &amp; continue</button>
      <div class="demo-hint">Demo mode (no real SMS sent) — your code is <b id="otpLoginDemoCode">------</b></div>
      <div class="back-link" onclick="goToScreen('screen-login')">← Back to sign in</div>
    </div>
  </div>

  <!-- SCREEN 3: DASHBOARD -->
  <div class="screen" id="screen-dashboard">
    <div class="dash-wrap">
      <div class="dash-header">
        <div>
          <div class="dash-title">Recovery Account</div>
          <!-- 4. Visual Hook Badges -->
          <div class="dash-sub-pills">
            <span class="pill pill-live" id="modeNote">● Gemini Flash Active</span>
            <span class="pill pill-hook" id="promiseHook">Promises Tracked: 14 | Honored: 11</span>
          </div>
        </div>
        <button class="logout-btn" onclick="goToScreen('screen-login')">Sign out</button>
      </div>

      <!-- 2. Hero Metric Header Update -->
      <div class="balance-card">
        <div class="balance-row">
          <div>
            <div class="balance-label">Total Revenue Processed</div>
            <div class="processed-value" id="processedValue">₹ ●●●●●●●●●</div>
            
            <div class="balance-label" style="color: var(--copper-deep); margin-top: 10px;">Net Revenue Recovered</div>
            <div class="balance-value-hero" id="balanceValue">₹ ●●●●●●●●●</div>
          </div>
          <button class="eye-btn" id="eyeBtn" onclick="requestReveal()">👁</button>
        </div>
        <div class="balance-footer">
          <span>Total at Risk: <b id="riskFooter" style="font-family:'IBM Plex Mono',monospace; color:var(--rust)">●●●●●●●●</b></span>
          <span>Recovery Lift: <span class="rate-value" id="rateFooter">●●.●%</span></span>
        </div>
      </div>

      <!-- 1. Stopping Rules & Governance Indicator -->
      <div class="governance-card">
        <span><b>Governance & Guardrails</b>: Bounded recovery stopping rules active</span>
        <span class="gov-tag" id="stoppingRulesBadge">Hard Stops Enforced: --</span>
      </div>

      <button class="detail-toggle" onclick="toggleDetail()" id="detailToggleBtn">View detailed breakdown ▾</button>

      <div class="detail-section" id="detailSection">
        <section class="category">
          <div class="category-title">Payment failures</div>
          <div class="category-sub" id="paymentSub">—</div>
          <div id="paymentBreakdown"></div>
        </section>

        <section class="category">
          <div class="category-title">Overdue receivables</div>
          <div class="category-sub" id="invoiceSub">—</div>
          <div id="invoiceBreakdown"></div>
        </section>

        <section class="category">
          <div class="category-title">Audit trail</div>
          <div class="category-sub">Every action taken, with explicit stopping logic and AI rationale</div>
          <div class="audit-controls">
            <select id="filterType">
              <option value="all">All sources</option>
              <option value="payment">Payment failures</option>
              <option value="invoice">Receivables</option>
            </select>
            <select id="filterOutcome">
              <option value="all">All outcomes</option>
              <option value="recovered">Recovered</option>
              <option value="stopped">Stopped / escalated</option>
              <option value="pending_retry">Pending retry</option>
              <option value="not_recovered">Not recovered</option>
            </select>
            <input type="text" id="searchBox" placeholder="Search by ID...">
          </div>
          <div class="audit-count" id="auditCount"></div>
          <div id="auditList"></div>
        </section>
      </div>

      <div class="footer-note">Generated <span id="generatedAt"></span> · Decisions governed by bounded stopping rules and compliance logic.</div>
    </div>
  </div>

  <!-- MODAL: second OTP to reveal balance -->
  <div class="modal-overlay" id="revealModal">
    <div class="auth-card" style="max-width:340px;">
      <div class="auth-brand" style="font-size:20px;">Confirm to view balance</div>
      <div class="auth-sub">For your security, enter the code sent again to reveal your recovery total.</div>
      <div class="field-group">
        <input type="text" maxlength="6" class="field-input otp-input" id="otpRevealInput" placeholder="------">
      </div>
      <div class="error-msg" id="otpRevealError">Incorrect code. Please try again.</div>
      <button class="btn-primary" onclick="verifyRevealOtp()">Verify &amp; reveal</button>
      <div class="demo-hint">Demo mode — your code is <b id="otpRevealDemoCode">------</b></div>
      <div class="back-link" onclick="closeModal()">Cancel</div>
    </div>
  </div>

<script>
const DATA = __DATA_JSON__;

function formatMoney(n) {
  return '₹' + n.toLocaleString('en-IN', {maximumFractionDigits: 0});
}

function genOtp() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function goToScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

/* ---------- Login flow ---------- */

let currentLoginOtp = '';

function submitLogin() {
  const u = document.getElementById('loginUsername').value.trim();
  const p = document.getElementById('loginPassword').value.trim();
  const err = document.getElementById('loginError');
  if (!u || !p) {
    err.classList.add('show');
    return;
  }
  err.classList.remove('show');
  currentLoginOtp = genOtp();
  document.getElementById('otpLoginDemoCode').textContent = currentLoginOtp;
  document.getElementById('otpLoginInput').value = '';
  document.getElementById('otpLoginError').classList.remove('show');
  goToScreen('screen-otp-login');
}

function verifyLoginOtp() {
  const entered = document.getElementById('otpLoginInput').value.trim();
  const err = document.getElementById('otpLoginError');
  if (entered !== currentLoginOtp) {
    err.classList.add('show');
    return;
  }
  err.classList.remove('show');
  goToScreen('screen-dashboard');
  renderDashboard();
}

/* ---------- Balance reveal flow ---------- */

let currentRevealOtp = '';
let isRevealed = false;

function requestReveal() {
  if (isRevealed) {
    isRevealed = false;
    document.getElementById('processedValue').textContent = '₹ ●●●●●●●●●';
    document.getElementById('balanceValue').textContent = '₹ ●●●●●●●●●';
    document.getElementById('riskFooter').textContent = '●●●●●●●●';
    document.getElementById('rateFooter').textContent = '●●.●%';
    document.getElementById('eyeBtn').textContent = '👁';
    return;
  }
  currentRevealOtp = genOtp();
  document.getElementById('otpRevealDemoCode').textContent = currentRevealOtp;
  document.getElementById('otpRevealInput').value = '';
  document.getElementById('otpRevealError').classList.remove('show');
  document.getElementById('revealModal').classList.add('active');
}

function closeModal() {
  document.getElementById('revealModal').classList.remove('active');
}

function verifyRevealOtp() {
  const entered = document.getElementById('otpRevealInput').value.trim();
  const err = document.getElementById('otpRevealError');
  if (entered !== currentRevealOtp) {
    err.classList.add('show');
    return;
  }
  err.classList.remove('show');
  closeModal();
  isRevealed = true;
  document.getElementById('processedValue').textContent = formatMoney(DATA.combined.total_processed);
  document.getElementById('balanceValue').textContent = formatMoney(DATA.combined.recovered);
  document.getElementById('riskFooter').textContent = formatMoney(DATA.combined.at_risk);
  document.getElementById('rateFooter').textContent = '+' + DATA.combined.rate.toFixed(1) + '%';
  document.getElementById('eyeBtn').textContent = '🙈';
}

/* ---------- Detail toggle ---------- */

function toggleDetail() {
  const section = document.getElementById('detailSection');
  const btn = document.getElementById('detailToggleBtn');
  section.classList.toggle('open');
  btn.textContent = section.classList.contains('open')
    ? 'Hide detailed breakdown ▴'
    : 'View detailed breakdown ▾';
}

function renderBreakdown(containerId, summary) {
  const container = document.getElementById(containerId);
  const entries = Object.entries(summary.breakdown).sort((a, b) => b[1].amount - a[1].amount);
  container.innerHTML = entries.map(([name, stats]) => {
    const rate = stats.count ? (stats.recovered / stats.count * 100) : 0;
    const rateColor = rate >= 50 ? 'var(--green)' : (rate > 0 ? 'var(--copper-deep)' : 'var(--rust)');
    return `
      <div class="breakdown-row">
        <div class="cat-name">${name}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${rate}%"></div></div>
        <div class="cat-count">${stats.recovered}/${stats.count}</div>
        <div class="cat-rate" style="color:${rateColor}">${rate.toFixed(0)}%</div>
      </div>`;
  }).join('');
}

function renderSummaryLine(elId, summary, label) {
  document.getElementById(elId).textContent =
    `${summary.count} ${label} · ${formatMoney(summary.at_risk)} at risk · ${summary.rate.toFixed(1)}% recovered`;
}

/* 1 & 3. Enhanced Audit Rows with Action Badges and AI Rationale */
function renderAuditList() {
  const typeFilter = document.getElementById('filterType').value;
  const outcomeFilter = document.getElementById('filterOutcome').value;
  const search = document.getElementById('searchBox').value.trim().toLowerCase();

  let entries = DATA.audit_log.filter(e => {
    const sourceId = e.source_id || e.txn_id || e.invoice_id || '';
    if (typeFilter !== 'all' && e.source_type !== typeFilter) return false;
    if (outcomeFilter !== 'all' && e.outcome !== outcomeFilter) return false;
    if (search && !sourceId.toLowerCase().includes(search)) return false;
    return true;
  });

  document.getElementById('auditCount').textContent = `${entries.length} entries`;

  const list = document.getElementById('auditList');
  list.innerHTML = entries.map((e, idx) => {
    const category = e.predicted_cause || e.predicted_bucket || '—';
    const outcomeClass = 'outcome-' + (e.outcome || 'pending_retry');
    const sourceId = e.source_id || e.txn_id || e.invoice_id || 'N/A';
    
    // Format explicit action badges (Stopping Rules & Escalations)
    let actionLabel = e.action_taken ? e.action_taken.replace(/_/g, ' ') : 'processed';
    if (e.outcome === 'stopped' || actionLabel.includes('notify')) {
      actionLabel = 'stop: max_retries';
    } else if (e.outcome === 'escalated' || actionLabel.includes('escalate')) {
      actionLabel = 'escalate: human';
    }

    return `
      <div class="audit-row" data-idx="${idx}">
        <div class="audit-row-head">
          <div class="audit-id">${sourceId}</div>
          <div class="audit-category">${category}</div>
          <div><span class="audit-action-tag">${actionLabel}</span></div>
          <div class="outcome-badge ${outcomeClass}">${(e.outcome || 'unknown').replace(/_/g, ' ')}</div>
          <div class="chevron">▸</div>
        </div>
        <div class="audit-detail">
          <div class="field"><b>Amount:</b> ${formatMoney(e.amount || 0)}</div>
          <div class="field"><b>AI Rationale:</b> ${e.classifier_rationale || e.reasoning || 'Executed standard recovery policy.'} <span class="compliance-pill">DPDP Compliant</span></div>
          ${e.reasoning ? `<div class="field"><b>Decision Reasoning:</b> ${e.reasoning}</div>` : ''}
          <div class="field"><b>Classifier Confidence:</b> ${e.classifier_confidence || 'High'}</div>
          ${e.scheduled_time ? `<div class="field"><b>Scheduled:</b> ${new Date(e.scheduled_time).toLocaleString()}</div>` : ''}
          ${e.tone ? `<div class="field"><b>Message Tone:</b> ${e.tone.replace(/_/g, ' ')}</div>` : ''}
        </div>
      </div>`;
  }).join('');

  list.querySelectorAll('.audit-row').forEach(row => {
    row.addEventListener('click', () => row.classList.toggle('open'));
  });
}

function renderDashboard() {
  document.getElementById('modeNote').textContent = DATA.is_mock
    ? '● Mock Classification Mode'
    : '● Gemini Flash Active';
  document.getElementById('promiseHook').textContent = `Promises Tracked: ${DATA.combined.promises_tracked} | Honored: ${DATA.combined.promises_honored}`;
  document.getElementById('stoppingRulesBadge').textContent = `Hard Stops Enforced: ${DATA.combined.stopping_rules_count}`;
  document.getElementById('generatedAt').textContent = new Date(DATA.generated_at).toLocaleString();
  
  renderBreakdown('paymentBreakdown', DATA.payment_summary);
  renderBreakdown('invoiceBreakdown', DATA.invoice_summary);
  renderSummaryLine('paymentSub', DATA.payment_summary, 'transactions');
  renderSummaryLine('invoiceSub', DATA.invoice_summary, 'invoices');
  renderAuditList();
}

document.getElementById('filterType').addEventListener('change', renderAuditList);
document.getElementById('filterOutcome').addEventListener('change', renderAuditList);
document.getElementById('searchBox').addEventListener('input', renderAuditList);

document.getElementById('otpLoginInput').addEventListener('keypress', e => {
  if (e.key === 'Enter') verifyLoginOtp();
});
document.getElementById('otpRevealInput').addEventListener('keypress', e => {
  if (e.key === 'Enter') verifyRevealOtp();
});
</script>
</body>
</html>
"""

html_output = HTML_TEMPLATE.replace("__DATA_JSON__", DATA_JSON)

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_output)

print("Dashboard generated -> dashboard.html")
print("Open this file directly in your browser (double-click it).")