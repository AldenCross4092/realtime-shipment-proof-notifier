from .infrai_client import InfraiRealtimeClient
from .models import NotificationPlan, PublishReceipt, ShipmentEvent, ShipmentEventType


def plan_notification(shipment: ShipmentEvent) -> NotificationPlan:
    channel = f"logistics:{shipment.account_id}:shipments"
    data: dict[str, object] = {
        "event_id": shipment.event_id,
        "shipment_id": shipment.shipment_id,
        "status": shipment.event_type.value,
        "occurred_at": shipment.occurred_at.isoformat(),
    }
    if shipment.location:
        data["location"] = shipment.location

    if shipment.event_type is ShipmentEventType.EXCEPTION:
        data["reason"] = shipment.exception_reason or ""
        return NotificationPlan(
            channel=channel,
            event="shipment.exception",
            priority="high",
            data=data,
        )

    if shipment.event_type is ShipmentEventType.DELIVERED and shipment.proof:
        data["proof"] = shipment.proof.model_dump(mode="json")
        return NotificationPlan(
            channel=channel,
            event="shipment.proof_ready",
            priority="normal",
            data=data,
        )

    return NotificationPlan(
        channel=channel,
        event="shipment.updated",
        priority="normal",
        data=data,
    )


def notify_shipment(
    shipment: ShipmentEvent, client: InfraiRealtimeClient
) -> PublishReceipt:
    plan = plan_notification(shipment)
    client.create_channel(plan.channel, f"channel:{plan.channel}")
    client.publish(
        channel=plan.channel,
        event=plan.event,
        data={**plan.data, "priority": plan.priority},
        account_id=shipment.account_id,
        idempotency_key=f"shipment-event:{shipment.event_id}",
    )
    return PublishReceipt(
        event_id=shipment.event_id,
        channel=plan.channel,
        notification_event=plan.event,
        published=True,
    )
