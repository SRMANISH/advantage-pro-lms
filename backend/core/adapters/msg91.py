"""MSG91 SMS adapter.

Uses MSG91's classic `sendsms` HTTP API (stable, non-template contract that maps
directly onto SmsAdapter.send(to, message)). If your MSG91 account is on DLT/Flow-only
routing, verify the endpoint/params against your MSG91 dashboard — templated flows need
a ``flow_id`` and template variables this simple adapter does not carry.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from .base import SmsAdapter

logger = logging.getLogger("lms.adapters")

_SEND_URL = "https://api.msg91.com/api/v2/sendsms"


class Msg91SmsAdapter(SmsAdapter):
    def send(self, to: str, message: str) -> None:
        if not to:
            return
        auth_key = getattr(settings, "MSG91_AUTH_KEY", "")
        sender = getattr(settings, "MSG91_SENDER_ID", "")
        route = getattr(settings, "MSG91_ROUTE", "4")
        country = getattr(settings, "MSG91_COUNTRY", "91")
        if not auth_key or not sender:
            logger.warning("MSG91_AUTH_KEY/MSG91_SENDER_ID not configured — SMS not sent to %s", to)
            return
        payload = {
            "sender": sender,
            "route": route,
            "country": country,
            "sms": [{"message": message, "to": [to.lstrip("+")]}],
        }
        try:
            resp = requests.post(
                _SEND_URL,
                json=payload,
                headers={"authkey": auth_key, "Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("MSG91 send failed (%s): %s", resp.status_code, resp.text[:300])
        except requests.RequestException:
            logger.exception("MSG91 request failed for %s", to)
