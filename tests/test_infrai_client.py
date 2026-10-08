import httpx
import pytest

from logistics_notify.infrai_client import InfraiError, InfraiRealtimeClient


def test_client_decodes_business_rejection_before_http_status() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "ok": False,
                "data": None,
                "error": {"code": "rejected", "message": "Request rejected"},
                "metadata": {},
            },
        )

    client = InfraiRealtimeClient("test-key", transport=httpx.MockTransport(reject))
    with pytest.raises(InfraiError) as caught:
        client.create_channel("logistics:ops:shipments", "channel:ops")

    assert caught.value.code == "rejected"
    assert caught.value.status_code == 400
    client.close()


def test_client_honors_retry_after_for_rate_limit() -> None:
    attempts = 0
    delays: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ok": False, "data": None, "error": {}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"published": True}, "error": None, "metadata": {}},
        )

    client = InfraiRealtimeClient(
        "test-key", transport=httpx.MockTransport(respond), sleep=delays.append
    )
    result = client.publish(
        channel="logistics:ops:shipments",
        event="shipment.updated",
        data={"shipment_id": "SHP-1"},
        account_id="ops",
        idempotency_key="shipment-event:evt-1",
    )

    assert result == {"published": True}
    assert attempts == 2
    assert delays == [2.0]
    client.close()
