
from datetime import datetime, timedelta


PAYMENT_POLICY = {
    "bank_server_down":      {"action": "auto_retry", "delay_minutes": 120, "max_retries": 2},
    "network_drop":          {"action": "auto_retry", "delay_minutes": 5,   "max_retries": 2},
    "otp_expired":           {"action": "prompt_user_retry", "delay_minutes": 0, "max_retries": 3},
    "insufficient_funds":    {"action": "retry_on_salary_day", "delay_minutes": None, "max_retries": 1},
    "wrong_credentials":     {"action": "notify_only", "delay_minutes": 0, "max_retries": 0},
    "card_declined_generic": {"action": "notify_alt_method", "delay_minutes": 0, "max_retries": 1},
}


def _next_salary_day(now: datetime) -> datetime:
    """Most Indian salaries land on the 1st or somewhere around the last
    working day of the month - just picking whichever of those two is
    closer in the future for the retry."""
    first_of_next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    month_end = first_of_next_month - timedelta(days=1)
    candidates = [d for d in (
        now.replace(day=1) + timedelta(days=31), 
        month_end,
    ) if d > now]
    return min(candidates) if candidates else first_of_next_month


def decide_payment_action(event: dict, predicted_cause: str) -> dict:
    """
    event: the payment event dict (has retry_count, amount, txn_id, etc.)
    predicted_cause: the cause string returned by the Gemini classifier

    Returns a decision dict: action, scheduled_time, stop, reasoning
    """
    policy = PAYMENT_POLICY.get(predicted_cause)

    if policy is None:
        return {
            "action": "flag_for_human_review",
            "scheduled_time": None,
            "stop": True,
            "reasoning": f"Cause '{predicted_cause}' not in policy table. "
                         f"Failing safe: no automated action taken.",
        }

    retry_count = event.get("retry_count", 0)
    max_retries = policy["max_retries"]

    if policy["action"] == "notify_only" and max_retries == 0:
        return {
            "action": policy["action"],
            "scheduled_time": None,
            "stop": True,
            "reasoning": f"Cause='{predicted_cause}': policy is notify-only "
                         f"(retrying on a security failure isn't safe, "
                         f"no auto-retry permitted here).",
        }

    if retry_count >= max_retries:
        return {
            "action": "escalate_to_support",
            "scheduled_time": None,
            "stop": True,
            "reasoning": f"Cause='{predicted_cause}': retry_count "
                         f"({retry_count}) has reached max_retries "
                         f"({max_retries}). Stopping rule triggered - "
                         f"escalating to human support.",
        }

    if policy["action"] == "retry_on_salary_day":
        scheduled_time = _next_salary_day(datetime.utcnow()).isoformat() + "Z"
        return {
            "action": "retry_on_salary_day",
            "scheduled_time": scheduled_time,
            "stop": False,
            "reasoning": f"Cause='{predicted_cause}': balance is probably "
                         f"just low right now, not a real failure. Scheduling "
                         f"a retry for the next salary date ({scheduled_time}) "
                         f"instead of giving up immediately, along with a "
                         f"discounted top-up link.",
        }

    scheduled_time = (
        datetime.utcnow() + timedelta(minutes=policy["delay_minutes"])
    ).isoformat() + "Z"

    return {
        "action": policy["action"],
        "scheduled_time": scheduled_time,
        "stop": False,
        "reasoning": f"Cause='{predicted_cause}': retry_count "
                     f"({retry_count}) < max_retries ({max_retries}). "
                     f"Scheduling '{policy['action']}' in "
                     f"{policy['delay_minutes']} min.",
    }



INVOICE_POLICY = {
    "polite":         {"tone": "polite_reminder", "channel": "email_payment_link",   "auto_send": True,  "stop": False},
    "firm":           {"tone": "firm_reminder",    "channel": "whatsapp_reminder",    "auto_send": True,  "stop": False},
    "final_notice":   {"tone": "final_notice",     "channel": "hinglish_voice_call",  "auto_send": True,  "stop": False},
    "escalate_human": {"tone": None,               "channel": None,                  "auto_send": False, "stop": True},
}


def decide_invoice_action(invoice: dict, predicted_bucket: str) -> dict:
    promise_date = invoice.get("promise_to_pay_date")
    if promise_date:
        return {
            "action": "await_promised_payment",
            "tone": None,
            "channel": None,
            "stop": False,
            "reasoning": f"Customer promised payment by {promise_date}. "
                         f"Holding off on escalation until that date passes.",
        }

    policy = INVOICE_POLICY.get(predicted_bucket)

    if policy is None:
        return {
            "action": "flag_for_human_review",
            "tone": None,
            "channel": None,
            "stop": True,
            "reasoning": f"Bucket '{predicted_bucket}' not recognized. "
                         f"Failing safe: no automated message sent.",
        }

    if policy["stop"]:
        return {
            "action": "escalate_to_human",
            "tone": None,
            "channel": None,
            "stop": True,
            "reasoning": f"Bucket='{predicted_bucket}' (days_overdue="
                         f"{invoice['days_overdue']}): hard stop rule - "
                         f"invoice is severely overdue (35+ days). "
                         f"Auto-messaging halted, routed to human "
                         f"collections review.",
        }

    return {
        "action": "send_message",
        "tone": policy["tone"],
        "channel": policy["channel"],
        "stop": False,
        "reasoning": f"Bucket='{predicted_bucket}' (days_overdue="
                     f"{invoice['days_overdue']}): sending "
                     f"'{policy['tone']}' via {policy['channel']} "
                     f"per the escalation ladder.",
    }
