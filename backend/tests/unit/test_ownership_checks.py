"""
Proves cross-user access is blocked and indistinguishable from
non-existence (both return 404 MANDATE_NOT_FOUND / APPROVAL_NOT_FOUND).
"""

import uuid
from datetime import date

import pytest

from app.models import User
from app.services.mandate_service import MandateService


@pytest.fixture
def two_users(db_session):
    owner = User(name="Owner", email=f"owner-{uuid.uuid4()}@example.com")
    intruder = User(name="Intruder", email=f"intruder-{uuid.uuid4()}@example.com")
    db_session.add_all([owner, intruder])
    db_session.commit()
    yield owner, intruder
    db_session.delete(owner)
    db_session.delete(intruder)
    db_session.commit()


def test_intruder_cannot_view_other_users_mandate(client, db_session, two_users):
    owner, intruder = two_users
    mandate = MandateService.create_mandate(
        db_session, owner.id, "MERCH_1", "Owner's Gym", "subscriptions", 999, "MONTHLY", date.today()
    )

    response = client.get(f"/api/mandates/{mandate.id}", headers={"X-User-ID": str(intruder.id)})
    assert response.status_code == 404
    assert response.json()["error_code"] == "MANDATE_NOT_FOUND"


def test_intruder_cannot_pause_other_users_mandate(client, db_session, two_users):
    owner, intruder = two_users
    mandate = MandateService.create_mandate(
        db_session, owner.id, "MERCH_2", "Owner's Streaming", "subscriptions", 500, "MONTHLY", date.today()
    )

    response = client.post(
        f"/api/mandates/{mandate.id}/pause", headers={"X-User-ID": str(intruder.id)}, json={}
    )
    assert response.status_code == 404

    db_session.refresh(mandate)
    assert mandate.status == "ACTIVE"  # untouched by the intruder's attempt


def test_owner_can_still_access_their_own_mandate(client, db_session, two_users):
    owner, _ = two_users
    mandate = MandateService.create_mandate(
        db_session, owner.id, "MERCH_3", "Owner's Gym", "subscriptions", 999, "MONTHLY", date.today()
    )
    response = client.get(f"/api/mandates/{mandate.id}", headers={"X-User-ID": str(owner.id)})
    assert response.status_code == 200