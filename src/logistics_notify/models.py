from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ShipmentEventType(StrEnum):
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class ProofOfDelivery(BaseModel):
    object_key: str = Field(min_length=1)
    download_url: HttpUrl
    content_type: str = Field(min_length=1)
    checksum_sha256: str = Field(min_length=64, max_length=64)


class ShipmentEvent(BaseModel):
    event_id: str = Field(min_length=1)
    shipment_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    occurred_at: datetime
    event_type: ShipmentEventType
    location: str | None = None
    exception_reason: str | None = None
    proof: ProofOfDelivery | None = None

    @model_validator(mode="after")
    def validate_event_details(self) -> "ShipmentEvent":
        if self.event_type is ShipmentEventType.EXCEPTION and not self.exception_reason:
            raise ValueError("exception_reason is required for exception events")
        if self.event_type is not ShipmentEventType.DELIVERED and self.proof is not None:
            raise ValueError("proof is accepted only for delivered events")
        return self


class NotificationPlan(BaseModel):
    channel: str
    event: str
    priority: str
    data: dict[str, object]


class PublishReceipt(BaseModel):
    event_id: str
    channel: str
    notification_event: str
    published: bool
