"""Resolve configured adapters from settings.LMS_ADAPTERS.

Call sites use ``get_storage()`` / ``get_email()`` / etc. and never import concrete
classes, so providers are swappable purely through configuration.
"""

from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string

from .base import EmailAdapter, SchedulerAdapter, SmsAdapter, StorageAdapter, WhatsAppAdapter


@cache
def _build(kind: str):
    dotted_path = settings.LMS_ADAPTERS[kind]
    return import_string(dotted_path)()


def get_storage() -> StorageAdapter:
    return _build("storage")


def get_email() -> EmailAdapter:
    return _build("email")


def get_sms() -> SmsAdapter:
    return _build("sms")


def get_whatsapp() -> WhatsAppAdapter:
    return _build("whatsapp")


def get_scheduler() -> SchedulerAdapter:
    return _build("scheduler")
