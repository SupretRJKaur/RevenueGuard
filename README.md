# RevenueGuard
An automated AI revenue recovery agent that monitors incoming transactions to catch the two primary sources of silent revenue leakage: **failed payment attempts** and **overdue unpaid invoices**.

Built for **Track 3 — AI Revenue Recovery**.

---

## The Problem

Money rarely disappears all at once — it leaks through small, unhandled edge cases:

* A UPI payment times out due to a temporary bank server issue.
* A customer's OTP window expires before completion.
* A B2B invoice remains overdue for weeks because manual follow-ups don't scale.

Standard payment gateways often handle these situations with brute-force retries or generic reminders. This can trigger unnecessary decline fees, annoy customers, and create compliance risks.

**RevenueGuard** replaces blind retries with:

* Intelligent failure classification
* Bounded governance rules
* Dynamic promise-to-pay tracking
* Automated recovery simulation
* Complete audit logging

### System Overview

```text
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ Synthetic Data  │ ──►│ Gemini Flash    │ ──►│ Rules Engine     │ ──►│ Audit Log &       │
│ & Failures      │    │ Classifier      │    │ Bounded Policies │    │ Dashboard Portal  │
└─────────────────┘    └─────────────────┘    └──────────────────┘    └───────────────────┘
```

---

## What RevenueGuard Actually Does

The system processes payment failures and overdue invoices through four structured stages.

### 1. Classify

Gemini analyzes each failed payment's error code and metadata to determine why the payment failed.

Possible causes include:

* Bank server downtime
* OTP expiration
* Insufficient funds
* Incorrect credentials

For overdue invoices, the system evaluates:

* How long the invoice has been overdue
* Customer payment history
* Payment urgency
* Previous recovery behavior

The classifier focuses only on **understanding the situation**. It does not decide what action should be taken.

---

### 2. Decide — Bounded Rules Engine

The actual decision-making is handled by a fixed policy table in `rules_engine.py`.

The LLM classifies the situation, while the deterministic rules engine decides what happens next.

For example:

#### Insufficient Funds

```text
insufficient_funds
        │
        ▼
Do NOT retry immediately
        │
        ▼
Schedule retry around likely salary day
```

#### Bank Server Down

```text
bank_server_down
        │
        ▼
Retry #1
        │
      2 hours
        │
        ▼
Retry #2
        │
        ▼
Stop & escalate to human
```

Every policy includes a **hard stop condition**.

Allowing an LLM to freely decide how many times to retry a payment could result in uncontrolled retries, unnecessary fees, or other financial risks.

**The model explains. The rules decide.**

---

### 3. Simulate Outcomes & Honest Metrics

RevenueGuard operates on synthetic data rather than a live payment gateway.

Therefore, recovery outcomes are simulated using realistic recovery probabilities.

| Failure / Situation      | Simulated Recovery Behavior |
| ------------------------ | --------------------------- |
| Bank server issue        | ~90% recovery               |
| Wrong credentials        | 0% recovery                 |
| Insufficient funds       | ~35–40% when rescheduled    |
| 35+ day overdue invoices | 0% automatic collection     |

These values are intentionally bounded.

For example, **wrong credentials remain at 0%** because repeatedly retrying a security-related failure is not meaningful revenue recovery.

Similarly, highly overdue invoices are escalated to humans rather than pretending an automated system can magically collect money that has been sitting unpaid for weeks.

---

### 4. Promise-to-Pay Tracking & Audit Logging

If a customer receives a reminder and promises to make a payment on a specific date, RevenueGuard records that commitment separately.

The system then:

1. Records the promised payment date.
2. Pauses further escalation.
3. Waits until the promised date.
4. Checks whether the commitment has been fulfilled.
5. Escalates only if the promise is broken.

Every decision is recorded in `audit_log.json`, including:

* Original transaction
* Classification
* Classification reasoning
* Selected action
* Policy applied
* Recovery outcome
* Promise-to-pay information
* Compliance status

This creates a complete and traceable decision history.

---

# Dashboard

`generate_dashboard.py` converts the audit log into a standalone HTML dashboard.

The generated `dashboard.html` can be opened directly in a browser without running a web server.

### Dashboard Features

#### Secure Login Flow

The dashboard is designed to resemble a financial portal:

```text
Login
  │
  ▼
OTP Verification
  │
  ▼
Masked Financial Data
  │
  ▼
Second OTP
  │
  ▼
Unmasked Dashboard
```

For demonstration purposes, the login credentials and OTPs are displayed on-screen.

#### Revenue Overview

The dashboard provides:

* Total balance
* Recovered revenue
* Revenue at risk
* Overall recovery rate

#### Cause-Level Analysis

Recovery performance can be analyzed by failure cause, such as:

* Bank server failures
* Insufficient funds
* OTP expiration
* Wrong credentials
* Overdue invoices

#### Searchable Audit Trail

Every transaction can be inspected individually.

The audit trail displays:

* Transaction details
* Classification
* Classification reasoning
* Action taken
* Recovery result
* Compliance status

---

# Technology Stack

