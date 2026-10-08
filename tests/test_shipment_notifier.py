from datetime import datetime, timezone

from logistics_notify.models import ProofOfDelivery, ShipmentEvent, ShipmentEventType
from logistics_notify.shipment_notifier import notify_shipment, plan_notification


class RecordingClient:
    def __init__(self) -> None:
        self.channel_calls: list[tuple[str, str]] = []
        self.publish_calls: list[dict[str, object]] = []

    def create_channel(self, channel: str, idempotency_key: str) -> dict[str, object]:
        self.channel_calls.append((channel, idempotency_key))
        return {"channel": channel}

    def publish(self, **values: object) -> dict[str, object]:
        self.publish_calls.append(values)
        return {"published": True}


def shipment(event_type: ShipmentEventType, **values: object) -> ShipmentEvent:
    return ShipmentEvent(
        event_id="evt-44",
        shipment_id="SHP-20418",
        account_id="north-hub",
        occurred_at=datetime(2026, 9, 6, 9, 42, tzinfo=timezone.utc),
        event_type=event_type,
        **values,
    )


def test_exception_becomes_high_priority_operator_notification() -> None:
    plan = plan_notification(
        shipment(ShipmentEventType.EXCEPTION, exception_reason="Customs inspection")
    )

    assert plan.event == "shipment.exception"
    assert plan.priority == "high"
    assert plan.data["reason"] == "Customs inspection"


def test_delivery_proof_is_published_once_with_event_idempotency() -> None:
    client = RecordingClient()
    event = shipment(
        ShipmentEventType.DELIVERED,
        proof=ProofOfDelivery(
            object_key="pod/SHP-20418/receipt.pdf",
            download_url="https://files.example.test/pod/SHP-20418",
            content_type="application/pdf",
            checksum_sha256="b" * 64,
        ),
    )

    receipt = notify_shipment(event, client)  # type: ignore[arg-type]

    assert receipt.notification_event == "shipment.proof_ready"
    assert client.channel_calls == [
        ("logistics:north-hub:shipments", "channel:logistics:north-hub:shipments")
    ]
    assert client.publish_calls[0]["idempotency_key"] == "shipment-event:evt-44"
    assert client.publish_calls[0]["data"]["proof"]["object_key"] == "pod/SHP-20418/receipt.pdf"  # type: ignore[index]
