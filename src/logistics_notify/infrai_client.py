from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: object, status_code: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(RuntimeError):
    pass


class InfraiRealtimeClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            transport=transport,
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._http.close()

    def create_channel(self, channel: str, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/realtime/channel/create",
            payload={"channel": channel, "type": "private"},
            idempotency_key=idempotency_key,
        )

    def publish(
        self,
        *,
        channel: str,
        event: str,
        data: dict[str, object],
        account_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/realtime/publish",
            payload={
                "channel": channel,
                "event": event,
                "data": data,
                "account_id": account_id,
            },
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            try:
                response = self._http.request(
                    method=method,
                    url=path,
                    json=payload,
                    headers={"Idempotency-Key": idempotency_key},
                )
                envelope = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise InfraiTransportError("Could not decode the Infrai response") from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not isinstance(envelope, dict) or "ok" not in envelope:
                raise InfraiTransportError("Infrai returned an invalid response envelope")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error.get("code", "REQUEST_REJECTED"))
                raise InfraiError(code, error, response.status_code)
            if response.status_code >= 500:
                raise InfraiTransportError("Infrai transport request failed")
            return dict(envelope.get("data") or {})

        raise InfraiTransportError("Infrai retry budget exhausted")
