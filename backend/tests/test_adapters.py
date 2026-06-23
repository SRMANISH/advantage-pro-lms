"""The adapter registry must resolve configured providers and round-trip storage."""

import io
import shutil
from pathlib import Path

from core.adapters.base import EmailAdapter, SchedulerAdapter, StorageAdapter
from core.adapters.registry import get_email, get_scheduler, get_storage


def test_registry_resolves_configured_adapters():
    assert isinstance(get_storage(), StorageAdapter)
    assert isinstance(get_email(), EmailAdapter)
    assert isinstance(get_scheduler(), SchedulerAdapter)


def test_local_storage_round_trip(settings):
    # LocalStorageAdapter reads MEDIA_ROOT per call, so overriding it here is enough.
    media = Path(settings.BASE_DIR) / ".pytest_media"
    settings.MEDIA_ROOT = media
    try:
        storage = get_storage()
        storage.save("sample/hello.txt", io.BytesIO(b"hello world"))
        with storage.open("sample/hello.txt") as fh:
            assert fh.read() == b"hello world"
        storage.delete("sample/hello.txt")
        assert not (media / "sample" / "hello.txt").exists()
    finally:
        shutil.rmtree(media, ignore_errors=True)