| Component         | Technology                           |
| ----------------- | ------------------------------------ |
| AI Classification | Gemini Flash                         |
| Gemini SDK        | `google-genai`                       |
| Rules Engine      | Python                               |
| Orchestration     | Python                               |
| Data Generation   | Python                               |
| Dashboard         | HTML / CSS / JavaScript              |
| Data Storage      | JSON                                 |
| Dataset           | Synthetic transaction & invoice data |

### AI Model

RevenueGuard uses the official **`google-genai`** SDK with:

```text
gemini-flash-latest
```

The model is used specifically for **classification and reasoning**, while deterministic business rules control financial actions.

---

# Project Structure

```text
RevenueGuard/
│
├── data/
│   └── # Synthetic payment events & invoice datasets
│
├── logs/
│   └── # Output audit logs and execution records
│
├── classifier.py
│   └── # Gemini Flash classification logic
│
├── rules_engine.py
│   └── # Bounded decision engine & retry policies
│
├── main.py
│   └── # Main orchestration engine
│
├── generate_data.py
│   └── # Synthetic dataset generator
│
├── generate_dashboard.py
│   └── # Generates standalone dashboard.html
│
├── dashboard.html
│   └── # Generated dashboard UI
│
├── requirements.txt
│   └── # Project dependencies
│
├── .env.example
│   └── # Environment variable template
│
└── README.md
    └── # Project documentation
```

---

# Quick Start

## 1. Install Dependencies

Clone the repository and install the required Python packages:

```bash
pip install -r requirements.txt
```

---

## 2. Configure API Credentials

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

> **Note:** An API key is optional for demonstration purposes. Without one, RevenueGuard runs in mock-classification mode so the complete pipeline can still be tested.

---

## 3. Generate Synthetic Data

Run:

```bash
python generate_data.py
```

This creates the synthetic payment failure and invoice datasets used by the pipeline.

---

## 4. Run the Revenue Recovery Pipeline

Execute:

```bash
python main.py
```

This runs the complete classification and decision pipeline and generates the audit logs.

The resulting decisions are stored in:

```text
logs/audit_log.json
```

---

## 5. Generate the Dashboard

Run:

```bash
python generate_dashboard.py
```

This converts the audit data into:

```text
dashboard.html
```

---

## 6. Open the Dashboard

Open `dashboard.html` directly in any modern web browser.

No web server is required.

For the demo login:

* Any username/password can be used.
* OTPs are displayed directly on-screen.

---

# Complete Pipeline

The complete RevenueGuard workflow looks like this:

```text
              ┌──────────────────────┐
              │ Generate Synthetic   │
              │ Payment & Invoice    │
              │ Data                 │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Gemini Flash         │
              │ Classification       │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Deterministic Rules  │
              │ Engine               │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Simulated Recovery   │
              │ Outcome              │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Promise-to-Pay       │
              │ Tracking             │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Audit Log            │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Dashboard            │
              └──────────────────────┘
```

---

# Technical Challenges & Learnings

## 1. SDK & Model Migration

The project was migrated from the deprecated `google-generativeai` package to Google's newer official:

```text
google-genai
```

The system uses:

```text
gemini-flash-latest
```

This provides a more current SDK architecture and avoids relying on the deprecated package.

---

## 2. Classifier Calibration

Classification accuracy was improved using **structured few-shot examples** within the Gemini prompt.

The classifier is also instructed to return structured JSON output using:

```text
response_mime_type
```

This makes the output easier for the Python pipeline to validate and process.

---

## 3. Rate-Limit Resilience

Batch-processing multiple records can result in API rate limits and temporary service errors.

RevenueGuard therefore implements:

* Exponential backoff
* Retry handling
* Request delays
* Graceful fallback to mock classification

This allows the complete pipeline to continue running even when the API is temporarily unavailable.

---

# Design Principles

RevenueGuard is built around four core principles.

### AI for Understanding

Gemini is responsible for interpreting messy payment and invoice information.

### Rules for Decisions

Financial actions are controlled by deterministic rules rather than unrestricted LLM decisions.

### Hard Stops for Safety

Every retry policy has a maximum number of attempts or escalation condition.

### Everything is Auditable

Every classification and action is recorded for later inspection.

```text
AI understands
      ↓
Rules decide
      ↓
Simulation tests
      ↓
Audit records
      ↓
Dashboard explains
```

---

# Future Roadmap

### Real-Time Payment Integration

Integrate with live payment platforms such as:

* Razorpay
* Stripe

through real-time webhook listeners.

### Multi-Channel Communication

Support automated recovery messaging through:

* WhatsApp
* Email
* Telegram

### Promise-to-Pay Automation

Introduce automated second-stage reminders when a customer breaks a promised payment date.

### Advanced Recovery Intelligence

Future versions could incorporate historical customer behavior to improve recovery timing while keeping the final decision within bounded policies.

---

# Disclaimer

RevenueGuard is a **prototype built using synthetic data**.

Recovery percentages and transaction outcomes are simulated for demonstration purposes and should not be interpreted as real-world financial performance.

The system is designed to demonstrate how AI classification can be combined with deterministic governance and auditability for revenue recovery workflows.

---

## 🎥 Project Pitch

[▶️ RevenueGuard pitch](https://drive.google.com/file/d/1XOxGi14xcIVC0pqpNbc8cZCzbANwDPak/view?usp=drive_link)
