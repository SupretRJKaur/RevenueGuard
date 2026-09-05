import os
import json
import random
from datetime import datetime, timedelta

random.seed(42)

PAYMENT_CAUSES = {
    "bank_server_down": {
        "weight": 0.28,
        "error_codes": ["BANK_TIMEOUT_502", "GATEWAY_UNAVAILABLE_503", "BANK_5XX_ERROR"],
    },
    "otp_expired": {
        "weight": 0.24,
        "error_codes": ["OTP_TIMEOUT", "OTP_EXPIRED_401", "OTP_WINDOW_CLOSED"],
    },
    "network_drop": {
        "weight": 0.16,
        "error_codes": ["CONN_RESET", "NETWORK_TIMEOUT", "REQUEST_ABORTED"],
    },
    "insufficient_funds": {
        "weight": 0.16,
        "error_codes": ["INSUFFICIENT_FUNDS", "BALANCE_LOW_402"],
    },
    "wrong_credentials": {
        "weight": 0.08,
        "error_codes": ["AUTH_FAILED_403", "INVALID_PIN", "CRED_MISMATCH"],
    },
    "card_declined_generic": {
        "weight": 0.08,
        "error_codes": ["CARD_DECLINED", "ISSUER_DECLINED_05"],
    },
}

METHODS = ["UPI", "Card", "NetBanking", "Wallet"]
TIERS = ["recurring", "new", "high_value"]
HISTORY = ["always_on_time", "sometimes_late", "frequently_late"]


def generate_payment_events(n=60):
    causes = list(PAYMENT_CAUSES.keys())
    weights = [PAYMENT_CAUSES[c]["weight"] for c in causes]
    events = []
    base_time = datetime(2026, 8, 1, 9, 0, 0)

    for i in range(1, n + 1):
        cause = random.choices(causes, weights=weights, k=1)[0]
        error_code = random.choice(PAYMENT_CAUSES[cause]["error_codes"])
        method = random.choice(METHODS) if cause != "otp_expired" else random.choice(["UPI", "NetBanking"])
        amount = round(random.uniform(199, 15000), 2)
        timestamp = base_time + timedelta(hours=random.randint(0, 800))

        events.append({
            "txn_id": f"TXN-{i:04d}",
            "timestamp": timestamp.isoformat() + "Z",
            "amount": amount,
            "method": method,
            "error_code": error_code,
            "retry_count": 0,
            "customer_id": f"CUST-{random.randint(100, 350)}",
            "status": "failed",
            "_ground_truth_cause": cause,
        })

    return events


def bucket_for_days(days_overdue):
    if days_overdue <= 7:
        return "polite"
    elif days_overdue <= 20:
        return "firm"
    elif days_overdue <= 35:
        return "final_notice"
    return "escalate_human"


def generate_invoices(n=40):
    invoices = []
    today = datetime(2026, 9, 5)

    for i in range(1, n + 1):
        days_overdue = random.randint(1, 60)
        due_date = today - timedelta(days=days_overdue)
        amount = round(random.uniform(8000, 250000), 2)

        invoices.append({
            "invoice_id": f"INV-{i:04d}",
            "customer_id": f"CUST-{random.randint(400, 550)}",
            "amount": amount,
            "due_date": due_date.date().isoformat(),
            "days_overdue": days_overdue,
            "customer_tier": random.choice(TIERS),
            "prior_payment_history": random.choice(HISTORY),
            "status": "unpaid",
            "_ground_truth_bucket": bucket_for_days(days_overdue),
        })

    return invoices


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    
    payment_events = generate_payment_events(60)
    invoices = generate_invoices(40)

    with open("data/payment_events.json", "w") as f:
        json.dump(payment_events, f, indent=2)

    with open("data/invoices.json", "w") as f:
        json.dump(invoices, f, indent=2)

    print(f"Generated {len(payment_events)} payment events -> data/payment_events.json")
    print(f"Generated {len(invoices)} invoices -> data/invoices.json")