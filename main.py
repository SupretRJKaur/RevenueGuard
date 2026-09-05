import json
import random
from datetime import datetime, timezone, timedelta

from classifier import classify_payment_failure, classify_invoice
from rules_engine import decide_payment_action, decide_invoice_action

random.seed(7)  
RECOVERY_LIKELIHOOD = {
    "bank_server_down": 0.65,
    "network_drop": 0.75,
    "otp_expired": 0.55,
    "insufficient_funds": 0.45,  
                                  
                                  
    "wrong_credentials": 0.05,    
                                  
                                  
    "card_declined_generic": 0.30,
}

INVOICE_RECOVERY_LIKELIHOOD = {
    "polite": 0.70,
    "firm": 0.50,
    "final_notice": 0.30,
    "escalate_human": 0.0,  
}

PROMISE_TO_PAY_CHANCE = {
    "polite": 0.40,
    "firm": 0.30,
}
PROMISE_KEPT_LIKELIHOOD = 0.65


def simulate_outcome(action: str, likelihood: float) -> str:
    if action in ("escalate_to_support", "escalate_to_human", "flag_for_human_review"):
        return "stopped"
    if action == "notify_only":
        return "recovered" if random.random() < likelihood else "not_recovered"
    return "recovered" if random.random() < likelihood else "pending_retry"


