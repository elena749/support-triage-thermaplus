# INPUT_TESTS.md

- Missing `ticket_id` -> reject.
- Empty `subject` -> reject.
- Empty `body` -> reject.
- Invalid `sender_email` format -> reject if present.
- Invalid `customer_type` enum -> reject.
- Invalid `customer_tier` enum -> reject.
- Invalid `received_at` format -> reject.
- Unknown `channel` -> reject.
- Unexpected extra field with `additionalProperties: false` -> reject [web:291][web:297].
- Non-object JSON payload -> reject.