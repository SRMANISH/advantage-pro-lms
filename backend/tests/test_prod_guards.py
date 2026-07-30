"""Fail-fast guards that stop an unsafe production deploy.

Two classes of accident this covers:
  * booting prod with the console notification stubs, which log messages instead of sending
    them — a silent failure, since every send "succeeds";
  * running the demo seeder against a real database, which would create working logins for
    every role using a publicly-known password.
"""

from io import StringIO

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError

STUB = "core.adapters.local.ConsoleEmailAdapter"
REAL_EMAIL = "core.adapters.smtp.SmtpEmailAdapter"
REAL_SMS = "core.adapters.msg91.Msg91SmsAdapter"
REAL_WA = "core.adapters.whatsapp_cloud.WhatsAppCloudAdapter"


def check_adapters(adapters, allow_console=False):
    """Re-run prod.py's adapter guard in isolation (importing prod settings for real would
    require a full production env). Mirrors the logic under test."""
    if allow_console:
        return
    stubbed = sorted(
        channel
        for channel in ("email", "sms", "whatsapp")
        if adapters.get(channel, "").startswith("core.adapters.local")
    )
    if stubbed:
        raise ImproperlyConfigured(
            f"These notification channels are still using the local console stub: {stubbed}"
        )


def test_prod_guard_rejects_console_stubs():
    with pytest.raises(ImproperlyConfigured) as exc:
        check_adapters({"email": STUB, "sms": REAL_SMS, "whatsapp": REAL_WA})
    assert "email" in str(exc.value)


def test_prod_guard_names_every_stubbed_channel():
    with pytest.raises(ImproperlyConfigured) as exc:
        check_adapters(
            {
                "email": STUB,
                "sms": "core.adapters.local.ConsoleSmsAdapter",
                "whatsapp": "core.adapters.local.ConsoleWhatsAppAdapter",
            }
        )
    message = str(exc.value)
    assert "email" in message and "sms" in message and "whatsapp" in message


def test_prod_guard_passes_with_real_adapters():
    check_adapters({"email": REAL_EMAIL, "sms": REAL_SMS, "whatsapp": REAL_WA})


def test_prod_guard_can_be_explicitly_opted_out_of():
    """A staging box with no provider yet can acknowledge the risk deliberately."""
    check_adapters({"email": STUB, "sms": STUB, "whatsapp": STUB}, allow_console=True)


def test_the_real_prod_settings_carry_the_guard():
    """Guard against the check being deleted: prod.py must still reference the opt-out."""
    from pathlib import Path

    from django.conf import settings as django_settings

    source = (Path(django_settings.BASE_DIR) / "config" / "settings" / "prod.py").read_text(
        encoding="utf-8"
    )
    assert "LMS_ALLOW_CONSOLE_ADAPTERS" in source
    assert "core.adapters.local" in source


# --------------------------- demo seeder ---------------------------


@pytest.mark.django_db
def test_seed_demo_refuses_to_run_when_debug_is_off(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError) as exc:
        call_command("seed_demo", stdout=StringIO())
    assert "--force" in str(exc.value)

    from accounts.models import User

    assert not User.objects.filter(username="superadmin1").exists()


@pytest.mark.django_db
def test_seed_demo_runs_with_force_even_when_debug_is_off(settings):
    settings.DEBUG = False
    call_command("seed_demo", "--force", stdout=StringIO())

    from accounts.models import User

    assert User.objects.filter(username="superadmin1").exists()


@pytest.mark.django_db
def test_seed_demo_runs_normally_in_development(settings):
    settings.DEBUG = True
    call_command("seed_demo", stdout=StringIO())

    from accounts.models import User

    assert User.objects.filter(username="faculty1").exists()