def run_payment_pipeline():
    with open("data/payment_events.json") as f:
        events = json.load(f)

    audit_entries = []
    correct = 0
    total_at_risk = 0.0
    total_recovered = 0.0
    by_cause = {}

    for event in events:
        total_at_risk += event["amount"]
        classification = classify_payment_failure(event)
        predicted = classification["predicted_cause"]
        ground_truth = event["_ground_truth_cause"]

        if predicted == ground_truth:
            correct += 1

        decision = decide_payment_action(event, predicted)
        likelihood = RECOVERY_LIKELIHOOD.get(predicted, 0.2)
        outcome = simulate_outcome(decision["action"], likelihood)

        if outcome == "recovered":
            total_recovered += event["amount"]

        by_cause.setdefault(predicted, {"count": 0, "recovered": 0})
        by_cause[predicted]["count"] += 1
        if outcome == "recovered":
            by_cause[predicted]["recovered"] += 1

        audit_entries.append({
            "log_id": f"LOG-{event['txn_id']}",
            "source_id": event["txn_id"],
            "source_type": "payment",
            "predicted_cause": predicted,
            "classifier_confidence": classification.get("confidence"),
            "classifier_rationale": classification.get("rationale"),
            "action_taken": decision["action"],
            "scheduled_time": decision["scheduled_time"],
            "stop": decision["stop"],
            "reasoning": decision["reasoning"],
            "outcome": outcome,
            "amount": event["amount"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    accuracy = correct / len(events) if events else 0
    return audit_entries, accuracy, total_at_risk, total_recovered, by_cause


def run_invoice_pipeline():
    with open("data/invoices.json") as f:
        invoices = json.load(f)

    audit_entries = []
    correct = 0
    total_at_risk = 0.0
    total_recovered = 0.0
    by_bucket = {}

    for invoice in invoices:
        total_at_risk += invoice["amount"]
        classification = classify_invoice(invoice)
        predicted = classification["predicted_bucket"]
        ground_truth = invoice["_ground_truth_bucket"]

        if predicted == ground_truth:
            correct += 1

        decision = decide_invoice_action(invoice, predicted)

        by_bucket.setdefault(predicted, {"count": 0, "recovered": 0})
        by_bucket[predicted]["count"] += 1
        promised = (
            decision["action"] == "send_message"
            and predicted in PROMISE_TO_PAY_CHANCE
            and random.random() < PROMISE_TO_PAY_CHANCE[predicted]
        )

        if promised:
            promise_date = (datetime.now(timezone.utc) + timedelta(days=random.randint(3, 10))).date().isoformat()

            audit_entries.append({
                "log_id": f"LOG-{invoice['invoice_id']}-1",
                "source_id": invoice["invoice_id"],
                "source_type": "invoice",
                "predicted_bucket": predicted,
                "classifier_confidence": classification.get("confidence"),
                "classifier_rationale": classification.get("rationale"),
                "action_taken": decision["action"],
                "tone": decision.get("tone"),
                "channel": decision.get("channel"),
                "stop": False,
                "reasoning": decision["reasoning"],
                "outcome": "pending_retry",
                "amount": invoice["amount"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            invoice_with_promise = {**invoice, "promise_to_pay_date": promise_date}
            follow_up = decide_invoice_action(invoice_with_promise, predicted)
            kept = random.random() < PROMISE_KEPT_LIKELIHOOD
            final_outcome = "recovered" if kept else "not_recovered"

            audit_entries.append({
                "log_id": f"LOG-{invoice['invoice_id']}-2",
                "source_id": invoice["invoice_id"],
                "source_type": "invoice",
                "predicted_bucket": predicted,
                "classifier_confidence": None,
                "classifier_rationale": None,
                "action_taken": follow_up["action"],
                "tone": follow_up.get("tone"),
                "channel": follow_up.get("channel"),
                "stop": False,
                "reasoning": follow_up["reasoning"] + (
                    f" Promise was kept - payment received."
                    if kept else
                    f" Promised date passed with no payment; needs re-escalation."
                ),
                "outcome": final_outcome,
                "amount": invoice["amount"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if final_outcome == "recovered":
                total_recovered += invoice["amount"]
                by_bucket[predicted]["recovered"] += 1

            continue

        likelihood = INVOICE_RECOVERY_LIKELIHOOD.get(predicted, 0.0)
        outcome = simulate_outcome(decision["action"], likelihood)

        if outcome == "recovered":
            total_recovered += invoice["amount"]
            by_bucket[predicted]["recovered"] += 1

        audit_entries.append({
            "log_id": f"LOG-{invoice['invoice_id']}",
            "source_id": invoice["invoice_id"],
            "source_type": "invoice",
            "predicted_bucket": predicted,
            "classifier_confidence": classification.get("confidence"),
            "classifier_rationale": classification.get("rationale"),
            "action_taken": decision["action"],
            "tone": decision.get("tone"),
            "channel": decision.get("channel"),
            "stop": decision["stop"],
            "reasoning": decision["reasoning"],
            "outcome": outcome,
            "amount": invoice["amount"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    accuracy = correct / len(invoices) if invoices else 0
    return audit_entries, accuracy, total_at_risk, total_recovered, by_bucket


def print_summary(label, accuracy, at_risk, recovered, breakdown):
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Classification accuracy vs ground truth: {accuracy*100:.1f}%")
    print(f"Total ₹ at risk:      ₹{at_risk:,.2f}")
    print(f"Total ₹ recovered:    ₹{recovered:,.2f}")
    print(f"Recovery rate:        {(recovered/at_risk*100) if at_risk else 0:.1f}%")
    print(f"\nBreakdown by category:")
    for cat, stats in breakdown.items():
        rate = (stats["recovered"] / stats["count"] * 100) if stats["count"] else 0
        print(f"  {cat:25s} count={stats['count']:3d}  recovered={stats['recovered']:3d}  rate={rate:5.1f}%")


if __name__ == "__main__":
    print("Running RevenueGuard pipeline...\n")

    payment_log, p_acc, p_risk, p_recovered, p_breakdown = run_payment_pipeline()
    invoice_log, i_acc, i_risk, i_recovered, i_breakdown = run_invoice_pipeline()

    full_audit_log = payment_log + invoice_log
    with open("logs/audit_log.json", "w") as f:
        json.dump(full_audit_log, f, indent=2)

    print_summary("PAYMENT FAILURE RECOVERY", p_acc, p_risk, p_recovered, p_breakdown)
    print_summary("INVOICE RECEIVABLES RECOVERY", i_acc, i_risk, i_recovered, i_breakdown)

    combined_risk = p_risk + i_risk
    combined_recovered = p_recovered + i_recovered
    print(f"\n{'='*60}")
    print(f"COMBINED TOTALS")
    print(f"{'='*60}")
    print(f"Total ₹ at risk:      ₹{combined_risk:,.2f}")
    print(f"Total ₹ recovered:    ₹{combined_recovered:,.2f}")
    print(f"Overall recovery rate: {(combined_recovered/combined_risk*100) if combined_risk else 0:.1f}%")
    print(f"\nFull audit trail written to logs/audit_log.json ({len(full_audit_log)} entries)")
