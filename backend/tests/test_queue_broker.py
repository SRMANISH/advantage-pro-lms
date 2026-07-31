"""The task queue's broker is the database, and that is load-bearing.

``django_q.brokers.get_broker`` tests ``Conf.ORM`` before ``Conf.REDIS``, so ``Q_CLUSTER["orm"]``
wins unconditionally and a ``redis`` key alongside it is never read. One used to be built from
REDIS_URL; it was dead config that made the settings, DEPLOYMENT.md and the compose file all
describe a Redis-backed queue that did not exist.

Keeping the ORM broker is a deliberate correctness choice, not inertia: enqueueing writes a row
through the same connection, so a task queued inside ``transaction.atomic()`` is rolled back
with it. Notifications *are* sent from inside atomic blocks and none of those sites wrap the
send in ``on_commit`` — under a Redis broker every rollback would leave an email or SMS queued
for work that never happened. These tests exist so that swapping the broker fails here, loudly,
rather than silently in production months later.
"""

import pytest
from django.conf import settings
from django.db import transaction

from core.roles import Role
from notifications.models import Notification

from .helpers import user


def test_queue_is_database_backed_not_redis():
    assert settings.Q_CLUSTER["orm"] == "default"
    assert "redis" not in settings.Q_CLUSTER, (
        "A 'redis' key here is dead config — get_broker() checks ORM first, so it would "
        "never be read while 'orm' is set. It previously misled every deployment doc."
    )


@pytest.mark.django_db
def test_the_configured_broker_really_is_the_orm_one(settings):
    """Assert against django-q2's own resolution rather than restating our config.

    A future django-q2 release could reorder that precedence; this catches it. The db mark is
    needed because the ORM broker opens a database connection on construction — which is the
    point: a Redis broker would not.
    """
    settings.Q_CLUSTER = {**settings.Q_CLUSTER, "sync": False}
    from django_q.brokers import get_broker

    broker = get_broker()
    assert type(broker).__module__ == "django_q.brokers.orm", type(broker).__module__


def test_retry_exceeds_timeout():
    """If retry <= timeout, django-q2 re-queues a task that is still running — every slow
    notification would be delivered twice."""
    assert settings.Q_CLUSTER["retry"] > settings.Q_CLUSTER["timeout"]


@pytest.mark.django_db(transaction=True)
def test_a_notification_queued_in_a_rolled_back_block_is_discarded():
    """The property the ORM broker is being kept for.

    ``transaction=True`` so the rollback is real rather than nested in the test's own
    transaction.
    """
    from notifications.services import notify

    student = user("q_rollback", Role.STUDENT)

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with transaction.atomic():
            notify(student, "test_kind", "should not survive", channels=("in_app",))
            assert Notification.objects.filter(recipient=student).exists()  # visible inside
            raise Boom

    # The in-app row went with the rollback; nothing was left half-committed.
    assert not Notification.objects.filter(recipient=student).exists()
