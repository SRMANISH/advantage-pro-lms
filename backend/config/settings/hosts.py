"""Host-list helpers shared by settings modules."""

from collections.abc import Iterable

DEV_ALLOWED_HOSTS = ("localhost", "127.0.0.1")
_DEV_ALLOWED_HOSTS = set(DEV_ALLOWED_HOSTS)


def normalize_allowed_hosts(*host_groups: str | Iterable[str] | None) -> list[str]:
    """Return a trimmed, de-duplicated list of Django host names."""
    hosts: list[str] = []
    seen: set[str] = set()

    for group in host_groups:
        if not group:
            continue

        values = group.split(",") if isinstance(group, str) else group
        for value in values:
            if value is None:
                continue
            host = str(value).strip()
            if host and host not in seen:
                hosts.append(host)
                seen.add(host)

    return hosts


def is_missing_or_dev_default(hosts: Iterable[str]) -> bool:
    """Whether a production host list is empty or only the local-dev defaults."""
    normalized = normalize_allowed_hosts(hosts)
    return not normalized or set(normalized).issubset(_DEV_ALLOWED_HOSTS)
