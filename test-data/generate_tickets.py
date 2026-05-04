"""
Generate individual ticket JSON files and ground_truth.json
from test-data/tickets_brainstorm.md
"""

import json
import re
from pathlib import Path

BRAINSTORM = Path("test-data/tickets_brainstorm.md")
TICKETS_DIR = Path("test-data/tickets")
GROUND_TRUTH = Path("test-data/ground_truth.json")


def parse_brainstorm(text):
    sections = re.split(r"\n## TH-", text)[1:]
    tickets = []

    for section in sections:
        section = "## TH-" + section

        ticket_id_match = re.search(r"## (TH-\d{4}-\d{5})", section)
        if not ticket_id_match:
            continue
        ticket_id = ticket_id_match.group(1)

        severity = re.search(r"severity=(\w+)", section)
        intent = re.search(r"intent=(\w+)", section)
        edge_case = re.search(r"\*\*Edge case:\*\*\s*(.+?)(?:\n|$)", section)

        def field(name):
            pattern = rf"-\s*{name}:\s*\"?(.+?)\"?\s*\n"
            m = re.search(pattern, section)
            return m.group(1).strip().strip('"') if m else None

        subject = field("subject")
        body = field("body")
        sender_email = field("sender_email")
        sender_name = field("sender_name")
        received_at = field("received_at")

        combined = re.search(
            r"-\s*customer_type:\s*(\w+),\s*customer_tier:\s*(\w+),\s*channel:\s*(\w+)",
            section,
        )
        if combined:
            customer_type = combined.group(1)
            customer_tier = combined.group(2)
            channel = combined.group(3)
        else:
            customer_type = field("customer_type")
            customer_tier = field("customer_tier")
            channel = field("channel")

        customer_id = "CUST-" + ticket_id.split("-")[-1]

        ticket = {
            "ticket_id": ticket_id,
            "subject": subject,
            "body": body,
            "sender_email": sender_email,
            "customer_id": customer_id,
            "customer_type": customer_type,
            "customer_tier": customer_tier,
            "received_at": received_at,
            "channel": channel,
        }
        if sender_name:
            ticket["sender_name"] = sender_name

        ticket = {k: v for k, v in ticket.items() if v is not None}

        ground = {
            "expected_severity": severity.group(1) if severity else None,
            "expected_intent": intent.group(1) if intent else None,
            "edge_case": edge_case.group(1).strip() if edge_case else None,
        }

        tickets.append((ticket_id, ticket, ground))

    return tickets


def main():
    text = BRAINSTORM.read_text(encoding="utf-8")
    tickets = parse_brainstorm(text)

    TICKETS_DIR.mkdir(parents=True, exist_ok=True)

    ground_truth = {}
    for i, (ticket_id, ticket, ground) in enumerate(tickets, start=1):
        path = TICKETS_DIR / f"ticket_{i:03d}.json"
        path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        ground_truth[ticket_id] = ground

    GROUND_TRUTH.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Generated {len(tickets)} ticket files in {TICKETS_DIR}/")
    print(f"Ground truth written to {GROUND_TRUTH}")


if __name__ == "__main__":
    main()
