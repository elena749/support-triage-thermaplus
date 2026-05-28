# INPUT_EXAMPLES.md

## Valid example 1
```json
{
  "ticket_id": "TH-2026-04321",
  "subject": "No heating since last night",
  "body": "Hello, the radiators are cold and we have no hot water since 22:00. Two small children are in the flat.",
  "sender_email": "anna@example.com",
  "sender_name": "Anna Keller",
  "customer_id": "CUST-18373",
  "customer_type": "private",
  "customer_tier": "B",
  "received_at": "2026-05-28T00:45:00Z",
  "channel": "email",
  "language": "en",
  "building_type": "multi_family",
  "occupant_flags": ["child_present"]
}
```

## Valid example 2
```json
{
  "ticket_id": "TH-2026-04322",
  "subject": "Heizung ausgefallen in drei Objekten",
  "body": "Wir verwalten drei Gebäude. In zwei Häusern gibt es kein Warmwasser, im dritten fällt die Heizung aus.",
  "customer_id": "CUST-90012",
  "customer_type": "business",
  "customer_tier": "A",
  "received_at": "2026-05-28T01:02:00Z",
  "channel": "webform",
  "language": "de",
  "property_count": 3,
  "building_type": "multi_family"
}
```

## Invalid example 1 — missing ticket_id
```json
{
  "subject": "No heating",
  "body": "Please help.",
  "customer_type": "private",
  "customer_tier": "B",
  "received_at": "2026-05-28T00:45:00Z",
  "channel": "email"
}
```

## Invalid example 2 — bad enum
```json
{
  "ticket_id": "TH-2026-04323",
  "subject": "Heating problem",
  "body": "It is cold.",
  "customer_type": "vip",
  "customer_tier": "B",
  "received_at": "2026-05-28T00:45:00Z",
  "channel": "email"
}
```

## Invalid example 3 — empty body
```json
{
  "ticket_id": "TH-2026-04324",
  "subject": "Empty",
  "body": "",
  "customer_type": "private",
  "customer_tier": "C",
  "received_at": "2026-05-28T00:45:00Z",
  "channel": "chat"
}
```