"""Integration adapters (ports & adapters).

External services (storage, email, SMS, WhatsApp, scheduler) sit behind the interfaces
in ``base``. Concrete implementations are selected at runtime from settings via
``registry`` — swap a dotted path in the environment to plug in Hostinger or a 3rd-party
provider without touching call sites.
"""
