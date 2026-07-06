"""Meta WhatsApp Cloud API adapter.

Sends a free-form text message, which Meta only accepts within the 24h customer-service
session window (i.e. after the user has messaged your business number recently). Outside
that window, WhatsApp requires a pre-approved message *template* instead — configure
WHATSAPP_TEMPLATE_NAME to switch to template sends once you have one approved.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from .base import WhatsAppAdapter

logger = logging.getLogger("lms.adapters")


class WhatsAppCloudAdapter(WhatsAppAdapter):
    def send(self, to: str, message: str) -> None:
        if not to:
            return
        token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        phone_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        if not token or not phone_id:
            logger.warning(
                "WHATSAPP_ACCESS_TOKEN/WHATSAPP_PHONE_NUMBER_ID not configured — "
                "WhatsApp not sent to %s",
                to,
            )
            return
        template_name = getattr(settings, "WHATSAPP_TEMPLATE_NAME", "")
        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        body: dict[str, Any]
        if template_name:
            body = {
                "messaging_product": "whatsapp",
                "to": to.lstrip("+"),
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": getattr(settings, "WHATSAPP_TEMPLATE_LANG", "en")},
                    "components": [
                        {"type": "body", "parameters": [{"type": "text", "text": message}]}
                    ],
                },
            }
        else:
            body = {
                "messaging_product": "whatsapp",
                "to": to.lstrip("+"),
                "type": "text",
                "text": {"body": message},
            }
        try:
            resp = requests.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("WhatsApp send failed (%s): %s", resp.status_code, resp.text[:300])
        except requests.RequestException:
            logger.exception("WhatsApp request failed for %s", to)
