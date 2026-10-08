import json
import os

from logistics_notify.infrai_client import InfraiRealtimeClient
from logistics_notify.models import ShipmentEvent
from logistics_notify.shipment_notifier import notify_shipment


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this script")

    shipment = ShipmentEvent.model_validate(
        {
            "event_id": "evt_2026_09_06_001",
            "shipment_id": "SHP-20418",
            "account_id": "north-hub",
            "occurred_at": "2026-09-06T09:42:00Z",
            "event_type": "delivered",
            "location": "Dock 7",
            "proof": {
                "object_key": "pod/SHP-20418/signed-receipt.pdf",
                "download_url": "https://files.example.test/pod/SHP-20418",
                "content_type": "application/pdf",
                "checksum_sha256": "a" * 64,
            },
        }
    )
    client = InfraiRealtimeClient(api_key)
    try:
        receipt = notify_shipment(shipment, client)
        print(json.dumps(receipt.model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
