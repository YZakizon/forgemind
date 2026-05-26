import asyncio

import pytest
from fastapi import HTTPException

from app.main import archive_memories, export_user_data, login
from app.services.auth import DEMO_USER_ID, issue_access_token
from app.schemas import AuthProvider, AuthRequest, DataControlResponse, UserDataExport
from app.services import store


def bearer(user_id: str = DEMO_USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def test_data_controls_require_authentication():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(export_user_data(DEMO_USER_ID, authorization=None))
    assert exc.value.status_code == 401


def test_data_controls_reject_mismatched_user(monkeypatch):
    async def fake_export(user_id: str) -> UserDataExport:
        return UserDataExport(user_id=user_id)

    monkeypatch.setattr(store, "export_user_data", fake_export)

    other_user = "00000000-0000-4000-8000-000000000002"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(export_user_data(DEMO_USER_ID, authorization=bearer(other_user)["Authorization"]))

    assert exc.value.status_code == 403


def test_data_controls_allow_matching_token(monkeypatch):
    async def fake_archive(user_id: str) -> int:
        assert user_id == DEMO_USER_ID
        return 2

    monkeypatch.setattr(store, "archive_user_memories", fake_archive)

    response = asyncio.run(archive_memories(DEMO_USER_ID, authorization=bearer()["Authorization"]))

    assert isinstance(response, DataControlResponse)
    assert response.detail == "Archived 2 active memories."


def test_demo_login_issues_demo_user_token(monkeypatch):
    async def fake_upsert_user(**kwargs) -> None:
        return None

    monkeypatch.setattr(store, "upsert_user", fake_upsert_user)

    response = asyncio.run(login(AuthRequest(provider=AuthProvider.google, identity_token="demo-token")))

    assert response.user_id == DEMO_USER_ID
