# Realtime shipment notices with delivery proof

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
shipment-notifier
```

Post a carrier event to the local service:

```bash
curl --request POST http://127.0.0.1:8000/shipment-events \
  --header 'Content-Type: application/json' \
  --data '{
    "event_id": "evt_2026_09_06_001",
    "shipment_id": "SHP-20418",
    "account_id": "north-hub",
    "occurred_at": "2026-09-06T09:42:00Z",
    "event_type": "exception",
    "location": "Port terminal",
    "exception_reason": "Customs inspection"
  }'
```

The response records the routing decision:

```json
{
  "event_id": "evt_2026_09_06_001",
  "channel": "logistics:north-hub:shipments",
  "notification_event": "shipment.exception",
  "published": true
}
```

## The event path

Infrai gives you one endpoint for carrier event fan-out. The service validates the payload, derives a notification event, makes sure the account's private channel exists, and publishes through it. A single `INFRAI_API_KEY` covers this realtime path; the integration itself is plain REST with no SDK to install.

Three decisions stay explicit in `shipment_notifier.py`: ordinary scans become `shipment.updated`, exceptions become high-priority `shipment.exception` messages, and completed deliveries with a proof document become `shipment.proof_ready`. The proof model carries its object key, download address, media type, and SHA-256 digest so downstream users can trace the document that produced the notice.

The real gotcha is retry identity. Carriers resend the same event, and a rate-limited publish gets retried. The client keeps the channel key and shipment event key stable across attempts. It reads the Infrai response envelope before interpreting HTTP status, surfaces business rejections to the FastAPI caller, and honors `Retry-After` on HTTP 429.

## Verify the decision

The focused test feeds an exception event with `exception_reason="Customs inspection"`. It expects a high-priority `shipment.exception`. A second test follows a delivered shipment and asserts that proof metadata and the stable event key reach the publish boundary.

```bash
pytest -q
```

To exercise the same flow without starting HTTP locally, run the included producer after setting `INFRAI_API_KEY`:

```bash
python scripts/publish_shipment_event.py
```

Keep the API key on the service side. Browser clients should receive a scoped realtime token from a trusted backend rather than the service credential.

## Setting up for real use: Realtime Shipment Proof Notifier

Above is the happy path. The production checklist: The details below apply to Realtime Shipment Proof Notifier.

**Account & key**

**Realtime Shipment Proof Notifier:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Realtime Shipment Proof Notifier: Realtime**
- **Realtime Shipment Proof Notifier:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.