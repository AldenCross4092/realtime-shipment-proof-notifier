import os

import uvicorn
from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiError, InfraiRealtimeClient, InfraiTransportError
from .models import PublishReceipt, ShipmentEvent
from .shipment_notifier import notify_shipment


app = FastAPI(title="Shipment event notifier")


def get_client() -> InfraiRealtimeClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiRealtimeClient(api_key)


@app.post("/shipment-events", response_model=PublishReceipt)
def publish_shipment_event(shipment: ShipmentEvent) -> PublishReceipt:
    client = get_client()
    try:
        return notify_shipment(shipment, client)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        client.close()


def run() -> None:
    uvicorn.run("logistics_notify.service:app", host="127.0.0.1", port=8000)
